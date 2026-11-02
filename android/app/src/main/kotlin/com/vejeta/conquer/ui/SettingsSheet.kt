// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.vejeta.conquer.R
import com.vejeta.conquer.settings.AppSettings
import com.vejeta.conquer.sound.AppSound

/** The name of a race for the chips and the "Auto (Elf)" label. */
@Composable
private fun raceName(key: String): String = stringResource(
    when (key) {
        "elf" -> R.string.race_elf
        "dwarf" -> R.string.race_dwarf
        "orc" -> R.string.race_orc
        else -> R.string.race_human
    }
)

/**
 * The settings, as a bottom sheet over the home screen or the browser.
 * [detected] is the race the page reported; it names what Auto means.
 * [onSignOut] is null where there is no page to sign out of (the home screen).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsSheet(
    settings: AppSettings,
    sound: AppSound,
    detected: Race,
    onWatchStory: () -> Unit,
    onSignOut: (() -> Unit)?,
    onForgetAccount: () -> Unit,
    onClose: () -> Unit,
) {
    val colors = MaterialTheme.colorScheme
    // Reading the version makes the sheet follow every change
    @Suppress("UNUSED_VARIABLE") val v = settings.version
    val context = LocalContext.current
    val version = remember(context) {
        try {
            context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: ""
        } catch (e: Exception) {
            ""
        }
    }

    ModalBottomSheet(onDismissRequest = onClose, containerColor = colors.surface) {
        Column(
            Modifier
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 8.dp)
                .navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    stringResource(R.string.settings_title),
                    fontFamily = Retro,
                    style = MaterialTheme.typography.headlineSmall,
                    color = colors.primary,
                    modifier = Modifier.weight(1f),
                )
                TextButton(onClick = { sound.tap(); onClose() }) { Text(stringResource(R.string.close)) }
            }

            SwitchRow(R.string.set_music, settings.music) { sound.tap(); settings.setMusic(it); sound.refresh() }
            VolumeRow(settings.musicVolume, settings.music) { settings.setMusicVolume(it); sound.refresh() }
            SwitchRow(R.string.set_effects, settings.effects) { settings.setEffects(it); sound.tap() }
            VolumeRow(settings.effectsVolume, settings.effects, onDone = { sound.tap() }) { settings.setEffectsVolume(it) }

            HorizontalDivider(Modifier.padding(vertical = 8.dp), color = colors.outlineVariant)

            Text(stringResource(R.string.set_race), color = colors.onSurface)
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                val choices = listOf("auto", "human", "elf", "dwarf", "orc")
                for (key in choices) {
                    FilterChip(
                        selected = settings.raceChoice == key,
                        onClick = {
                            sound.tap()
                            settings.setRaceChoice(key)
                        },
                        label = {
                            Text(
                                if (key == "auto") {
                                    if (settings.raceChoice == "auto") {
                                        stringResource(R.string.race_auto_detected, raceName(detected.key))
                                    } else {
                                        stringResource(R.string.race_auto)
                                    }
                                } else {
                                    raceName(key)
                                }
                            )
                        },
                    )
                }
            }

            SwitchRow(R.string.set_plain, settings.plain, R.string.set_plain_hint) { sound.tap(); settings.setPlain(it) }
            SwitchRow(R.string.set_crt, settings.crt) { sound.tap(); settings.setCrt(it) }

            HorizontalDivider(Modifier.padding(vertical = 8.dp), color = colors.outlineVariant)

            TextButton(onClick = { sound.tap(); onClose(); onWatchStory() }) {
                Text(stringResource(R.string.set_story), color = colors.onSurface)
            }
            if (onSignOut != null) {
                TextButton(onClick = { sound.tap(); onClose(); onSignOut() }) {
                    Text(stringResource(R.string.sign_out), color = colors.onSurface)
                }
            }
            TextButton(onClick = { sound.tap(); onForgetAccount(); onClose() }) {
                Text(stringResource(R.string.forget_account), color = colors.onSurface)
            }

            HorizontalDivider(Modifier.padding(vertical = 8.dp), color = colors.outlineVariant)

            Text(stringResource(R.string.set_about), color = colors.onSurface)
            Text(stringResource(R.string.about_version, version), color = colors.onSurfaceVariant)
            Text(stringResource(R.string.about_licences), color = colors.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun SwitchRow(label: Int, on: Boolean, hint: Int? = null, onChange: (Boolean) -> Unit) {
    val colors = MaterialTheme.colorScheme
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(stringResource(label), color = colors.onSurface)
            if (hint != null) {
                Text(stringResource(hint), color = colors.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
            }
        }
        Switch(checked = on, onCheckedChange = onChange)
    }
}

@Composable
private fun VolumeRow(value: Float, enabled: Boolean, onDone: () -> Unit = {}, onChange: (Float) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(stringResource(R.string.set_volume), color = MaterialTheme.colorScheme.onSurfaceVariant)
        Slider(
            value = value,
            onValueChange = onChange,
            onValueChangeFinished = onDone,
            enabled = enabled,
            modifier = Modifier.weight(1f).padding(start = 12.dp),
        )
    }
}
