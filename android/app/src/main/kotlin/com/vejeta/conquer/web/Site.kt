// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.web

import android.os.LocaleList
import java.util.Locale

/** Addresses of the game server and of the pages of the website copy. */
object Site {
    const val HOST = "conquer.vejeta.com"
    const val URL = "https://$HOST"
    const val PLAY = "$URL/play/"
    const val STATUS = "$URL/status/status.json"

    /** Codes of web/site.js (LANGUAGES); the tutorial is written in all of them. */
    private val LANGUAGES = setOf("en", "es", "de", "pt-br", "pl", "ru", "zh")

    /**
     * The site's language for the phone's languages, chosen the way
     * web/site.js chooses from navigator.languages: the first one the site
     * has (by its full tag, or by its language), else English. Portuguese
     * of any country is the site's Brazilian Portuguese.
     */
    fun language(locales: LocaleList = LocaleList.getAdjustedDefault()): String {
        for (i in 0 until locales.size()) {
            val tag = locales[i].toLanguageTag().lowercase(Locale.ROOT)
            if (tag in LANGUAGES) return tag
            val base = tag.substringBefore('-')
            if (base in LANGUAGES) return base
            if (base == "pt") return "pt-br"
        }
        return "en"
    }

    /** The tutorial in [lang]: tutorial.html, tutorial.es.html... */
    fun tutorialPage(lang: String): String =
        (if (lang == "en") "tutorial.html" else "tutorial.$lang.html") + "?lang=$lang"

    /** The practice world, which runs from the app's own copy of the pages. */
    fun practicePage(lang: String): String = "try/?lang=$lang"

    /** The home page of the online site. */
    fun siteUrl(lang: String): String = "$URL/?lang=$lang"
}
