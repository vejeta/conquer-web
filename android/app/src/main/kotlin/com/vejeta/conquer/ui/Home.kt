// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vejeta.conquer.R

private val Bg = Color(0xFF0D1117)
private val Panel = Color(0xFF161B22)
private val Accent = Color(0xFF3FB950)
private val TextColor = Color(0xFFE6EDF3)
private val Muted = Color(0xFF8B949E)

/** The retro font of the site's title (web/fonts/vt323). */
val Retro = FontFamily(Font(R.font.vt323))

/** The colours of the website (web/index.html), always dark. */
@Composable
fun ConquerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Accent,
            onPrimary = Bg,
            secondary = Muted,
            background = Bg,
            onBackground = TextColor,
            surface = Panel,
            onSurface = TextColor,
        ),
        content = content,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Home(
    onPlayOnline: () -> Unit,
    onPractice: () -> Unit,
    onTutorial: () -> Unit,
    onSite: () -> Unit,
    onForgetAccount: () -> Unit,
) {
    var settings by remember { mutableStateOf(false) }
    val wide = Modifier
        .fillMaxWidth()
        .widthIn(max = 480.dp)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Bg)
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
            color = Accent,
            fontFamily = Retro,
            fontSize = 56.sp,
            letterSpacing = 8.sp,
        )
        Text(
            text = stringResource(R.string.tagline),
            color = Muted,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(8.dp))

        Button(onClick = onPlayOnline, modifier = wide.height(64.dp)) { Label(R.string.btn_play) }
        FilledTonalButton(
            onClick = onPractice,
            modifier = wide.height(64.dp),
            colors = ButtonDefaults.filledTonalButtonColors(containerColor = Panel, contentColor = Accent),
        ) { Label(R.string.btn_practice) }
        OutlinedButton(onClick = onTutorial, modifier = wide.height(64.dp)) { Label(R.string.btn_tutorial) }
        OutlinedButton(onClick = onSite, modifier = wide.height(64.dp)) { Label(R.string.btn_site) }

        TextButton(onClick = { settings = true }) {
            Text(stringResource(R.string.settings), color = Muted)
        }
    }

    if (settings) {
        ModalBottomSheet(onDismissRequest = { settings = false }, containerColor = Panel) {
            Column(Modifier.padding(horizontal = 24.dp, vertical = 8.dp).navigationBarsPadding()) {
                TextButton(onClick = {
                    onForgetAccount()
                    settings = false
                }) {
                    Text(stringResource(R.string.forget_account), color = TextColor)
                }
            }
        }
    }
}

@Composable
private fun Label(text: Int) {
    Text(text = stringResource(text), fontFamily = Retro, fontSize = 26.sp)
}
