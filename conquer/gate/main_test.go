// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import (
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"
)

func TestAccountNames(t *testing.T) {
	good := []string{"a", "kestrel", "Ana_2", "a.b-c", "9lives", strings.Repeat("x", 32)}
	bad := []string{
		"", ".", "..", ".hidden", "-v", "-", "_x", "a b", "a:b", "a\tb", "a\nb", "a/b", "a;b",
		"$(id)", "`id`", "ana\x00", "ñandú", strings.Repeat("x", 33),
	}
	for _, name := range good {
		if !accountRe.MatchString(name) {
			t.Errorf("%q should be a valid account name", name)
		}
	}
	for _, name := range bad {
		if accountRe.MatchString(name) {
			t.Errorf("%q should not be a valid account name", name)
		}
	}
}

func TestCodes(t *testing.T) {
	if got := normalizeCode("k7qm 3xpa"); got != "K7QM-3XPA" {
		t.Errorf("normalizeCode = %q", got)
	}
	for _, c := range []string{"K7QM-3XPA", "ZZZZ-9999"} {
		if !codeRe.MatchString(c) {
			t.Errorf("%q should be a code", c)
		}
	}
	for _, c := range []string{"", "K7QM3XPA", "K7QM-3XP", "k7qm-3xpa", "K7QM-3XPA\n.*", ".*"} {
		if codeRe.MatchString(c) {
			t.Errorf("%q should not be a code", c)
		}
	}
}

func TestSameOrigin(t *testing.T) {
	req := func(origin, forwarded string) *http.Request {
		r := httptest.NewRequest(http.MethodPost, "http://conquer-local:7682/join/api/request", nil)
		r.Host = "conquer.example.com"
		if origin != "" {
			r.Header.Set("Origin", origin)
		}
		if forwarded != "" {
			r.Header.Set("X-Forwarded-Host", forwarded)
		}
		return r
	}
	cases := []struct {
		name      string
		origin    string
		forwarded string
		want      bool
	}{
		{"no Origin (not a browser)", "", "", true},
		{"same site", "https://conquer.example.com", "", true},
		{"same site behind the proxy", "https://conquer.example.com", "conquer.example.com", true},
		{"other site", "https://evil.example", "", false},
		{"other site, forwarded host", "https://evil.example", "conquer.example.com", false},
		// Apache appends its value to what the client sent
		{"client-supplied forwarded host first", "https://evil.example", "evil.example, conquer.example.com", false},
		{"garbage Origin", "://", "", false},
	}
	for _, c := range cases {
		if got := sameOrigin(req(c.origin, c.forwarded)); got != c.want {
			t.Errorf("%s: sameOrigin = %v, want %v", c.name, got, c.want)
		}
	}
}

func TestClientIPIsTheOneApacheAdded(t *testing.T) {
	r := httptest.NewRequest(http.MethodPost, "/join/api/request", nil)
	r.RemoteAddr = "172.18.0.3:40000"
	if got := clientIP(r); got != "172.18.0.3" {
		t.Errorf("without a forwarded address: %q", got)
	}
	// A client can send its own X-Forwarded-For; Apache appends the real one
	r.Header.Set("X-Forwarded-For", "6.6.6.6, 203.0.113.9")
	if got := clientIP(r); got != "203.0.113.9" {
		t.Errorf("with a forged first address: %q", got)
	}
}

func TestLimiter(t *testing.T) {
	l := newLimiter(2, time.Hour)
	if !l.allow("a") || !l.allow("a") {
		t.Fatal("the first two events are within the limit")
	}
	if l.allow("a") {
		t.Error("the third event is over the limit")
	}
	if !l.allow("b") {
		t.Error("another address has its own count")
	}
	if !l.full("a") || l.full("b") {
		t.Error("full reports only the exhausted key")
	}
}

func TestShortTextIsOneLine(t *testing.T) {
	got := shortText("a\r\nb\tc\x0b d", 100)
	if strings.ContainsAny(got, "\r\n\t") {
		t.Errorf("shortText left a line break or tab: %q", got)
	}
	if r := []rune(shortText(strings.Repeat("é", 600), 500)); len(r) != 500 {
		t.Errorf("shortText kept %d characters, want 500", len(r))
	}
}

func TestEmailsCannotCarryHeaders(t *testing.T) {
	for _, e := range []string{"a@b.co", "first.last+tag@example.org"} {
		if !validEmail(e) {
			t.Errorf("%q should be accepted", e)
		}
	}
	for _, e := range []string{
		"a@b", "a b@c.de", "a@b.co\r\nBcc: x@y.zz", "a@b.co\nBcc: x@y.zz", "<a@b.co>", "a@b.co,c@d.ee",
		"\"a\"@b.co", "a@b.co;c@d.ee", strings.Repeat("x", 121) + "@b.co",
	} {
		if validEmail(e) {
			t.Errorf("%q should be refused", e)
		}
	}
	if got := oneLine("Hello\r\nBcc: x@y.zz"); strings.ContainsAny(got, "\r\n") {
		t.Errorf("oneLine left a line break: %q", got)
	}
}

func TestAdminNeedsTheMark(t *testing.T) {
	dir := t.TempDir()
	g := &gate{lib: dir, admin: newLimiter(120, time.Minute)}
	write := func(content string) {
		if err := os.WriteFile(dir+"/.players", []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	call := func(user string) int {
		r := httptest.NewRequest(http.MethodGet, "/admin/api/state", nil)
		if user != "" {
			r.Header.Set("X-WEBAUTH-USER", user)
		}
		w := httptest.NewRecorder()
		if g.adminOnly(w, r, http.MethodGet) {
			return http.StatusOK
		}
		return w.Code
	}
	// "x:*:y" is a nation called "*:y" for the shell tools and no administrator
	write("boss:*\nplayer:sahara\nodd:*:y\nwaiting:?\nnew:+\n")
	cases := map[string]int{
		"":        http.StatusUnauthorized,
		"boss":    http.StatusOK,
		"player":  http.StatusForbidden,
		"odd":     http.StatusForbidden,
		"waiting": http.StatusForbidden,
		"new":     http.StatusForbidden,
		"nobody":  http.StatusForbidden,
		"Boss":    http.StatusForbidden,
		"-boss":   http.StatusForbidden,
	}
	for user, want := range cases {
		if got := call(user); got != want {
			t.Errorf("X-WEBAUTH-USER %q: status %d, want %d", user, got, want)
		}
	}
}

func TestNationArgs(t *testing.T) {
	for _, ok := range []string{"fung", "Anorian", "+", "*", "a.b_c-1"} {
		if !nationArgRe.MatchString(ok) {
			t.Errorf("%q should be accepted", ok)
		}
	}
	for _, bad := range []string{"", "toolongname", "a b", "a:b", "+*", "../x", "a\nb"} {
		if nationArgRe.MatchString(bad) {
			t.Errorf("%q should be refused", bad)
		}
	}
}
