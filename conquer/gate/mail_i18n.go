// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import "strings"

// The texts of the notification mails (to the administrator) and of the webhook message, by
// language and key. Placeholders are {name}s, filled in by mailText:
//
//	account  the account name
//	count    how many requests a digest holds
//	list     the accounts of a digest, one per line
//	url      the administrator page
//
// A language or key that is missing falls back to English. The test
// mail stays in English.
var mailTexts = map[string]map[string]string{
	"en": {
		"subject_request": "Conquer: {account} asks for a seat",
		"body_request":    "{account} asks for a seat in Conquer.\n\nApprove or reject it here: {url}\n",
		"webhook_request": "Conquer: {account} asks for a seat. Approve it at {url}",
		"subject_digest":  "Conquer: {count} new requests for a seat",
		"body_digest":     "{count} accounts ask for a seat in Conquer:\n\n{list}\nApprove or reject them here: {url}\n",
		"webhook_digest":  "Conquer: {count} new requests for a seat. Approve them at {url}",
	},
	"es": {
		"subject_request": "Conquer: {account} pide una plaza",
		"body_request":    "{account} pide una plaza en Conquer.\n\nApruébala o recházala aquí: {url}\n",
		"webhook_request": "Conquer: {account} pide una plaza. Apruébala en {url}",
		"subject_digest":  "Conquer: {count} solicitudes nuevas de plaza",
		"body_digest":     "{count} cuentas piden una plaza en Conquer:\n\n{list}\nApruébalas o recházalas aquí: {url}\n",
		"webhook_digest":  "Conquer: {count} solicitudes nuevas de plaza. Apruébalas en {url}",
	},
	"de": {
		"subject_request": "Conquer: {account} fragt nach einem Platz",
		"body_request":    "{account} fragt nach einem Platz in Conquer.\n\nHier freigeben oder ablehnen: {url}\n",
		"webhook_request": "Conquer: {account} fragt nach einem Platz. Freigeben unter {url}",
		"subject_digest":  "Conquer: {count} neue Anfragen nach einem Platz",
		"body_digest":     "{count} Konten fragen nach einem Platz in Conquer:\n\n{list}\nHier freigeben oder ablehnen: {url}\n",
		"webhook_digest":  "Conquer: {count} neue Anfragen nach einem Platz. Freigeben unter {url}",
	},
	"pl": {
		"subject_request": "Conquer: {account} prosi o miejsce",
		"body_request":    "{account} prosi o miejsce w Conquer.\n\nZatwierdź lub odrzuć tutaj: {url}\n",
		"webhook_request": "Conquer: {account} prosi o miejsce. Zatwierdź na {url}",
		"subject_digest":  "Conquer: {count} nowych próśb o miejsce",
		"body_digest":     "{count} kont prosi o miejsce w Conquer:\n\n{list}\nZatwierdź lub odrzuć tutaj: {url}\n",
		"webhook_digest":  "Conquer: {count} nowych próśb o miejsce. Zatwierdź na {url}",
	},
	"pt-br": {
		"subject_request": "Conquer: {account} pede uma vaga",
		"body_request":    "{account} pede uma vaga no Conquer.\n\nAprove ou recuse aqui: {url}\n",
		"webhook_request": "Conquer: {account} pede uma vaga. Aprove em {url}",
		"subject_digest":  "Conquer: {count} novos pedidos de vaga",
		"body_digest":     "{count} contas pedem uma vaga no Conquer:\n\n{list}\nAprove ou recuse aqui: {url}\n",
		"webhook_digest":  "Conquer: {count} novos pedidos de vaga. Aprove em {url}",
	},
	"ru": {
		"subject_request": "Conquer: {account} просит место",
		"body_request":    "{account} просит место в Conquer.\n\nОдобрить или отклонить можно здесь: {url}\n",
		"webhook_request": "Conquer: {account} просит место. Одобрить: {url}",
		"subject_digest":  "Conquer: новых заявок на место: {count}",
		"body_digest":     "Заявок на место в Conquer: {count}\n\n{list}\nОдобрить или отклонить можно здесь: {url}\n",
		"webhook_digest":  "Conquer: новых заявок на место: {count}. Одобрить: {url}",
	},
	"zh": {
		"subject_request": "Conquer：{account} 申请席位",
		"body_request":    "{account} 申请 Conquer 中的席位。\n\n请在这里批准或拒绝：{url}\n",
		"webhook_request": "Conquer：{account} 申请席位。请在 {url} 批准",
		"subject_digest":  "Conquer：{count} 个新的席位申请",
		"body_digest":     "有 {count} 个账号申请 Conquer 中的席位：\n\n{list}\n请在这里批准或拒绝：{url}\n",
		"webhook_digest":  "Conquer：{count} 个新的席位申请。请在 {url} 批准",
	},
}

// mailLangs are the languages of the site
var mailLangs = []string{"en", "es", "de", "pl", "pt-br", "ru", "zh"}

// validLang returns lang when it is one of the site's languages, else "en"
func validLang(lang string) string {
	lang = strings.ToLower(strings.TrimSpace(lang))
	for _, l := range mailLangs {
		if l == lang {
			return lang
		}
	}
	return "en"
}

// mailText returns the text of key in lang (English when missing) with the
// {name} placeholders replaced by vars (pairs: name, value, ...). The
// values are inserted as they are and not looked at again.
func mailText(lang, key string, vars ...string) string {
	s, ok := mailTexts[lang][key]
	if !ok {
		s = mailTexts["en"][key]
	}
	pairs := make([]string, 0, len(vars))
	for i := 0; i+1 < len(vars); i += 2 {
		pairs = append(pairs, "{"+vars[i]+"}", vars[i+1])
	}
	return strings.NewReplacer(pairs...).Replace(s)
}
