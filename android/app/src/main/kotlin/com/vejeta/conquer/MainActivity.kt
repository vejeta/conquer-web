// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer

import android.Manifest
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
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
import androidx.compose.runtime.setValue
import com.vejeta.conquer.auth.Credentials
import com.vejeta.conquer.bridge.Bridge
import com.vejeta.conquer.ui.BrowserScreen
import com.vejeta.conquer.ui.ConquerTheme
import com.vejeta.conquer.ui.Home
import com.vejeta.conquer.ui.Race
import com.vejeta.conquer.settings.AppSettings
import com.vejeta.conquer.sound.AppSound
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
    private lateinit var prefs: SharedPreferences
    private lateinit var settings: AppSettings
    private lateinit var sound: AppSound

    // The page on screen (null: the home screen); the bridge's "home" clears it
    private var url by mutableStateOf<String?>(null)

    // The colours: the race chosen on the site (stored; human until then)
    private var race by mutableStateOf(Race.Human)

    // Why the screen must stay on: "page" (a game is open), "bridge" (a page asked)
    private val awake = mutableSetOf<String>()

    private val askNotifications =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // The same port every run: the practice world is kept in the origin's
        // IndexedDB, and the port is part of the origin
        prefs = getSharedPreferences("conquer", MODE_PRIVATE)
        server = LoopbackServer(assets, prefs.getInt("port", 0))
        server.start()
        prefs.edit().putInt("port", server.port).apply()

        credentials = Credentials(this)
        settings = AppSettings(prefs)
        sound = AppSound(this, settings)
        // First launch: sound is on, and the player is told once where to change it
        if (!prefs.getBoolean("sound_toast", false)) {
            prefs.edit().putBoolean("sound_toast", true).apply()
            Toast.makeText(this, R.string.sound_on_toast, Toast.LENGTH_LONG).show()
        }
        race = Race.fromKey(prefs.getString("race", null)) ?: Race.Human
        bridge = Bridge(
            this,
            onKeepAwake = { on -> keepAwake("bridge", on) },
            onRace = { chosen ->
                prefs.edit().putString("race", chosen.key).apply()
                race = chosen
            },
            onHome = { url = null },
        )

        Notifications.ensureChannel(this)
        TurnCheck.schedule(this)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && !Notifications.canPost(this)) {
            askNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        // First launch: the story opens by itself, once; it is on Home (and in the settings) afterwards
        if (!prefs.getBoolean("story_seen", false)) {
            prefs.edit().putBoolean("story_seen", true).apply()
            url = "${server.origin}/${Site.storyPage(Site.language())}"
        }

        setContent {
            // A race chosen in the settings wins; Auto follows what the page detected
            val shown = Race.fromKey(settings.raceChoice) ?: race
            ConquerTheme(shown) {
                val lang = Site.language()
                val open = url
                if (open == null) {
                    Home(
                        onPlayOnline = { url = Site.playPage(lang) },
                        onPractice = { url = "${server.origin}/${Site.practicePage(lang)}" },
                        onTutorial = { url = "${server.origin}/${Site.tutorialPage(lang)}" },
                        onSite = { openInBrowser(Site.siteUrl(lang)) },
                        onStory = { url = "${server.origin}/${Site.storyPage(lang)}" },
                        settings = settings,
                        sound = sound,
                        detected = race,
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
                        settings = settings,
                        sound = sound,
                        detected = race,
                        onStory = { url = "${server.origin}/${Site.storyPage(lang)}" },
                    )
                }
            }
        }
    }

    /** The online site is a website: it opens in the system's browser, not in the game. */
    private fun openInBrowser(address: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(address)))
        } catch (e: android.content.ActivityNotFoundException) {
            Toast.makeText(this, address, Toast.LENGTH_LONG).show()
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

    override fun onResume() {
        super.onResume()
        sound.setForeground(true)
    }

    override fun onPause() {
        sound.setForeground(false)
        super.onPause()
    }

    override fun onDestroy() {
        sound.release()
        server.close()
        super.onDestroy()
    }
}
