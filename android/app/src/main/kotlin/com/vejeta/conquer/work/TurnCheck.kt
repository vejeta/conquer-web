// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.work

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.vejeta.conquer.MainActivity
import com.vejeta.conquer.R
import com.vejeta.conquer.web.Site
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

/** Local notifications: the turn check's and the page bridge's. */
object Notifications {
    private const val CHANNEL = "turns"

    fun ensureChannel(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(
            CHANNEL,
            context.getString(R.string.notif_channel),
            NotificationManager.IMPORTANCE_DEFAULT,
        )
        manager.createNotificationChannel(channel)
    }

    fun canPost(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED

    /** Posts a notification that opens the app; false without the permission. */
    fun post(context: Context, id: Int, title: String, text: String): Boolean {
        if (!canPost(context)) return false
        ensureChannel(context)
        val open = PendingIntent.getActivity(
            context,
            0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(text)
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        context.getSystemService(NotificationManager::class.java).notify(id, notification)
        return true
    }
}

/**
 * Every hour, with a network: reads the game server's public status and, when
 * its turn is newer than the last one seen, tells the player "Turn N has run".
 * The first check only remembers the turn.
 */
class TurnCheck(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val turn = try {
            fetchTurn()
        } catch (e: Exception) {
            return@withContext Result.retry()
        }
        if (turn < 0) return@withContext Result.success()

        val prefs = applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val seen = prefs.getInt(KEY_TURN, -1)
        if (turn != seen) {
            prefs.edit().putInt(KEY_TURN, turn).apply()
            // A new season starts again at turn 1: not worth a notification
            if (seen >= 0 && turn > seen) {
                val ctx = applicationContext
                Notifications.post(
                    ctx,
                    NOTIFICATION_ID,
                    ctx.getString(R.string.app_name),
                    ctx.getString(R.string.notif_turn, turn),
                )
            }
        }
        Result.success()
    }

    /** The "turn" of status.json, or -1 when the file does not have one. */
    private fun fetchTurn(): Int {
        val connection = URL(Site.STATUS).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 15_000
            connection.readTimeout = 15_000
            connection.setRequestProperty("Accept", "application/json")
            if (connection.responseCode != HttpURLConnection.HTTP_OK) {
                throw java.io.IOException("status.json: HTTP ${connection.responseCode}")
            }
            val text = connection.inputStream.bufferedReader().use { it.readText() }
            return JSONObject(text).optInt("turn", -1)
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        private const val PREFS = "conquer_turn"
        private const val KEY_TURN = "turn"
        private const val NOTIFICATION_ID = 1
        private const val WORK_NAME = "turn-check"

        /** Schedules the hourly check; harmless to call at every launch. */
        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<TurnCheck>(1, TimeUnit.HOURS)
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
                )
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }
    }
}
