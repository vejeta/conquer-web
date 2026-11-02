// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.sound

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.SoundPool
import com.vejeta.conquer.settings.AppSettings

/**
 * The app's own sounds (the pages make theirs): a loop on the home screen
 * and short effects. The OGG files ship with the website copy under
 * assets/web/sound/; a file that is missing is skipped silently. The
 * Music and Effects settings and their volumes are respected.
 */
class AppSound(context: Context, private val settings: AppSettings) {
    private val assets = context.applicationContext.assets
    private val attrs = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_GAME)
        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
        .build()

    private val pool: SoundPool = SoundPool.Builder().setMaxStreams(4).setAudioAttributes(attrs).build()
    private val ids = HashMap<String, Int>()
    private var loop: MediaPlayer? = null

    private var onHome = false
    private var foreground = false

    init {
        for (name in EFFECTS) {
            try {
                assets.openFd("$DIR/$name.ogg").use { ids[name] = pool.load(it, 1) }
            } catch (e: Exception) {
                // not shipped: silent
            }
        }
    }

    fun tap() = play("ui-tap")
    fun doorsOpen() = play("app-doors-open")
    fun doorsFail() = play("app-doors-fail")

    /** The home screen is (not) on screen. */
    fun setHome(visible: Boolean) {
        onHome = visible
        refresh()
    }

    /** The app is (not) in the foreground. */
    fun setForeground(on: Boolean) {
        foreground = on
        refresh()
    }

    /** Applies the settings: starts, stops or re-volumes the home loop. */
    fun refresh() {
        val want = onHome && foreground && settings.music
        if (!want) {
            loop?.takeIf { it.isPlaying }?.pause()
            return
        }
        var player = loop
        if (player == null) {
            player = try {
                assets.openFd("$DIR/app-home.ogg").use { fd ->
                    MediaPlayer().apply {
                        setAudioAttributes(attrs)
                        setDataSource(fd.fileDescriptor, fd.startOffset, fd.length)
                        isLooping = true
                        prepare()
                    }
                }
            } catch (e: Exception) {
                return
            }
            loop = player
        }
        player.setVolume(settings.musicVolume, settings.musicVolume)
        if (!player.isPlaying) player.start()
    }

    fun release() {
        loop?.release()
        loop = null
        pool.release()
    }

    private fun play(name: String) {
        if (!settings.effects) return
        val id = ids[name] ?: return
        val v = settings.effectsVolume
        pool.play(id, v, v, 1, 0, 1f)
    }

    private companion object {
        const val DIR = "web/sound"
        val EFFECTS = listOf("app-doors-open", "app-doors-fail", "ui-tap")
    }
}
