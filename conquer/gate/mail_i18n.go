// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import "strings"

// The texts of the notification mails and of the webhook message, by
// language and key. Placeholders are {name}s, filled in by mailText:
//
//	account  the account name
//	details  the "Email:" and "Message:" lines of a request (may be empty)
//	url      the administrator page
//	site     the game's website
//	turn     the current turn
//	email    the player's address (line_email)
//	message  the player's message (line_message)
//
// A language or key that is missing falls back to English. The test
// mail stays in English.
var mailTexts = map[string]map[string]string{
	"en": {
		"subject_request":     "Conquer: {account} asks for a seat",
		"body_request":        "{account} asks for a seat in Conquer.\n\n{details}\nApprove or reject it here: {url}\n",
		"line_email":          "Email: {email}\n",
		"line_message":        "Message: {message}\n",
		"webhook_request":     "Conquer: {account} asks for a seat. Approve it at {url}",
		"subject_approved":    "Conquer: your seat is approved",
		"site_fallback":       "the game's website",
		"body_approved_early": "Hello {account},\n\nYour seat in Conquer is approved.\n\nPress Play at {site} with your account and password, and found your nation.\n\nSee you in the game.\n",
		"body_approved_late":  "Hello {account},\n\nYour seat in Conquer is approved.\n\nThe game is already at turn {turn}, so the administrator will add your nation by hand. Sign in and press Play at {site} to see your status; you will be contacted when it is ready.\n\nSee you in the game.\n",
	},
	"es": {
		"subject_request":     "Conquer: {account} pide una plaza",
		"body_request":        "{account} pide una plaza en Conquer.\n\n{details}\nApruébala o recházala aquí: {url}\n",
		"line_email":          "Correo: {email}\n",
		"line_message":        "Mensaje: {message}\n",
		"webhook_request":     "Conquer: {account} pide una plaza. Apruébala en {url}",
		"subject_approved":    "Conquer: tu plaza está aprobada",
		"site_fallback":       "la web del juego",
		"body_approved_early": "Hola {account}:\n\nTu plaza en Conquer está aprobada.\n\nPulsa Jugar en {site} con tu cuenta y tu contraseña, y funda tu nación.\n\nNos vemos en la partida.\n",
		"body_approved_late":  "Hola {account}:\n\nTu plaza en Conquer está aprobada.\n\nLa partida ya va por el turno {turn}, así que el administrador añadirá tu nación a mano. Entra y pulsa Jugar en {site} para ver cómo va; te avisaremos cuando esté lista.\n\nNos vemos en la partida.\n",
	},
	"de": {
		"subject_request":     "Conquer: {account} fragt nach einem Platz",
		"body_request":        "{account} fragt nach einem Platz in Conquer.\n\n{details}\nHier freigeben oder ablehnen: {url}\n",
		"line_email":          "E-Mail: {email}\n",
		"line_message":        "Nachricht: {message}\n",
		"webhook_request":     "Conquer: {account} fragt nach einem Platz. Freigeben unter {url}",
		"subject_approved":    "Conquer: dein Platz ist freigegeben",
		"site_fallback":       "die Website des Spiels",
		"body_approved_early": "Hallo {account},\n\ndein Platz in Conquer ist freigegeben.\n\nDrück auf {site} mit deinem Konto und deinem Passwort auf Spielen und gründe deine Nation.\n\nBis gleich im Spiel.\n",
		"body_approved_late":  "Hallo {account},\n\ndein Platz in Conquer ist freigegeben.\n\nDas Spiel ist schon bei Runde {turn}, deshalb fügt der Spielleiter deine Nation von Hand hinzu. Melde dich an und drück auf {site} auf Spielen, um deinen Stand zu sehen; wir melden uns, sobald sie bereit ist.\n\nBis gleich im Spiel.\n",
	},
	"pl": {
		"subject_request":     "Conquer: {account} prosi o miejsce",
		"body_request":        "{account} prosi o miejsce w Conquer.\n\n{details}\nZatwierdź lub odrzuć tutaj: {url}\n",
		"line_email":          "E-mail: {email}\n",
		"line_message":        "Wiadomość: {message}\n",
		"webhook_request":     "Conquer: {account} prosi o miejsce. Zatwierdź na {url}",
		"subject_approved":    "Conquer: twoje miejsce jest zatwierdzone",
		"site_fallback":       "strona gry",
		"body_approved_early": "Cześć {account},\n\ntwoje miejsce w Conquer jest zatwierdzone.\n\nKliknij Graj na {site}, zaloguj się swoim kontem i hasłem, i załóż swój naród.\n\nDo zobaczenia w grze.\n",
		"body_approved_late":  "Cześć {account},\n\ntwoje miejsce w Conquer jest zatwierdzone.\n\nGra jest już w turze {turn}, więc administrator doda twój naród ręcznie. Zaloguj się i kliknij Graj na {site}, żeby zobaczyć swój stan; damy ci znać, gdy będzie gotowy.\n\nDo zobaczenia w grze.\n",
	},
	"pt-br": {
		"subject_request":     "Conquer: {account} pede uma vaga",
		"body_request":        "{account} pede uma vaga no Conquer.\n\n{details}\nAprove ou recuse aqui: {url}\n",
		"line_email":          "E-mail: {email}\n",
		"line_message":        "Mensagem: {message}\n",
		"webhook_request":     "Conquer: {account} pede uma vaga. Aprove em {url}",
		"subject_approved":    "Conquer: a sua vaga foi aprovada",
		"site_fallback":       "o site do jogo",
		"body_approved_early": "Olá {account},\n\nA sua vaga no Conquer foi aprovada.\n\nClique em Jogar em {site} com a sua conta e a sua senha, e funde a sua nação.\n\nAté já no jogo.\n",
		"body_approved_late":  "Olá {account},\n\nA sua vaga no Conquer foi aprovada.\n\nO jogo já está no turno {turn}, então o administrador vai adicionar a sua nação manualmente. Entre e clique em Jogar em {site} para ver como está; entraremos em contato quando ela estiver pronta.\n\nAté já no jogo.\n",
	},
	"ru": {
		"subject_request":     "Conquer: {account} просит место",
		"body_request":        "{account} просит место в Conquer.\n\n{details}\nОдобрить или отклонить можно здесь: {url}\n",
		"line_email":          "Почта: {email}\n",
		"line_message":        "Сообщение: {message}\n",
		"webhook_request":     "Conquer: {account} просит место. Одобрить: {url}",
		"subject_approved":    "Conquer: ваше место одобрено",
		"site_fallback":       "сайт игры",
		"body_approved_early": "Здравствуйте, {account}!\n\nВаше место в Conquer одобрено.\n\nНажмите «Играть» на {site}, войдите со своей учётной записью и паролем и основайте свой народ.\n\nДо встречи в игре.\n",
		"body_approved_late":  "Здравствуйте, {account}!\n\nВаше место в Conquer одобрено.\n\nИгра уже на ходу {turn}, поэтому администратор добавит ваш народ вручную. Войдите и нажмите «Играть» на {site}, чтобы увидеть своё состояние; мы свяжемся с вами, когда всё будет готово.\n\nДо встречи в игре.\n",
	},
	"zh": {
		"subject_request":     "Conquer：{account} 申请席位",
		"body_request":        "{account} 申请 Conquer 中的席位。\n\n{details}\n请在这里批准或拒绝：{url}\n",
		"line_email":          "邮箱：{email}\n",
		"line_message":        "留言：{message}\n",
		"webhook_request":     "Conquer：{account} 申请席位。请在 {url} 批准",
		"subject_approved":    "Conquer：你的席位已获批",
		"site_fallback":       "游戏网站",
		"body_approved_early": "你好 {account}，\n\n你在 Conquer 中的席位已获批。\n\n请在 {site} 点击“开始游戏”，用你的账号和密码登录，然后建立你的国家。\n\n游戏里见。\n",
		"body_approved_late":  "你好 {account}，\n\n你在 Conquer 中的席位已获批。\n\n游戏已进行到第 {turn} 回合，所以管理员会手动为你添加国家。请登录并在 {site} 点击“开始游戏”查看状态；准备好后我们会联系你。\n\n游戏里见。\n",
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
