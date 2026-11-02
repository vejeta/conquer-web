// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Sound for the game pages: recorded instruments, not oscillators.
// web/sound/*.ogg is rendered from a SoundFont by tools/sound/build.py:
// ambient beds (map-human/elf/dwarf/orc, builder, report, combat, app-home)
// that play as loops and cross-fade into one another, and short effects.
// Music and effects have their own on/off and volume (kept in localStorage)
// and the music ducks under an effect. Off by default on the web; on in the
// app (html.in-app), from the first gesture. The synthesiser of the first
// version stays below only as a fallback for a file that fails to load.
//
// window.conquerAudio:
//   enable(on) / enabled()            both channels together (enabled: either is on)
//   setMusic(on) / music()            the music channel
//   setEffects(on) / effects()        the effects channel
//   setVolume(v) / volume()           the overall volume, 0..1
//   musicVolume([v]) / effectsVolume([v])   get, or set when given a number
//   event(name)   ui, move, bump, open, close, news, message, turn, combat,
//                 found, approved, app-doors-open, app-doors-fail
//   screen(name)  map (the bed of the race in <html data-race>), builder,
//                 report*, combat, app-home, off; other names keep what plays
//   _demo(), _state(), _nodes(), _bed(), _loaded(), _failed()  (tests)
// Every method is a no-op when the browser has no Web Audio.
(function () {
  'use strict';
  var KEY = 'conquer-audio';
  var AC = window.AudioContext || window.webkitAudioContext;
  var BASE = (function () {
    try {
      var s = document.currentScript && document.currentScript.src;
      if (s) return s.replace(/[^\/]*$/, '') + 'sound/';
    } catch (e) {}
    return 'sound/';
  })();
  var BEDS = ['map-human', 'map-elf', 'map-dwarf', 'map-orc', 'builder', 'report', 'combat', 'app-home'];
  var FX = ['ui-tap', 'move', 'bump', 'open', 'close', 'news', 'message', 'turn', 'combat-hit', 'found', 'approved',
            'app-doors-open', 'app-doors-fail'];
  var ALIAS = { ui: 'ui-tap', combat: 'combat-hit' };
  var SYN = { 'ui-tap': 'ui', 'combat-hit': 'combat', found: 'turn', approved: 'open', 'app-doors-open': 'turn', 'app-doors-fail': 'bump' };
  var FADE = 2.5;                  // s, the cross-fade between beds

  var musicOn = false, fxOn = false, vol = 0.8, mVol = 0.5, fVol = 0.8;
  var ctx = null, master = null, musicBus = null, duck = null, fxBus = null, noiseBuf = null;
  var screenName = '', pending = false, nodes = 0, moveStep = 0;
  var bed = null, bedKey = '';                 // the bed that plays: {key, el, gain, synth}
  var buffers = {}, failed = {}, loading = {}, beds = {};
  var duckTimer = 0, under = 1;   // under: the music's share while a voice speaks (not saved)

  function inApp() {
    try {
      return document.documentElement.classList.contains('in-app') || !!(window.conquerApp && window.conquerApp.is);
    } catch (e) { return false; }
  }
  function num(v, d) { return typeof v === 'number' && v >= 0 && v <= 1 ? v : d; }
  function load() {
    var stored = null;
    try { stored = window.localStorage.getItem(KEY); } catch (e) {}
    if (stored !== null) {
      try {
        var s = JSON.parse(stored || '{}');
        vol = num(s.volume, vol);
        mVol = num(s.musicVolume, mVol);
        fVol = num(s.effectsVolume, fVol);
        if ('music' in s || 'effects' in s) { musicOn = s.music === true; fxOn = s.effects === true; }
        else if (s.enabled === true) { musicOn = true; fxOn = true; }       // the first version's single switch
      } catch (e) {}
    } else if (inApp()) {
      musicOn = true; fxOn = true;      // in the app sound is on until the player turns it off
    }
  }
  function save() {
    try {
      window.localStorage.setItem(KEY, JSON.stringify({ music: musicOn, effects: fxOn, volume: vol, musicVolume: mVol, effectsVolume: fVol }));
    } catch (e) {}
  }

  function hz(m) { return 440 * Math.pow(2, (m - 69) / 12); }


  // ---- building blocks, all scheduled on the AudioContext clock ----------
  function tone(type, freq, t, dur, level, opt) {
    opt = opt || {};
    var o = ctx.createOscillator(), g = ctx.createGain(), out = opt.dest || fxBus;
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (opt.to) o.frequency.exponentialRampToValueAtTime(opt.to, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(level, t + Math.min(0.008, dur / 4));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g);
    if (opt.lp) {
      var f = ctx.createBiquadFilter();
      f.type = 'lowpass'; f.frequency.value = opt.lp;
      g.connect(f); f.connect(out);
    } else {
      g.connect(out);
    }
    o.start(t); o.stop(t + dur + 0.02);
    nodes++;
  }
  function noise(t, dur, level, ftype, freq, dest) {
    if (!noiseBuf) {
      noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      var d = noiseBuf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    var s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = noiseBuf; s.loop = true;
    f.type = ftype; f.frequency.value = freq;
    g.gain.setValueAtTime(level, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(dest || fxBus);
    s.start(t); s.stop(t + dur + 0.02);
    nodes++;
  }

  // ---- one-shot effects -----------------------------------------------------
  var EVENTS = {
    move: function (t) {
      tone('triangle', 300 + (moveStep++ % 4) * 22 + Math.random() * 12, t, 0.04, 0.25);
    },
    bump: function (t) { tone('square', 70, t, 0.12, 0.18, { lp: 500 }); },
    ui: function (t) {
      noise(t, 0.02, 0.2, 'highpass', 4000);
      tone('sine', 1200, t, 0.03, 0.18);
    },
    open: function (t) {
      tone('triangle', hz(72), t, 0.09, 0.28);
      tone('triangle', hz(79), t + 0.09, 0.14, 0.28);
    },
    close: function (t) {
      tone('triangle', hz(79), t, 0.09, 0.28);
      tone('triangle', hz(72), t + 0.09, 0.14, 0.28);
    },
    combat: function (t) {
      for (var i = 0; i < 12; i++) noise(t + i * 0.05, 0.05, 0.1 + i * 0.02, 'lowpass', 900);
      var c = [50, 53, 57];
      for (var j = 0; j < c.length; j++)
        tone('sawtooth', hz(c[j]), t + 0.2, 0.4, 0.09, { lp: 1400 });
    },
    turn: function (t) {
      var n = [62, 65, 69, 74];
      for (var i = 0; i < 4; i++)
        tone('square', hz(n[i]), t + i * 0.3, i === 3 ? 0.3 : 0.26, 0.12, { lp: 2500 });
    },
    news: function (t) {
      for (var i = 0; i < 6; i++) {
        noise(t + i * 0.09, 0.015, 0.2, 'bandpass', 2500 + (i % 2) * 700);
        tone('square', 180 + (i % 2) * 40, t + i * 0.09, 0.02, 0.05);
      }
    },
    message: function (t) {
      tone('sawtooth', hz(57), t, 0.16, 0.12, { lp: 1200 });
      tone('sawtooth', hz(62), t + 0.18, 0.28, 0.12, { lp: 1200 });
    }
  };

  // ---- ambient music ----------------------------------------------------------
  // A track is {bpm, steps (eighth notes in the loop), play(i, t, dur, dest)}.
  var MAP = (function () {
    // D dorian: Dm, Dm, G, Dm, C, Am, G, Dm (8 bars of 8 eighths)
    var chords = [[50, 57, 62, 65], [50, 57, 62, 65], [55, 62, 67, 71], [50, 57, 62, 65],
                  [48, 60, 64, 67], [57, 60, 64, 69], [55, 62, 67, 71], [50, 57, 62, 65]];
    var hits = { 0: 0, 3: 1, 4: 2, 6: 3 };
    return { bpm: 72, steps: 64, play: function (i, t, d, dest) {
      var b = Math.floor(i / 8), s = i % 8, c = chords[b];
      if (s === 0) tone('square', hz(c[0] - 12), t, d * 3, 0.07, { dest: dest, lp: 500 });
      if (hits[s] !== undefined && !(b % 4 === 3 && s === 6))
        tone('triangle', hz(c[hits[s]] + 12), t, d * 2.5, 0.16, { dest: dest });
    } };
  })();
  var BUILDER = (function () {
    // A aeolian lullaby, 8 bars of 8 eighths (0 = rest)
    var m = [[69, 0, 72, 0, 76, 0, 72, 0], [71, 0, 74, 0, 72, 0, 0, 0],
             [69, 0, 72, 0, 76, 0, 79, 0], [77, 0, 76, 0, 72, 0, 0, 0],
             [74, 0, 77, 0, 76, 0, 72, 0], [71, 0, 72, 0, 69, 0, 0, 0],
             [67, 0, 71, 0, 74, 0, 72, 0], [69, 0, 0, 0, 0, 0, 0, 0]];
    var roots = [45, 47, 45, 41, 38, 40, 43, 45];
    return { bpm: 60, steps: 64, play: function (i, t, d, dest) {
      var b = Math.floor(i / 8), s = i % 8, n = m[b][s];
      if (s === 0 || s === 4) tone('triangle', hz(roots[b]), t, d * 3.5, 0.13, { dest: dest });
      if (n) tone('triangle', hz(n), t, d * 2.5, 0.14, { dest: dest });
    } };
  })();
  var COMBAT = {
    bpm: 100, steps: 16, play: function (i, t, d, dest) {
      var s = i % 8;
      if (s === 0 || s === 3 || s === 7) tone('sine', 120, t, 0.12, 0.3, { dest: dest, to: 45 });
      if (s === 4) noise(t, 0.1, 0.14, 'bandpass', 1800, dest);
      if (s % 2 === 1) noise(t, 0.03, 0.05, 'highpass', 6000, dest);
      if (i === 0) tone('square', hz(38), t, d * 8, 0.06, { dest: dest, lp: 400 });
    }
  };
  var TRACKS = { map: MAP, builder: BUILDER, combat: COMBAT };

  function startMusic(key) {
    var out = ctx.createGain(), now = ctx.currentTime, m = { gain: out, stopped: false, timer: 0, oscs: [] };
    out.gain.setValueAtTime(0.0001, now);
    out.gain.linearRampToValueAtTime(1, now + 1.5);
    out.connect(musicBus);
    if (key === 'report') {
      // a quiet drone: two slightly detuned triangles
      [-5, 5].forEach(function (cents) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.type = 'triangle'; o.frequency.value = 110; o.detune.value = cents;
        g.gain.value = 0.07;
        o.connect(g); g.connect(out); o.start(now);
        m.oscs.push(o); nodes++;
      });
      return m;
    }
    var tr = TRACKS[key], dur = 60 / tr.bpm / 2, i = 0, next = now + 0.05;
    function tick() {
      if (m.stopped) return;
      var horizon = ctx.currentTime + 0.1;
      if (next < ctx.currentTime - 0.2) next = ctx.currentTime;   // throttled tab: resync
      while (next < horizon) {
        tr.play(i % tr.steps, next, dur, out);
        next += dur; i++;
      }
      m.timer = window.setTimeout(tick, 25);
    }
    tick();
    return m;
  }
  function stopMusic(m, fade) {
    if (!m) return;
    m.stopped = true;
    window.clearTimeout(m.timer);
    var t = ctx.currentTime;
    try {
      m.gain.gain.cancelScheduledValues(t);
      m.gain.gain.setValueAtTime(Math.max(m.gain.gain.value, 0.0001), t);
      m.gain.gain.linearRampToValueAtTime(0.0001, t + fade);
    } catch (e) {}
    window.setTimeout(function () {
      m.oscs.forEach(function (o) { try { o.stop(); } catch (e) {} });
      try { m.gain.disconnect(); } catch (e) {}
    }, fade * 1000 + 300);
  }


  // ---- recorded effects -------------------------------------------------------------
  function fetchBuffer(name) {
    if (buffers[name] || failed[name] || loading[name] || !ctx) return;
    loading[name] = true;
    var done = function (ok, buf) {
      loading[name] = false;
      if (ok) buffers[name] = buf; else failed[name] = true;
    };
    try {
      window.fetch(BASE + name + '.ogg').then(function (r) {
        if (!r.ok) throw new Error(String(r.status));
        return r.arrayBuffer();
      }).then(function (ab) {
        return new Promise(function (res, rej) {
          var p = ctx.decodeAudioData(ab, res, rej);
          if (p && p.catch) p.catch(rej);
        });
      }).then(function (b) { done(true, b); }, function () { done(false); });
    } catch (e) { done(false); }
  }
  function duckFor(sec) {
    if (!ctx || !duck) return;
    var t = ctx.currentTime;
    duck.gain.cancelScheduledValues(t);
    duck.gain.setTargetAtTime(0.45, t, 0.03);
    window.clearTimeout(duckTimer);
    duckTimer = window.setTimeout(function () {
      if (ctx && duck) duck.gain.setTargetAtTime(1, ctx.currentTime, 0.5);
    }, Math.min(sec, 3) * 1000);
  }
  function playFx(name) {
    var b = buffers[name];
    if (!b) {
      if (failed[name]) {               // the file did not load: the synthesised cue
        var f = EVENTS[SYN[name] || name];
        if (f) f(ctx.currentTime + 0.01);
      } else fetchBuffer(name);
      return;
    }
    var s = ctx.createBufferSource();
    s.buffer = b;
    if (name === 'move') s.playbackRate.value = 0.94 + Math.random() * 0.12;     // no two ticks alike
    s.connect(fxBus);
    s.start(ctx.currentTime + 0.005);
    nodes++;
    if (b.duration > 0.6) duckFor(Math.min(b.duration, 2.5) * 0.6);
  }

  // ---- beds: HTMLAudio loops through the graph, cross-faded ---------------------------
  function bedFor(key) {
    if (beds[key]) return beds[key];
    var el = new Audio();
    el.loop = true;
    el.preload = 'auto';
    var g = ctx.createGain();
    g.gain.value = 0;
    var b = { key: key, el: el, gain: g, synth: null, dead: false };
    el.addEventListener('error', function () { failed[key] = true; if (bed === b) synthBed(b); });
    try {
      var src = ctx.createMediaElementSource(el);
      src.connect(g); g.connect(musicBus);
    } catch (e) { failed[key] = true; }
    el.src = BASE + key + '.ogg';
    beds[key] = b;
    return b;
  }
  function synthBed(b) {          // the fallback: the first version's synthesised bed
    if (b.synth || !ctx) return;
    var k = b.key.indexOf('map') === 0 ? 'map' : b.key === 'app-home' ? 'builder' : b.key;
    b.synth = startMusic(k);
  }
  function fadeIn(b) {
    var t = ctx.currentTime;
    b.gain.gain.cancelScheduledValues(t);
    b.gain.gain.setValueAtTime(b.gain.gain.value, t);
    b.gain.gain.linearRampToValueAtTime(1, t + FADE);
    if (failed[b.key]) { synthBed(b); return; }
    var p = b.el.play();
    nodes++;
    if (p && p.catch) p.catch(function () { failed[b.key] = true; synthBed(b); });
  }
  function fadeOut(b, sec) {
    if (!b) return;
    var t = ctx.currentTime;
    try {
      b.gain.gain.cancelScheduledValues(t);
      b.gain.gain.setValueAtTime(b.gain.gain.value, t);
      b.gain.gain.linearRampToValueAtTime(0, t + sec);
    } catch (e) {}
    if (b.synth) { stopMusic(b.synth, sec); b.synth = null; }
    window.setTimeout(function () { if (bed !== b) { try { b.el.pause(); } catch (e) {} } }, sec * 1000 + 100);
  }
  function race() {
    var r = document.documentElement.getAttribute('data-race') || 'human';
    return /^(human|elf|dwarf|orc)$/.test(r) ? r : 'human';
  }
  function keyFor(name) {
    if (name === 'map') return 'map-' + race();
    if (name === 'builder' || name === 'combat' || name === 'app-home') return name;
    if (/^report/.test(name)) return 'report';
    if (!name || name === 'off' || name === 'none' || name === 'silence') return '';
    return null;   // prompt_*, anykey, menu, unknown: keep what plays
  }
  function applyScreen() {
    if (!ctx || !musicOn) return;
    var k = keyFor(screenName);
    if (k === null || k === bedKey) return;
    var old = bed;
    bed = k ? bedFor(k) : null;
    bedKey = k;
    fadeOut(old, FADE);
    if (bed) fadeIn(bed);
  }
  function applyGains() {
    if (!ctx) return;
    var t = ctx.currentTime;
    master.gain.setTargetAtTime(vol, t, 0.03);
    musicBus.gain.setTargetAtTime(musicOn ? mVol * under : 0, t, 0.05);
    fxBus.gain.setTargetAtTime(fxOn ? fVol : 0, t, 0.02);
  }

  // ---- context and gesture handling ------------------------------------------
  function start() {
    if (!AC) return;
    try {
      if (!ctx) {
        ctx = new AC();
        master = ctx.createGain();
        musicBus = ctx.createGain();
        duck = ctx.createGain();
        fxBus = ctx.createGain();
        musicBus.connect(duck); duck.connect(master); fxBus.connect(master);
        var comp = ctx.createDynamicsCompressor();
        comp.threshold.value = -14; comp.ratio.value = 6;
        master.connect(comp); comp.connect(ctx.destination);
        applyGains();
        master.gain.value = vol; musicBus.gain.value = musicOn ? mVol : 0; fxBus.gain.value = fxOn ? fVol : 0;
        FX.forEach(fetchBuffer);
      }
      var p = ctx.resume();
      if (p && p.catch) p.catch(function () {});
      applyScreen();
    } catch (e) { ctx = null; }
  }
  function waitForGesture() {
    if (pending || !AC) return;
    pending = true;
    var go = function () {
      document.removeEventListener('click', go, true);
      document.removeEventListener('keydown', go, true);
      document.removeEventListener('pointerdown', go, true);
      pending = false;
      if (musicOn || fxOn) start();
    };
    document.addEventListener('click', go, true);
    document.addEventListener('keydown', go, true);
    document.addEventListener('pointerdown', go, true);
  }
  function stopBed() {
    if (bed) { var b = bed; bed = null; bedKey = ''; fadeOut(b, 0.4); }
  }
  function refresh(wasAny) {
    var any = musicOn || fxOn;
    if (any && !ctx) start();
    else if (ctx) {
      applyGains();
      if (!musicOn) stopBed(); else applyScreen();
      if (!any) {
        var c = ctx;
        window.setTimeout(function () { if (!musicOn && !fxOn && c.suspend) c.suspend().catch(function () {}); }, 600);
      } else if (ctx.state === 'suspended') ctx.resume().catch(function () {});
    }
  }
  function clamp01(v) { v = Number(v); if (!(v >= 0)) v = 0; return v > 1 ? 1 : v; }

  var api = {
    enable: function (v) {
      if (!AC) return;
      musicOn = !!v; fxOn = !!v; save(); refresh();
    },
    enabled: function () { return !!AC && (musicOn || fxOn); },
    setMusic: function (v) { if (!AC) return; musicOn = !!v; save(); refresh(); },
    music: function () { return !!AC && musicOn; },
    setEffects: function (v) { if (!AC) return; fxOn = !!v; save(); refresh(); },
    effects: function () { return !!AC && fxOn; },
    setVolume: function (v) { vol = clamp01(v); if (AC) save(); if (ctx) applyGains(); },
    volume: function () { return vol; },
    musicVolume: function (v) {
      if (v !== undefined) { mVol = clamp01(v); if (AC) save(); if (ctx) applyGains(); }
      return mVol;
    },
    // a narration speaks: the music bed sinks to this share of the player's volume (1 = back); not saved
    underVoice: function (f) { under = clamp01(f); if (ctx) applyGains(); return under; },
    effectsVolume: function (v) {
      if (v !== undefined) { fVol = clamp01(v); if (AC) save(); if (ctx) applyGains(); }
      return fVol;
    },
    event: function (name) {
      name = ALIAS[name] || name;
      if (!ctx || !fxOn || FX.indexOf(name) < 0) return;
      try {
        if (ctx.state === 'suspended') ctx.resume();
        playFx(name);
      } catch (e) {}
    },
    screen: function (name) {
      screenName = name ? String(name) : '';
      try { applyScreen(); } catch (e) {}
    },
    // the preview of the options panel: the doors of the app open
    _demo: function () {
      var names = ['app-doors-open'];
      if (ctx && fxOn) api.event(names[0]);
      return names;
    },
    _nodes: function () { return nodes; },
    _state: function () { return ctx ? ctx.state : 'none'; },
    _bed: function () { return bedKey; },
    _loaded: function () { return Object.keys(buffers); },
    _failed: function () { return Object.keys(failed); }
  };

  load();
  if (!AC) { musicOn = false; fxOn = false; }
  window.conquerAudio = api;
  document.addEventListener('conquer:race', function () {
    // another race, another map bed
    if (ctx && musicOn && /^map/.test(bedKey)) { bedKey = ''; try { applyScreen(); } catch (e) {} }
  });
  if (musicOn || fxOn) waitForGesture();
})();
