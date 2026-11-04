// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

// What a signed-in player can do with the account, and what a player who
// forgot the password can do with the recovery code. The site keeps no
// email address, so the recovery code is the only way back:
//
//   - the first time an approved player reaches a signed-in page the page
//     calls POST /account/api/init; the gate makes a code (12 characters
//     from crypto/rand, written XXXX-XXXX-XXXX), conquer-signup stores only
//     its bcrypt hash in lib/.recovery, and the code is in that one answer:
//     the page shows it once. Later calls only say that a code exists.
//   - POST /account/api/password changes the password (needs the current
//     one) and POST /account/api/recovery makes a new code (needs the
//     current password; the old code stops working).
//   - POST /join/api/recover sets a new password for an account and a
//     recovery code, and answers with a NEW code (the used one is void).
//
// The account is the one Apache signed in (X-WEBAUTH-USER): Apache drops
// any value a client sends and sets it from the session, and only Apache
// can reach this service, as for the administrator page. Wrong current
// passwords and wrong codes are limited to 5 an hour per address and per
// account; both are logged ("refused", status 403) in a way fail2ban can
// match (vps/fail2ban/conquer-recover.conf).

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"log"
	"net/http"
	"regexp"
	"strings"
	"time"
)

const (
	// Wrong passwords or codes per hour, for one address and for one account
	accountFailures = 5
	// The alphabet of a recovery code: 32 characters without I, O, 0 and 1
	recoveryAlphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
)

var recoveryRe = regexp.MustCompile(`^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$`)

// newRecoveryCode: 12 characters (60 bits) from crypto/rand as XXXX-XXXX-XXXX
func newRecoveryCode() string {
	b := make([]byte, 12)
	if _, err := rand.Read(b); err != nil {
		log.Fatalf("no random numbers: %v", err)
	}
	out := make([]byte, 0, 14)
	for i, v := range b {
		if i > 0 && i%4 == 0 {
			out = append(out, '-')
		}
		out = append(out, recoveryAlphabet[int(v)&31]) // 32 divides 256: no bias
	}
	return string(out)
}

// normalizeRecovery accepts "k7qm 3xpa 9rtd", "K7QM3XPA9RTD" and the dashed form
func normalizeRecovery(s string) string {
	s = strings.ToUpper(strings.NewReplacer(" ", "", "-", "", "\t", "").Replace(s))
	if len(s) == 12 {
		s = s[:4] + "-" + s[4:8] + "-" + s[8:]
	}
	return s
}

// goodPassword checks a new password the way the sign-up does: 8 to 72
// bytes on one line. It returns the error code, or "".
func goodPassword(p string) string {
	switch {
	case len(p) < 8:
		return "short_password"
	case len(p) > 72 || strings.ContainsAny(p, "\r\n\x00"):
		return "bad_password"
	}
	return ""
}

// hasRecovery says whether the account has a recovery code (lib/.recovery
// holds "account:bcrypt hash" lines, never a code)
func (g *gate) hasRecovery(account string) bool {
	for _, line := range readLines(g.lib + "/.recovery") {
		if name, _, ok := strings.Cut(line, ":"); ok && name == account {
			return true
		}
	}
	return false
}

// signedIn checks what every player endpoint needs: POST, the account
// Apache signed in, the same-origin check and the per address limit. It
// answers and returns false when the request may not go on.
func (g *gate) signedIn(w http.ResponseWriter, r *http.Request) (string, bool) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", "POST")
		fail(w, http.StatusMethodNotAllowed, "method")
		return "", false
	}
	user := strings.TrimSpace(r.Header.Get("X-WEBAUTH-USER"))
	if user == "" {
		fail(w, http.StatusUnauthorized, "unauthenticated")
		return "", false
	}
	if !accountRe.MatchString(user) {
		fail(w, http.StatusForbidden, "forbidden")
		return "", false
	}
	if !sameOrigin(r) {
		fail(w, http.StatusForbidden, "origin")
		return "", false
	}
	if !g.acct.allow("ip:" + clientIP(r)) {
		fail(w, http.StatusTooManyRequests, "rate_limited")
		return "", false
	}
	return user, true
}

// limited says whether the address or the account used up its wrong tries
func limited(l *limiter, ip, account string) bool {
	return l.full("ip:"+ip) || l.full("acct:"+account)
}

// strike records a wrong password or code for the address and the account
func strike(l *limiter, ip, account string) {
	l.allow("ip:" + ip)
	l.allow("acct:" + account)
}

// helperErr answers for a failed run of conquer-signup: a known reason with
// its status, anything else as a server error (logged with what it said)
func (g *gate) helperErr(w http.ResponseWriter, what, account string, err error, out string, extra map[int]string) (string, bool) {
	if reason, status, ok := helperStatus(err, extra); ok {
		fail(w, status, reason)
		return reason, true
	}
	log.Printf("%s failed: account=%s: %v %s", what, account, err, out)
	fail(w, http.StatusInternalServerError, "server")
	return "", false
}

// accountInit: the first call of an approved account makes its recovery code
func (g *gate) accountInit(w http.ResponseWriter, r *http.Request) {
	user, ok := g.signedIn(w, r)
	if !ok {
		return
	}
	body := map[string]any{"ok": true, "account": user, "has_recovery": g.hasRecovery(user)}
	if body["has_recovery"] == false {
		code := newRecoveryCode()
		ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
		defer cancel()
		out, err := g.runHelper(ctx, code+"\n", "recovery-init", user)
		switch {
		case err == nil:
			body["has_recovery"], body["recovery_code"] = true, code
			log.Printf("recovery code made for account %s", user)
		default:
			// 2: made by another call a moment ago; 3: waiting for approval
			// (no code yet): neither is an error
			if reason, _, known := helperStatus(err, map[int]string{2: "has_recovery", 3: "pending"}); known {
				body["has_recovery"] = reason == "has_recovery"
			} else {
				log.Printf("recovery code failed: account=%s: %v %s", user, err, out)
				fail(w, http.StatusInternalServerError, "server")
				return
			}
		}
	}
	reply(w, http.StatusOK, body)
}

// accountPassword changes the password of the signed-in account
func (g *gate) accountPassword(w http.ResponseWriter, r *http.Request) {
	user, ok := g.signedIn(w, r)
	if !ok {
		return
	}
	var in struct {
		Current string `json:"current"`
		New     string `json:"new"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 2048)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	ip := clientIP(r)
	if e := goodPassword(in.New); e != "" {
		fail(w, http.StatusBadRequest, e)
		return
	}
	if limited(g.pwFail, ip, user) {
		log.Printf("account password refused: too many wrong passwords account=%s ip=%s", user, ip)
		fail(w, http.StatusTooManyRequests, "rate_limited")
		return
	}
	if in.Current == "" || len(in.Current) > 72 || strings.ContainsAny(in.Current, "\r\n\x00") {
		strike(g.pwFail, ip, user)
		log.Printf("account password refused: wrong current password account=%s ip=%s", user, ip)
		fail(w, http.StatusForbidden, "bad_current")
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	out, err := g.runHelper(ctx, in.Current+"\n"+in.New+"\n", "passwd", user)
	if err != nil {
		reason, known := g.helperErr(w, "account password", user, err, out, map[int]string{2: "bad_current", 3: "no_account"})
		if known && reason == "bad_current" {
			strike(g.pwFail, ip, user)
			log.Printf("account password refused: wrong current password account=%s ip=%s", user, ip)
		}
		return
	}
	log.Printf("account: password changed account=%s ip=%s", user, ip)
	reply(w, http.StatusOK, map[string]any{"ok": true})
}

// accountRecovery makes a new recovery code for the signed-in account; the
// old one stops working. The current password is needed.
func (g *gate) accountRecovery(w http.ResponseWriter, r *http.Request) {
	user, ok := g.signedIn(w, r)
	if !ok {
		return
	}
	var in struct {
		Current string `json:"current"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 2048)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	ip := clientIP(r)
	if limited(g.pwFail, ip, user) {
		log.Printf("recovery code refused: too many wrong passwords account=%s ip=%s", user, ip)
		fail(w, http.StatusTooManyRequests, "rate_limited")
		return
	}
	if in.Current == "" || len(in.Current) > 72 || strings.ContainsAny(in.Current, "\r\n\x00") {
		strike(g.pwFail, ip, user)
		log.Printf("recovery code refused: wrong current password account=%s ip=%s", user, ip)
		fail(w, http.StatusForbidden, "bad_current")
		return
	}
	code := newRecoveryCode()
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	out, err := g.runHelper(ctx, in.Current+"\n"+code+"\n", "recovery-renew", user)
	if err != nil {
		reason, known := g.helperErr(w, "recovery code", user, err, out, map[int]string{2: "bad_current", 3: "no_account"})
		if known && reason == "bad_current" {
			strike(g.pwFail, ip, user)
			log.Printf("recovery code refused: wrong current password account=%s ip=%s", user, ip)
		}
		return
	}
	log.Printf("account: new recovery code made account=%s ip=%s", user, ip)
	reply(w, http.StatusOK, map[string]any{"ok": true, "recovery_code": code})
}

// recover sets a new password for a player who forgot it, with the account's
// recovery code, and answers with a new code (the used one is void)
func (g *gate) recover(w http.ResponseWriter, r *http.Request) {
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
	if !g.acct.allow("ip:" + ip) {
		fail(w, http.StatusTooManyRequests, "rate_limited")
		return
	}
	var in struct {
		Account  string `json:"account"`
		Code     string `json:"code"`
		Password string `json:"password"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 2048)
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		fail(w, http.StatusBadRequest, "bad_request")
		return
	}
	account := strings.TrimSpace(in.Account)
	if !accountRe.MatchString(account) {
		fail(w, http.StatusBadRequest, "bad_account")
		return
	}
	if e := goodPassword(in.Password); e != "" {
		fail(w, http.StatusBadRequest, e)
		return
	}
	if limited(g.recFail, ip, account) {
		log.Printf("recover refused: too many wrong codes account=%s ip=%s", account, ip)
		fail(w, http.StatusTooManyRequests, "rate_limited")
		return
	}
	code := normalizeRecovery(in.Code)
	if !recoveryRe.MatchString(code) {
		strike(g.recFail, ip, account)
		log.Printf("recover refused: wrong recovery code account=%s ip=%s", account, ip)
		fail(w, http.StatusForbidden, "bad_recovery")
		return
	}
	fresh := newRecoveryCode()
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Second)
	defer cancel()
	out, err := g.runHelper(ctx, code+"\n"+in.Password+"\n"+fresh+"\n", "reset", account)
	if err != nil {
		reason, known := g.helperErr(w, "recover", account, err, out, map[int]string{2: "bad_recovery", 3: "bad_recovery"})
		if known && reason == "bad_recovery" {
			strike(g.recFail, ip, account)
			log.Printf("recover refused: wrong recovery code account=%s ip=%s", account, ip)
		}
		return
	}
	log.Printf("recover: password reset with the recovery code account=%s ip=%s", account, ip)
	reply(w, http.StatusOK, map[string]any{"ok": true, "recovery_code": fresh})
}
