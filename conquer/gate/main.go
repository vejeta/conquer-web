// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

// conquer-gate: the site's gate to the game. Visitors ask for a seat on the
// sign-up page (web/signup.html): the account is created at once but stays
// pending until the administrator approves it at /admin/ (or the visitor
// brings a valid invite code, which approves it on the spot). The game
// opens the nation builder the first time an approved player plays.
// Without an approved account nobody reaches the game terminal.
//
// The files are changed by conquer-signup (a shell script next to the
// other account tools, under the same lock); this service only checks the
// request, limits how often each address may try, reports the result and
// tells the administrator (and the player) by email or webhook, see
// notify.go.
//
// Public endpoints:
//
//	POST /join/api/request {"account","password","email"?,"message"?,"lang"?,"code"?}
//	                       -> {"ok":true,"account":...,"status":"pending"|"approved"}
//	                          or {"ok":false,"error":...}
//	POST /join/api/signup  the same (old links)
//	GET  /join/api/token   -> {"ok":true,"token":...}, sent back by the form in X-Form-Token
//	GET  /join/api/health  -> "ok"
//
// Administrator endpoints (Apache signs the user in and sets
// X-WEBAUTH-USER; only accounts marked "*" in lib/.players may use them):
//
//	GET  /admin/api/state
//	POST /admin/api/approve {"account"}
//	POST /admin/api/reject  {"account"}
//	POST /admin/api/invite  {"count"}
//	POST /admin/api/assign  {"account", "nation" | "found" | "admin"}
package main

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

// After this turn a new nation starts late and the game's nation builder
// gives it extra points. Nobody is turned away: an approved account founds
// its nation at any turn (conqrun -A, no super user password)
const lastJoinTurn = 5

var (
	// The first character is a letter or digit: a name that starts with "-"
	// would be read as an option by htpasswd, and "." or ".." must never
	// become a directory name (the menu's practice world is named after it)
	accountRe = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$`)
	codeRe    = regexp.MustCompile(`^[A-Z0-9]{4}-[A-Z0-9]{4}$`)
	// A nation name (up to 9 characters), "+" (found one) or "*" (administrator)
	nationArgRe = regexp.MustCompile(`^([A-Za-z0-9_.-]{1,9}|[+*])$`)
	turnRe      = regexp.MustCompile(`(?m)^Conquer .*, Turn ([0-9]+)$`)
	// Names that must not become player accounts
	reserved = map[string]bool{"god": true, "root": true, "admin": true, "conquer": true, "join": true}
)

// Exit codes of conquer-signup
var helperErrors = map[int]string{
	2: "bad_code",
	3: "account_taken",
	5: "closed",
	6: "no_nation",
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
	lib      string // the world directory: .players, .requests, .invites
	htpasswd string
	conquer  string   // the game binary, to read the turn
	requests *limiter // any sign-up request
	failures *limiter // wrong invite codes: guessing is slow
	daily    *limiter // requests that made a pending account: few per address and day
	tokens   *formTokens
	reqMu    sync.Mutex // one request at a time between the e-mail check and the account
	admin    *limiter   // administrator actions
	notify   *notifier
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
	// Apache adds its own value last; whatever a client sent comes before
	parts := strings.Split(host, ",")
	return strings.EqualFold(u.Host, strings.TrimSpace(parts[len(parts)-1]))
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

// shortText: one line of at most max characters
func shortText(s string, max int) string {
	s = strings.Join(strings.Fields(s), " ")
	if r := []rune(s); len(r) > max {
		s = string(r[:max])
	}
	return s
}

// helperStatus maps a failed run of conquer-signup to an error code and
// HTTP status; ok is false when it failed for another reason
func helperStatus(err error, extra map[int]string) (reason string, status int, ok bool) {
	var exit *exec.ExitError
	if !errors.As(err, &exit) {
		return "", 0, false
	}
	reason, ok = extra[exit.ExitCode()]
	if !ok {
		reason, ok = helperErrors[exit.ExitCode()]
	}
	if !ok {
		return "", 0, false
	}
	status = http.StatusBadRequest
	switch reason {
	case "account_taken", "not_pending", "no_account":
		status = http.StatusConflict
	case "closed":
		status = http.StatusForbidden
	}
	return reason, status, true
}

// runHelper runs conquer-signup with args and the given standard input
func (g *gate) runHelper(ctx context.Context, stdin string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, g.helper, args...)
	if stdin != "" {
		cmd.Stdin = strings.NewReader(stdin)
	}
	out, err := cmd.CombinedOutput()
	return strings.TrimSpace(string(out)), err
}

// turn: the game's current turn, 0 when it cannot be read
func (g *gate) turn(ctx context.Context) int {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	out, err := exec.CommandContext(ctx, g.conquer, "-s").Output()
	if err != nil {
		return 0
	}
	if m := turnRe.FindSubmatch(out); m != nil {
		n, _ := strconv.Atoi(string(m[1]))
		return n
	}
	return 0
}

// nation is one nation of the world
type nation struct {
	Name    string  `json:"name"`
	Race    string  `json:"race"`
	Class   string  `json:"class"`
	Account *string `json:"account"`
}

// nations lists the nations of the world from "conquer -s" (id, name, race,
// class, alignment, score; monsters have no score row), the same source as
// status.json, each with the account assigned to it
func (g *gate) nations(ctx context.Context, marks map[string]string, accounts []string) []nation {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	list := []nation{}
	out, err := exec.CommandContext(ctx, g.conquer, "-s").Output()
	if err != nil {
		return list
	}
	owner := map[string]string{}
	for _, acc := range accounts {
		switch m := marks[acc]; m {
		case "", "*", "+", "?":
			// An account with no assignment opens the nation named like it
			if m == "" {
				owner[strings.ToLower(acc)] = acc
			}
		default:
			owner[strings.ToLower(m)] = acc
		}
	}
	for _, line := range strings.Split(string(out), "\n") {
		f := strings.Fields(line)
		if len(f) < 6 {
			continue
		}
		if _, err := strconv.Atoi(f[0]); err != nil {
			continue
		}
		if _, err := strconv.Atoi(f[5]); err != nil {
			continue
		}
		n := nation{Name: f[1], Race: f[2], Class: f[3]}
		if acc, ok := owner[strings.ToLower(f[1])]; ok {
			n.Account = &acc
		}
		list = append(list, n)
	}
	sort.SliceStable(list, func(i, j int) bool { return strings.ToLower(list[i].Name) < strings.ToLower(list[j].Name) })
	return list
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
		Email    string `json:"email"`
		Message  string `json:"message"`
		Lang     string `json:"lang"`
		Website  string `json:"website"` // the honeypot: people never see it
	}
	r.Body = http.MaxBytesReader(w, r.Body, 8192)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	account := strings.TrimSpace(in.Account)
	// A script is told its request was taken, and nothing is created
	if strings.TrimSpace(in.Website) != "" {
		log.Printf("signup dropped: honeypot filled account=%q ip=%s", shortText(account, 40), ip)
		reply(w, http.StatusOK, map[string]any{"ok": true, "account": account, "status": "pending"})
		return
	}
	if ok, why := g.tokens.check(r.Header.Get(tokenHeader), ip); !ok {
		log.Printf("signup dropped: %s account=%q ip=%s", why, shortText(account, 40), ip)
		reply(w, http.StatusOK, map[string]any{"ok": true, "account": account, "status": "pending"})
		return
	}
	code := ""
	if strings.TrimSpace(in.Code) != "" {
		code = normalizeCode(in.Code)
	}
	email := strings.TrimSpace(in.Email)
	message := shortText(in.Message, 500)
	lang := validLang(in.Lang)
	switch {
	case code != "" && !codeRe.MatchString(code):
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
	case len(in.Password) > 72 || strings.ContainsAny(in.Password, "\r\n\x00"):
		fail(w, http.StatusBadRequest, "bad_password")
		return
	case email != "" && !validEmail(email):
		fail(w, http.StatusBadRequest, "bad_email")
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	args := []string{"request", account, email, message, lang}
	status := "pending"
	if code != "" {
		args = []string{"invite", code, account}
		status = "approved"
	} else {
		// Pending accounts per address and day, and one request per
		// address of e-mail: the queue cannot be filled by one visitor
		if g.daily.full(ip) {
			log.Printf("signup refused: daily limit ip=%s", ip)
			fail(w, http.StatusTooManyRequests, "daily_limit")
			return
		}
		g.reqMu.Lock()
		defer g.reqMu.Unlock()
		if g.emailPending(email) {
			log.Printf("signup refused: e-mail already waiting account=%s ip=%s", account, ip)
			fail(w, http.StatusConflict, "email_pending")
			return
		}
	}
	out, err := g.runHelper(ctx, in.Password+"\n", args...)
	if err != nil {
		if reason, httpStatus, ok := helperStatus(err, nil); ok {
			if reason == "bad_code" {
				g.failures.allow(ip)
			}
			log.Printf("signup refused: %s account=%s ip=%s", reason, account, ip)
			fail(w, httpStatus, reason)
			return
		}
		log.Printf("signup failed: account=%s ip=%s: %v %s", account, ip, err, out)
		fail(w, http.StatusInternalServerError, "server")
		return
	}
	log.Printf("signup: account %s created (%s) ip=%s", account, status, ip)
	if status == "pending" {
		g.daily.allow(ip) // counted only now that the account exists
		g.notify.newRequest(account, email, message)
	}
	reply(w, http.StatusOK, map[string]any{"ok": true, "account": account, "status": status})
}

// readLines returns the lines of a file (none when it does not exist)
func readLines(path string) []string {
	f, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer f.Close()
	var lines []string
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 64<<10), 1<<20)
	for sc.Scan() {
		if line := strings.TrimRight(sc.Text(), "\r"); line != "" {
			lines = append(lines, line)
		}
	}
	return lines
}

// marks reads lib/.players: account -> nation, "*", "+" or "?"
func (g *gate) marks() map[string]string {
	m := map[string]string{}
	for _, line := range readLines(g.lib + "/.players") {
		if name, state, ok := strings.Cut(line, ":"); ok {
			m[name] = state
		}
	}
	return m
}

type request struct {
	Account string `json:"account"`
	Since   int64  `json:"since"`
	Email   string `json:"email"`
	Message string `json:"message"`
	Lang    string `json:"lang"`
}

// pending reads lib/.requests, oldest first
func (g *gate) pending() []request {
	list := []request{}
	for _, line := range readLines(g.lib + "/.requests") {
		f := strings.SplitN(line, "\t", 5)
		if len(f) < 2 {
			continue
		}
		since, _ := strconv.ParseInt(f[1], 10, 64)
		req := request{Account: f[0], Since: since}
		if len(f) > 2 {
			req.Email = f[2]
		}
		if len(f) > 3 {
			req.Message = f[3]
		}
		req.Lang = "en"
		if len(f) > 4 {
			req.Lang = validLang(f[4])
		}
		list = append(list, req)
	}
	sort.SliceStable(list, func(i, j int) bool { return list[i].Since < list[j].Since })
	return list
}

// adminOnly checks the account Apache signed in; it answers and returns
// false when the request may not go on. POSTs also get the same-origin
// check and a rate limit.
func (g *gate) adminOnly(w http.ResponseWriter, r *http.Request, method string) bool {
	if r.Method != method {
		w.Header().Set("Allow", method)
		fail(w, http.StatusMethodNotAllowed, "method")
		return false
	}
	user := strings.TrimSpace(r.Header.Get("X-WEBAUTH-USER"))
	if user == "" {
		fail(w, http.StatusUnauthorized, "unauthenticated")
		return false
	}
	if !accountRe.MatchString(user) || g.marks()[user] != "*" {
		log.Printf("admin refused: %s is not an administrator ip=%s", user, clientIP(r))
		fail(w, http.StatusForbidden, "forbidden")
		return false
	}
	if method == http.MethodPost {
		if !sameOrigin(r) {
			fail(w, http.StatusForbidden, "origin")
			return false
		}
		if !g.admin.allow(clientIP(r)) {
			fail(w, http.StatusTooManyRequests, "rate_limited")
			return false
		}
	}
	return true
}

func (g *gate) adminState(w http.ResponseWriter, r *http.Request) {
	if !g.adminOnly(w, r, http.MethodGet) {
		return
	}
	marks := g.marks()
	players := []map[string]any{}
	seen := map[string]bool{}
	var names []string
	for _, line := range readLines(g.htpasswd) {
		if name, _, ok := strings.Cut(line, ":"); ok && name != "" && !seen[name] {
			seen[name] = true
			names = append(names, name)
		}
	}
	sort.Strings(names)
	for _, name := range names {
		state, nation := marks[name], any(nil)
		switch state {
		case "", "*", "+", "?":
		default:
			nation, state = state, "nation"
		}
		players = append(players, map[string]any{"account": name, "state": state, "nation": nation})
	}
	invites := []string{}
	for _, line := range readLines(g.lib + "/.invites") {
		if codeRe.MatchString(line) {
			invites = append(invites, line)
		}
	}
	reply(w, http.StatusOK, map[string]any{
		"ok": true, "turn": g.turn(r.Context()), "last_join_turn": lastJoinTurn,
		"requests": g.pending(), "players": players, "invites": invites,
		"nations": g.nations(r.Context(), marks, names),
	})
}

// adminAssign gives an account a nation of the world, a new nation to found
// or the administrator mark
func (g *gate) adminAssign(w http.ResponseWriter, r *http.Request) {
	if !g.adminOnly(w, r, http.MethodPost) {
		return
	}
	var in struct {
		Account string `json:"account"`
		Nation  string `json:"nation"`
		Found   bool   `json:"found"`
		Admin   bool   `json:"admin"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1024)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil || !accountRe.MatchString(in.Account) {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	target, choices := in.Nation, 0
	if in.Nation != "" {
		choices++
	}
	if in.Found {
		target = "+"
		choices++
	}
	if in.Admin {
		target = "*"
		choices++
	}
	if choices != 1 || target == "+" && in.Nation != "" || !nationArgRe.MatchString(target) {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	out, err := g.runHelper(ctx, "", "assign", in.Account, target)
	if err != nil {
		if reason, status, ok := helperStatus(err, map[int]string{2: "no_account"}); ok {
			fail(w, status, reason)
			return
		}
		log.Printf("admin assign failed: account=%s: %v %s", in.Account, err, out)
		fail(w, http.StatusInternalServerError, "server")
		return
	}
	log.Printf("admin: assign %s to %s by %s", in.Account, target, r.Header.Get("X-WEBAUTH-USER"))
	assigned := target
	if lines := strings.Split(out, "\n"); len(lines) > 0 {
		assigned = strings.TrimSpace(lines[len(lines)-1])
	}
	reply(w, http.StatusOK, map[string]any{"ok": true, "account": in.Account, "assigned": assigned})
}

// accountAction approves or rejects a pending request
func (g *gate) accountAction(verb string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !g.adminOnly(w, r, http.MethodPost) {
			return
		}
		var in struct {
			Account string `json:"account"`
		}
		r.Body = http.MaxBytesReader(w, r.Body, 1024)
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil || !accountRe.MatchString(in.Account) {
			fail(w, http.StatusBadRequest, "bad_request")
			return
		}
		email, lang := "", "en"
		for _, req := range g.pending() {
			if req.Account == in.Account {
				email, lang = req.Email, req.Lang
			}
		}
		ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
		defer cancel()
		out, err := g.runHelper(ctx, "", verb, in.Account)
		if err != nil {
			if reason, status, ok := helperStatus(err, map[int]string{2: "not_pending"}); ok {
				fail(w, status, reason)
				return
			}
			log.Printf("admin %s failed: account=%s: %v %s", verb, in.Account, err, out)
			fail(w, http.StatusInternalServerError, "server")
			return
		}
		log.Printf("admin: %s %s by %s", verb, in.Account, r.Header.Get("X-WEBAUTH-USER"))
		if verb == "reject" {
			reply(w, http.StatusOK, map[string]any{"ok": true})
			return
		}
		emailed := email != "" && g.notify.mailEnabled()
		if emailed {
			g.notify.approved(in.Account, email, lang, g.turn(r.Context()))
		}
		reply(w, http.StatusOK, map[string]any{"ok": true, "account": in.Account, "emailed": emailed})
	}
}

func (g *gate) adminInvite(w http.ResponseWriter, r *http.Request) {
	if !g.adminOnly(w, r, http.MethodPost) {
		return
	}
	var in struct {
		Count int `json:"count"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1024)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil || in.Count < 1 || in.Count > 20 {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	out, err := g.runHelper(ctx, "", "invites", strconv.Itoa(in.Count))
	if err != nil {
		if reason, status, ok := helperStatus(err, nil); ok {
			fail(w, status, reason)
			return
		}
		log.Printf("admin invite failed: %v %s", err, out)
		fail(w, http.StatusInternalServerError, "server")
		return
	}
	codes := []string{}
	for _, line := range strings.Split(out, "\n") {
		if line = strings.TrimSpace(line); codeRe.MatchString(line) {
			codes = append(codes, line)
		}
	}
	reply(w, http.StatusOK, map[string]any{"ok": true, "codes": codes})
}

// testMail sends one mail to address and says how it went (conquer-gate
// -test-mail ADDRESS), to try the SMTP settings
func testMail(address string) int {
	n := loadNotifier()
	if !n.mailEnabled() {
		fmt.Fprintln(os.Stderr, "SMTP_HOST is not set: no mail can be sent")
		return 1
	}
	body := "This is a test mail from the Conquer game server.\nIf you can read it, the mail settings work.\n"
	if err := n.sendMail(address, "Conquer: test mail", body); err != nil {
		fmt.Fprintf(os.Stderr, "Could not send the mail through %s: %v\n", n.smtpHost, err)
		return 1
	}
	fmt.Printf("Mail sent to %s through %s (from %s)\n", address, n.smtpHost, n.from)
	return 0
}

func main() {
	listen := flag.String("listen", ":7682", "address to listen on")
	helper := flag.String("signup", "/usr/local/bin/conquer-signup", "program that creates the account")
	lib := flag.String("lib", "/opt/conquer/lib", "world directory (.players, .requests, .invites)")
	htpasswd := flag.String("htpasswd", "/opt/conquer/auth/htpasswd", "account file Apache checks")
	conquer := flag.String("conquer", "/opt/conquer/bin/conquer", "game binary, to read the turn")
	testAddr := flag.String("test-mail", "", "send one test mail to this address and exit")
	flag.Parse()
	log.SetPrefix("[gate] ")
	log.SetFlags(0)

	if *testAddr != "" {
		os.Exit(testMail(*testAddr))
	}

	g := &gate{
		helper:   *helper,
		lib:      strings.TrimRight(*lib, "/"),
		htpasswd: *htpasswd,
		conquer:  *conquer,
		requests: newLimiter(20, 10*time.Minute),
		failures: newLimiter(5, time.Hour),
		daily:    newLimiter(envInt("SIGNUP_DAILY_LIMIT", defaultDailyPerIP), 24*time.Hour),
		admin:    newLimiter(120, 10*time.Minute),
		notify:   loadNotifier(),
	}
	g.tokens = newFormTokens(loadSecret(g.lib+"/"+secretFileName),
		time.Duration(envInt("SIGNUP_MIN_FILL", int(defaultMinFill/time.Second)))*time.Second)
	if days := envInt("SIGNUP_EXPIRE_DAYS", defaultExpireDays); days > 0 {
		go g.expireLoop(days, expireFirstRunAfter, expireInterval)
	}
	go func() {
		for range time.Tick(10 * time.Minute) {
			g.requests.cleanup()
			g.failures.cleanup()
			g.daily.cleanup()
			g.admin.cleanup()
		}
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("/join/api/request", g.signup)
	mux.HandleFunc("/join/api/signup", g.signup)
	mux.HandleFunc("/join/api/token", g.token)
	mux.HandleFunc("/join/api/health", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("ok\n"))
	})
	mux.HandleFunc("/admin/api/state", g.adminState)
	mux.HandleFunc("/admin/api/approve", g.accountAction("approve"))
	mux.HandleFunc("/admin/api/reject", g.accountAction("reject"))
	mux.HandleFunc("/admin/api/invite", g.adminInvite)
	mux.HandleFunc("/admin/api/assign", g.adminAssign)
	srv := &http.Server{
		Addr:              *listen,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       20 * time.Second,
		WriteTimeout:      30 * time.Second,
		MaxHeaderBytes:    16 << 10,
	}
	switch {
	case g.notify.mailEnabled():
		log.Printf("listening on %s (mail through %s)", *listen, g.notify.smtpHost)
	default:
		log.Printf("listening on %s (no mail: SMTP_HOST is not set)", *listen)
	}
	log.Fatal(srv.ListenAndServe())
}
