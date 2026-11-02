// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.ui

import android.app.Activity
import android.os.SystemClock
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.displayCutoutPadding
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.cefrium.CefriumBrowser
import com.cefrium.compose.CefriumBridge
import com.cefrium.compose.CefriumView
import com.cefrium.compose.rememberCefriumNavigator
import com.cefrium.compose.rememberCefriumViewState
import com.vejeta.conquer.R
import com.vejeta.conquer.auth.Account
import com.vejeta.conquer.auth.Credentials
import com.vejeta.conquer.web.Site
import kotlinx.coroutines.delay

/** A Basic authentication challenge the user has to answer. */
private class AuthRequest(
    val host: String,
    val realm: String,
    /** The server just refused the credentials that were sent. */
    val wrong: Boolean,
    val callback: CefriumBrowser.HttpAuthCallback,
)

/**
 * Answers the game server's Basic authentication. The saved account goes out
 * at once, but only to the game server (never to another host, nor to a
 * proxy), and only once in a while: when the server asks again right after,
 * the account was refused and the user is asked, so a wrong password does not
 * loop.
 */
private class AuthFlow(
    private val credentials: Credentials,
    private val ask: (AuthRequest) -> Unit,
) {
    private var lastProceed = 0L

    fun onRequest(
        host: String,
        realm: String,
        isProxy: Boolean,
        callback: CefriumBrowser.HttpAuthCallback,
    ) {
        if (isProxy || host != Site.HOST) {
            callback.cancel()
            return
        }
        val recent = SystemClock.elapsedRealtime() - lastProceed < RETRY_MS
        val saved = credentials.load()
        if (saved != null && !recent) {
            answered()
            callback.proceed(saved.user, saved.password)
        } else {
            ask(AuthRequest(host, realm, recent, callback))
        }
    }

    fun answered() {
        lastProceed = SystemClock.elapsedRealtime()
    }

    private companion object {
        const val RETRY_MS = 20_000L
    }
}

/**
 * A page in the browser: a thin bar that hides itself, the system bars
 * hidden (swipe from an edge to see them), Back walks the page history and
 * then leaves for [onExit].
 *
 * [bridge] answers window.cefriumQuery; [keepAwake] keeps the screen on
 * while the page is the game (/play/ or /try/).
 */
@Composable
fun BrowserScreen(
    url: String,
    bridge: CefriumBridge,
    credentials: Credentials,
    keepAwake: (source: String, on: Boolean) -> Unit,
    onExit: () -> Unit,
) {
    val state = rememberCefriumViewState(url)
    val navigator = rememberCefriumNavigator()
    var barVisible by remember { mutableStateOf(true) }
    var auth by remember { mutableStateOf<AuthRequest?>(null) }
    val flow = remember {
        AuthFlow(credentials) { request ->
            auth?.callback?.cancel()
            auth = request
        }
    }

    BackHandler {
        if (state.canGoBack) navigator.navigateBack() else onExit()
    }

    // Immersive: the page gets the whole screen
    val activity = LocalContext.current as Activity
    DisposableEffect(Unit) {
        val controller = WindowCompat.getInsetsController(activity.window, activity.window.decorView)
        controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        controller.hide(WindowInsetsCompat.Type.systemBars())
        onDispose { controller.show(WindowInsetsCompat.Type.systemBars()) }
    }

    // The screen stays on while a game is on it
    val current = state.lastLoadedUrl ?: url
    val game = "/play/" in current || "/try/" in current
    LaunchedEffect(game) { keepAwake("page", game) }
    DisposableEffect(Unit) {
        onDispose {
            keepAwake("page", false)
            keepAwake("bridge", false)
        }
    }

    LaunchedEffect(barVisible) {
        if (barVisible) {
            delay(BAR_MS)
            barVisible = false
        }
    }

    Box(Modifier.fillMaxSize().background(Color.Black)) {
        CefriumView(
            state = state,
            modifier = Modifier.fillMaxSize().displayCutoutPadding(),
            navigator = navigator,
            bridge = bridge,
            onBrowserReady = { browser ->
                browser.setHttpAuthHandler(
                    CefriumBrowser.HttpAuthHandler { host, realm, _, isProxy, callback ->
                        flow.onRequest(host, realm, isProxy, callback)
                    }
                )
            },
        )

        if (barVisible) {
            Surface(
                color = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
                modifier = Modifier.align(Alignment.TopCenter).fillMaxWidth(),
            ) {
                Column(Modifier.displayCutoutPadding()) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                        modifier = Modifier.padding(horizontal = 4.dp),
                    ) {
                        TextButton(onClick = onExit) { Text("‹ " + stringResource(R.string.home)) }
                        Text(
                            text = state.pageTitle ?: "",
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f),
                        )
                        TextButton(onClick = { navigator.reload() }) { Text("↻") }
                    }
                    if (state.isLoading) LinearProgressIndicator(Modifier.fillMaxWidth())
                }
            }
        } else {
            // Where the bar was: tap to bring it back
            Box(
                Modifier
                    .align(Alignment.TopCenter)
                    .width(56.dp)
                    .height(18.dp)
                    .background(Color(0x99161B22), RoundedCornerShape(bottomStart = 10.dp, bottomEnd = 10.dp))
                    .clickable { barVisible = true },
            )
        }

        if (state.rendererTermination != null) {
            Column(
                Modifier.align(Alignment.Center).padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Button(onClick = { navigator.reload() }) { Text("↻") }
            }
        }
    }

    auth?.let { request ->
        AuthDialog(
            request = request,
            saved = credentials.load(),
            onSignIn = { account, remember ->
                auth = null
                flow.answered()
                if (remember) credentials.save(account)
                request.callback.proceed(account.user, account.password)
            },
            onCancel = {
                auth = null
                request.callback.cancel()
            },
        )
    }
}

@Composable
private fun AuthDialog(
    request: AuthRequest,
    saved: Account?,
    onSignIn: (Account, Boolean) -> Unit,
    onCancel: () -> Unit,
) {
    var user by remember { mutableStateOf(saved?.user ?: "") }
    var password by remember { mutableStateOf("") }
    var rememberMe by remember { mutableStateOf(true) }

    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text(stringResource(R.string.login_title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(request.host + if (request.realm.isNotEmpty()) " · " + request.realm else "")
                if (request.wrong) {
                    Text(
                        stringResource(R.string.login_wrong),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
                OutlinedTextField(
                    value = user,
                    onValueChange = { user = it },
                    label = { Text(stringResource(R.string.login_user)) },
                    singleLine = true,
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text(stringResource(R.string.login_password)) },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                )
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { rememberMe = !rememberMe },
                ) {
                    Checkbox(checked = rememberMe, onCheckedChange = null)
                    Text(
                        stringResource(R.string.login_remember),
                        modifier = Modifier.padding(start = 8.dp),
                    )
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onSignIn(Account(user.trim(), password), rememberMe) },
                enabled = user.isNotBlank() && password.isNotEmpty(),
            ) { Text(stringResource(R.string.ok)) }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text(stringResource(R.string.cancel)) }
        },
    )
}

private const val BAR_MS = 3000L
