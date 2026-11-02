// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.ui

import android.provider.Settings
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.border
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.vejeta.conquer.R
import com.vejeta.conquer.auth.Account
import kotlinx.coroutines.delay

/** Noto Sans Runic (OFL), for the inscription over the doors. */
private val Runic = FontFamily(Font(R.font.noto_sans_runic))

/** "pedo mellon a minno" (speak, friend, and enter), as the site's gate writes it. */
private const val INSCRIPTION = "ᛈᛖᛞᛟ ᛗᛖᛚᛚᛟᚾ ᚨ ᛗᛁᚾᚾᛟ"

/** How long the leaves take to open (web/theme.css: .gate .leaf). */
const val DOORS_OPEN_MS = 600

private const val OPEN_DEGREES = 105f
private val Ease = CubicBezierEasing(0.5f, 0f, 0.2f, 1f)

/**
 * True when the user turned animations off (Settings.Global
 * ANIMATOR_DURATION_SCALE = 0): everything then happens at once.
 */
@Composable
fun rememberAnimationsOff(): Boolean {
    val resolver = LocalContext.current.contentResolver
    return remember {
        Settings.Global.getFloat(resolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
    }
}

/**
 * The login as the Doors of Durin: two wooden leaves with a carved arch and
 * a rune inscription that glows while a field has the focus; the account and
 * the password sit in the middle. "Speak friend" sends the account and the
 * leaves swing open ([opening]), uncovering the page; when the server
 * refuses, [request] is a new one with `wrong` set: the runes flicker and
 * fade and the doors shake, and the leaves close again.
 */
@Composable
internal fun DoorsDialog(
    request: AuthRequest,
    saved: Account?,
    opening: Boolean,
    onSpeak: (Account, Boolean) -> Unit,
    onCancel: () -> Unit,
) {
    val race = LocalRace.current
    val off = rememberAnimationsOff()

    var user by remember { mutableStateOf(saved?.user ?: "") }
    var password by remember { mutableStateOf("") }
    var rememberMe by remember { mutableStateOf(true) }
    var userFocus by remember { mutableStateOf(false) }
    var passwordFocus by remember { mutableStateOf(false) }

    // The leaves: 0 closed, 1 open
    val open by animateFloatAsState(
        targetValue = if (opening) 1f else 0f,
        animationSpec = tween(if (off) 0 else DOORS_OPEN_MS, easing = Ease),
        label = "leaves",
    )

    // The runes: stone when idle, phosphor and a glow when a field is focused
    val lit = (userFocus || passwordFocus) && !opening
    var flicker by remember { mutableStateOf(false) }
    val runeColor by animateColorAsState(
        targetValue = if (lit && !flicker) race.phos else race.stone,
        animationSpec = tween(if (off || flicker) 0 else 700),
        label = "runes",
    )
    val runeGlow by animateFloatAsState(
        targetValue = if (lit && !flicker) 1f else 0f,
        animationSpec = tween(if (off || flicker) 0 else 700),
        label = "glow",
    )
    val runeFade = remember { Animatable(1f) }

    // A refusal: the runes flicker and fade, the doors shake a little
    val shake = remember { Animatable(0f) }
    LaunchedEffect(request) {
        if (!request.wrong) return@LaunchedEffect
        password = ""
        if (off) {
            runeFade.snapTo(1f)
            return@LaunchedEffect
        }
        runeFade.snapTo(1f)
        for (i in 0 until 3) {
            flicker = true
            delay(120)
            flicker = false
            delay(120)
        }
        // After the flicker the runes are stone and dim for a moment
        runeFade.animateTo(0.35f, tween(500))
        runeFade.animateTo(1f, tween(700))
    }
    LaunchedEffect(request) {
        if (!request.wrong || off) return@LaunchedEffect
        for (target in floatArrayOf(-12f, 12f, -9f, 9f, -5f, 5f, 0f)) {
            shake.animateTo(target, tween(60))
        }
    }

    Dialog(
        onDismissRequest = { if (!opening) onCancel() },
        properties = DialogProperties(usePlatformDefaultWidth = false, dismissOnClickOutside = false),
    ) {
        BoxWithConstraints(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            val height = minOf(460.dp, maxHeight * 0.96f)
            Box(
                Modifier
                    .fillMaxWidth(0.94f)
                    .widthIn(max = 440.dp)
                    .height(height)
                    .offset { IntOffset(shake.value.dp.roundToPx(), 0) },
            ) {
                // The leaves, hinged on the outer edges
                Row(Modifier.fillMaxSize().padding(horizontal = 6.dp, vertical = 6.dp)) {
                    Leaf(left = true, open = open, modifier = Modifier.weight(1f).fillMaxHeight())
                    Leaf(left = false, open = open, modifier = Modifier.weight(1f).fillMaxHeight())
                }
                // The stone frame (the archway)
                Box(
                    Modifier
                        .fillMaxSize()
                        .border(
                            4.dp,
                            race.stone,
                            RoundedCornerShape(topStart = 56.dp, topEnd = 56.dp, bottomStart = 6.dp, bottomEnd = 6.dp),
                        ),
                )

                // The inscription over the doors
                Text(
                    text = INSCRIPTION,
                    fontFamily = Runic,
                    fontSize = 20.sp,
                    letterSpacing = 6.sp,
                    maxLines = 1,
                    textAlign = TextAlign.Center,
                    color = runeColor,
                    style = LocalTextStyle.current.copy(
                        shadow = Shadow(
                            color = race.phos.copy(alpha = 0.7f * runeGlow),
                            blurRadius = 18f * runeGlow,
                        ),
                    ),
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(top = 30.dp, start = 24.dp, end = 24.dp)
                        .alpha(runeFade.value * (1f - open)),
                )

                // The account and the password, in the middle
                Column(
                    modifier = Modifier
                        .align(Alignment.Center)
                        .padding(top = 28.dp)
                        .fillMaxWidth(0.8f)
                        .heightIn(max = height - 90.dp)
                        .alpha((1f - open * 2f).coerceIn(0f, 1f))
                        .clip(RoundedCornerShape(6.dp))
                        .background(race.bg2)
                        .border(2.dp, race.stone, RoundedCornerShape(6.dp))
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        stringResource(R.string.login_title),
                        color = race.ink,
                        textAlign = TextAlign.Center,
                    )
                    Text(
                        request.host + if (request.realm.isNotEmpty()) " · " + request.realm else "",
                        color = race.inkDim,
                        textAlign = TextAlign.Center,
                        fontSize = 12.sp,
                    )
                    if (request.wrong) {
                        Text(
                            stringResource(R.string.login_wrong),
                            color = MaterialTheme.colorScheme.error,
                            textAlign = TextAlign.Center,
                        )
                    }
                    val centered = LocalTextStyle.current.copy(textAlign = TextAlign.Center)
                    OutlinedTextField(
                        value = user,
                        onValueChange = { user = it },
                        label = { Text(stringResource(R.string.login_user)) },
                        singleLine = true,
                        textStyle = centered,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text),
                        enabled = !opening,
                        modifier = Modifier.fillMaxWidth().onFocusChanged { userFocus = it.isFocused },
                    )
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        label = { Text(stringResource(R.string.login_password)) },
                        singleLine = true,
                        textStyle = centered,
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                        enabled = !opening,
                        modifier = Modifier.fillMaxWidth().onFocusChanged { passwordFocus = it.isFocused },
                    )
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.clickable(enabled = !opening) { rememberMe = !rememberMe },
                    ) {
                        Checkbox(checked = rememberMe, onCheckedChange = null)
                        Text(
                            stringResource(R.string.login_remember),
                            color = race.ink,
                            modifier = Modifier.padding(start = 8.dp),
                        )
                    }
                    Button(
                        onClick = { onSpeak(Account(user.trim(), password), rememberMe) },
                        enabled = !opening && user.isNotBlank() && password.isNotEmpty(),
                    ) { Text(stringResource(R.string.login_speak), fontFamily = Retro, fontSize = 22.sp) }
                    TextButton(onClick = onCancel, enabled = !opening) {
                        Text(stringResource(R.string.cancel), color = race.inkDim)
                    }
                }
            }
        }
    }
}

/**
 * One leaf of the door: dark wood with planks, a beveled edge and the arch
 * carved in it (the look of web/theme.css .gate .leaf). It swings about its
 * outer edge, seen in perspective, up to 105 degrees.
 */
@Composable
private fun Leaf(left: Boolean, open: Float, modifier: Modifier) {
    Canvas(
        modifier.graphicsLayer {
            rotationY = (if (left) -OPEN_DEGREES else OPEN_DEGREES) * open
            transformOrigin = TransformOrigin(if (left) 0f else 1f, 0.5f)
            cameraDistance = 16f * density
        },
    ) {
        val w = size.width
        val h = size.height
        // Wood
        drawRect(
            Brush.verticalGradient(
                0f to Color(0xFF6F6558),
                0.45f to Color(0xFF51483E),
                1f to Color(0xFF3D362E),
            ),
        )
        // Planks
        val step = 14.dp.toPx()
        val grain = 2.dp.toPx()
        var x = 0f
        while (x < w) {
            drawRect(Color(0x38000000), topLeft = Offset(x, 0f), size = Size(grain, h))
            x += step
        }
        // Bevel
        drawRect(Color(0x59000000), style = Stroke(width = 8.dp.toPx()))
        drawRect(Color(0x14EFE6CF), topLeft = Offset(4.dp.toPx(), 4.dp.toPx()), size = Size(w - 8.dp.toPx(), h - 8.dp.toPx()), style = Stroke(width = 2.dp.toPx()))
        // The seam in the middle
        val seam = 2.dp.toPx()
        drawRect(Color(0xFF1C1812), topLeft = Offset(if (left) w - seam else 0f, 0f), size = Size(seam, h))
        // The carved arch: inset 18% / 16%, an elliptical top
        for (inset in floatArrayOf(0f, 8.dp.toPx())) {
            val l = w * 0.18f + inset
            val r = w * 0.82f - inset
            val top = h * 0.16f + inset
            val bottom = h * 0.84f - inset
            val ry = (bottom - top) * 0.3f
            if (r > l && bottom > top + ry) {
                val arch = Path().apply {
                    moveTo(l, bottom)
                    lineTo(l, top + ry)
                    arcTo(Rect(l, top, r, top + 2 * ry), 180f, 180f, false)
                    lineTo(r, bottom)
                }
                drawPath(arch, if (inset == 0f) Color(0x1FEFE6CF) else Color(0x1F000000), style = Stroke(width = 2.dp.toPx()))
            }
        }
    }
}
