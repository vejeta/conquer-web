// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.ui

import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.graphics.Color
import com.vejeta.conquer.R

/**
 * The colours of one race, the values of the website's tokens (web/theme.css:
 * the defaults for the human, and the [data-race] overrides).
 */
class Race(
    val key: String,
    val bg: Color,
    val bg2: Color,
    val ink: Color,
    val inkDim: Color,
    val phos: Color,
    val phosDim: Color,
    val onPhos: Color,
    val stone: Color,
    val gold: Color,
    val bad: Color,
    /** The silhouette behind the home screen (web/mountains*.svg). */
    val mountains: Int,
) {
    companion object {
        val Human = Race(
            key = "human",
            bg = Color(0xFF0B1210), bg2 = Color(0xFF121C18),
            ink = Color(0xFFE6E2D3), inkDim = Color(0xFF9AA89C),
            phos = Color(0xFF8FE3A0), phosDim = Color(0xFF4E9A63), onPhos = Color(0xFF0B1210),
            stone = Color(0xFF7F8F93), gold = Color(0xFFD9B35A), bad = Color(0xFFD97A6A),
            mountains = R.drawable.mountains_human,
        )
        val Elf = Race(
            key = "elf",
            bg = Color(0xFF0B1016), bg2 = Color(0xFF121A22),
            ink = Color(0xFFE6E2D3), inkDim = Color(0xFF9DB0BB),
            phos = Color(0xFFA9D3E6), phosDim = Color(0xFF5A90A8), onPhos = Color(0xFF0B1016),
            stone = Color(0xFF93A3AD), gold = Color(0xFFE0C98A), bad = Color(0xFFD97A6A),
            mountains = R.drawable.mountains_elf,
        )
        val Dwarf = Race(
            key = "dwarf",
            bg = Color(0xFF100E0B), bg2 = Color(0xFF1A1611),
            ink = Color(0xFFE6E2D3), inkDim = Color(0xFFAA9F90),
            phos = Color(0xFFF2A93B), phosDim = Color(0xFFB67A22), onPhos = Color(0xFF100E0B),
            stone = Color(0xFF8A7F73), gold = Color(0xFFE3C56A), bad = Color(0xFFD97A6A),
            mountains = R.drawable.mountains_dwarf,
        )
        val Orc = Race(
            key = "orc",
            bg = Color(0xFF0E0B0B), bg2 = Color(0xFF171212),
            ink = Color(0xFFE6E2D3), inkDim = Color(0xFFA89C9A),
            phos = Color(0xFFE07A5A), phosDim = Color(0xFF9C4A30), onPhos = Color(0xFF0E0B0B),
            stone = Color(0xFF7D7272), gold = Color(0xFFC9A24A), bad = Color(0xFFFF9D8A),
            mountains = R.drawable.mountains_orc,
        )

        val all = listOf(Human, Elf, Dwarf, Orc)

        /** The race named [key] ("human", "elf", "dwarf", "orc"), or null. */
        fun fromKey(key: String?): Race? = all.firstOrNull { it.key == key }
    }
}

/** The race of the current theme, for what Material's colour scheme does not carry (stone, gold, mountains). */
val LocalRace = compositionLocalOf { Race.Human }
