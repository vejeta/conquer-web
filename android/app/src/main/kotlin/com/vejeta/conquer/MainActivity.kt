// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer

import android.Manifest
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.vejeta.conquer.auth.Credentials
import com.vejeta.conquer.bridge.Bridge
import com.vejeta.conquer.ui.BrowserScreen
import com.vejeta.conquer.ui.ConquerTheme
import com.vejeta.conquer.ui.Home
import com.vejeta.conquer.web.LoopbackServer
import com.vejeta.conquer.web.Site
import com.vejeta.conquer.work.Notifications
import com.vejeta.conquer.work.TurnCheck

/**
 * The only Activity: the home screen, and a browser for the pages. The
 * offline pages come from the app's assets through a server on 127.0.0.1,
 * which lives as long as the Activity.
 */
class MainActivity : ComponentActivity() {
    private lateinit var server: LoopbackServer
    private lateinit var credentials: Credentials
    private lateinit var bridge: Bridge

    // Why the screen must stay on: "page" (a game is open), "bridge" (a page asked)
    private val awake = mutableSetOf<String>()

    private val askNotifications =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // The same port every run: the practice world is kept in the origin's
        // IndexedDB, and the port is part of the origin
        val prefs = getSharedPreferences("conquer", MODE_PRIVATE)
        server = LoopbackServer(assets, prefs.getInt("port", 0))
        server.start()
        prefs.edit().putInt("port", server.port).apply()

        credentials = Credentials(this)
        bridge = Bridge(this) { on -> keepAwake("bridge", on) }

        Notifications.ensureChannel(this)
        TurnCheck.schedule(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && !Notifications.canPost(this)) {
            askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            ConquerTheme {
                var url by remember { mutableStateOf<String?>(null) }
                val lang = Site.language()
                val open = url
                if (open == null) {
                    Home(
                        onPlayOnline = { url = Site.PLAY },
                        onPractice = { url = "${server.origin}/${Site.practicePage(lang)}" },
                        onTutorial = { url = "${server.origin}/${Site.tutorialPage(lang)}" },
                        onSite = { url = Site.siteUrl(lang) },
                        onForgetAccount = {
                            credentials.clear()
                            Toast.makeText(this@MainActivity, R.string.forgotten, Toast.LENGTH_SHORT).show()
                        },
                    )
                } else {
                    BrowserScreen(
                        url = open,
                        bridge = bridge.forView(server.origin, Site.URL),
                        credentials = credentials,
                        keepAwake = this@MainActivity::keepAwake,
                        onExit = { url = null },
                    )
                }
            }
        }
    }

    private fun keepAwake(source: String, on: Boolean) {
        if (on) awake.add(source) else awake.remove(source)
        if (awake.isEmpty()) {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    override fun onDestroy() {
        server.close()
        super.onDestroy()
    }
}
