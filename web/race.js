// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The race of the visitor's nation sets the phosphor of the whole site
// (theme.css: data-race on <html>). Load this file in <head>, before the
// first paint: it applies the saved race at once.
//
//   conquerRace.get()          the race in use: human, elf, dwarf or orc
//   conquerRace.choice()       what the visitor chose in the options: a race or "auto"
//   conquerRace.choose(v)      "auto" or a race: saved ('conquer-race'), applied
//   conquerRace.seen(race)     the game showed the nation's race: used unless the visitor chose
//   conquerRace.detect(text)   the race word on a nation screen (English), or ''
//   conquerRace.terminal(parchment)
//                              an xterm.js theme from the page's colours (theme.css tokens)
//
// A choice made in the options always wins over what the game shows.
(function () {
  'use strict';
  var RACES = ['human', 'elf', 'dwarf', 'orc'];
  var CHOSEN = 'conquer-race', SEEN = 'conquer-race-seen';

  function read(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function write(key, value) {
    try { if (value) localStorage.setItem(key, value); else localStorage.removeItem(key); } catch (e) {}
  }
  function valid(v) { return RACES.indexOf(v) >= 0 ? v : null; }

  function choice() { return valid(read(CHOSEN)) || 'auto'; }
  function get() { return valid(read(CHOSEN)) || valid(read(SEEN)) || 'human'; }

  function apply() {
    var r = get(), root = document.documentElement;
    if (r === 'human') root.removeAttribute('data-race'); else root.setAttribute('data-race', r);
    try { document.dispatchEvent(new CustomEvent('conquer:race', { detail: r })); } catch (e) {}
    return r;
  }

  function choose(v) {
    write(CHOSEN, valid(v));
    return apply();
  }
  function seen(race) {
    race = valid(String(race || '').toLowerCase());
    if (!race || read(SEEN) === race) return get();
    write(SEEN, race);
    return apply();
  }

  // "National Race: Human" in the nation builder, or a race word on the
  // nation's own report
  function detect(text, anywhere) {
    var m = /(?:National )?Race\s*:\s*(Human|Elf|Dwarf|Orc)\b/i.exec(text);
    if (!m && anywhere) m = /\b(Human|Elf|Dwarf|Orc)\b/.exec(text);
    return m ? m[1].toLowerCase() : '';
  }

  // The colours of the screen, read from the tokens so that no colour lives
  // outside theme.css. On parchment the ink is dark on paper.
  function terminal(parchment) {
    var cs = getComputedStyle(document.documentElement);
    function v(name) { return cs.getPropertyValue(name).trim(); }
    if (parchment) {
      return { background: v('--paper'), foreground: v('--paper-ink'), cursor: v('--paper-cursor'),
               cursorAccent: v('--paper'), selectionBackground: v('--phos-glow') };
    }
    return { background: v('--screen'), foreground: v('--phos'), cursor: v('--phos'),
             cursorAccent: v('--screen'), selectionBackground: v('--phos-glow') };
  }

  window.conquerRace = { races: RACES, get: get, choice: choice, choose: choose, seen: seen, detect: detect, terminal: terminal, apply: apply };
  apply();
})();
