// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vejeta.conquer.R
import com.vejeta.conquer.settings.AppSettings
import com.vejeta.conquer.sound.AppSound

/** The retro font of the site's title (web/fonts/vt323). */
val Retro = FontFamily(Font(R.font.vt323))

/**
 * The colours of the website for one race (web/theme.css), always dark.
 * Typography stays the system's, except the retro title font.
 */
@Composable
fun ConquerTheme(race: Race = Race.Human, content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalRace provides race) {
        MaterialTheme(
            colorScheme = darkColorScheme(
                primary = race.phos,
                onPrimary = race.onPhos,
                primaryContainer = race.phosDim,
                onPrimaryContainer = race.ink,
                secondary = race.stone,
                onSecondary = race.bg,
                tertiary = race.gold,
                onTertiary = race.bg,
                background = race.bg,
                onBackground = race.ink,
                surface = race.bg2,
                onSurface = race.ink,
                surfaceVariant = race.bg2,
                onSurfaceVariant = race.inkDim,
                outline = race.stone,
                outlineVariant = race.stone.copy(alpha = 0.45f),
                error = race.bad,
                onError = race.bg,
            ),
            content = content,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Home(
    onPlayOnline: () -> Unit,
    onPractice: () -> Unit,
    onTutorial: () -> Unit,
    onSite: () -> Unit,
    onForgetAccount: () -> Unit,
    onStory: () -> Unit,
    settings: AppSettings,
    sound: AppSound,
    detected: Race,
) {
    DisposableEffect(Unit) {
        sound.setHome(true)
        onDispose { sound.setHome(false) }
    }
    LaunchedEffect(settings.version) { sound.refresh() }
    val tapped = { action: () -> Unit -> { sound.tap(); action() } }
    var sheet by remember { mutableStateOf(false) }
    val wide = Modifier
        .fillMaxWidth()
        .widthIn(max = 480.dp)

    val race = LocalRace.current
    val colors = MaterialTheme.colorScheme

    Box(Modifier.fillMaxSize().background(race.bg)) {
    // The race's mountains along the bottom; the sides are cropped on wide screens
    Image(
        painter = painterResource(race.mountains),
        contentDescription = null,
        contentScale = ContentScale.Crop,
        alignment = Alignment.BottomCenter,
        modifier = Modifier.align(Alignment.BottomCenter).fillMaxWidth().height(200.dp),
    )
    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp, vertical = 16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Image(
            painter = painterResource(R.drawable.hero),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = wide
                .aspectRatio(800f / 420f)
                .clip(RoundedCornerShape(12.dp)),
        )
        Text(
            text = "CONQUER",
            color = colors.primary,
            fontFamily = Retro,
            fontSize = 56.sp,
            letterSpacing = 8.sp,
        )
        Text(
            text = stringResource(R.string.tagline),
            color = colors.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))

        Button(onClick = tapped(onPlayOnline), modifier = wide.height(64.dp)) { Label(R.string.btn_play) }
        FilledTonalButton(
            onClick = tapped(onPractice),
            modifier = wide.height(64.dp),
            colors = ButtonDefaults.filledTonalButtonColors(containerColor = colors.surface, contentColor = colors.primary),
        ) { Label(R.string.btn_practice) }
        OutlinedButton(onClick = tapped(onTutorial), modifier = wide.height(64.dp)) { Label(R.string.btn_tutorial) }
        OutlinedButton(onClick = tapped(onSite), modifier = wide.height(64.dp)) { Label(R.string.btn_site) }

        TextButton(onClick = { sound.tap(); sheet = true }) {
            Text(stringResource(R.string.settings), color = colors.onSurfaceVariant)
        }
    }
    }

    if (sheet) {
        SettingsSheet(
            settings = settings,
            sound = sound,
            detected = detected,
            onWatchStory = onStory,
            onSignOut = null,
            onForgetAccount = onForgetAccount,
            onClose = { sheet = false },
        )
    }
}

@Composable
private fun Label(text: Int) {
    Text(text = stringResource(text), fontFamily = Retro, fontSize = 26.sp)
}
