// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The story of Conquer (story.html): eight scenes, each with its narration
// (story/<lang>/<n>.mp3 or .ogg, when the owner has put one there; otherwise
// the panel is timed by the length of its text), a typewriter dialogue and a
// little motion, all made of the design system's own pieces (artefact frames,
// gate, mock terminals). The sound is audio.js: each scene sets a bed
// (screen) and some effects (event), see TL. Tap, click, Space or the right
// arrow go on; the left arrow goes back; Skip is always there.
// window.conquerStory is the hook of the tests.
(function () {
  'use strict';
  var PANELS = 8, SEEN = 'conquer-story-seen', SOUND = 'conquer-story-sound';
  var q = new URLSearchParams(location.search);
  var durFixed = (q.get('dur') || '').split(',').map(Number);
  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (id) { return document.getElementById(id); };
  var T = function (k, p) { return window.conquerI18n.t('story.' + k, p); };
  var n = 0, timers = [], typers = [], started = false, sound = true, panelStart = 0, panelD = 0, advTimer = 0;
  var audio = null, narr = {}, gen = 0, ownChoice = false, touched = false, nel = null;
  var RENDER = q.get('render') === '1';   // the video driver: no narration, no sound, it advances the scenes itself
  var SILENT = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
  var AUDIO_KEY = 'conquer-audio';    // audio.js keeps the player's choice here

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {} return null; }

  // ---- the timeline of each scene: [fraction of the narration, hook, audio cue] -----
  // cue: 'screen:<bed>' or 'event:<name>' of window.conquerAudio (audio.js)
  var TL = {
    1: [[0, '', 'screen:report'], [0.10, 'login', ''], [0.42, 'password', ''], [0.52, 'prompt', ''], [0.64, 'conquer', '']],
    2: [[0.02, 'subject', 'event:news'], [0.06, '', 'screen:app-home'], [0.2, 'from', ''], [0.3, 'map', '']],
    3: [[0.13, 'v0', 'race:human'], [0.36, 'v1', 'race:elf'], [0.59, 'v2', 'race:dwarf'], [0.79, 'v3', 'race:orc']],
    4: [[0.02, 'sky', 'screen:map'], [0.04, '', 'event:turn'], [0.05, 'armies', ''], [0.68, 'paper', ''], [0.74, 'news', '']],
    5: [[0, '', 'screen:off'], [0.04, 'beam', ''], [0.12, 'off0', ''], [0.25, 'off1', ''], [0.38, 'off2', ''], [0.5, 'off3', ''], [0.62, 'off4', ''], [0.7, 'drawer', ''], [0.8, 'offmain', '']],
    6: [[0.04, 'r0', ''], [0.10, 'r1', ''], [0.16, 'r2', ''], [0.22, 'r3', ''], [0.28, 'say', ''], [0.46, 'open', 'event:app-doors-open'], [0.56, 'theme', 'screen:app-home']],
    7: [[0, '', 'screen:builder'], [0.04, 'label', ''], [0.26, 'name', ''], [0.46, 'pick', ''], [0.7, 'confirm', 'event:found']],
    8: [[0.03, 'screen', 'event:turn'], [0.14, '', 'screen:map'], [0.30, 'controls', ''], [0.5, 'title', ''], [0.62, 'fanfare', ''], [0.82, 'hum', '']]
  };
  var cues = {};
  Object.keys(TL).forEach(function (k) { cues[k] = TL[k].filter(function (e) { return e[2]; }).map(function (e) { return [e[0], e[2]]; }); });

  // ---- little helpers ---------------------------------------------------------
  function after(ms, fn) { var id = setTimeout(fn, ms); timers.push(id); return id; }
  function clearAll() { timers.forEach(clearTimeout); timers = []; typers = []; clearTimeout(advTimer); }
  function pad(s, w) { s = String(s); while (s.length < w) s += ' '; return s.slice(0, w); }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
  function rng(seed) { return function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }

  // a coarse value-noise island; returns rows of glyphs
  function terrain(w, h, seed, style) {
    var r = rng(seed), gw = 9, gh = 6, g = [], i, j, k;
    for (j = 0; j <= gh; j++) { g[j] = []; for (i = 0; i <= gw; i++) g[j][i] = r(); }
    var m = [];
    for (j = 0; j <= gh; j++) { m[j] = []; for (i = 0; i <= gw; i++) m[j][i] = r(); }
    function samp(a, x, y) {
      var fx = x * gw, fy = y * gh, ix = Math.min(gw - 1, Math.floor(fx)), iy = Math.min(gh - 1, Math.floor(fy)), dx = fx - ix, dy = fy - iy;
      dx = dx * dx * (3 - 2 * dx); dy = dy * dy * (3 - 2 * dy);
      return (a[iy][ix] * (1 - dx) + a[iy][ix + 1] * dx) * (1 - dy) + (a[iy + 1][ix] * (1 - dx) + a[iy + 1][ix + 1] * dx) * dy;
    }
    var rows = [];
    style = style || {};
    for (j = 0; j < h; j++) {
      var s = '';
      for (i = 0; i < w; i++) {
        var x = i / (w - 1), y = j / (h - 1), ex = (x - .5) * 2, ey = (y - .5) * 2;
        var v = samp(g, x, y) * 1.15 - (ex * ex * .55 + ey * ey * .7) + (style.land || 0), mo = samp(m, x, y), c;
        if (v < .30) c = '~';
        else if (v < .36) c = '.';
        else if (v > .70 + (style.rock || 0)) c = '#';
        else if (v > .58 + (style.rock || 0)) c = '^';
        else if (mo > .52) c = '%';
        else c = (i * 7 + j * 3) % 11 === 0 ? ',' : '.';
        s += c;
      }
      rows.push(s);
    }
    return rows;
  }
  function glyphs(row, armies, j) {
    var out = '', run = '', cls = '', i, c, a, k;
    function flush() { if (run) { out += cls ? '<i class="' + cls + '">' + run + '</i>' : run; run = ''; } }
    for (i = 0; i < row.length; i++) {
      c = row.charAt(i); a = null;
      if (armies) for (k = 0; k < armies.length; k++) if (armies[k].x === i && armies[k].y === j) a = armies[k];
      if (a) { flush(); out += '<b class="army a' + a.k + '">' + a.c + '</b>'; continue; }
      var cl = c === '~' ? 'w' : (c === '.' || c === ',') ? 'dim' : '';
      if (cl !== cls) { flush(); cls = cl; }
      run += c;
    }
    flush();
    return out;
  }

  // ---- the real game screen: the world of hero/map.json in the game's own layout ------------
  var WORLD = { w: 0, rows: [], nations: {}, war: { armies: [], conquered: [], battle: [0, 0] } };
  var RIGHT = ["  *army 0: 250 Inf     ", "   mv:0 st:GARRISON   ", " >King 1: str=100     ", "   mv:20 st:DEFEND    ", " >Baron 2: str=50     ", "   mv:20 st:DEFEND    ", " >Baron 3: str=50     ", "   mv:20 st:DEFEND    ", " >Baron 4: str=50     ", "   mv:20 st:DEFEND    ", "  MORE...             ", "  x is 13  y is 26    ", "  owner: tidewater    ", "  CAPITOL   LT VEG   6", "  HUMAN     FLAT      ", "  people:  33000      ", "  move cost:   1      ", "  item: philosophy(c) ", "  gold:  0  metal:  0 ", "  fortress: +60%      ", "                      "];
  var BOTTOM = ["Conquer: 4.12 Turn 1                                        nation...tidewater  ",
                "  type Q to save & quit           You have Conquer Mail     treasury.300000     ",
                "  type ? for help                                           Spring of Year 1    "];
  function sec(x, y) {
    var row = WORLD.rows[y];
    if (!row || x < 0 || x >= WORLD.w) return null;
    var i = x * 4;
    return { alt: row.charAt(i), des: row.charAt(i + 1), owner: parseInt(row.substr(i + 2, 2), 16) };
  }
  // one sector as the game draws it: its designation, else its owner's mark, else its altitude
  function cell(x, y, o) {
    var k = x + ',' + y;
    if (o.special && o.special[k]) return o.special[k];
    var s = sec(x, y);
    if (!s) return [' ', ''];
    if (o.taken && o.taken[k]) return [WORLD.war.winner, 'b'];
    if (s.des && s.des !== '-') return [s.des, 'b'];
    if (s.owner) return [WORLD.nations[s.owner] || '?', 'b'];
    return [s.alt, s.alt === '~' ? 'w' : ''];
  }
  // rows of the map window: every sector is a character and a space
  function worldRows(x0, y0, cols, rows, o) {
    var out = [];
    for (var j = 0; j < rows; j++) {
      var line = '', run = '', cls = null;
      for (var i = 0; i < cols; i++) {
        var c = cell(x0 + i, y0 + j, o);
        if (/army|cursor/.test(c[1])) {
          if (run) line += cls ? '<i class="' + cls + '">' + esc(run) + '</i>' : esc(run);
          run = ''; cls = null; line += '<i class="' + c[1] + '">' + esc(c[0]) + '</i> ';
          continue;
        }
        if (c[1] !== cls) { if (run) line += cls ? '<i class="' + cls + '">' + esc(run) + '</i>' : esc(run); run = ''; cls = c[1]; }
        run += c[0] + ' ';
      }
      if (run) line += cls ? '<i class="' + cls + '">' + esc(run) + '</i>' : esc(run);
      out.push(line);
    }
    return out;
  }
  // the map screen of the game (the recorded one: map left, army and sector panel right, status below)
  function gameScreen(x0, y0, o) {
    o = o || {};
    var sp = o.special || {};
    (o.armies || []).forEach(function (a) { sp[a.x + ',' + a.y] = [a.c, 'army ' + (a.def ? 'a2' : 'a1')]; });
    if (o.cursor) sp[o.cursor[0] + ',' + o.cursor[1]] = ['C', 'cursor'];
    o.special = sp;
    var m = worldRows(x0, y0, 29, 21, o), out = '';
    for (var j = 0; j < 21; j++) out += m[j] + esc(RIGHT[j]) + '\n';
    return out + esc(BOTTOM[0]) + '\n' + esc(BOTTOM[1]) + '\n' + esc(BOTTOM[2]);
  }
  function ARCH() {
    return '<div class="arch" aria-hidden="true"><i class="lintel"></i><i class="sill"></i><i class="col l"></i><i class="col r"></i><i class="cor tl"></i><i class="cor tr"></i><i class="cor bl b"></i><i class="cor br b"></i></div>';
  }
  var RUNES = 'ᛈᛖᛞᛟ ᛗᛖᛚᛚᛟᚾ ᚨ ᛗᛁᚾᚾᛟ';
  function stone(cls, pre, attrs, rows) {
    rows = rows || 24;
    var have = pre.split('\n').length;
    while (have++ < rows) pre += '\n ';
    return '<div class="gamescreen"><div class="gs"><div class="stone ' + (cls || '') + '"' + (attrs || '') + '><span class="roll l"></span><span class="roll r"></span><span class="slit"></span>' +
      ARCH() + '<div class="runes" aria-hidden="true">' + RUNES + '</div><div class="terminal" role="img" aria-label="Conquer"><pre>' + pre + '</pre></div></div></div></div>';
  }
  function raceNow() {
    var r = store('conquer-race') || store('conquer-race-seen');
    return /^(elf|dwarf|orc)$/.test(r) ? r : 'human';
  }

  // fit the text of every terminal of the panel to its width
  function fit(root) {
    var ts = (root || document).querySelectorAll('.stone .terminal');
    Array.prototype.forEach.call(ts, function (t) {
      var p = t.querySelector('pre');
      if (!t.clientWidth) return;
      var cs = getComputedStyle(t), avail = t.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      p.style.fontSize = '100px';
      var w = p.getBoundingClientRect().width;
      var min = t.closest('.vig') ? 7 : 8;
      p.style.fontSize = Math.max(min, Math.min(40, 100 * avail / w)).toFixed(2) + 'px';
    });
  }

  // ---- typewriter (40 ms per character, a tap finishes it) ------------------------
  function cursorAfter(el) {
    var pre = el.closest('pre');
    if (!pre) return;
    Array.prototype.forEach.call(pre.querySelectorAll('.cursor'), function (c) { c.parentNode.removeChild(c); });
    var c = document.createElement('span'); c.className = 'cursor'; c.textContent = ' ';
    el.parentNode.insertBefore(c, el.nextSibling);
  }
  function typeInto(el, text, done, onChar) {
    if (!el) return;
    cursorAfter(el);
    if (reduced) { el.textContent = text; if (onChar) onChar(); if (done) done(); return; }
    var i = 0, id, rec;
    function step() {
      i++; el.textContent = text.slice(0, i);
      if (onChar) onChar();
      if (i >= text.length) { finish(); } else { id = setTimeout(step, 40); rec.id = id; timers.push(id); }
    }
    function finish() {
      clearTimeout(rec.id); el.textContent = text; typers.splice(typers.indexOf(rec), 1);
      if (onChar) onChar();
      if (done) done();
    }
    rec = { finish: finish, id: 0 };
    typers.push(rec);
    step();
  }

  // ---- the scenes -------------------------------------------------------------------
  var STATUS = '  CONQUER ';
  function room(mainPre, crts) {
    var cr = '';
    for (var i = 0; i < crts; i++) cr += '<i class="crt" data-i="' + i + '"></i>';
    return '<div class="sky"></div><div class="room"><div class="window"><div class="rain"></div><span class="mull"></span></div><div class="crts">' + cr + '</div><div class="desk"></div>' +
      '<div class="sw">' + stone('', mainPre) + '</div></div>';
  }
  function dust() {
    var s = '<div class="beam"></div><div class="dust">';
    for (var i = 0; i < 26; i++) s += '<i style="left:' + (8 + (i * 37) % 70) + '%;top:' + (20 + (i * 53) % 70) + '%;animation-delay:-' + ((i * 7) % 9) + 's"></i>';
    return s + '</div>';
  }
  var DRAWER = '<div class="drawer"><svg viewBox="0 0 220 110" aria-hidden="true"><rect x="2" y="30" width="216" height="78" rx="4" fill="#1a130c" stroke="#4a3a28" stroke-width="3"/><rect x="2" y="30" width="216" height="14" fill="#2a2118"/>' +
    '<g transform="translate(18 48) rotate(-6)"><rect width="62" height="62" rx="3" fill="#222"/><rect x="12" width="38" height="24" fill="#8c9aa0"/><rect x="34" y="4" width="9" height="16" fill="#222"/><rect x="8" y="34" width="46" height="26" rx="2" fill="#d8d1b8"/><path d="M14 44h34M14 50h26" stroke="#8a7f5e" stroke-width="2"/></g>' +
    '<g transform="translate(112 44)"><rect width="92" height="58" rx="5" fill="#2b2b2e" stroke="#555" stroke-width="2"/><circle cx="28" cy="29" r="15" fill="#111" stroke="#777" stroke-width="3"/><circle cx="64" cy="29" r="15" fill="#111" stroke="#777" stroke-width="3"/><circle cx="28" cy="29" r="5" fill="#777"/><circle cx="64" cy="29" r="5" fill="#777"/><rect x="14" y="46" width="64" height="6" fill="#6a5a3a"/></g></svg></div>';

  var SCENES = {
    1: function () {
      var pre = pad(' ' + 'CC-VAX computing centre', 40) + pad('tty03   Tue 13 Oct 1987', 40) + '\n\n' +
        '4.3 BSD UNIX (cc-vax)\n\n' +
        '<span class="ty" id="t-login"></span><span class="cursor"> </span>\n' +
        '<span class="hid" id="t-pw">Password:</span>\n' +
        '<span class="hid" id="t-last">Last login: Mon Oct 12 23:58:41 on tty03</span>\n\n' +
        '<span class="hid" id="t-prompt">$ conquer</span>\n<span class="ty" id="t-conq"></span>\n';
      return room(pre, 4);
    },
    2: function () {
      var rows = worldRows(12, 60, 40, 17, {}), out = '';
      rows.forEach(function (r) { out += '<span class="mrow hid">' + r + '</span>\n'; });
      var pre = pad('NEWS  comp.sources.games', 56) + pad('1 of 1', 24) + '\n\n' +
        '<span class="ty" id="t-subj"></span><span class="cursor"> </span>\n' +
        '<span class="hid" id="t-from">From: Ed Barlow, Adam Bryant</span>\n<span class="hid" id="t-date">Date: 1987</span>\n\n' + out;
      return '<div class="sky"></div><div class="sw">' + stone('', pre) + '</div>';
    },
    3: function () {
      var races = ['human', 'elf', 'dwarf', 'orc'], seeds = [11, 23, 37, 51], styles = [{}, { land: -.04 }, { rock: -.12 }, { rock: -.2, land: .02 }], h = '<div class="bgv"></div>';
      races.forEach(function (r, i) {
        var rows = terrain(30, 11, seeds[i], styles[i]), pre = pad(' ' + r.toUpperCase(), 30) + '\n';
        rows.forEach(function (row, j) { pre += glyphs(row) + '\n'; });
        h += '<div class="vig" data-race="' + r + '" id="v' + i + '">' + stone('', pre, '', 12) + '<b class="name">' + esc(T('r_' + r)) + '</b><small>' + esc(T('a_' + r)) + '</small></div>';
      });
      return h;
    },
    4: function () {
      var paper = pad('', 80) + '\n\n  Message from Conquer\n\n  <span class="ty" id="t-news"></span><span class="cursor"> </span>\n\n\n\n                      HIT ANY KEY TO CONTINUE\n                  HIT RETURN TO DELETE MESSAGE';
      return '<div class="skyv" id="skyv" style="animation-play-state:paused"></div><div class="orbit" id="orbit" style="animation-play-state:paused"><i class="sun"></i><i class="moon"></i></div>' +
        '<div class="sw" id="map4">' + stone('', gameScreen(17, 62, {})) + '</div><div class="paper" id="paper">' + stone('parchment', paper, '', 11) + '</div>';
    },
    5: function () {
      var pre = pad(' ' + 'CC-VAX computing centre', 40) + pad('tty03', 40) + '\n\n4.3 BSD UNIX (cc-vax)\n\nlogin: edb\nPassword:\nLast login: Mon Oct 12 23:58:41 on tty03\n\n$ conquer\nConquer v4 — Turn 1<span class="cursor"> </span>\n';
      return room(pre, 5) + dust() + DRAWER;
    },
    6: function () {
      var runes = RUNES.split(' ').map(function (w, i) { return '<i data-w="' + i + '">' + w + '</i>'; }).join(' ');
      var pre = gameScreen(59, 18, { cursor: [72, 27] });
      return '<div class="sky"></div><div class="glow" id="glow"></div><div class="gate" id="gate"><div class="gate-stage" data-race="dwarf">' +
        ARCH().replace('class="arch"', 'class="arch" style="z-index:6"') + '<div class="runes" id="gate-runes" aria-hidden="true">' + runes + '</div>' +
        '<div class="behind"><div class="gamescreen" style="width:100%"><div class="gs"><div class="stone">' + ARCH() + '<div class="terminal" role="img" aria-label="Conquer"><pre>' + pre + '</pre></div></div></div></div></div>' +
        '<div class="leaf l"></div><div class="leaf r"></div><div class="rbig" id="rbig" aria-hidden="true">' + runes + '</div><div class="say" id="say"><span class="ty" id="t-say"></span></div></div></div>';
    },
    7: function () {
      var pre = 'Building Country Number 8\n<span class="ty" id="t-lab"></span> <span class="ty" id="t-name"></span>\n\n' +
        '<span class="hid" id="b-leader">Leader Name: Pelayo</span>\n<span class="hid" id="b-race">Enter your Race [ (D)warf (E)lf (H)uman (O)rc ]: <span class="ty" id="t-race"></span></span>\n\n' +
        '<span class="hid" id="b-ok">Ok, Your Nation has been Added to the World</span>';
      var rows = pre.split('\n').length;
      while (rows++ < 22) pre += '\n';
      pre += ' Conquer 4.12: Nation Builder                                       Country #8\n-';
      var quill = '<svg class="quill" id="quill" viewBox="0 0 120 200" aria-hidden="true"><path d="M2 198 C10 150 30 60 100 4 C108 60 90 120 6 198Z" fill="#241a10"/><path d="M12 188 C40 120 70 70 98 14" stroke="#7a6a50" stroke-width="2" fill="none"/></svg>';
      return '<div class="sky"></div><div class="bld" id="bld">' + stone('parchment', pre) + '</div><div class="mini" id="mini"><i class="ring" id="ring"></i><div class="flag" id="flag"><svg viewBox="0 0 60 80"><rect x="4" y="0" width="3" height="80" fill="#c9c2ac"/><path class="cloth" d="M7 4 H56 L46 18 L56 32 H7Z"/></svg></div></div>' + quill;
    },
    8: function () {
      var r = raceNow(), pre = gameScreen(59, 18, { cursor: [72, 27] });
      var chips = ['Move', 'Army', 'Budget', 'News', 'Diplomacy', 'Score'].map(function (c) { return '<span class="key key-small">' + c + '</span>'; }).join('');
      var dp = '<div class="dpad" aria-hidden="true"><span class="key">&#8598;</span><span class="key">&#8593;</span><span class="key">&#8599;</span><span class="key">&#8592;</span><span class="key gap"></span><span class="key">&#8594;</span><span class="key">&#8601;</span><span class="key">&#8595;</span><span class="key">&#8600;</span></div>';
      return '<div data-race="' + r + '" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.6cqh"><div class="sky"></div><div class="bgmap"></div><div class="title" id="title">CONQUER</div><div class="sw" id="sw8" style="margin-top:6cqh">' + stone('', pre) + '</div><div class="controls" id="controls"><div class="chips">' + chips + '</div>' + dp + '</div></div>';
    }
  };

  // ---- the hooks that animate each scene -------------------------------------------------
  var HOOK = {
    login: function (P) { typeInto($('t-login'), T('d1a')); },
    password: function () { $('t-pw').classList.remove('hid'); $('t-last').classList.remove('hid'); },
    prompt: function () { $('t-prompt').classList.remove('hid'); },
    conquer: function () { typeInto($('t-conq'), T('d1b')); },
    subject: function () { typeInto($('t-subj'), T('d2')); },
    from: function () { ['t-from', 't-date'].forEach(function (i) { $(i).classList.remove('hid'); }); },
    map: function (P, D) {
      var rows = P.querySelectorAll('.mrow'), step = Math.max(60, (D * 0.5 * 1000) / rows.length), i = 0;
      function one() { if (i >= rows.length) return; rows[i++].classList.remove('hid'); if (reduced) { one(); } else after(step, one); }
      one();
    },
    v0: function () { $('v0').classList.add('on'); }, v1: function () { $('v1').classList.add('on'); },
    v2: function () { $('v2').classList.add('on'); }, v3: function () { $('v3').classList.add('on'); },
    sky: function (P, D) {
      var d = Math.max(6, D * 0.7).toFixed(1) + 's';
      ['skyv', 'orbit'].forEach(function (i) { var e = $(i); e.style.animationDuration = d; e.style.animationPlayState = 'running'; });
    },
    armies: function (P, D) {
      var war = WORLD.war, pre = P.querySelector('#map4 pre'), tick = 0, MARCH = 8;
      function draw() {
        var armies = [], taken = {}, special = {};
        war.armies.forEach(function (a) {
          if (a.defender && tick > MARCH + 4) return;
          var k = a.defender ? 1 : Math.min(1, tick / MARCH);
          armies.push({ x: Math.round(a.from[0] + (a.to[0] - a.from[0]) * k), y: Math.round(a.from[1] + (a.to[1] - a.from[1]) * k), c: a.mark, def: a.defender });
        });
        if (tick > MARCH && tick <= MARCH + 4) {
          var b = war.battle;
          [[-1, 0], [1, 0], [0, -1], [0, 1]].forEach(function (d, i) { if (i < tick - MARCH + 1) special[(b[0] + d[0]) + ',' + (b[1] + d[1])] = ['*', 'b war']; });
          special[b[0] + ',' + b[1]] = ['!', 'b war'];
          armies = armies.filter(function (a) { return a.def || tick <= MARCH; });
        }
        if (tick > MARCH + 4) war.conquered.slice(0, tick - MARCH - 4).forEach(function (p) { taken[p[0] + ',' + p[1]] = true; });
        pre.innerHTML = gameScreen(17, 62, { armies: armies, taken: taken, special: special });
        fit(P);
      }
      draw();
      if (reduced) { tick = MARCH + 12; draw(); return; }
      (function go() {
        if (++tick > MARCH + 12) return;
        draw(); after(tick > MARCH + 4 ? 180 : 650, go);
      })();
    },
    paper: function () { $('paper').classList.add('on'); fit($('paper')); },
    news: function (P) { typeInto($('t-news'), T('d4')); },
    beam: function () { var b = document.querySelector('.p5 .beam'), d = document.querySelector('.p5 .dust'); b.classList.add('on'); d.classList.add('on'); },
    off0: function () { crtOff(0); }, off1: function () { crtOff(1); }, off2: function () { crtOff(2); }, off3: function () { crtOff(3); }, off4: function () { crtOff(4); },
    drawer: function () { document.querySelector('.p5 .drawer').classList.add('on'); },
    offmain: function (P) { P.querySelector('.terminal').classList.add('off'); },
    r0: function () { rune(0); }, r1: function () { rune(1); }, r2: function () { rune(2); }, r3: function () { rune(3); },
    say: function () { $('rbig').classList.add('dimmed'); typeInto($('t-say'), T('d6')); },
    open: function () { $('gate').classList.add('open'); $('glow').classList.add('on'); },
    theme: function () {},
    label: function () { $('quill').classList.add('on'); typeInto($('t-lab'), T('d7'), null, quillTo); },
    name: function () { typeInto($('t-name'), 'Valdor', null, quillTo); },
    pick: function (P, D) {
      $('b-leader').classList.remove('hid'); $('b-race').classList.remove('hid');
      var letters = ['D', 'E', 'O', 'H'], i = 0, el = $('t-race');
      function sel() { el.textContent = letters[i % 4]; cursorAfter(el); quillTo(el); i++; if (i < 5 && !reduced) after(520, sel); }
      sel();
    },
    confirm: function () { $('b-ok').classList.remove('hid'); $('quill').classList.remove('on'); $('flag').classList.add('on'); $('ring').classList.add('on'); },
    screen: function () {},
    controls: function () { $('controls').classList.add('on'); },
    title: function () { $('title').classList.add('on'); },
    fanfare: function () {}, hum: function () {}
  };
  function crtOff(i) { var c = document.querySelector('.p5 .crt[data-i="' + i + '"]'); if (c) c.classList.add('off'); }
  function rune(i) {
    Array.prototype.forEach.call(document.querySelectorAll('.p6 i[data-w="' + i + '"]'), function (el) { el.classList.add('lit'); });
    document.getElementById('gate-runes').classList.add('lit');
  }
  function quillTo(target) {
    var qe = $('quill'), P = qe && qe.parentNode; if (!qe) return;
    var cur = (target && target.getBoundingClientRect) ? target : document.querySelector('#bld .cursor');
    if (!cur) return;
    var a = cur.getBoundingClientRect(), b = P.getBoundingClientRect(), h = qe.getBoundingClientRect().height;
    qe.style.transform = 'translate(' + (a.right - b.left - 2) + 'px,' + (a.bottom - b.top - h) + 'px)';
    qe.style.transition = 'transform 120ms linear, opacity 500ms';
  }

  // ---- panels ----------------------------------------------------------------------------
  function estimate(n) { return Math.max(5, 2.2 + T('p' + n).length * 0.062); }
  function setCaption(n) {
    var p = $('cap-text');
    p.classList.add('hide');
    setTimeout(function () { p.textContent = T('p' + n); p.classList.remove('hide'); }, reduced ? 0 : 250);
    if (reduced) p.textContent = T('p' + n);
  }
  function dots() {
    var d = $('dots'), h = '';
    for (var i = 1; i <= PANELS; i++) h += '<i class="' + (i < n ? 'done' : i === n ? 'on' : '') + '"></i>';
    d.innerHTML = h; d.setAttribute('aria-label', T('progress', { n: n, total: PANELS }));
  }

  // ---- sound: audio.js beds and effects (both are no-ops without Web Audio) ---------------
  function cue(c) {
    var A = window.conquerAudio, p = c.split(':');
    if (!sound || !A) return;
    if (c === 'screen:map') p = ['race', n === 8 ? raceNow() : 'human'];
    try {
      if (p[0] === 'race') {
        // the map bed follows the race of the sub-panel that lights up: audio.js reads <html data-race>
        // when it is asked, so the attribute is set for that call only (the artefacts of the page
        // are dressed by their own data-race, and an html one would override them all)
        var root = document.documentElement, was = root.getAttribute('data-race');
        root.setAttribute('data-race', p[1]);
        try { A.screen('map'); } finally { if (was === null) root.removeAttribute('data-race'); else root.setAttribute('data-race', was); }
      } else if (p[0] === 'screen') A.screen(p[1]);
      else if (p[0] === 'event') A.event(p[1]);
    } catch (e) {}
  }
  // the screen of the scene that plays, again (sound turned on half-way)
  function resumeBed() {
    var done = null;
    TL[n].forEach(function (e) { if (e[2] && e[0] * panelD * 1000 <= Date.now() - panelStart && /^(screen|race):/.test(e[2])) done = e[2]; });
    if (done) cue(done);
  }

  function show(k) {
    var myGen = ++gen;
    clearAll();
    if (audio) { try { audio.pause(); } catch (e) {} audio = null; }
    voice(false);
    var prev = n; n = k;
    $('story').setAttribute('data-n', n);
    $('back').disabled = n <= 1;
    $('actions').hidden = true;
    dots(); setCaption(n);
    var panels = $('panels'), P;
    Array.prototype.forEach.call(panels.children, function (c) { if (c.getAttribute('data-p') != n) c.classList.remove('on'); });
    P = panels.querySelector('[data-p="' + n + '"]');
    if (!P) { P = document.createElement('section'); P.className = 'panel p' + n; P.setAttribute('data-p', n); panels.appendChild(P); }
    P.innerHTML = SCENES[n]();
    P.classList.add('on');
    fit(P);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { fit(P); });
    var D = durFixed[n - 1] || estimate(n);
    var mp;
    function run(realD) {
      if (myGen !== gen) return;
      D = durFixed[n - 1] || realD || D; panelD = D; panelStart = Date.now();
      TL[n].forEach(function (e) {
        after(e[0] * D * 1000, function () {
          if (e[1] && HOOK[e[1]]) HOOK[e[1]](P, D);
          if (e[2]) cue(e[2]);
          fit(P);
        });
      });
      if (n === PANELS) after(Math.min(0.5 * D * 1000, 4000), function () { $('actions').hidden = false; });
      else if (!RENDER) after((D + 1.0) * 1000, function () { go(n + 1); });
      if (sound && audio) {
        voice(true);
        audio.onended = function () { voice(false); };
        var pr = audio.play(); if (pr && pr.catch) pr.catch(function () {});
      }
    }
    // narration: story/<lang>/<n>.mp3 (or .ogg) when the owner has put one there, else the text
    // alone, timed by its length. A file that is not there is asked for once.
    var key = window.conquerLang() + '/' + n, a = nel || (nel = new Audio()), got = false, exts = ['mp3', 'ogg'], e = 0;
    function ready() { if (got) return; got = true; narr[key] = true; audio = a; run(a.duration); }
    function fail() { if (got) return; got = true; narr[key] = false; run(0); }
    if (RENDER || narr[key] === false) { run(0); return; }
    a.preload = 'auto';
    a.onloadedmetadata = function () { if (isFinite(a.duration) && a.duration > 0) ready(); else fail(); };
    a.onerror = function () {
      if (got) return;
      if (++e < exts.length) { a.src = 'story/' + key + '.' + exts[e]; a.load(); } else fail();
    };
    setTimeout(function () { if (!got) fail(); }, 3000);
    a.src = 'story/' + key + '.' + exts[0];
    a.load();
  }

  // the music bed sinks while the narration speaks (audio.js keeps the player's own volume)
  function voice(on) { var A = window.conquerAudio; try { if (A && A.underVoice) A.underVoice(on ? 0.35 : 1); } catch (e) {} }

  function go(k) {
    if (k < 1 || k > PANELS) return;
    show(k);
  }
  function flush() { if (!typers.length) return false; typers.slice().forEach(function (t) { t.finish(); }); return true; }
  function next() { if (!started) return; if (flush()) return; if (n < PANELS) go(n + 1); }
  function back() { if (!started) return; if (n > 1) go(n - 1); }

  function target() {
    var nx = q.get('next'), lang = window.conquerLang(), t;
    if (nx && /^[\w.\/-]+(\?[\w=&.%-]*)?$/.test(nx) && nx.indexOf('..') < 0) t = nx;
    else if (q.get('to') === 'try') t = 'try/';
    else t = window.conquerServerUrl ? window.conquerServerUrl('game.html') : 'game.html';
    if (lang !== 'en' && !/[?&]lang=/.test(t)) t += (t.indexOf('?') < 0 ? '?' : '&') + 'lang=' + lang;
    return t;
  }
  // in the Android app the game is not behind a link: leaving goes to the app's Home
  function leave() {
    store(SEEN, '1');
    var go = function () { location.href = target(); }, A = window.conquerApp;
    if (A && A.is && A.has && A.has() && A.send({ type: 'home' }, go)) return;
    go();
  }

  // the player's own choice (audio.js keeps it in localStorage); without one, the story plays with sound
  function audioChoice() { return store(AUDIO_KEY); }
  function soundWanted() {
    var A = window.conquerAudio;
    if (audioChoice() !== null) return !!(A && (A.music() || A.effects()));
    return store(SOUND) !== '0';
  }
  function paintSound() {
    var b = $('sound');
    b.setAttribute('aria-pressed', sound ? 'true' : 'false'); b.textContent = sound ? T('sound_on') : T('sound_off');
  }
  // user: the button was pressed (that is a choice, and audio.js keeps it)
  function setSound(on, user) {
    var A = window.conquerAudio;
    sound = on;
    paintSound();
    if (user) { store(SOUND, on ? '1' : '0'); ownChoice = false; }
    if (A) {
      if (user || (on && ownChoice)) {
        A.setMusic(on); A.setEffects(on);
        // switched on by the story, not by the player: the game page keeps its own default
        if (!user) { try { localStorage.removeItem(AUDIO_KEY); } catch (e) {} }
      }
      if (!on) A.screen('off');
    }
    if (audio) {
      if (!on) { try { audio.pause(); } catch (e) {} }
      else if (panelStart) { var el = (Date.now() - panelStart) / 1000; if (el < panelD) { try { audio.currentTime = el; audio.play(); } catch (e) {} } }
    }
    if (on && started && n) resumeBed();
  }

  function start() {
    if (started) return;
    started = true;
    document.body.classList.add('go');
    $('begin').classList.add('gone');
    store(SEEN, '1');
    // the first tap unlocks the narration element for the whole story (iOS, Android autoplay rules)
    if (!RENDER) {
      try {
        nel = nel || new Audio(); nel.src = SILENT;
        var up = nel.play(); nel.pause(); if (up && up.catch) up.catch(function () {});
      } catch (e) {}
    }
    setSound(sound, false);
    go(1);
  }

  function init() {
    document.title = T('title');
    $('story').setAttribute('aria-label', T('title'));
    $('back').setAttribute('aria-label', T('back'));
    $('play').href = target();
    ownChoice = audioChoice() === null;
    sound = RENDER ? false : soundWanted();
    paintSound();
    if (RENDER) ['sound', 'skip', 'back'].forEach(function (id) { $(id).style.visibility = 'hidden'; });
    dots(); n = 0;
    var P0 = document.createElement('section'); P0.className = 'panel p1 on'; P0.setAttribute('data-p', '1'); P0.innerHTML = SCENES[1](); $('panels').appendChild(P0); fit(P0);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { fit(P0); });
    $('skip').addEventListener('click', function (e) { e.stopPropagation(); leave(); });
    $('play').addEventListener('click', function (e) { e.preventDefault(); leave(); });
    $('sound').addEventListener('click', function (e) { e.stopPropagation(); setSound(!sound, true); });
    $('back').addEventListener('click', function (e) { e.stopPropagation(); back(); });
    $('replay').addEventListener('click', function (e) { e.stopPropagation(); go(1); });
    $('begin').addEventListener('click', function (e) { e.stopPropagation(); start(); });
    $('story').addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('button, a')) return;
      next();
    });
    document.addEventListener('keydown', function (e) {
      if (e.target && e.target.closest && e.target.closest('button, a') && (e.key === ' ' || e.key === 'Enter')) return;
      if (!started) { if (e.key === ' ' || e.key === 'Enter' || e.key === 'ArrowRight') { e.preventDefault(); start(); } return; }
      if (e.key === ' ' || e.key === 'ArrowRight') { e.preventDefault(); next(); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); back(); }
      else if (e.key === 'Escape') { leave(); }
    });
    window.addEventListener('resize', function () { fit($('panels')); });
    document.addEventListener('conquer:lang', function () {
      init.texts();
      if (started) { var k = n; show(k); }
    });
    if (q.get('begin') === '0') start();
  }
  init.texts = function () {
    document.title = T('title');
    $('story').setAttribute('aria-label', T('title'));
    $('sound').textContent = sound ? T('sound_on') : T('sound_off');
    $('play').href = target();
  };

  window.conquerStory = { cues: cues, TL: TL, start: start, go: go, next: next, back: back, state: function () { return { n: n, started: started, sound: sound, D: panelD }; } };
  Promise.all([window.conquerI18n.ready(), fetch('hero/map.json').then(function (r) { return r.json(); }).catch(function () { return null; })]).then(function (r) {
    if (r[1]) WORLD = r[1];
    window.conquerI18n.apply(); init();
  });
})();
