// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later

package com.vejeta.conquer.settings

import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue

/**
 * The player's settings, kept in the "conquer" preferences. Music and effects
 * start on. Every change bumps [version], which the screens watch to push the
 * settings into the page and to update the sound.
 */
class AppSettings(private val prefs: SharedPreferences) {
    /** Changes with every setting, for effects to key on. */
    var version by mutableIntStateOf(0)
        private set

    var music = prefs.getBoolean("music", true); private set
    var musicVolume = prefs.getFloat("music_volume", 0.6f); private set
    var effects = prefs.getBoolean("effects", true); private set
    var effectsVolume = prefs.getFloat("effects_volume", 0.8f); private set

    /** "auto" or a race key (human, elf, dwarf, orc). */
    var raceChoice = prefs.getString("race_choice", "auto") ?: "auto"; private set
    var plain = prefs.getBoolean("plain", false); private set
    var crt = prefs.getBoolean("crt", false); private set

    fun setMusic(on: Boolean) = change { music = on; putBoolean("music", on) }
    fun setMusicVolume(v: Float) = change { musicVolume = v.coerceIn(0f, 1f); putFloat("music_volume", musicVolume) }
    fun setEffects(on: Boolean) = change { effects = on; putBoolean("effects", on) }
    fun setEffectsVolume(v: Float) = change { effectsVolume = v.coerceIn(0f, 1f); putFloat("effects_volume", effectsVolume) }
    fun setRaceChoice(key: String) = change { raceChoice = key; putString("race_choice", key) }
    fun setPlain(on: Boolean) = change { plain = on; putBoolean("plain", on) }
    fun setCrt(on: Boolean) = change { crt = on; putBoolean("crt", on) }

    private fun change(edit: SharedPreferences.Editor.() -> Unit) {
        prefs.edit().apply(edit).apply()
        version++
    }

    /**
     * JavaScript that puts the settings into the page it runs in. Everything
     * is guarded: a page without the API (or without storage) is left alone.
     * The keys are those of web/touch.js ('conquer-touch': plain, scan) and
     * web/race.js ('conquer-race').
     */
    fun script(): String {
        val m = if (music) "true" else "false"
        val e = if (effects) "true" else "false"
        val race = if (raceChoice == "auto") "''" else "'$raceChoice'"
        return """
(function () {
  try {
    var a = window.conquerAudio;
    function has(n) { return a && typeof a[n] === 'function'; }
    if (a) {
      if (has('setMusic')) a.setMusic($m);
      if (has('setEffects')) a.setEffects($e);
      if (has('setMusicVolume') || has('setEffectsVolume')) {
        if (has('setVolume')) a.setVolume(1);
        if (has('setMusicVolume')) a.setMusicVolume($musicVolume);
        if (has('setEffectsVolume')) a.setEffectsVolume($effectsVolume);
      } else if (has('setVolume')) {
        a.setVolume(${maxOf(musicVolume, effectsVolume)});
      }
    }
  } catch (x) {}
  try {
    var race = $race;
    if (window.conquerRace && typeof conquerRace.choose === 'function') {
      conquerRace.choose(race || 'auto');
    } else {
      if (race) localStorage.setItem('conquer-race', race); else localStorage.removeItem('conquer-race');
      if (race) {
        if (race === 'human') document.documentElement.removeAttribute('data-race');
        else document.documentElement.dataset.race = race;
      }
    }
  } catch (x) {}
  try {
    var p = {};
    try { p = JSON.parse(localStorage.getItem('conquer-touch')) || {}; } catch (y) { p = {}; }
    p.plain = $plain;
    p.scan = $crt;
    p.crt = $crt;
    localStorage.setItem('conquer-touch', JSON.stringify(p));
    var v = document.querySelectorAll('.touch-viewport');
    for (var i = 0; i < v.length; i++) v[i].classList.toggle('touch-scan', $crt);
    var s = document.querySelectorAll('.stone');
    for (var j = 0; j < s.length; j++) s[j].classList.toggle('plain', $plain);
  } catch (x) {}
})();
""".trimIndent()
    }
}
