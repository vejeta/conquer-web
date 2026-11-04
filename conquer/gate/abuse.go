// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

// Defences of the sign-up page against a script that fills the queue:
//
//   - formTokens: the sign-up form asks GET /join/api/token when it opens
//     and sends the answer back in the X-Form-Token header. The token is
//     the time it was issued, signed (HMAC) together with the client
//     address; a request whose token is missing, forged, from another
//     address, too old, or younger than the minimum fill time is a script
//     (or a very fast robot) and is dropped without telling it so.
//   - a honeypot: an input called "website" that people never see. A
//     request that fills it is dropped the same way.
//   - expiry of requests nobody decided (gate.expire).
//
// "Dropped" means the visitor gets the same answer as for a real request
// ({"ok":true,"status":"pending"}) and nothing is created, so a script
// cannot tell it has been caught. The refusal is logged.

import (
	"context"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	defaultMinFill       = 3 * time.Second
	defaultDailyPerIP    = 3
	defaultExpireDays    = 30
	tokenMaxAge          = 48 * time.Hour
	tokenHeader          = "X-Form-Token"
	expireFirstRunAfter  = 2 * time.Minute
	expireInterval       = 24 * time.Hour
	secretFileName       = ".gate-secret"
	pendingHelperTimeout = 60 * time.Second
)

// formTokens issues and checks the timestamps of the sign-up form
type formTokens struct {
	secret  []byte
	minFill time.Duration // 0 turns the check off
	maxAge  time.Duration
	now     func() time.Time
}

func newFormTokens(secret []byte, minFill time.Duration) *formTokens {
	return &formTokens{secret: secret, minFill: minFill, maxAge: tokenMaxAge, now: time.Now}
}

func (f *formTokens) mac(stamp, ip string) string {
	h := hmac.New(sha256.New, f.secret)
	h.Write([]byte("form|" + stamp + "|" + ip))
	return hex.EncodeToString(h.Sum(nil))
}

// issue gives ip a token that starts counting now
func (f *formTokens) issue(ip string) string {
	stamp := strconv.FormatInt(f.now().Unix(), 10)
	return stamp + "." + f.mac(stamp, ip)
}

// check says whether token was issued to ip, no more than maxAge and at
// least minFill ago; the reason is for the log
func (f *formTokens) check(token, ip string) (ok bool, reason string) {
	if f.minFill <= 0 {
		return true, ""
	}
	stamp, sum, found := strings.Cut(token, ".")
	if !found {
		return false, "no form token"
	}
	if !hmac.Equal([]byte(sum), []byte(f.mac(stamp, ip))) {
		return false, "bad form token"
	}
	secs, err := strconv.ParseInt(stamp, 10, 64)
	if err != nil {
		return false, "bad form token"
	}
	age := f.now().Sub(time.Unix(secs, 0))
	switch {
	case age < f.minFill:
		return false, fmt.Sprintf("form filled in %.1fs", age.Seconds())
	case age > f.maxAge:
		return false, "form token too old"
	}
	return true, ""
}

// loadSecret reads the signing key from path, or makes one and keeps it
// there so that a restart of the gate does not void forms people have open;
// a key that cannot be kept lives only until the next start
func loadSecret(path string) []byte {
	if data, err := os.ReadFile(path); err == nil {
		if key, err := hex.DecodeString(strings.TrimSpace(string(data))); err == nil && len(key) >= 32 {
			return key
		}
	}
	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		log.Fatalf("no random numbers: %v", err)
	}
	if err := os.WriteFile(path, []byte(hex.EncodeToString(key)+"\n"), 0o600); err != nil {
		log.Printf("the form key is not kept (%v): forms open during a restart are dropped", err)
	}
	return key
}

// envInt reads a whole number setting; empty or malformed gives def
func envInt(name string, def int) int {
	v := strings.TrimSpace(os.Getenv(name))
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil || n < 0 {
		log.Printf("%s=%q is not a whole number: using %d", name, v, def)
		return def
	}
	return n
}

// token answers the form's GET /join/api/token
func (g *gate) token(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET")
		fail(w, http.StatusMethodNotAllowed, "method")
		return
	}
	reply(w, http.StatusOK, map[string]any{"ok": true, "token": g.tokens.issue(clientIP(r))})
}

// scrub removes the email address and the message that older versions
// kept with each pending request (conquer-signup scrub); it returns how
// many requests it changed
func (g *gate) scrub(ctx context.Context) (int, error) {
	ctx, cancel := context.WithTimeout(ctx, pendingHelperTimeout)
	defer cancel()
	out, err := g.runHelper(ctx, "", "scrub")
	if err != nil {
		return 0, fmt.Errorf("%v: %s", err, out)
	}
	lines := strings.Split(out, "\n")
	n, _ := strconv.Atoi(strings.TrimSpace(lines[len(lines)-1]))
	return n, nil
}

// expire removes the requests nobody decided in days days, with their
// accounts (conquer-signup expire); it returns the account names
func (g *gate) expire(ctx context.Context, days int) ([]string, error) {
	ctx, cancel := context.WithTimeout(ctx, pendingHelperTimeout)
	defer cancel()
	out, err := g.runHelper(ctx, "", "expire", strconv.Itoa(days))
	if err != nil {
		return nil, fmt.Errorf("%v: %s", err, out)
	}
	var names []string
	for _, line := range strings.Split(out, "\n") {
		if line = strings.TrimSpace(line); accountRe.MatchString(line) {
			names = append(names, line)
		}
	}
	return names, nil
}

// expireOnce runs expire and logs what it did
func (g *gate) expireOnce(days int) {
	names, err := g.expire(context.Background(), days)
	if err != nil {
		log.Printf("expire: failed: %v", err)
		return
	}
	for _, name := range names {
		log.Printf("expire: request of account %s older than %d days removed", name, days)
	}
}

// expireLoop expires old requests shortly after the start and then every
// day; it never returns
func (g *gate) expireLoop(days int, first, every time.Duration) {
	time.Sleep(first)
	for {
		g.expireOnce(days)
		time.Sleep(every)
	}
}
