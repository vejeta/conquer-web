// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import (
	"bytes"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"mime"
	"net"
	"net/http"
	"net/smtp"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// emailRe is a simple check, not the RFC: something@host.tld without
// spaces, quotes, commas or angle brackets
var emailRe = regexp.MustCompile(`^[^@\s<>",;:]+@[^@\s<>",;:]+\.[^@\s<>",;:]+$`)

func validEmail(s string) bool {
	return len(s) <= 120 && emailRe.MatchString(s)
}

// notifier tells the administrator about new requests (email and webhook)
// and the player about an approval (email). Settings come from the
// environment; nothing is sent for what is left empty.
type notifier struct {
	adminEmail string // NOTIFY_EMAIL, else ADMIN_CONTACT when it is an address
	smtpHost   string // SMTP_HOST, host:port
	smtpUser   string
	smtpPass   string
	from       string
	startTLS   bool
	webhook    string // SIGNUP_WEBHOOK_URL, else TURN_WEBHOOK_URL
	siteURL    string
	lang       string // NOTIFY_LANG: the administrator's language

	// Requests are announced in digests: at most one mail (and one webhook
	// message) per digestEvery, however many requests came in
	digestEvery time.Duration
	digestMu    sync.Mutex
	queue       []queuedRequest
	timer       *time.Timer
	lastDigest  time.Time
	mailer      func(to, subject, body string) error // sendMail unless a test replaces it
	poster      func(text string) error              // post unless a test replaces it
}

type queuedRequest struct{ account, email, message string }

const (
	defaultDigestEvery = 10 * time.Minute
	digestListMax      = 25 // accounts named in a digest; the rest are counted
)

func envOr(names ...string) string {
	for _, n := range names {
		if v := strings.TrimSpace(os.Getenv(n)); v != "" {
			return v
		}
	}
	return ""
}

// envFileValue reads NAME from a shell-style KEY="value" file
func envFileValue(path, name string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	for _, line := range strings.Split(string(data), "\n") {
		k, v, ok := strings.Cut(line, "=")
		if ok && strings.TrimSpace(k) == name {
			return strings.Trim(strings.TrimSpace(v), `"'`)
		}
	}
	return ""
}

func loadNotifier() *notifier {
	n := &notifier{
		adminEmail: envOr("NOTIFY_EMAIL"),
		smtpHost:   envOr("SMTP_HOST"),
		smtpUser:   envOr("SMTP_USER"),
		smtpPass:   os.Getenv("SMTP_PASSWORD"),
		from:       envOr("SMTP_FROM"),
		startTLS:   !strings.EqualFold(envOr("SMTP_STARTTLS"), "off"),
		webhook:    envOr("SIGNUP_WEBHOOK_URL", "TURN_WEBHOOK_URL"),
		siteURL:    strings.TrimRight(envOr("SITE_URL"), "/"),
		lang:       validLang(envOr("NOTIFY_LANG")),

		digestEvery: defaultDigestEvery,
	}
	if n.adminEmail == "" {
		if c := envOr("ADMIN_CONTACT"); validEmail(c) {
			n.adminEmail = c
		}
	}
	if n.siteURL == "" {
		n.siteURL = strings.TrimRight(envFileValue("/etc/conquer-web.env", "SITE_URL"), "/")
	}
	if n.siteURL == "" {
		if d := envOr("DOMAIN"); d != "" {
			n.siteURL = "https://" + d
		}
	}
	if n.from == "" {
		if validEmail(n.smtpUser) {
			n.from = n.smtpUser
		} else {
			n.from = "conquer@localhost"
		}
	}
	return n
}

func (n *notifier) mailEnabled() bool { return n.smtpHost != "" }

// header text safe to put in a mail header
func oneLine(s string) string {
	return strings.Join(strings.Fields(s), " ")
}

// sendMail sends one plain text message through the configured server
func (n *notifier) sendMail(to, subject, body string) error {
	if !n.mailEnabled() {
		return errors.New("SMTP_HOST is not set")
	}
	if !validEmail(to) {
		return fmt.Errorf("not an email address: %q", to)
	}
	host, port, err := net.SplitHostPort(n.smtpHost)
	if err != nil {
		host, port = n.smtpHost, "25"
	}
	addr := net.JoinHostPort(host, port)

	dialer := &net.Dialer{Timeout: 15 * time.Second}
	var conn net.Conn
	if port == "465" {
		// Implicit TLS (SMTPS)
		conn, err = tls.DialWithDialer(dialer, "tcp", addr, &tls.Config{ServerName: host})
	} else {
		conn, err = dialer.Dial("tcp", addr)
	}
	if err != nil {
		return err
	}
	_ = conn.SetDeadline(time.Now().Add(60 * time.Second))
	c, err := smtp.NewClient(conn, host)
	if err != nil {
		conn.Close()
		return err
	}
	defer c.Close()

	if port != "465" && n.startTLS {
		if ok, _ := c.Extension("STARTTLS"); !ok {
			return errors.New("the server does not offer STARTTLS (set SMTP_STARTTLS=off for a trusted relay)")
		}
		if err := c.StartTLS(&tls.Config{ServerName: host}); err != nil {
			return err
		}
	}
	if n.smtpUser != "" {
		if err := c.Auth(smtp.PlainAuth("", n.smtpUser, n.smtpPass, host)); err != nil {
			return err
		}
	}
	if err := c.Mail(n.from); err != nil {
		return err
	}
	if err := c.Rcpt(to); err != nil {
		return err
	}
	w, err := c.Data()
	if err != nil {
		return err
	}
	var msg bytes.Buffer
	fmt.Fprintf(&msg, "From: Conquer <%s>\r\n", n.from)
	fmt.Fprintf(&msg, "To: %s\r\n", to)
	fmt.Fprintf(&msg, "Subject: %s\r\n", mime.QEncoding.Encode("utf-8", oneLine(subject)))
	fmt.Fprintf(&msg, "Date: %s\r\n", time.Now().Format(time.RFC1123Z))
	fmt.Fprintf(&msg, "Message-ID: <%d.%d@%s>\r\n", time.Now().UnixNano(), os.Getpid(), host)
	msg.WriteString("MIME-Version: 1.0\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: 8bit\r\n\r\n")
	msg.WriteString(strings.ReplaceAll(strings.ReplaceAll(body, "\r\n", "\n"), "\n", "\r\n"))
	msg.WriteString("\r\n")
	if _, err := w.Write(msg.Bytes()); err != nil {
		return err
	}
	if err := w.Close(); err != nil {
		return err
	}
	return c.Quit()
}

// post sends text to the webhook the way turn.sh does ("text" for
// Slack and Mattermost, "content" for Discord)
func (n *notifier) post(text string) error {
	body, _ := json.Marshal(map[string]string{"text": text, "content": text})
	client := &http.Client{Timeout: 20 * time.Second}
	resp, err := client.Post(n.webhook, "application/json", bytes.NewReader(body))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("webhook answered %s", resp.Status)
	}
	return nil
}

func (n *notifier) adminURL() string {
	if n.siteURL == "" {
		return "/admin/"
	}
	return n.siteURL + "/admin/"
}

// newRequest queues a pending request for the administrator; it returns
// at once. The first request after a quiet spell is announced right away,
// the ones that follow within digestEvery are held and announced together
// in one message ("N new requests"), so a flood of requests is one mail.
func (n *notifier) newRequest(account, email, message string) {
	if n.adminEmail == "" && n.webhook == "" {
		return
	}
	n.digestMu.Lock()
	defer n.digestMu.Unlock()
	n.queue = append(n.queue, queuedRequest{account, email, message})
	if n.timer != nil {
		return // a digest is already due
	}
	wait := time.Until(n.lastDigest.Add(n.digestEvery))
	if wait < 0 {
		wait = 0
	}
	n.timer = time.AfterFunc(wait, n.flushDigest)
}

// flushDigest announces what is queued, in the administrator's language
func (n *notifier) flushDigest() {
	n.digestMu.Lock()
	batch := n.queue
	n.queue = nil
	n.timer = nil
	n.lastDigest = time.Now()
	n.digestMu.Unlock()
	if len(batch) == 0 {
		return
	}
	send, post := n.mailer, n.poster
	if send == nil {
		send = n.sendMail
	}
	if post == nil {
		post = n.post
	}
	if n.adminEmail != "" && (n.mailEnabled() || n.mailer != nil) {
		subject, body := n.digestMail(batch)
		if err := send(n.adminEmail, subject, body); err != nil {
			log.Printf("notify: mail to the administrator failed: %v", err)
		}
	}
	if n.webhook != "" {
		text := mailText(n.lang, "webhook_request", "account", batch[0].account, "url", n.adminURL())
		if len(batch) > 1 {
			text = mailText(n.lang, "webhook_digest", "count", strconv.Itoa(len(batch)), "url", n.adminURL())
		}
		if err := post(text); err != nil {
			log.Printf("notify: webhook failed: %v", err)
		}
	}
}

// digestMail is the mail for the queued requests: the usual one for a
// single request, a list (account and email, never the free-text message)
// for several
func (n *notifier) digestMail(batch []queuedRequest) (subject, body string) {
	if len(batch) == 1 {
		r := batch[0]
		details := ""
		if r.email != "" {
			details += mailText(n.lang, "line_email", "email", r.email)
		}
		if r.message != "" {
			details += mailText(n.lang, "line_message", "message", r.message)
		}
		return mailText(n.lang, "subject_request", "account", r.account),
			mailText(n.lang, "body_request", "account", r.account, "details", details, "url", n.adminURL())
	}
	var list strings.Builder
	for i, r := range batch {
		if i == digestListMax {
			fmt.Fprintf(&list, "  ... +%d\n", len(batch)-digestListMax)
			break
		}
		line := "  - " + oneLine(r.account)
		if r.email != "" {
			line += " <" + oneLine(r.email) + ">"
		}
		list.WriteString(line + "\n")
	}
	count := strconv.Itoa(len(batch))
	return mailText(n.lang, "subject_digest", "count", count),
		mailText(n.lang, "body_digest", "count", count, "list", list.String(), "url", n.adminURL())
}

// approved tells the player their seat is approved, in their language;
// it returns at once
func (n *notifier) approved(account, email, lang string, turn int) {
	lang = validLang(lang)
	go func() {
		site := n.siteURL
		if site == "" {
			site = mailText(lang, "site_fallback")
		}
		key := "body_approved_early"
		if turn > lastJoinTurn {
			key = "body_approved_late"
		}
		body := mailText(lang, key, "account", account, "site", site, "turn", strconv.Itoa(turn))
		if err := n.sendMail(email, mailText(lang, "subject_approved", "account", account), body); err != nil {
			log.Printf("notify: approval mail to %s failed: %v", account, err)
		}
	}()
}
