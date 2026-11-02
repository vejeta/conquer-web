// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Optional sound for the game pages, synthesised with the Web Audio API
// (no audio files). Chiptune with a medieval flavour: modal scales, square
// and triangle waves, a soft noise drum. Off by default and quiet
// (on by default in the Android app, after the first gesture).
// window.conquerAudio: enable(on), enabled(), setVolume(v), volume(),
// event(name), screen(name), _demo(). Every method is a no-op when the
// browser has no Web Audio.
(function () {
  'use strict';
  var KEY = 'conquer-audio';
  var AC = window.AudioContext || window.webkitAudioContext;
  var on = false, vol = 0.4, ctx = null, master = null, noiseBuf = null;
  var screenName = '', music = null, musicKey = '', pending = false;
  var moveStep = 0, nodes = 0;

  function load() {
    try {
      var s = JSON.parse(window.localStorage.getItem(KEY) || '{}');
      if (typeof s.volume === 'number' && s.volume >= 0 && s.volume <= 1) vol = s.volume;
      if (s.enabled === true) on = true;
    } catch (e) {}
    // In the app, sound is on until the player turns it off (it starts at
    // the first gesture); on the web it is off until asked for
    try {
      if (window.conquerApp && window.conquerApp.is && window.localStorage.getItem(KEY) === null) on = true;
    } catch (e) {}
  }
  function save() {
    try { window.localStorage.setItem(KEY, JSON.stringify({ enabled: on, volume: vol })); } catch (e) {}
  }

  function hz(m) { return 440 * Math.pow(2, (m - 69) / 12); }

  // ---- building blocks, all scheduled on the AudioContext clock ----------
  function tone(type, freq, t, dur, level, opt) {
    opt = opt || {};
    var o = ctx.createOscillator(), g = ctx.createGain(), out = opt.dest || master;
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
    s.connect(f); f.connect(g); g.connect(dest || master);
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
    out.connect(master);
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
  function keyFor(name) {
    if (name === 'map' || name === 'builder' || name === 'combat') return name;
    if (/^report/.test(name)) return 'report';
    if (!name || name === 'off' || name === 'none' || name === 'silence') return '';
    return null;   // prompt_*, anykey, menu, unknown: keep what plays
  }
  function applyScreen() {
    if (!ctx || !on) return;
    var k = keyFor(screenName);
    if (k === null || k === musicKey) return;
    stopMusic(music, 1.5);
    music = k ? startMusic(k) : null;
    musicKey = k;
  }

  // ---- context and gesture handling ------------------------------------------
  function start() {
    if (!AC) return;
    try {
      if (!ctx) {
        ctx = new AC();
        master = ctx.createGain();
        master.gain.value = vol;
        var comp = ctx.createDynamicsCompressor();
        comp.threshold.value = -18; comp.ratio.value = 12;
        master.connect(comp); comp.connect(ctx.destination);
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
      pending = false;
      if (on) start();
    };
    document.addEventListener('click', go, true);
    document.addEventListener('keydown', go, true);
  }

  var api = {
    enable: function (v) {
      if (!AC) return;
      on = !!v;
      save();
      if (on) { start(); }
      else if (ctx) {
        stopMusic(music, 0.3); music = null; musicKey = '';
        var c = ctx;
        window.setTimeout(function () { if (!on && c.suspend) c.suspend().catch(function () {}); }, 500);
      }
    },
    enabled: function () { return !!AC && on; },
    setVolume: function (v) {
      v = Number(v);
      if (!(v >= 0)) v = 0;
      if (v > 1) v = 1;
      vol = v;
      if (AC) save();
      if (master) master.gain.setTargetAtTime(vol, ctx.currentTime, 0.02);
    },
    volume: function () { return vol; },
    event: function (name) {
      if (!ctx || !on || !EVENTS.hasOwnProperty(name)) return;
      try {
        if (ctx.state === 'suspended') ctx.resume();
        EVENTS[name](ctx.currentTime + 0.01);
      } catch (e) {}
    },
    screen: function (name) {
      screenName = name ? String(name) : '';
      try { applyScreen(); } catch (e) {}
    },
    // plays every effect in turn; returns the names, in order
    _demo: function () {
      var names = ['move', 'bump', 'ui', 'open', 'close', 'combat', 'turn', 'news', 'message'];
      if (!ctx || !on) return names;
      names.forEach(function (n, i) { window.setTimeout(function () { api.event(n); }, i * 1500); });
      return names;
    },
    _nodes: function () { return nodes; },
    _state: function () { return ctx ? ctx.state : 'none'; }
  };

  load();
  if (!AC) on = false;
  window.conquerAudio = api;
  if (on) waitForGesture();
})();
