// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.auth

import com.vejeta.conquer.web.Site
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** The answer of the site's form login. */
sealed class LoginResult {
    /** The server gave a session cookie ([name]=[value]). */
    class Ok(val name: String, val value: String) : LoginResult()

    /** The server sent the user back to /login.html?failed=1: wrong account or password. */
    object Refused : LoginResult()

    /** No answer, or one that is not the login's (the server is not on the form login). */
    object Unavailable : LoginResult()
}

/**
 * Posts the site's login form (what web/login.html does): httpd_username,
 * httpd_password and httpd_location, urlencoded, to /login/do (a session
 * cookie) or /login/long ("remember me": 30 days). Redirects are not
 * followed: success is a 302 to the location with a `conquer_session` cookie,
 * failure a 302 to /login.html?failed=1. The caller puts the cookie into the
 * browser engine.
 */
object SiteLogin {
    const val COOKIE = "conquer_session"

    suspend fun login(account: Account, long: Boolean): LoginResult = withContext(Dispatchers.IO) {
        var conn: HttpURLConnection? = null
        try {
            conn = (URL(Site.URL + (if (long) "/login/long" else "/login/do")).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                instanceFollowRedirects = false
                connectTimeout = 15_000
                readTimeout = 20_000
                doOutput = true
                setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
            }
            val body = "httpd_username=" + enc(account.user) +
                "&httpd_password=" + enc(account.password) +
                "&httpd_location=" + enc("/play/")
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            val location = conn.getHeaderField("Location").orEmpty()
            if (code in 300..399 && "/login.html" in location) return@withContext LoginResult.Refused
            val cookie = conn.headerFields.entries
                .filter { it.key.equals("Set-Cookie", ignoreCase = true) }
                .flatMap { it.value }
                .firstOrNull { it.startsWith("$COOKIE=") }
            val value = cookie?.substringAfter('=')?.substringBefore(';')
            if (code in 300..399 && !value.isNullOrEmpty()) LoginResult.Ok(COOKIE, value) else LoginResult.Unavailable
        } catch (e: Exception) {
            LoginResult.Unavailable
        } finally {
            conn?.disconnect()
        }
    }

    private fun enc(s: String) = URLEncoder.encode(s, "UTF-8")
}
