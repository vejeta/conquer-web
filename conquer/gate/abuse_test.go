// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// fakeHelper writes a stand-in for conquer-signup: "request" appends the
// account and language to lib/.requests, "invite" succeeds, "expire" prints
// what the test put in lib/expired, "scrub" prints lib/scrubbed. Every call
// is logged to lib/calls.
func fakeHelper(t *testing.T, lib string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "conquer-signup")
	script := `#!/bin/sh
LIB="` + lib + `"
echo "$@" >> "$LIB/calls"
cat > /dev/null
case "$1" in
request) printf '%s\t1\t%s\n' "$2" "$3" >> "$LIB/.requests" ;;
expire) cat "$LIB/expired" 2>/dev/null ;;
scrub) cat "$LIB/scrubbed" 2>/dev/null || echo 0 ;;
esac
exit 0
`
	if err := os.WriteFile(path, []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}
	return path
}

func testGate(t *testing.T) (*gate, string) {
	t.Helper()
	lib := t.TempDir()
	g := &gate{
		helper:   fakeHelper(t, lib),
		lib:      lib,
		requests: newLimiter(20, 10*time.Minute),
		failures: newLimiter(5, time.Hour),
		daily:    newLimiter(3, 24*time.Hour),
		admin:    newLimiter(120, time.Minute),
		notify:   &notifier{},
		tokens:   newFormTokens([]byte("0123456789abcdef0123456789abcdef"), 3*time.Second),
	}
	return g, lib
}

func calls(lib string) []string {
	return readLines(filepath.Join(lib, "calls"))
}

type result struct {
	Code   int
	OK     bool
	Error  string
	Status string
}

// post sends a sign-up request from ip with an optional token
func post(g *gate, ip, token string, body map[string]any) result {
	raw, _ := json.Marshal(body)
	r := httptest.NewRequest(http.MethodPost, "/join/api/request", strings.NewReader(string(raw)))
	r.Header.Set("X-Forwarded-For", ip)
	if token != "" {
		r.Header.Set(tokenHeader, token)
	}
	w := httptest.NewRecorder()
	g.signup(w, r)
	var out struct {
		OK     bool   `json:"ok"`
		Error  string `json:"error"`
		Status string `json:"status"`
	}
	_ = json.Unmarshal(w.Body.Bytes(), &out)
	return result{w.Code, out.OK, out.Error, out.Status}
}

// oldToken is a token issued to ip long enough ago to pass the minimum fill time
func oldToken(g *gate, ip string) string {
	issued := g.tokens.now
	defer func() { g.tokens.now = issued }()
	g.tokens.now = func() time.Time { return time.Now().Add(-time.Minute) }
	return g.tokens.issue(ip)
}

func asking(account string) map[string]any {
	return map[string]any{"account": account, "password": "long enough"}
}

func TestTokenTooFastIsDroppedSilently(t *testing.T) {
	g, lib := testGate(t)
	fresh := g.tokens.issue("203.0.113.1")
	res := post(g, "203.0.113.1", fresh, asking("fast"))
	if !res.OK || res.Status != "pending" {
		t.Fatalf("a dropped request must look accepted: %+v", res)
	}
	if len(calls(lib)) != 0 {
		t.Errorf("nothing may be created for a too fast form: %v", calls(lib))
	}
	if g.daily.full("203.0.113.1") {
		t.Error("a dropped request does not use up the daily limit")
	}
	// Slow enough: created
	res = post(g, "203.0.113.1", oldToken(g, "203.0.113.1"), asking("slow"))
	if !res.OK || len(calls(lib)) != 1 {
		t.Fatalf("a form filled in a minute is accepted: %+v %v", res, calls(lib))
	}
}

func TestTokenMissingForgedForeignOrOld(t *testing.T) {
	g, lib := testGate(t)
	ip := "203.0.113.2"
	good := oldToken(g, ip)
	stamp, sum, _ := strings.Cut(good, ".")
	cases := map[string]string{
		"none":     "",
		"garbage":  "abc",
		"forged":   stamp + "." + strings.Repeat("0", len(sum)),
		"other ip": oldToken(g, "198.51.100.7"),
		"future": func() string {
			g.tokens.now = func() time.Time { return time.Now().Add(time.Hour) }
			defer func() { g.tokens.now = time.Now }()
			return g.tokens.issue(ip)
		}(),
		"too old": func() string {
			g.tokens.now = func() time.Time { return time.Now().Add(-72 * time.Hour) }
			defer func() { g.tokens.now = time.Now }()
			return g.tokens.issue(ip)
		}(),
		"bad stamp": "x." + g.tokens.mac("x", ip),
	}
	for name, token := range cases {
		res := post(g, ip, token, asking("bot"+strings.ReplaceAll(name, " ", "")))
		if !res.OK {
			t.Errorf("%s: a dropped request must look accepted: %+v", name, res)
		}
	}
	if len(calls(lib)) != 0 {
		t.Errorf("no token that fails the check may create an account: %v", calls(lib))
	}
	if res := post(g, ip, good, asking("human")); !res.OK || len(calls(lib)) != 1 {
		t.Errorf("the good token works: %+v", res)
	}
}

func TestTokenCheckOffWhenMinFillIsZero(t *testing.T) {
	g, lib := testGate(t)
	g.tokens.minFill = 0
	if res := post(g, "203.0.113.3", "", asking("api")); !res.OK || len(calls(lib)) != 1 {
		t.Fatalf("with the check off no token is needed: %+v", res)
	}
}

func TestHoneypot(t *testing.T) {
	g, lib := testGate(t)
	ip := "203.0.113.4"
	body := asking("spam")
	body["website"] = "http://spam.example"
	res := post(g, ip, oldToken(g, ip), body)
	if !res.OK || res.Status != "pending" {
		t.Fatalf("the honeypot request looks accepted: %+v", res)
	}
	if len(calls(lib)) != 0 || g.daily.full(ip) {
		t.Error("the honeypot request creates nothing and costs the visitor nothing")
	}
	body["website"] = "   "
	if res := post(g, ip, oldToken(g, ip), body); !res.OK || len(calls(lib)) != 1 {
		t.Errorf("a blank website is not the honeypot: %+v %v", res, calls(lib))
	}
}

func TestDailyLimitCountsOnlySuccesses(t *testing.T) {
	g, lib := testGate(t)
	ip := "203.0.113.5"
	// Refused requests do not count
	for i := 0; i < 5; i++ {
		if res := post(g, ip, oldToken(g, ip), map[string]any{"account": "..", "password": "long enough"}); res.Error != "bad_account" {
			t.Fatalf("expected bad_account: %+v", res)
		}
	}
	if g.daily.full(ip) {
		t.Fatal("refused requests must not use up the daily limit")
	}
	for i, name := range []string{"a1", "a2", "a3"} {
		if res := post(g, ip, oldToken(g, ip), asking(name)); !res.OK {
			t.Fatalf("request %d: %+v", i, res)
		}
	}
	res := post(g, ip, oldToken(g, ip), asking("a4"))
	if res.Code != http.StatusTooManyRequests || res.Error != "daily_limit" {
		t.Fatalf("the fourth request of the day is limited: %+v", res)
	}
	if n := len(calls(lib)); n != 3 {
		t.Errorf("%d accounts were created, want 3", n)
	}
	// Another address has its own count
	if res := post(g, "203.0.113.6", oldToken(g, "203.0.113.6"), asking("b1")); !res.OK {
		t.Errorf("another address is not limited: %+v", res)
	}
}

func TestDailyLimitDoesNotStopInviteCodes(t *testing.T) {
	g, lib := testGate(t)
	ip := "203.0.113.7"
	for _, name := range []string{"a1", "a2", "a3"} {
		post(g, ip, oldToken(g, ip), asking(name))
	}
	body := asking("invited")
	body["code"] = "K7QM-3XPA"
	if res := post(g, ip, oldToken(g, ip), body); !res.OK || res.Status != "approved" {
		t.Fatalf("an invite code is not a request: %+v", res)
	}
	if got := calls(lib); !strings.HasPrefix(got[len(got)-1], "invite K7QM-3XPA invited") {
		t.Errorf("calls: %v", got)
	}
}

// The sign-up form no longer asks for an email address or a message; one
// that an old page or a script sends is not stored, passed on or logged
func TestEmailAndMessageAreNeverKept(t *testing.T) {
	g, lib := testGate(t)
	var logs strings.Builder
	log.SetOutput(&logs)
	defer log.SetOutput(os.Stderr)
	body := asking("first")
	body["email"] = "ana@example.org"
	body["message"] = "call me on 555-0100"
	body["lang"] = "es"
	if res := post(g, "203.0.113.8", oldToken(g, "203.0.113.8"), body); !res.OK {
		t.Fatalf("first: %+v", res)
	}
	got := calls(lib)
	if len(got) != 1 || got[0] != "request first es" {
		t.Errorf("the helper gets the account and the language only: %v", got)
	}
	if raw, _ := os.ReadFile(filepath.Join(lib, ".requests")); strings.Contains(string(raw), "ana@") || strings.Contains(string(raw), "555") {
		t.Errorf("the request file holds personal data: %q", raw)
	}
	if strings.Contains(logs.String(), "ana@") || strings.Contains(logs.String(), "555") {
		t.Errorf("the log holds personal data: %q", logs.String())
	}
	// The same address does not collide any more: there is none
	body = asking("second")
	body["email"] = "ANA@example.org"
	if res := post(g, "203.0.113.9", oldToken(g, "203.0.113.9"), body); !res.OK {
		t.Errorf("a second request is not refused for an email: %+v", res)
	}
}

func TestPendingReadsOldAndNewRequestLines(t *testing.T) {
	g, lib := testGate(t)
	lines := "old\t10\told@example.org\thello\tes\n" + "new\t20\tde\n" + "bare\t30\n"
	if err := os.WriteFile(filepath.Join(lib, ".requests"), []byte(lines), 0o600); err != nil {
		t.Fatal(err)
	}
	var got []string
	for _, r := range g.pending() {
		raw, _ := json.Marshal(r)
		if strings.Contains(string(raw), "example.org") || strings.Contains(string(raw), "hello") {
			t.Errorf("a pending request shows personal data: %s", raw)
		}
		got = append(got, r.Account+":"+r.Lang)
	}
	if strings.Join(got, ",") != "old:es,new:de,bare:en" {
		t.Errorf("pending = %v", got)
	}
}

func TestScrubAsksTheHelperAndReportsTheCount(t *testing.T) {
	g, lib := testGate(t)
	if err := os.WriteFile(filepath.Join(lib, "scrubbed"), []byte("3\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	n, err := g.scrub(context.Background())
	if err != nil || n != 3 {
		t.Fatalf("scrub = %d, %v", n, err)
	}
	if got := calls(lib); len(got) != 1 || got[0] != "scrub" {
		t.Errorf("the helper was called as %v", got)
	}
}

func TestTokenEndpoint(t *testing.T) {
	g, _ := testGate(t)
	r := httptest.NewRequest(http.MethodGet, "/join/api/token", nil)
	r.Header.Set("X-Forwarded-For", "203.0.113.12")
	w := httptest.NewRecorder()
	g.token(w, r)
	var out struct {
		OK    bool   `json:"ok"`
		Token string `json:"token"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &out); err != nil || !out.OK || out.Token == "" {
		t.Fatalf("token reply: %s", w.Body.String())
	}
	// The token is bound to the address that asked
	if ok, _ := g.tokens.check(out.Token, "203.0.113.13"); ok {
		t.Error("a token must not work from another address")
	}
	w = httptest.NewRecorder()
	g.token(w, httptest.NewRequest(http.MethodPost, "/join/api/token", nil))
	if w.Code != http.StatusMethodNotAllowed {
		t.Errorf("POST to the token endpoint: %d", w.Code)
	}
}

func TestSecretIsKept(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".gate-secret")
	a := loadSecret(path)
	b := loadSecret(path)
	if len(a) != 32 || string(a) != string(b) {
		t.Error("the key is made once and read back")
	}
	if info, err := os.Stat(path); err != nil || info.Mode().Perm() != 0o600 {
		t.Errorf("the key file is private: %v %v", info, err)
	}
	if c := loadSecret(filepath.Join(t.TempDir(), "no-such-dir", "x")); len(c) != 32 {
		t.Error("an unwritable path still gives a key")
	}
}

func TestExpireReportsTheNames(t *testing.T) {
	g, lib := testGate(t)
	if err := os.WriteFile(filepath.Join(lib, "expired"), []byte("old1\nold2\nnot a name!\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	names, err := g.expire(context.Background(), 30)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(names, ",") != "old1,old2" {
		t.Errorf("names = %v", names)
	}
	if got := calls(lib); len(got) != 1 || got[0] != "expire 30" {
		t.Errorf("the helper was called as %v", got)
	}
}

func TestExpireLoopRunsAtOnceAndAgain(t *testing.T) {
	g, lib := testGate(t)
	go g.expireLoop(7, time.Millisecond, 20*time.Millisecond)
	deadline := time.Now().Add(3 * time.Second)
	for len(calls(lib)) < 3 && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	if got := calls(lib); len(got) < 3 || got[0] != "expire 7" {
		t.Errorf("the daily job did not repeat: %v", got)
	}
}

func TestEnvInt(t *testing.T) {
	t.Setenv("GATE_TEST_N", "")
	if envInt("GATE_TEST_N", 3) != 3 {
		t.Error("empty gives the default")
	}
	t.Setenv("GATE_TEST_N", "0")
	if envInt("GATE_TEST_N", 3) != 0 {
		t.Error("0 is a value (it turns a check off)")
	}
	for _, bad := range []string{"-1", "x", "1.5"} {
		t.Setenv("GATE_TEST_N", bad)
		if envInt("GATE_TEST_N", 3) != 3 {
			t.Errorf("%q gives the default", bad)
		}
	}
}
