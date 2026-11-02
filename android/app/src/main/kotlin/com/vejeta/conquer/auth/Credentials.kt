// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** The account the user typed for the game server's Basic authentication. */
data class Account(val user: String, val password: String)

/**
 * The saved account, in EncryptedSharedPreferences (AES-256, key in the
 * Android Keystore). If the encrypted store cannot be opened (a keystore that
 * was reset, a restored backup), nothing is saved or returned: the app asks
 * again.
 */
class Credentials(context: Context) {
    private val prefs: SharedPreferences? = try {
        val key = MasterKey.Builder(context.applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context.applicationContext,
            FILE,
            key,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    } catch (e: Exception) {
        null
    }

    fun load(): Account? {
        val p = prefs ?: return null
        return try {
            val user = p.getString(KEY_USER, null)
            val password = p.getString(KEY_PASSWORD, null)
            if (user.isNullOrEmpty() || password == null) null else Account(user, password)
        } catch (e: Exception) {
            null
        }
    }

    fun save(account: Account) {
        prefs?.edit()?.putString(KEY_USER, account.user)?.putString(KEY_PASSWORD, account.password)?.apply()
    }

    /** "Forget account". */
    fun clear() {
        prefs?.edit()?.clear()?.apply()
    }

    private companion object {
        const val FILE = "conquer_account"
        const val KEY_USER = "user"
        const val KEY_PASSWORD = "password"
    }
}
