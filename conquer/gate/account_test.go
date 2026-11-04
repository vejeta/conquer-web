// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import (
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

// recordingHelper is a stand-in for conquer-signup that logs its arguments
// to lib/calls, its standard input to lib/stdin and exits with the number
// in lib/exit-<command> (0 when there is none)
func recordingHelper(t *testing.T, lib string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "conquer-signup")
	script := `#!/bin/sh
LIB="` + lib + `"
echo "$@" >> "$LIB/calls"
cat > "$LIB/stdin"
if [ -f "$LIB/exit-$1" ]; then exit "$(cat "$LIB/exit-$1")"; fi
exit 0
`
	if err := os.WriteFile(path, []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}
	return path
}

func accountGate(t *testing.T) (*gate, string) {
	t.Helper()
	g, lib := testGate(t)
	g.helper = recordingHelper(t, lib)
	g.pwFail = newLimiter(accountFailures, time.Hour)
	g.recFail = newLimiter(accountFailures, time.Hour)
	g.acct = newLimiter(120, 10*time.Minute)
	return g, lib
}

func exitWith(t *testing.T, lib, command string, code string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(lib, "exit-"+command), []byte(code), 0o600); err != nil {
		t.Fatal(err)
	}
}

type reply2 struct {
	Code     int
	OK       bool            `json:"ok"`
	Error    string          `json:"error"`
	Account  string          `json:"account"`
	HasCode  bool            `json:"has_recovery"`
	Recovery string          `json:"recovery_code"`
	Raw      json.RawMessage `json:"-"`
}

// call runs a handler as Apache would: the signed-in account in
// X-WEBAUTH-USER (empty: none), the client address in X-Forwarded-For
func call(h http.HandlerFunc, method, user, ip string, body any, header ...string) reply2 {
	raw, _ := json.Marshal(body)
	r := httptest.NewRequest(method, "/account/api/x", strings.NewReader(string(raw)))
	if user != "" {
		r.Header.Set("X-WEBAUTH-USER", user)
	}
	r.Header.Set("X-Forwarded-For", ip)
	for i := 0; i+1 < len(header); i += 2 {
		r.Header.Set(header[i], header[i+1])
	}
	w := httptest.NewRecorder()
	h(w, r)
	var out reply2
	_ = json.Unmarshal(w.Body.Bytes(), &out)
	out.Code = w.Code
	out.Raw = w.Body.Bytes()
	return out
}

func stdin(lib string) string {
	b, _ := os.ReadFile(filepath.Join(lib, "stdin"))
	return string(b)
}

func TestRecoveryCodeFormat(t *testing.T) {
	seen := map[string]bool{}
	for i := 0; i < 2000; i++ {
		c := newRecoveryCode()
		if !recoveryRe.MatchString(c) {
			t.Fatalf("%q is not XXXX-XXXX-XXXX from the alphabet", c)
		}
		if seen[c] {
			t.Fatalf("%q came twice", c)
		}
		seen[c] = true
	}
	if got := normalizeRecovery(" k7qm 3xpa-9rtd "); got != "K7QM-3XPA-9RTD" {
		t.Errorf("normalizeRecovery = %q", got)
	}
	if got := normalizeRecovery("K7QM3XPA9RTD"); got != "K7QM-3XPA-9RTD" {
		t.Errorf("normalizeRecovery = %q", got)
	}
	for _, bad := range []string{"", "K7QM-3XPA", "K7QM-3XPA-9RT0", "K7QM-3XPA-9RTD\n.*", "K7QM-3XPA-9RTDX"} {
		if recoveryRe.MatchString(normalizeRecovery(bad)) {
			t.Errorf("%q must not pass", bad)
		}
	}
}

func TestPlayerEndpointsNeedTheSignedInAccount(t *testing.T) {
	g, lib := accountGate(t)
	for name, h := range map[string]http.HandlerFunc{"init": g.accountInit, "password": g.accountPassword, "recovery": g.accountRecovery} {
		if r := call(h, http.MethodPost, "", "203.0.113.1", map[string]any{}); r.Code != http.StatusUnauthorized {
			t.Errorf("%s without the header: %d", name, r.Code)
		}
		if r := call(h, http.MethodPost, "../etc", "203.0.113.1", map[string]any{}); r.Code != http.StatusForbidden {
			t.Errorf("%s with a bad name: %d", name, r.Code)
		}
		if r := call(h, http.MethodGet, "ana", "203.0.113.1", nil); r.Code != http.StatusMethodNotAllowed {
			t.Errorf("%s by GET: %d", name, r.Code)
		}
		if r := call(h, http.MethodPost, "ana", "203.0.113.1", map[string]any{}, "Origin", "https://evil.example"); r.Code != http.StatusForbidden {
			t.Errorf("%s from another site: %d", name, r.Code)
		}
	}
	if len(calls(lib)) != 0 {
		t.Errorf("nothing may run for a request that is not signed in: %v", calls(lib))
	}
}

func TestInitMakesTheCodeOnceAndShowsItOnce(t *testing.T) {
	g, lib := accountGate(t)
	r := call(g.accountInit, http.MethodPost, "ana", "203.0.113.1", map[string]any{})
	if r.Code != 200 || !r.OK || r.Account != "ana" || !r.HasCode || !recoveryRe.MatchString(r.Recovery) {
		t.Fatalf("first call: %+v", r)
	}
	if got := calls(lib); len(got) != 1 || got[0] != "recovery-init ana" {
		t.Errorf("helper calls: %v (the code must not be in the command line)", got)
	}
	if strings.TrimSpace(stdin(lib)) != r.Recovery {
		t.Errorf("the helper got %q, the page %q", stdin(lib), r.Recovery)
	}
	// Once the hash is stored, the code is never sent again
	if err := os.WriteFile(filepath.Join(lib, ".recovery"), []byte("bob:$2y$10$x\nana:$2y$10$abc\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	again := call(g.accountInit, http.MethodPost, "ana", "203.0.113.1", map[string]any{})
	if !again.OK || !again.HasCode || again.Recovery != "" || strings.Contains(string(again.Raw), "recovery_code") {
		t.Errorf("second call: %s", again.Raw)
	}
	if len(calls(lib)) != 1 {
		t.Errorf("the helper ran again: %v", calls(lib))
	}
}

func TestInitWhenAnotherCallWasFirstOrTheSeatIsPending(t *testing.T) {
	g, lib := accountGate(t)
	exitWith(t, lib, "recovery-init", "2")
	if r := call(g.accountInit, http.MethodPost, "ana", "203.0.113.1", map[string]any{}); !r.OK || !r.HasCode || r.Recovery != "" {
		t.Errorf("a code made a moment ago by another call: %s", r.Raw)
	}
	exitWith(t, lib, "recovery-init", "3")
	if r := call(g.accountInit, http.MethodPost, "ana", "203.0.113.1", map[string]any{}); !r.OK || r.HasCode || r.Recovery != "" {
		t.Errorf("a seat waiting for approval has no code: %s", r.Raw)
	}
	exitWith(t, lib, "recovery-init", "1")
	if r := call(g.accountInit, http.MethodPost, "ana", "203.0.113.1", map[string]any{}); r.Code != 500 || r.Error != "server" {
		t.Errorf("a helper failure is a server error: %+v", r)
	}
}

func TestPasswordChange(t *testing.T) {
	g, lib := accountGate(t)
	ok := call(g.accountPassword, http.MethodPost, "ana", "203.0.113.1", map[string]any{"current": "old password", "new": "new password"})
	if ok.Code != 200 || !ok.OK {
		t.Fatalf("%+v", ok)
	}
	if got := calls(lib); len(got) != 1 || got[0] != "passwd ana" {
		t.Errorf("helper calls: %v", got)
	}
	if stdin(lib) != "old password\nnew password\n" {
		t.Errorf("stdin = %q", stdin(lib))
	}
	for name, in := range map[string]map[string]any{
		"short":   {"current": "old password", "new": "short"},
		"newline": {"current": "old password", "new": "new\npassword"},
		"long":    {"current": "old password", "new": strings.Repeat("x", 73)},
	} {
		want := map[string]string{"short": "short_password", "newline": "bad_password", "long": "bad_password"}[name]
		if r := call(g.accountPassword, http.MethodPost, "ana", "203.0.113.1", in); r.Code != 400 || r.Error != want {
			t.Errorf("%s: %+v, want %s", name, r, want)
		}
	}
	if len(calls(lib)) != 1 {
		t.Errorf("a bad new password must not reach the helper: %v", calls(lib))
	}
	exitWith(t, lib, "passwd", "2")
	if r := call(g.accountPassword, http.MethodPost, "ana", "203.0.113.1", map[string]any{"current": "nope nope", "new": "new password"}); r.Code != 403 || r.Error != "bad_current" {
		t.Errorf("wrong current password: %+v", r)
	}
}

func TestWrongCurrentPasswordsAreLimitedPerAddressAndPerAccount(t *testing.T) {
	g, lib := accountGate(t)
	exitWith(t, lib, "passwd", "2")
	wrong := map[string]any{"current": "nope nope", "new": "new password"}
	for i := 0; i < accountFailures; i++ {
		if r := call(g.accountPassword, http.MethodPost, "ana", "203.0.113.1", wrong); r.Error != "bad_current" {
			t.Fatalf("try %d: %+v", i, r)
		}
	}
	ran := len(calls(lib))
	// The sixth try is refused without asking the helper, even with the right password
	if err := os.Remove(filepath.Join(lib, "exit-passwd")); err != nil {
		t.Fatal(err)
	}
	right := map[string]any{"current": "old password", "new": "new password"}
	if r := call(g.accountPassword, http.MethodPost, "ana", "203.0.113.1", right); r.Code != 429 || r.Error != "rate_limited" {
		t.Fatalf("over the limit: %+v", r)
	}
	// Another address, same account: the account's count holds
	if r := call(g.accountPassword, http.MethodPost, "ana", "198.51.100.9", right); r.Code != 429 {
		t.Errorf("the account is limited from any address: %+v", r)
	}
	// Same address, another account: the address's count holds
	if r := call(g.accountPassword, http.MethodPost, "bob", "203.0.113.1", right); r.Code != 429 {
		t.Errorf("the address is limited for any account: %+v", r)
	}
	// Both fresh: fine
	if r := call(g.accountPassword, http.MethodPost, "bob", "198.51.100.9", right); r.Code != 200 {
		t.Errorf("a fresh address and account: %+v", r)
	}
	if len(calls(lib)) != ran+1 {
		t.Errorf("limited tries must not reach the helper: %d calls, %d before", len(calls(lib)), ran)
	}
	// The recovery code of the same account is behind the same limit
	if r := call(g.accountRecovery, http.MethodPost, "ana", "203.0.113.50", map[string]any{"current": "old password"}); r.Code != 429 {
		t.Errorf("making a new code is limited like the password change: %+v", r)
	}
}

func TestNewRecoveryCodeNeedsThePassword(t *testing.T) {
	g, lib := accountGate(t)
	r := call(g.accountRecovery, http.MethodPost, "ana", "203.0.113.1", map[string]any{"current": "old password"})
	if r.Code != 200 || !recoveryRe.MatchString(r.Recovery) {
		t.Fatalf("%+v", r)
	}
	if got := calls(lib); len(got) != 1 || got[0] != "recovery-renew ana" {
		t.Errorf("helper calls: %v", got)
	}
	if stdin(lib) != "old password\n"+r.Recovery+"\n" {
		t.Errorf("stdin = %q", stdin(lib))
	}
	exitWith(t, lib, "recovery-renew", "2")
	if r := call(g.accountRecovery, http.MethodPost, "ana", "203.0.113.1", map[string]any{"current": "wrong"}); r.Code != 403 || r.Error != "bad_current" || r.Recovery != "" {
		t.Errorf("wrong password: %+v", r)
	}
	if r := call(g.accountRecovery, http.MethodPost, "ana", "203.0.113.1", map[string]any{}); r.Code != 403 {
		t.Errorf("no password: %+v", r)
	}
}

func TestRecoverWithTheCode(t *testing.T) {
	g, lib := accountGate(t)
	body := map[string]any{"account": "ana", "code": "k7qm 3xpa 9rtd", "password": "brand new password"}
	r := call(g.recover, http.MethodPost, "", "203.0.113.1", body)
	if r.Code != 200 || !r.OK || !recoveryRe.MatchString(r.Recovery) || r.Recovery == "K7QM-3XPA-9RTD" {
		t.Fatalf("%+v", r)
	}
	if got := calls(lib); len(got) != 1 || got[0] != "reset ana" {
		t.Errorf("helper calls: %v", got)
	}
	if stdin(lib) != "K7QM-3XPA-9RTD\nbrand new password\n"+r.Recovery+"\n" {
		t.Errorf("the helper got the normalized code, the password and the NEW code: %q", stdin(lib))
	}
	// It is open (no sign-in), but not for another site, and not by GET
	if r := call(g.recover, http.MethodGet, "", "203.0.113.1", nil); r.Code != 405 {
		t.Errorf("GET: %d", r.Code)
	}
	if r := call(g.recover, http.MethodPost, "", "203.0.113.1", body, "Origin", "https://evil.example"); r.Code != 403 {
		t.Errorf("foreign origin: %d", r.Code)
	}
	for name, in := range map[string]map[string]any{
		"bad account": {"account": "..", "code": "K7QM-3XPA-9RTD", "password": "brand new password"},
		"short":       {"account": "ana", "code": "K7QM-3XPA-9RTD", "password": "short"},
	} {
		if r := call(g.recover, http.MethodPost, "", "203.0.113.2", in); r.Code != 400 {
			t.Errorf("%s: %+v", name, r)
		}
	}
}

func TestRecoverFailuresAreLimitedAndAnswerTheSame(t *testing.T) {
	g, lib := accountGate(t)
	exitWith(t, lib, "reset", "2")
	body := func(account, code string) map[string]any {
		return map[string]any{"account": account, "code": code, "password": "brand new password"}
	}
	// A wrong code, a malformed one and an unknown account all say bad_recovery with 403
	for i, in := range []map[string]any{body("ana", "K7QM-3XPA-9RTD"), body("ana", "garbage"), body("nobody", "K7QM-3XPA-9RTD")} {
		if r := call(g.recover, http.MethodPost, "", "203.0.113.1", in); r.Code != 403 || r.Error != "bad_recovery" {
			t.Fatalf("case %d: %+v", i, r)
		}
	}
	for i := 0; i < accountFailures-3; i++ {
		call(g.recover, http.MethodPost, "", "203.0.113.1", body("ana", "K7QM-3XPA-9RTD"))
	}
	// ana has had four wrong codes and 203.0.113.1 five; a fifth for ana from elsewhere
	call(g.recover, http.MethodPost, "", "198.51.100.77", body("ana", "K7QM-3XPA-9RTD"))
	ran := len(calls(lib))
	good := body("ana", "K7QM-3XPA-9RTD")
	if err := os.Remove(filepath.Join(lib, "exit-reset")); err != nil {
		t.Fatal(err)
	}
	if r := call(g.recover, http.MethodPost, "", "203.0.113.1", good); r.Code != 429 || r.Error != "rate_limited" {
		t.Errorf("the address is out of tries: %+v", r)
	}
	if r := call(g.recover, http.MethodPost, "", "198.51.100.5", good); r.Code != 429 {
		t.Errorf("the account is out of tries from any address: %+v", r)
	}
	if r := call(g.recover, http.MethodPost, "", "198.51.100.5", body("bob", "K7QM-3XPA-9RTD")); r.Code != 200 {
		t.Errorf("another address and account is free: %+v", r)
	}
	if len(calls(lib)) != ran+1 {
		t.Errorf("limited tries must not reach the helper")
	}
}

func TestNothingSecretIsLogged(t *testing.T) {
	g, lib := accountGate(t)
	var logs strings.Builder
	logTo(&logs)
	defer logTo(os.Stderr)
	exitWith(t, lib, "reset", "2")
	call(g.recover, http.MethodPost, "", "203.0.113.1", map[string]any{"account": "ana", "code": "K7QM-3XPA-9RTD", "password": "brand new password"})
	exitWith(t, lib, "passwd", "2")
	call(g.accountPassword, http.MethodPost, "ana", "203.0.113.1", map[string]any{"current": "my old password", "new": "my new password"})
	call(g.accountInit, http.MethodPost, "bob", "203.0.113.3", map[string]any{})
	out := logs.String()
	for _, secret := range []string{"K7QM", "brand new password", "my old password", "my new password", "recovery_code"} {
		if strings.Contains(out, secret) {
			t.Errorf("the log holds %q:\n%s", secret, out)
		}
	}
	if !strings.Contains(out, "refused") || !strings.Contains(out, "ip=203.0.113.1") {
		t.Errorf("failures are logged with the address: %s", out)
	}
	if got := stdin(lib); strings.Contains(strings.Join(calls(lib), " "), "K7QM") || got == "" {
		t.Errorf("secrets travel on standard input, not in arguments: %v", calls(lib))
	}
}

func logTo(w interface{ Write([]byte) (int, error) }) { log.SetOutput(w) }
