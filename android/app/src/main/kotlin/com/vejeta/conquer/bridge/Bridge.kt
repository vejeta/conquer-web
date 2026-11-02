// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.bridge

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import com.cefrium.CefriumBrowser
import com.cefrium.compose.CefriumBridge
import com.vejeta.conquer.ui.Race
import com.vejeta.conquer.work.Notifications
import org.json.JSONException
import org.json.JSONObject

/**
 * What the pages can ask of the app through window.cefriumQuery. The request
 * is a JSON object with a "type":
 *
 *  - {"type":"haptic","ms":8}: vibrate for ms milliseconds (1 to 500)
 *  - {"type":"keepAwake","on":true}: keep the screen on (or let it sleep)
 *  - {"type":"notify","title":"...","body":"..."}: a local notification
 *  - {"type":"race","race":"elf"}: the race of the colours (human, elf,
 *    dwarf or orc); the app stores it and themes itself with it
 *  - {"type":"home"}: leave the page for the app's home screen
 *
 * The answer is {"ok":true}, or a failure with a code: -1 bad request, -2
 * unknown type, -3 no permission to notify. The contract is in
 * android/README.md.
 *
 * Which pages may call is decided by the origins given to [forView]: the
 * app's own pages on its loopback port and the game server, nothing else.
 */
class Bridge(
    context: Context,
    private val onKeepAwake: (Boolean) -> Unit,
    private val onRace: (Race) -> Unit,
    private val onHome: () -> Unit,
) {
    private val context = context.applicationContext
    private val main = Handler(Looper.getMainLooper())
    private val vibrator: Vibrator? = this.context.getSystemService(Vibrator::class.java)

    /** The bridge for a CefriumView, open to [allowedOrigins] only. */
    fun forView(vararg allowedOrigins: String): CefriumBridge =
        CefriumBridge(CefriumBrowser.QueryOriginPolicy.exactly(*allowedOrigins)) { request, _, callback ->
            handle(request, callback)
        }

    private fun handle(request: String, callback: CefriumBrowser.QueryCallback): Boolean {
        val json = try {
            JSONObject(request)
        } catch (e: JSONException) {
            callback.failure(-1, "bad request")
            return true
        }
        when (json.optString("type")) {
            "haptic" -> {
                val ms = json.optLong("ms", 10).coerceIn(1, 500)
                vibrator?.takeIf { it.hasVibrator() }
                    ?.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
                callback.success(OK)
            }
            "keepAwake" -> {
                val on = json.optBoolean("on", false)
                main.post { onKeepAwake(on) }
                callback.success(OK)
            }
            "notify" -> {
                val title = json.optString("title").take(100)
                val body = json.optString("body").take(500)
                if (Notifications.post(context, NOTIFICATION_ID, title, body)) {
                    callback.success(OK)
                } else {
                    callback.failure(-3, "notifications not allowed")
                }
            }
            "race" -> {
                val race = Race.fromKey(json.optString("race"))
                if (race == null) {
                    callback.failure(-1, "unknown race")
                } else {
                    main.post { onRace(race) }
                    callback.success(OK)
                }
            }
            "home" -> {
                main.post { onHome() }
                callback.success(OK)
            }
            else -> callback.failure(-2, "unknown type")
        }
        return true
    }

    private companion object {
        const val OK = "{\"ok\":true}"
        const val NOTIFICATION_ID = 2
    }
}
