// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.ui

import android.app.Activity
import android.content.pm.ActivityInfo
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
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.foundation.layout.size
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.sp
import com.vejeta.conquer.settings.AppSettings
import com.vejeta.conquer.sound.AppSound
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
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
import com.vejeta.conquer.auth.Credentials
import com.vejeta.conquer.auth.LoginResult
import com.vejeta.conquer.auth.SiteLogin
import com.vejeta.conquer.web.Site
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** A Basic authentication challenge the user has to answer. */
internal class AuthRequest(
    val host: String,
    val realm: String,
    /** The server just refused the credentials that were sent. */
    val wrong: Boolean,
    /** Null when the doors answer the site's login form instead of a Basic challenge. */
    val callback: CefriumBrowser.HttpAuthCallback?,
)

/**
 * Answers the game server's Basic authentication. The challenge comes from
 * /play/, the terminal that game.html frames, so it is a sub-frame's, and the
 * browser may ask again for the next request (the WebSocket): every challenge
 * from the game server is answered with the saved account, with no regard to
 * which frame asks. It goes out only to the game server (never to another
 * host, nor to a proxy), and only [MAX_ANSWERS] times within [RETRY_MS]: when
 * the server keeps asking, the account was refused and the user is asked, so a
 * wrong password does not loop.
 */
private class AuthFlow(
    private val credentials: Credentials,
    private val ask: (AuthRequest) -> Unit,
) {
    private var windowStart = 0L
    private var answers = 0

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
        val now = SystemClock.elapsedRealtime()
        if (now - windowStart > RETRY_MS) {
            windowStart = now
            answers = 0
        }
        val saved = credentials.load()
        if (saved != null && answers < MAX_ANSWERS) {
            answers++
            callback.proceed(saved.user, saved.password)
        } else {
            ask(AuthRequest(host, realm, answers > 0, callback))
        }
    }

    /** The user typed an account: it gets a fresh count of answers. */
    fun answered() {
        windowStart = SystemClock.elapsedRealtime()
        answers = 1
    }

    private companion object {
        const val RETRY_MS = 20_000L
        const val MAX_ANSWERS = 4
    }
}

/**
 * A page in the browser: a thin bar that hides itself, the system bars
 * hidden (swipe from an edge to see them), Back walks the page history and
 * then leaves for [onExit].
 *
 * [bridge] answers window.cefriumQuery; [keepAwake] keeps the screen on
 * while the page is the game (game.html, /play/ or /try/), which is shown
 * sideways (either landscape, following the sensor); the other pages turn
 * with the phone.
 */
@Composable
fun BrowserScreen(
    url: String,
    bridge: CefriumBridge,
    credentials: Credentials,
    keepAwake: (source: String, on: Boolean) -> Unit,
    onExit: () -> Unit,
    settings: AppSettings,
    sound: AppSound,
    detected: Race,
    onStory: () -> Unit,
) {
    val backLabel = stringResource(R.string.back)
    val state = rememberCefriumViewState(url)
    val navigator = rememberCefriumNavigator()
    var barVisible by remember { mutableStateOf(true) }
    var auth by remember { mutableStateOf<AuthRequest?>(null) }
    // The doors stay on screen while they swing open after "Speak friend"
    var leaving by remember { mutableStateOf<AuthRequest?>(null) }
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    // The user cancelled the doors on the login page: the web form stays
    var loginDismissed by remember { mutableStateOf(false) }
    var signOut by remember { mutableStateOf(false) }
    var sheet by remember { mutableStateOf(false) }
    val flow = remember {
        AuthFlow(credentials) { request ->
            auth?.callback?.cancel()
            leaving = null
            auth = request
        }
    }

    // Web history first, then the home screen (and from there the system leaves)
    val goBack = { if (state.canGoBack) navigator.navigateBack() else onExit() }
    BackHandler { goBack() }

    // The settings go into every page that loads, and again on any change
    // (a second time shortly after, for pages that set up their audio late)
    LaunchedEffect(state.isLoading, state.lastLoadedUrl, settings.version) {
        val at = state.lastLoadedUrl ?: return@LaunchedEffect
        if (state.isLoading || !(at.startsWith(Site.URL) || at.startsWith("http://127.0.0.1"))) return@LaunchedEffect
        navigator.evaluateJavaScript(settings.script())
        delay(1500)
        navigator.evaluateJavaScript(settings.script())
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
    val game = "/play/" in current || "/try/" in current || "/game.html" in current
    LaunchedEffect(game) { keepAwake("page", game) }

    // The server sent us to the login page (no session cookie): the doors
    // answer it instead of the web form, first with the saved account
    val onLogin = Site.isLoginPage(current)
    val wantsDoors = onLogin && "loggedout=" !in current && "failed=" !in current
    LaunchedEffect(onLogin) {
        if (!onLogin) loginDismissed = false
    }
    LaunchedEffect(wantsDoors) {
        if (!wantsDoors || loginDismissed || auth != null) return@LaunchedEffect
        val saved = credentials.load()
        if (saved != null) {
            busy = true
            val result = SiteLogin.login(saved, true)
            busy = false
            if (result is LoginResult.Ok) {
                sound.doorsOpen()
                navigator.setCookie(Site.URL, result.name, result.value)
                navigator.loadUrl(Site.PLAY)
                return@LaunchedEffect
            }
        }
        auth = AuthRequest(Site.HOST, "", false, null)
    }
    // The game is played sideways; everything else follows the phone
    DisposableEffect(game) {
        activity.requestedOrientation = if (game) {
            ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        } else {
            ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        }
        onDispose { }
    }
    DisposableEffect(Unit) {
        onDispose {
            activity.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
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
                        IconButton(onClick = { sound.tap(); goBack() }, modifier = Modifier.size(48.dp)) {
                            Text("←", fontSize = 24.sp, modifier = Modifier.semantics { contentDescription = backLabel })
                        }
                        TextButton(onClick = { sound.tap(); onExit() }) { Text(stringResource(R.string.home)) }
                        Text(
                            text = state.pageTitle ?: "",
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f),
                        )
                        TextButton(onClick = { sound.tap(); sheet = true }) { Text(stringResource(R.string.settings)) }
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

    val doors = auth ?: leaving
    if (doors != null) {
        DoorsDialog(
            request = doors,
            saved = credentials.load(),
            opening = auth == null,
            busy = busy,
            onSpeak = { account, remember ->
                val callback = doors.callback
                if (callback != null) {
                    // A Basic challenge (a server not yet on the form login)
                    auth = null
                    leaving = doors
                    sound.doorsOpen()
                    flow.answered()
                    if (remember) credentials.save(account)
                    callback.proceed(account.user, account.password)
                } else {
                    // The site's form: posted from here, the session cookie
                    // goes into the browser's cookie store
                    scope.launch {
                        busy = true
                        val result = SiteLogin.login(account, remember)
                        busy = false
                        when (result) {
                            is LoginResult.Ok -> {
                                sound.doorsOpen()
                                navigator.setCookie(Site.URL, result.name, result.value)
                                if (remember) credentials.save(account)
                                auth = null
                                leaving = doors
                                navigator.loadUrl(Site.PLAY)
                            }
                            // A new request: the runes flicker and the doors shake
                            is LoginResult.Refused -> {
                                sound.doorsFail()
                                auth = AuthRequest(doors.host, doors.realm, true, null)
                            }
                            // Not the form login (or no answer): the page's own way
                            is LoginResult.Unavailable -> {
                                loginDismissed = true
                                auth = null
                            }
                        }
                    }
                }
            },
            onCancel = {
                auth = null
                if (doors.callback == null) loginDismissed = true else doors.callback.cancel()
            },
        )
    }
    if (sheet) {
        SettingsSheet(
            settings = settings,
            sound = sound,
            detected = detected,
            onWatchStory = onStory,
            onSignOut = { signOut = true },
            onForgetAccount = { credentials.clear() },
            onClose = { sheet = false },
        )
    }
    if (signOut) {
        AlertDialog(
            onDismissRequest = { signOut = false },
            title = { Text(stringResource(R.string.sign_out)) },
            text = { Text(stringResource(R.string.sign_out_text)) },
            confirmButton = {
                TextButton(onClick = {
                    signOut = false
                    navigator.loadUrl(Site.LOGOUT)
                }) { Text(stringResource(R.string.sign_out)) }
            },
            dismissButton = {
                Row {
                    TextButton(onClick = { signOut = false }) { Text(stringResource(R.string.cancel)) }
                    TextButton(onClick = {
                        signOut = false
                        credentials.clear()
                        navigator.loadUrl(Site.LOGOUT)
                    }) { Text(stringResource(R.string.sign_out_forget)) }
                }
            },
        )
    }
    // Once the leaves are open the dialog goes; a refusal (a new request)
    // closes them again before this runs out
    val swinging = leaving
    val animationsOff = rememberAnimationsOff()
    LaunchedEffect(swinging) {
        if (swinging != null) {
            delay(if (animationsOff) 0L else DOORS_OPEN_MS + 150L)
            leaving = null
        }
    }
}

private const val BAR_MS = 3000L
