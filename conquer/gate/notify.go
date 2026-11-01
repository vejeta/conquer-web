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
	"strings"
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
}

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

// newRequest announces a pending request; it returns at once
func (n *notifier) newRequest(account, email, message string) {
	if n.adminEmail == "" && n.webhook == "" {
		return
	}
	go func() {
		if n.adminEmail != "" && n.mailEnabled() {
			var b strings.Builder
			fmt.Fprintf(&b, "%s asks for a seat in Conquer.\n\n", account)
			if email != "" {
				fmt.Fprintf(&b, "Email: %s\n", email)
			}
			if message != "" {
				fmt.Fprintf(&b, "Message: %s\n", message)
			}
			fmt.Fprintf(&b, "\nApprove or reject it here: %s\n", n.adminURL())
			if err := n.sendMail(n.adminEmail, "Conquer: "+account+" asks for a seat", b.String()); err != nil {
				log.Printf("notify: mail to the administrator failed: %v", err)
			}
		}
		if n.webhook != "" {
			text := fmt.Sprintf("Conquer: %s asks for a seat. Approve it at %s", account, n.adminURL())
			if err := n.post(text); err != nil {
				log.Printf("notify: webhook failed: %v", err)
			}
		}
	}()
}

// approved tells the player their seat is approved; it returns at once
func (n *notifier) approved(account, email string, turn int) {
	go func() {
		site := n.siteURL
		if site == "" {
			site = "the game's website"
		}
		var b strings.Builder
		fmt.Fprintf(&b, "Hello %s,\n\nYour seat in Conquer is approved.\n\n", account)
		if turn > lastJoinTurn {
			fmt.Fprintf(&b, "The game is already at turn %d, so the administrator will add your nation by hand. "+
				"Sign in and press Play at %s to see your status; you will be contacted when it is ready.\n", turn, site)
		} else {
			fmt.Fprintf(&b, "Press Play at %s with your account and password, and found your nation.\n", site)
		}
		b.WriteString("\nSee you in the game.\n")
		if err := n.sendMail(email, "Conquer: your seat is approved", b.String()); err != nil {
			log.Printf("notify: approval mail to %s failed: %v", account, err)
		}
	}()
}
