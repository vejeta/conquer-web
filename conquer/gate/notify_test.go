// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import (
	"fmt"
	"strings"
	"sync"
	"testing"
	"time"
)

type sent struct{ to, subject, body string }

// mu guards the slices the fake mailer and poster fill
var mu sync.Mutex

// digestNotifier collects the mails and webhook messages instead of sending them
func digestNotifier(every time.Duration) (*notifier, *[]sent, *[]string) {
	mails := &[]sent{}
	hooks := &[]string{}
	n := &notifier{adminEmail: "admin@example.org", webhook: "http://hook.invalid", siteURL: "https://game.example",
		digestEvery: every}
	n.mailer = func(to, subject, body string) error {
		mu.Lock()
		defer mu.Unlock()
		*mails = append(*mails, sent{to, subject, body})
		return nil
	}
	n.poster = func(text string) error {
		mu.Lock()
		defer mu.Unlock()
		*hooks = append(*hooks, text)
		return nil
	}
	return n, mails, hooks
}

func count(n *notifier, mails *[]sent) int {
	mu.Lock()
	defer mu.Unlock()
	return len(*mails)
}

func waitFor(t *testing.T, what string, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatalf("timed out: %s", what)
		}
		time.Sleep(5 * time.Millisecond)
	}
}

func TestFirstRequestIsAnnouncedAtOnce(t *testing.T) {
	n, mails, hooks := digestNotifier(time.Hour)
	n.newRequest("ana", "ana@example.org", "hello there")
	waitFor(t, "first mail", func() bool { return count(n, mails) == 1 })
	m := (*mails)[0]
	if m.to != "admin@example.org" || !strings.Contains(m.subject, "ana") ||
		!strings.Contains(m.body, "ana@example.org") || !strings.Contains(m.body, "hello there") {
		t.Errorf("a single request keeps the usual mail: %+v", m)
	}
	if len(*hooks) != 1 || !strings.Contains((*hooks)[0], "ana") {
		t.Errorf("webhook: %v", *hooks)
	}
}

func TestRequestsInsideTheIntervalAreOneDigest(t *testing.T) {
	n, mails, hooks := digestNotifier(300 * time.Millisecond)
	n.newRequest("first", "", "")
	waitFor(t, "first mail", func() bool { return count(n, mails) == 1 })
	for i := 0; i < 40; i++ {
		n.newRequest(fmt.Sprintf("bot%d", i), fmt.Sprintf("bot%d@example.org", i), "buy things <script>")
	}
	time.Sleep(100 * time.Millisecond)
	if got := count(n, mails); got != 1 {
		t.Fatalf("%d mails inside the interval, want still 1", got)
	}
	waitFor(t, "digest", func() bool { return count(n, mails) == 2 })
	time.Sleep(400 * time.Millisecond)
	if got := count(n, mails); got != 2 {
		t.Fatalf("40 requests made %d mails in total, want 2", got)
	}
	d := (*mails)[1]
	if !strings.Contains(d.subject, "40") || !strings.Contains(d.body, "bot0 <bot0@example.org>") ||
		!strings.Contains(d.body, "+15") || !strings.Contains(d.body, "https://game.example/admin/") {
		t.Errorf("digest: %+v", d)
	}
	if strings.Contains(d.body, "buy things") || strings.Contains(d.body, "bot30") {
		t.Errorf("the digest holds no user text and is cut at %d names: %s", digestListMax, d.body)
	}
	if len(*hooks) != 2 || !strings.Contains((*hooks)[1], "40") {
		t.Errorf("webhook: %v", *hooks)
	}
}

func TestDigestKeepsAtMostOneMailPerInterval(t *testing.T) {
	n, mails, _ := digestNotifier(150 * time.Millisecond)
	start := time.Now()
	for time.Since(start) < 700*time.Millisecond {
		n.newRequest("x", "", "")
		time.Sleep(10 * time.Millisecond)
	}
	waitFor(t, "last digest", func() bool { n.digestMu.Lock(); defer n.digestMu.Unlock(); return len(n.queue) == 0 })
	time.Sleep(50 * time.Millisecond)
	// 0.7 s of requests at 0.15 s: the first at once and at most one per interval after
	if got := count(n, mails); got > 6 || got < 2 {
		t.Errorf("%d mails in %v with an interval of 150ms", got, time.Since(start))
	}
}

func TestDigestIsInTheAdministratorsLanguage(t *testing.T) {
	n, mails, _ := digestNotifier(time.Hour)
	n.lang = "es"
	n.digestMu.Lock()
	n.lastDigest = time.Now() // as if a mail had just gone out
	n.digestMu.Unlock()
	n.newRequest("a", "", "")
	n.newRequest("b", "", "")
	n.flushDigest()
	if len(*mails) != 1 || !strings.Contains((*mails)[0].subject, "solicitudes nuevas") {
		t.Errorf("%+v", *mails)
	}
}

func TestNothingToAnnounceWithoutSettings(t *testing.T) {
	n := &notifier{digestEvery: time.Minute}
	n.newRequest("a", "", "")
	if n.timer != nil || len(n.queue) != 0 {
		t.Error("with no mail address and no webhook nothing is queued")
	}
}
