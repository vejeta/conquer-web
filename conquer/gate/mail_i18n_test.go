// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import (
	"regexp"
	"sort"
	"strings"
	"testing"
)

var placeholderRe = regexp.MustCompile(`\{[a-z]+\}`)

func placeholders(s string) string {
	found := placeholderRe.FindAllString(s, -1)
	sort.Strings(found)
	return strings.Join(found, " ")
}

func TestMailTextsComplete(t *testing.T) {
	en := mailTexts["en"]
	for _, lang := range mailLangs {
		texts, ok := mailTexts[lang]
		if !ok {
			t.Errorf("language %s has no texts", lang)
			continue
		}
		if len(texts) != len(en) {
			t.Errorf("%s has %d keys, en has %d", lang, len(texts), len(en))
		}
		for key, enText := range en {
			text, ok := texts[key]
			if !ok || strings.TrimSpace(text) == "" {
				t.Errorf("%s: key %s is missing", lang, key)
				continue
			}
			if got, want := placeholders(text), placeholders(enText); got != want {
				t.Errorf("%s: %s has placeholders [%s], en has [%s]", lang, key, got, want)
			}
		}
	}
	if len(mailTexts) != len(mailLangs) {
		t.Errorf("%d languages in mailTexts, %d expected", len(mailTexts), len(mailLangs))
	}
}

func TestMailTextFallbackAndValues(t *testing.T) {
	if got := mailText("xx", "subject_approved"); got != mailTexts["en"]["subject_approved"] {
		t.Errorf("unknown language did not fall back to en: %q", got)
	}
	// A value that looks like a placeholder is left alone
	if got := mailText("en", "webhook_request", "account", "{url}", "url", "U"); got != "Conquer: {url} asks for a seat. Approve it at U" {
		t.Errorf("unexpected: %q", got)
	}
	if validLang("PT-BR") != "pt-br" || validLang("fr") != "en" || validLang("") != "en" {
		t.Error("validLang")
	}
}
