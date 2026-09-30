// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

// conquer-gate: the site's gate to the game. For now it creates player
// accounts from invite codes (the sign-up page, web/signup.html): a visitor
// with a valid code gets their own account, and the game opens the nation
// builder the first time they play. Without a code nothing is created and
// nobody reaches the game terminal.
//
// The files are changed by conquer-signup (a shell script next to the
// other account tools, under the same lock); this service only checks the
// request, limits how often each address may try, and reports the result.
//
// Endpoints:
//
//	POST /join/api/signup  {"code","account","password"}
//	                       -> {"ok":true,"account":...} or {"ok":false,"error":...}
//	GET  /join/api/health  -> "ok"
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"log"
	"net"
	"net/http"
	"net/url"
	"os/exec"
	"regexp"
	"strings"
	"sync"
	"time"
)

var (
	accountRe = regexp.MustCompile(`^[A-Za-z0-9_.-]{1,32}$`)
	codeRe    = regexp.MustCompile(`^[A-Z0-9]{4}-[A-Z0-9]{4}$`)
	// Names that must not become player accounts
	reserved = map[string]bool{"god": true, "root": true, "admin": true, "conquer": true, "join": true}
)

// Exit codes of conquer-signup
var helperErrors = map[int]string{
	2: "bad_code",
	3: "account_taken",
	4: "too_late",
	5: "closed",
}

// limiter allows each client address a number of events per window
type limiter struct {
	mu     sync.Mutex
	max    int
	window time.Duration
	seen   map[string][]time.Time
}

func newLimiter(max int, window time.Duration) *limiter {
	return &limiter{max: max, window: window, seen: map[string][]time.Time{}}
}

// allow records an event for key and says whether it is within the limit
func (l *limiter) allow(key string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := time.Now()
	var recent []time.Time
	for _, t := range l.seen[key] {
		if now.Sub(t) < l.window {
			recent = append(recent, t)
		}
	}
	if len(recent) >= l.max {
		l.seen[key] = recent
		return false
	}
	l.seen[key] = append(recent, now)
	return true
}

// full says whether key has used up its events, without recording one
func (l *limiter) full(key string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	n := 0
	for _, t := range l.seen[key] {
		if time.Since(t) < l.window {
			n++
		}
	}
	return n >= l.max
}

func (l *limiter) cleanup() {
	l.mu.Lock()
	defer l.mu.Unlock()
	for k, ts := range l.seen {
		if len(ts) == 0 || time.Since(ts[len(ts)-1]) >= l.window {
			delete(l.seen, k)
		}
	}
}

type gate struct {
	helper   string
	requests *limiter // any sign-up request
	failures *limiter // wrong invite codes: guessing is slow
}

// clientIP: the address Apache (the only client that can reach this
// service) adds last to X-Forwarded-For, else the connection's
func clientIP(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		parts := strings.Split(xff, ",")
		return strings.TrimSpace(parts[len(parts)-1])
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

// sameOrigin: a browser posting from another site is refused
func sameOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true
	}
	u, err := url.Parse(origin)
	if err != nil {
		return false
	}
	host := r.Header.Get("X-Forwarded-Host")
	if host == "" {
		host = r.Host
	}
	return strings.EqualFold(u.Host, strings.Split(host, ",")[0])
}

func reply(w http.ResponseWriter, status int, body map[string]any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func fail(w http.ResponseWriter, status int, code string) {
	reply(w, status, map[string]any{"ok": false, "error": code})
}

// normalizeCode accepts "k7qm 3xpa", "K7QM3XPA" and "K7QM-3XPA"
func normalizeCode(s string) string {
	s = strings.ToUpper(strings.Join(strings.Fields(s), ""))
	if len(s) == 8 && !strings.Contains(s, "-") {
		s = s[:4] + "-" + s[4:]
	}
	return s
}

func (g *gate) signup(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", "POST")
		fail(w, http.StatusMethodNotAllowed, "method")
		return
	}
	if !sameOrigin(r) {
		fail(w, http.StatusForbidden, "origin")
		return
	}
	ip := clientIP(r)
	if g.failures.full(ip) || !g.requests.allow(ip) {
		log.Printf("signup refused: too many attempts ip=%s", ip)
		fail(w, http.StatusTooManyRequests, "rate_limited")
		return
	}

	var in struct {
		Code     string `json:"code"`
		Account  string `json:"account"`
		Password string `json:"password"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 4096)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	code := normalizeCode(in.Code)
	account := strings.TrimSpace(in.Account)
	switch {
	case !codeRe.MatchString(code):
		g.failures.allow(ip)
		log.Printf("signup refused: malformed code ip=%s", ip)
		fail(w, http.StatusBadRequest, "bad_code")
		return
	case !accountRe.MatchString(account) || reserved[strings.ToLower(account)]:
		fail(w, http.StatusBadRequest, "bad_account")
		return
	case len(in.Password) < 8:
		fail(w, http.StatusBadRequest, "short_password")
		return
	case len(in.Password) > 128 || strings.ContainsAny(in.Password, "\r\n\x00"):
		fail(w, http.StatusBadRequest, "bad_password")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, g.helper, code, account)
	cmd.Stdin = strings.NewReader(in.Password + "\n")
	out, err := cmd.CombinedOutput()
	if err != nil {
		var exit *exec.ExitError
		if errors.As(err, &exit) {
			if reason, ok := helperErrors[exit.ExitCode()]; ok {
				if reason == "bad_code" {
					g.failures.allow(ip)
				}
				log.Printf("signup refused: %s account=%s ip=%s", reason, account, ip)
				status := http.StatusBadRequest
				if reason == "account_taken" {
					status = http.StatusConflict
				} else if reason == "too_late" || reason == "closed" {
					status = http.StatusForbidden
				}
				fail(w, status, reason)
				return
			}
		}
		log.Printf("signup failed: account=%s ip=%s: %v %s", account, ip, err, strings.TrimSpace(string(out)))
		fail(w, http.StatusInternalServerError, "server")
		return
	}
	log.Printf("signup: account %s created ip=%s", account, ip)
	reply(w, http.StatusOK, map[string]any{"ok": true, "account": account})
}

func main() {
	listen := flag.String("listen", ":7682", "address to listen on")
	helper := flag.String("signup", "/usr/local/bin/conquer-signup", "program that creates the account")
	flag.Parse()
	log.SetPrefix("[gate] ")
	log.SetFlags(0)

	g := &gate{
		helper:   *helper,
		requests: newLimiter(20, 10*time.Minute),
		failures: newLimiter(5, time.Hour),
	}
	go func() {
		for range time.Tick(10 * time.Minute) {
			g.requests.cleanup()
			g.failures.cleanup()
		}
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("/join/api/signup", g.signup)
	mux.HandleFunc("/join/api/health", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("ok\n"))
	})
	srv := &http.Server{
		Addr:              *listen,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       20 * time.Second,
		WriteTimeout:      30 * time.Second,
		MaxHeaderBytes:    16 << 10,
	}
	log.Printf("listening on %s", *listen)
	log.Fatal(srv.ListenAndServe())
}
