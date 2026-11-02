// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The touch layer: Conquer's curses screen (80x24) stays exactly as the
// game draws it, and a transparent layer over it makes it playable with a
// finger: tap the map to go there, command chips with names (and the
// original key in small type), a compass (d-pad), a "where am I / back" plaque, zoom
// and pan on phones, and the soft keyboard only when the game asks for
// text. Every key still works.
//
//   conquerTouch({ term, send, host, lang, relayout })
//     term      function returning the xterm.js terminal (or null)
//     send      send(s) types a string into the game
//     host      the element that holds the terminal: the iframe of ttyd
//               (game.html) or the div of the terminal (try/). It sits in
//               <div class="touch-viewport"><div class="touch-stage">.
//     lang      language of the texts (default: the page's)
//     relayout  optional: called when the stage changes size, so the page
//               can fit the terminal again
//     gs        the element (.gs of theme.css) that holds the stone: the
//               "where am I" plaque goes before it, the ledge of chips and
//               the compass after it. Without it they go to the page's body.
//     stone     the .stone around the terminal: gets .parchment on reports
//               and the builder (and the terminal's colours with it), .plain
//   returns { refresh(), setMode(name|null), destroy(), where(), keyboard(),
//             toggleBar(), options }
//
// Pure helpers: conquerTouch.whereAmI(lines, cursor) -> the screen's class
// ("map", "builder", "report", "prompt_yn", "prompt_text", "prompt_number",
// "anykey", "menu", "move", "unknown"); conquerTouch.classify gives more
// (the report's kind, the menu's items, the turn number).
//
// Sound: optional, through window.conquerAudio (audio.js) when it exists.
(function () {
  'use strict';

  var STORE = 'conquer-touch';
  var NATW = 660, NATH = 400;       // the stage on a phone held upright (about 84x26 cells)
  var MAXZOOM = 2.5;
  var AUTOZOOM = 2;                 // a phone held upright starts zoomed on the map: about 40 of the 80 columns
  var STEP_MS = 35, MAX_KEYS = 40;  // tap to move: one key every 35 ms, 40 at most
  var DRAG_PX = 120;                // scrolling: one key per 120 px of drag
  var SLOP = 8;                     // a move over 8 px is a pan, not a tap
  var HOLD_MS = 450, DOUBLE_MS = 300;

  // ---------------------------------------------------------------- screen

  // The game's own screens, by their text (display.c, reports.c, forms.c,
  // magic.c, trade.c, commands.c, main.c, newlogin.c of the game's source)
  var REPORTS = [
    ['messages', /^Message from |HIT RETURN TO DELETE MESSAGE/m],
    ['army', /ARMY STATS SUMMARY/],
    ['navy', /NAVY STATS SUMMARY/],
    ['budget', /NEXT SEASON'S BUDGET/],
    ['production', /NEXT SEASON'S PRODUCTION/],
    ['campaign', /CAMPAIGN INFORMATION/],
    ['news', /CONQUER NEWS REPORT|N=next page, P=previous page/],
    ['diplomacy', /NATION DIPLOMACY SUMMARY/],
    ['score', /NATION SCORE SCREEN/],
    ['nation', /NATION STATS SUMMARY/],
    ['magic', /(?:MAGIC|CURRENT|LACKING) POWERS FOR/],
    ['trade', /COMMODITIES EXCHANGE/],
    ['help', /HELP SCREENS|TO END HELP HIT SPACE/],
    ['version', /Original contributors and acknowledgments/]
  ];
  var BUILDER = /Nation Builder/;
  var STATUS = /Conquer: \d+\.\d+\s+Turn\s+(\d+)/;
  var PANEL = /\bx is \d+\s+y is \d+|\bx = *\d+, y = *\d+|Sector Information/;
  var MOVESCREEN = /MOVESCREEN|HIT SPACE IF DONE/;
  var ANYKEY = /(?:hit|press) any (?:other )?key|hit return to|hit space|return to continue|press return|space to continue/i;
  var YESNO = /\(y or n\)|\(y\/n\)|\[ny\]|\[yn\]|\[y\/n\]/i;
  var YESNO_LINE = /^\s*(?:do you wish|are you sure|are your orders|disband your|pay him off|give them severance)/i;
  var NUMBER = /how (?:many|much)|[xy] loc|what (?:army|navy|item number|value)|to what (?:army|navy)|set what|which (?:army|navy)/i;
  var TEXTISH = /[:?]\s*[^\s:?]{0,30}$/;
  var COMBAT = /BATTLE SUMMARY|NAVAL BATTLE|Battle occ|You are on the (?:Attacking|Defending) Side|RESULT: Attackers/;
  var MENU_ITEM = /^\s*([0-9a-z])\)\s+(\S.*?)\s*$/;

  function nonEmptyEnd(lines) {
    var n = lines.length;
    while (n > 0 && !lines[n - 1]) n--;
    return n;
  }

  // The class of the screen. lines: the terminal's rows; cursor: {x, y}
  // (optional). Returns { where, kind, items, turn, prompt, combat }.
  function classify(rows, cursor) {
    var lines = [], i;
    for (i = 0; i < rows.length; i++) lines.push(String(rows[i] || '').replace(/\s+$/, ''));
    var end = nonEmptyEnd(lines);
    var text = lines.join('\n');
    var tail = lines.slice(Math.max(0, end - 6), end).join('\n');
    var out = { where: 'unknown', kind: '', items: [], turn: null, prompt: '', combat: COMBAT.test(text) };

    if (BUILDER.test(text)) { out.where = 'builder'; return out; }
    for (i = 0; i < REPORTS.length; i++) {
      if (REPORTS[i][1].test(text)) { out.where = 'report'; out.kind = REPORTS[i][0]; return out; }
    }
    // The site's terminal menu: numbered options
    var items = [];
    for (i = 0; i < lines.length; i++) {
      var m = MENU_ITEM.exec(lines[i]);
      if (m) items.push({ key: m[1], label: m[2] });
    }
    var hasQuit = items.some(function (it) { return it.key === 'q'; });
    if (items.length >= 2 && (/choose an option/i.test(text) || hasQuit)) {
      out.where = 'menu'; out.items = items; return out;
    }
    if (MOVESCREEN.test(tail)) { out.where = 'move'; return out; }

    // The line the player is answering: the cursor's, or the last one
    var prompt = '';
    if (cursor && lines[cursor.y]) prompt = lines[cursor.y];
    else if (end) prompt = lines[end - 1];
    out.prompt = prompt;
    var after = !cursor || cursor.y >= lines.length || !lines[cursor.y] || cursor.x >= prompt.length;

    var lastLines = lines.slice(Math.max(0, end - 4), end).join('\n');
    if (ANYKEY.test(lastLines)) { out.where = 'anykey'; return out; }
    if (YESNO.test(prompt) || YESNO_LINE.test(prompt)) { out.where = 'prompt_yn'; return out; }
    var st = STATUS.exec(tail);
    if (st) { out.where = 'map'; out.turn = parseInt(st[1], 10); return out; }
    if (prompt && after && NUMBER.test(prompt) && TEXTISH.test(prompt)) { out.where = 'prompt_number'; return out; }
    if (prompt && after && prompt.length > 3 && TEXTISH.test(prompt)) { out.where = 'prompt_text'; return out; }
    if (PANEL.test(text)) { out.where = 'map'; return out; }
    return out;
  }

  // The keys that take a cursor from one sector to another: diagonals first
  // (y u b n), then straights (h j k l), 40 at most
  function mapPath(dx, dy) {
    var keys = '', diag = Math.min(Math.abs(dx), Math.abs(dy)), i;
    var d = (dy < 0 ? (dx < 0 ? 'y' : 'u') : (dx < 0 ? 'b' : 'n'));
    for (i = 0; i < diag; i++) keys += d;
    var rx = Math.abs(dx) - diag, ry = Math.abs(dy) - diag;
    for (i = 0; i < rx; i++) keys += dx < 0 ? 'h' : 'l';
    for (i = 0; i < ry; i++) keys += dy < 0 ? 'k' : 'j';
    return keys.slice(0, MAX_KEYS);
  }

  // ------------------------------------------------------------- commands

  // The map's chips: icon, text key (touch.cmd_*), the key of the game
  var MAP_CHIPS = [
    ['move', '✥', 'move', null],
    ['army', '⚔', 'army', 'a'],
    ['budget', '⚖', 'budget', 'B'],
    ['construct', '⌂', 'construct', 'C'],
    ['draft', '✚', 'draft', 'D'],
    ['redesignate', '⟳', 'redesignate', 'r'],
    ['production', '❀', 'production', 'P'],
    ['magic', '✦', 'magic', 'M'],
    ['diplomacy', '⚑', 'diplomacy', 'S'],
    ['trade', '¤', 'trade', 'T'],
    ['news', '☰', 'news', 'N'],
    ['messages', '✉', 'messages', 'R'],
    ['score', '★', 'score', 's'],
    ['capital', '♛', 'capital', 'X'],
    ['goto', '⌖', 'goto', 'x'],
    ['nextarmy', '»', 'nextarmy', 'G'],
    ['help', '?', 'help', '?'],
    ['more', '…', 'more', null],
    ['quit', '⏻', 'quit', 'q']
  ];

  // Every command of the map (main.c, parse()), for the "More" sheet
  var ALL_KEYS = ['a', 'b', 'B', 'c', 'C', 'd', 'D', 'f', 'F', 'g', 'G', 'h', 'H', 'I', 'j', 'J', 'k', 'K',
    'l', 'L', 'm', 'M', 'n', 'N', 'o', 'p', 'P', 'q', 'r', 'R', 's', 'S', 't', 'T', 'u', 'U', 'v', 'w', 'W',
    'x', 'X', 'y', 'Y', 'Z', '?', 'redraw'];
  var ALL_SEND = { redraw: '\x0c' };

  // What each report offers: the key for the next page (or none), the
  // one that ends it (Back), and its other keys, from the game's own help
  // lines at the bottom of each screen
  var REPORT_KEYS = {
    army: { next: 'n', done: ' ', extra: [['edit', '\r']] },
    navy: { next: 'n', done: ' ', extra: [['edit', '\r']] },
    budget: { done: ' ', extra: [['cmd_production', 'P'], ['change', 'C']] },
    production: { done: ' ', extra: [['cmd_budget', 'B'], ['change', 'C']] },
    campaign: { done: ' ' },
    nation: { done: ' ', extra: [['cmd_budget', 'B'], ['cmd_production', 'P']] },
    news: { next: 'n', prev: 'p', done: ' ' },
    messages: { next: ' ', done: ' ', extra: [['delete', '\r']] },
    diplomacy: { next: 'n', done: ' ', extra: [['edit', '\r']] },
    score: { next: '\r', done: ' ' },
    magic: { done: ' ' },
    trade: { done: ' ', extra: [['buy', 'B'], ['sell', 'S'], ['unsell', 'U']] },
    help: { next: '\r', done: ' ' },
    version: { done: ' ' }
  };

  // icon, id, key sent, hint, text (touch.*)
  var BUILDER_CHIPS = [
    ['\u2191', 'up', 'k', 'k', 'b_up'], ['\u2193', 'down', 'j', 'j', 'b_down'], ['+1', 'buy', ' ', 'Space', 'b_buy'],
    ['\u25C2', 'add', 'h', 'h', 'b_add'], ['\u25B8', 'sub', 'l', 'l', 'b_sub'], ['?', 'info', '?', '?', 'b_info'],
    ['\u238B', 'esc', '\x1b', 'Esc', 'esc'], ['\u23CE', 'enter', '\r', 'Enter', 'enter'],
    ['\u232B', 'bs', '\x7f', '\u232B', 'backspace'], ['\u2713', 'yes', 'y', 'y', 'yes'], ['\u2717', 'no', 'n', 'n', 'no']
  ];

  var DPAD = [
    ['y', '↖'], ['k', '↑'], ['u', '↗'],
    ['h', '←'], ['p', '●'], ['l', '→'],
    ['b', '↙'], ['j', '↓'], ['n', '↘']
  ];

  var HINT_KEY = { ' ': 'Space', '\r': '⏎', '\x1b': 'Esc', '\x7f': '⌫', '\x0c': '^L' };
  var CANCEL_NUMBER = '\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\x7f\r';   // get_number() ends on Enter only

  function esc(k) {
    return k.replace(/\x1b/g, '\\x1b').replace(/\x7f/g, '\\x7f').replace(/\x0c/g, '\\x0c').replace(/\r/g, '\\r');
  }

  function el(tag, cls, attrs) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // ----------------------------------------------------------------- layer

  function conquerTouch(opts) {
    var host = opts.host;
    var stage = host.parentNode;                        // .touch-stage
    var viewport = stage.parentNode;                    // .touch-viewport
    var lang = opts.lang || (window.conquerLang ? window.conquerLang() : 'en');
    var coarse = !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
    var DEFAULTS = { sound: false, volume: 0.6, scan: false, plain: false, hints: true, padOn: null,
      bar: true, hintSeen: false, kbSeen: false };
    var prefs = load();

    var current = null, subs = [], timer = null, debounce = null;
    var state = { where: 'unknown', kind: '', items: [], turn: null, combat: false, prompt: '' };
    var forced = null, lastSig = '', lastTurn = null, rootWhere = null;
    var scaled = false, zoom = 1, tx = 0, ty = 0, fit = 1;
    var userView = false, autoForce = false, lastAuto = '', gx = 0, gy = 0;
    var inApp = !!(window.conquerApp && window.conquerApp.is);
    var shortScreen = false;          // a phone held sideways: the frame thins, the chips go to a rail
    var queue = '', queueTimer = null;
    var kbWanted = false, kbUp = false;
    var destroyed = false;
    var geom = { cw: 8, ch: 16, cols: 80, rows: 24 };
    var rendered = '';

    // ---- persistence
    function load() {
      var p = {}, k;
      try { p = JSON.parse(localStorage.getItem(STORE)) || {}; } catch (e) { p = {}; }
      for (k in DEFAULTS) if (!(k in p)) p[k] = DEFAULTS[k];
      return p;
    }
    function save() { try { localStorage.setItem(STORE, JSON.stringify(prefs)); } catch (e) {} }

    function T(key, params) {
      var v = window.conquerI18n ? conquerI18n.t('touch.' + key, params) : '';
      return v || key;
    }
    function audio() { return window.conquerAudio || null; }
    function ev(name) {
      var a = audio();
      try { if (a && a.event) a.event(name); } catch (e) {}
    }
    function evUi() {
      var a = audio();
      try { if (a && a.event && (!a.enabled || a.enabled())) a.event('ui'); } catch (e) {}
    }
    function tt() { try { return opts.term(); } catch (e) { return null; } }
    // A tap you can feel: the app's haptic (bridge), else the browser's vibration
    function buzz(always) {
      if (window.conquerApp && window.conquerApp.has && window.conquerApp.has()) {
        window.conquerApp.send({ type: 'haptic', ms: 8 });
      } else if (always && navigator.vibrate) {
        try { navigator.vibrate(8); } catch (e) {}
      }
    }
    // The app keeps the screen on while a game page is open
    function keepAwake(on) {
      if (window.conquerApp && window.conquerApp.has && window.conquerApp.has()) window.conquerApp.send({ type: 'keepAwake', on: on });
    }
    function send(s) { if (s) opts.send(s); }

    // ---- DOM: the grid over the terminal, scanlines, the bar, the d-pad
    var grid = el('div', 'touch-grid', { 'aria-hidden': 'true' });
    var crt = el('div', 'touch-crt', { 'aria-hidden': 'true' });
    stage.appendChild(grid);
    stage.appendChild(crt);
    viewport.classList.add('touch-on');

var ui = el('div', 'touch-ui');
    ui.id = 'touch-ui';
    var whereRow = el('div', 'touch-where');
    var crumb = el('span', 'touch-crumb plaque', { 'aria-live': 'polite' });
    crumb.id = 'touch-where';
    var backBtn = el('button', 'touch-back key key-small', { type: 'button' });
    backBtn.id = 'touch-back';
    var gear = el('button', 'touch-gear key key-small', { type: 'button', 'aria-expanded': 'false', 'aria-controls': 'touch-panel' });
    gear.id = 'touch-gear';
    gear.textContent = '⚙︎';
    var spacer = el('span', 'touch-spacer');
    whereRow.appendChild(crumb);
    whereRow.appendChild(backBtn);
    whereRow.appendChild(spacer);
    whereRow.appendChild(gear);
    var ledge = el('div', 'ledge touch-ledge');
    var chipsBox = el('div', 'chips touch-chips', { role: 'toolbar' });
    chipsBox.id = 'touch-chips';
    var builderBox = el('div', 'chips touch-chips builder', { role: 'toolbar' });
    builderBox.id = 'builder-keys';
    builderBox.hidden = true;
    ledge.appendChild(chipsBox);
    ledge.appendChild(builderBox);
    // In the app: a speaker to mute the sound (it is on by default there)
    var speaker = el('button', 'touch-sound key key-small', { type: 'button' });
    speaker.id = 'touch-sound';
    speaker.hidden = !inApp || !audio() || !audio().enable;
    ledge.appendChild(speaker);
    function paintSpeaker() {
      var a = audio(), on = !!(a && a.enabled && a.enabled());
      speaker.textContent = on ? '\u{1F50A}' : '\u{1F507}';
      speaker.setAttribute('aria-pressed', String(on));
      var label = conquerI18n.t('app.' + (on ? 'sound_on' : 'sound_off')) || (on ? 'Sound on' : 'Sound off');
      speaker.setAttribute('aria-label', label);
      speaker.title = label;
    }
    speaker.addEventListener('click', function () {
      var a = audio();
      if (!a || !a.enable) return;
      var on = !(a.enabled && a.enabled());
      prefs.sound = on; save();
      try { a.enable(on); } catch (e) {}
      paintSpeaker();
      var sb = document.getElementById('touch-opt-sound'); if (sb) sb.checked = on;
    });
    var panel = el('div', 'touch-panel sheet', { role: 'dialog' });
    panel.id = 'touch-panel';
    panel.hidden = true;
    ui.appendChild(panel);
    ui.appendChild(whereRow);
    ui.appendChild(ledge);
    var gs = opts.gs || null, stone = opts.stone || null;
    if (gs) gs.insertBefore(ui, gs.firstChild); else document.body.appendChild(ui);

    var hint = el('div', 'touch-hint toast', { role: 'status' });
    hint.hidden = true;
    var hintText = el('span');
    var hintClose = el('button', 'key key-small', { type: 'button' });
    hintClose.textContent = '×';
    hint.appendChild(hintText);
    hint.appendChild(hintClose);
    viewport.appendChild(hint);

    // The compass: the d-pad as eight points and a needle (theme.css .compass)
    var pad = el('div', 'touch-dpad compass', { role: 'group' });
    pad.hidden = true;
    pad.innerHTML = '<svg viewBox="0 0 232 232" aria-hidden="true"><circle class="rose-line" cx="116" cy="116" r="88" stroke-width="2" opacity=".5"/>' +
      '<circle class="rose-line" cx="116" cy="116" r="62" stroke-width="1.5" opacity=".4"/><g class="rose-stone">' +
      '<path d="M116 4 130 102 228 116 130 130 116 228 102 130 4 116 102 102Z" opacity=".85"/>' +
      '<path d="M116 116 190 42 130 102ZM116 116 190 190 130 130ZM116 116 42 190 102 130ZM116 116 42 42 102 102Z" opacity=".5"/></g>' +
      '<circle class="needle-dot" cx="116" cy="116" r="4"/></svg>';
    var padBtns = [];
    DPAD.forEach(function (d) {
      var b = el('button', 'touch-pb key' + (d[0] === 'p' ? ' needle' : '') + ('ykbn'.indexOf(d[0]) >= 0 ? ' diag' : ''), { type: 'button' });
      b.setAttribute('data-key', d[0]);
      b.innerHTML = '<span class="ar" aria-hidden="true">' + d[1] + '</span><small aria-hidden="true">' + d[0] + '</small>';
      pad.appendChild(b);
      padBtns.push(b);
    });
    if (gs) gs.appendChild(pad); else viewport.appendChild(pad);

    var sheet = null;

    // ---- chips
    function chip(c) {
      var b = el('button', 'touch-chip key key-small' + (c.cls ? ' ' + c.cls : ''), { type: 'button' });
      if (c.key != null) b.setAttribute('data-key', esc(c.key));
      if (c.id) b.setAttribute('data-chip', c.id);
      var label = c.label || '';
      var hintTxt = c.hint != null ? c.hint : (c.key != null ? (HINT_KEY[c.key] || c.key) : '');
      var h = '';
      if (c.icon) h += '<span class="ic" aria-hidden="true">' + c.icon + '︎</span>';
      if (label) h += '<span class="lb"></span>';
      if (hintTxt) h += '<span class="hint kh"></span>';
      b.innerHTML = h;
      if (label) b.querySelector('.lb').textContent = label;
      if (hintTxt) b.querySelector('.kh').textContent = hintTxt;
      b.setAttribute('aria-label', label ? label + (hintTxt ? ' (' + hintTxt + ')' : '') : (c.title || String(hintTxt)));
      if (c.title) b.title = c.title;
      b.addEventListener('click', function () {
        evUi();
        if (c.act) c.act(b);
        else { send(c.key); focusTerm(); }
      });
      return b;
    }
    function fill(box, list) {
      box.textContent = '';
      list.forEach(function (c) { box.appendChild(chip(c)); });
    }

    function homeChip() {
      return { id: 'home', icon: '⌂', label: T('home'), hint: '', act: goHome };
    }
    function typeChip() {
      return { id: 'type', icon: '⌨', label: T('type'), hint: '', act: function () { keyboard(); } };
    }

    function chipsFor(s) {
      var list = [], i, w = s.where;
      if (forced === 'start') return [{ id: 'play', icon: '▶', label: T('cmd_play'), key: ' ', cls: 'main' }];
      if (w === 'map') {
        MAP_CHIPS.forEach(function (c) {
          var o = { id: c[0], icon: c[1], label: T('cmd_' + c[2]), key: c[3] };
          if (c[0] === 'move') { o.hint = ''; o.act = function () { togglePad(); }; }
          else if (c[0] === 'more') { o.hint = ''; o.act = function () { openSheet(); }; }
          if (c[0] === 'quit') o.cls = 'warn';
          list.push(o);
        });
      } else if (w === 'move') {
        list.push({ id: 'done', icon: '✓', label: T('done'), key: ' ', cls: 'main' });
        list.push({ id: 'help', icon: '?', label: T('cmd_help'), key: '?' });
      } else if (w === 'report') {
        var r = REPORT_KEYS[s.kind] || { done: ' ' };
        if (r.next) list.push({ id: 'next', icon: '▸', label: T('next_page'), key: r.next, cls: 'main' });
        if (r.prev) list.push({ id: 'prev', icon: '◂', label: T('prev_page'), key: r.prev });
        (r.extra || []).forEach(function (x) {
          list.push({ id: x[0], icon: '', label: T(x[0]), key: x[1] });
        });
        list.push(homeChip());
      } else if (w === 'anykey') {
        list.push({ id: 'next', icon: '▸', label: T('next_page'), key: ' ', cls: 'main' });
        list.push(homeChip());
      } else if (w === 'prompt_yn') {
        list.push({ id: 'yes', icon: '✓', label: T('yes'), key: 'y', cls: 'main' });
        list.push({ id: 'no', icon: '✗', label: T('no'), key: 'n' });
      } else if (w === 'prompt_number') {
        for (i = 1; i <= 10; i++) {
          var d = String(i % 10);
          list.push({ id: 'd' + d, icon: '', label: d, hint: '', key: d, cls: 'digit' });
        }
        list.push({ id: 'bs', icon: '⌫', label: '', hint: '', key: '\x7f', cls: 'digit', title: T('backspace') });
        list.push({ id: 'enter', icon: '⏎', label: '', hint: '', key: '\r', cls: 'digit main', title: T('enter') });
      } else if (w === 'prompt_text') {
        list.push(typeChip());
        list.push({ id: 'enter', icon: '⏎', label: T('enter'), key: '\r', cls: 'main' });
        list.push({ id: 'bs', icon: '⌫', label: T('backspace'), key: '\x7f' });
        list.push({ id: 'esc', icon: '⎋', label: T('esc'), key: '\x1b' });
      } else if (w === 'menu') {
        s.items.forEach(function (it) {
          var lbl = it.label.length > 30 ? it.label.slice(0, 29) + '…' : it.label;
          list.push({ id: 'm' + it.key, icon: '', label: lbl, key: it.key, cls: it.key === 'q' ? 'warn' : '' });
        });
      } else if (w === 'builder') {
        list.push(typeChip());
        BUILDER_CHIPS.forEach(function (c) {
          list.push({ id: 'b' + c[1], icon: c[0], label: T(c[4]), key: c[2], hint: c[3] });
        });
      } else {
        list.push(typeChip());
        list.push({ id: 'enter', icon: '⏎', label: T('enter'), key: '\r' });
        list.push({ id: 'space', icon: '', label: T('space'), key: ' ' });
        list.push({ id: 'esc', icon: '⎋', label: T('esc'), key: '\x1b' });
      }
      return list;
    }

    // What Back does on this screen
    function backKey(s) {
      var w = s.where;
      if (forced) return null;
      if (w === 'report') return (REPORT_KEYS[s.kind] || { done: ' ' }).done;
      if (w === 'anykey' || w === 'move') return ' ';
      if (w === 'prompt_yn') return 'n';
      if (w === 'prompt_text') return '\x1b';
      if (w === 'prompt_number') return CANCEL_NUMBER;
      if (w === 'unknown') return '\x1b';
      return null;           // the map, the menu and the nation builder have nothing behind them
    }

    function goHome() {
      var tries = 0;
      (function go() {
        if (destroyed) return;
        var w = state.where;
        if (w === 'map' || w === 'menu' || tries > 6) return;
        if (w !== 'report' && w !== 'anykey' && w !== 'move') return;
        var k = backKey(state);
        if (!k) return;
        send(k);
        tries++;
        setTimeout(go, 200);
      })();
    }

    function whereName(w, kind) {
      if (forced === 'start') return T('where_menu');
      if (w === 'report') {
        var n = T('where_' + kind);
        return n === 'where_' + kind ? T('where_report') : n;
      }
      return T('where_' + w);
    }

    function renderBar(force) {
      var sig = [lang, forced, state.where, state.kind, state.items.map(function (i) { return i.key + i.label; }).join('|'),
        prefs.hints, T('cmd_army')].join('~');
      if (!force && sig === rendered) return;
      rendered = sig;
      var building = state.where === 'builder' && !forced;
      builderBox.hidden = !building;
      chipsBox.hidden = building;
      if (building) fill(builderBox, chipsFor(state)); else fill(chipsBox, chipsFor(state));
      chipsBox.classList.toggle('keypad', state.where === 'prompt_number');
      chipsBox.scrollLeft = 0;
      // Where am I: Map, or Map > Budget; never more than two levels
      var root = state.where === 'map' || state.where === 'menu' || state.where === 'builder' || forced;
      var names = [whereName(state.where, state.kind)];
      if (!root && rootWhere) names.unshift(T('where_' + rootWhere));
      crumb.textContent = names.join(' › ');
      var bk = backKey(state);
      backBtn.hidden = !bk;
      if (bk) {
        var hk = bk === CANCEL_NUMBER ? '⏎' : (HINT_KEY[bk] || bk);
        backBtn.innerHTML = '<span class="ic" aria-hidden="true">‹</span><span class="lb"></span><span class="hint kh"></span>';
        backBtn.querySelector('.lb').textContent = T('back');
        backBtn.querySelector('.kh').textContent = hk;
        backBtn.setAttribute('aria-label', T('back') + ' (' + hk + ')');
      }
      pad.setAttribute('aria-label', T('dpad_label'));
      padBtns.forEach(function (b) {
        var k = b.getAttribute('data-key');
        b.setAttribute('aria-label', T(k === 'p' ? 'dpad_pick' : 'dir_' + k) + ' (' + k + ')');
      });
      paintSpeaker();
      gear.setAttribute('aria-label', T('options'));
      gear.title = T('options');
      hintText.textContent = T('hint_rotate');
      hintClose.setAttribute('aria-label', T('hint_close'));
      ui.classList.toggle('touch-nohints', !prefs.hints);
      updatePad();
    }

    backBtn.addEventListener('click', function () {
      var k = backKey(state);
      if (k) { evUi(); send(k); focusTerm(); }
    });

    // ---- options panel
    function buildPanel() {
      panel.textContent = '';
      var h = el('h2'); h.textContent = T('options'); panel.appendChild(h);
      function row(labelText, control, forId) {
        var r = el('div', 'row');
        var l = el('label'); l.textContent = labelText;
        if (forId) l.setAttribute('for', forId);
        r.appendChild(l); r.appendChild(control);
        panel.appendChild(r);
        return r;
      }
      function checkbox(id, checked, fn) {
        var c = el('input', '', { type: 'checkbox', id: id });
        c.checked = !!checked;
        c.addEventListener('change', function () { fn(c.checked); });
        return c;
      }
      var a = audio();
      if (a && a.enable) {
        row(T('opt_sound'), checkbox('touch-opt-sound', a.enabled ? a.enabled() : prefs.sound, function (on) {
          prefs.sound = on; save();
          try { a.enable(on); } catch (e) {}
        }), 'touch-opt-sound');
        var vol = el('input', '', { type: 'range', id: 'touch-opt-volume', min: '0', max: '100', step: '5' });
        vol.value = String(Math.round((a.volume ? a.volume() : prefs.volume) * 100));
        vol.addEventListener('input', function () {
          prefs.volume = vol.value / 100; save();
          try { a.setVolume(prefs.volume); } catch (e) {}
        });
        row(T('opt_volume'), vol, 'touch-opt-volume');
        var pv = el('button', 'touch-reset key key-small', { type: 'button', id: 'touch-opt-preview' });
        pv.textContent = T('opt_preview');
        pv.addEventListener('click', function () {
          try {
            a.enable(true); prefs.sound = true; save();
            var sb = document.getElementById('touch-opt-sound'); if (sb) sb.checked = true;
            if (a._demo) a._demo();
          } catch (e) {}
        });
        panel.appendChild(pv);
      }
      row(T('opt_scan'), checkbox('touch-opt-scan', prefs.scan, function (on) { prefs.scan = on; save(); applyPrefs(); }), 'touch-opt-scan');
      var rc = el('select', 'select', { id: 'touch-opt-race' });
      ['auto'].concat(window.conquerRace ? conquerRace.races : []).forEach(function (r) {
        var o = el('option'); o.value = r; o.textContent = conquerI18n.t('race.' + r) || r;
        if ((window.conquerRace ? conquerRace.choice() : 'auto') === r) o.selected = true;
        rc.appendChild(o);
      });
      rc.addEventListener('change', function () { if (window.conquerRace) conquerRace.choose(rc.value); });
      if (window.conquerRace) row(T('opt_race'), rc, 'touch-opt-race');
      row(T('opt_plain'), checkbox('touch-opt-plain', prefs.plain, function (on) { prefs.plain = on; save(); applyPrefs(); }), 'touch-opt-plain');
      row(T('opt_hints'), checkbox('touch-opt-hints', prefs.hints, function (on) { prefs.hints = on; save(); applyPrefs(); }), 'touch-opt-hints');
      var reset = el('button', 'touch-reset key key-small', { type: 'button' });
      reset.textContent = T('opt_reset');
      reset.addEventListener('click', function () {
        prefs.padOn = null; prefs.hintSeen = false; save();
        userView = false; autoForce = true;
        zoom = 1; tx = 0; ty = 0; layout(); applyPrefs(); updatePad();
      });
      panel.appendChild(reset);
    }
    function showPanel(show) {
      if (show) buildPanel();
      panel.hidden = !show;
      gear.setAttribute('aria-expanded', String(show));
      if (show) { var f = panel.querySelector('input,select'); if (f) f.focus(); }
    }
    gear.addEventListener('click', function () { showPanel(panel.hidden); });
    document.addEventListener('keydown', onDocKey);
    function onDocKey(e) {
      if (e.key !== 'Escape') return;
      if (sheet && !sheet.hidden) { closeSheet(); e.preventDefault(); }
      else if (!panel.hidden) { showPanel(false); gear.focus(); e.preventDefault(); }
    }

    function applyPrefs() {
      viewport.classList.toggle('touch-scan', !!prefs.scan);
      ui.classList.toggle('touch-nohints', !prefs.hints);
      ui.hidden = !prefs.bar;
      // sideways on a phone, the frame is thin: every row of the screen counts
      if (stone) stone.classList.toggle('plain', !!prefs.plain || shortScreen);
    }

    // ---- the sheet with every command
    function openSheet() {
      if (!sheet) {
        sheet = el('div', 'touch-sheet', { role: 'dialog', 'aria-modal': 'true' });
        sheet.hidden = true;
        document.body.appendChild(sheet);
        sheet.addEventListener('click', function (e) { if (e.target === sheet) closeSheet(); });
      }
      sheet.textContent = '';
      var card = el('div', 'card');
      var h = el('h2'); h.textContent = T('more_title');
      var x = el('button', 'x', { type: 'button' });
      x.textContent = '×'; x.setAttribute('aria-label', T('more_close'));
      x.addEventListener('click', closeSheet);
      card.appendChild(x); card.appendChild(h);
      var list = el('div', 'list');
      ALL_KEYS.forEach(function (k) {
        var send1 = ALL_SEND[k] || k;
        var name = k === '?' ? 'qm' : k;
        var b = el('button', 'touch-cmd', { type: 'button' });
        b.innerHTML = '<kbd></kbd><span></span>';
        b.querySelector('kbd').textContent = HINT_KEY[send1] || send1;
        b.querySelector('span').textContent = T('keys.' + name);
        b.addEventListener('click', function () { evUi(); closeSheet(); send(send1); });
        list.appendChild(b);
      });
      card.appendChild(list);
      sheet.appendChild(card);
      sheet.hidden = false;
      x.focus();
    }
    function closeSheet() { if (sheet) sheet.hidden = true; }

    // ---- the d-pad
    function padWanted() {
      return prefs.padOn === null ? coarse : !!prefs.padOn;
    }
    function togglePad() {
      prefs.padOn = !padWanted(); save();
      updatePad();
    }
    function updatePad() {
      var show = padWanted() && (state.where === 'map' || state.where === 'move') && !kbUp && !forced;
      pad.hidden = !show;
      if (gs) gs.classList.toggle('has-compass', show);
      var mv = chipsBox.querySelector('[data-chip="move"]');
      if (mv) mv.setAttribute('aria-pressed', String(padWanted()));
    }
    function step(k) {
      send(k);
      ev('move');
      buzz(true);
    }
    padBtns.forEach(function (b) {
      var k = b.getAttribute('data-key'), hold = null, held = false;
      b.addEventListener('pointerdown', function (e) {
        if (e.pointerType === 'mouse' && e.button !== 0) return;
        held = false;
        if (k === 'p') return;
        hold = setTimeout(function () { held = true; hold = null; step(k.toUpperCase()); }, HOLD_MS);
      });
      function end() { if (hold) { clearTimeout(hold); hold = null; } }
      b.addEventListener('pointerleave', end);
      b.addEventListener('pointercancel', end);
      b.addEventListener('pointerup', function (e) {
        if (hold) { clearTimeout(hold); hold = null; }
        if (held) { e.preventDefault(); return; }
        if (k === 'p') send('p'); else step(k);
        evUi();
        e.preventDefault();
        if (e.pointerType === 'mouse') focusTerm();
      });
      // The keyboard: Enter or Space on the button
      b.addEventListener('click', function (e) {
        if (e.detail === 0) { if (k === 'p') send('p'); else step(k); }
      });
    });
    // ---- the soft keyboard: only when the game asks for text
    function inputMode() {
      var t = tt();
      try { if (t && t.textarea) t.textarea.setAttribute('inputmode', kbWanted ? 'text' : 'none'); } catch (e) {}
    }
    function focusTerm() {
      var t = tt();
      try { if (t && t.focus) t.focus(); } catch (e) {}
    }
    function keyboard() {
      var t = tt();
      kbWanted = true;
      inputMode();
      try {
        if (t && t.textarea) { t.textarea.blur(); t.textarea.focus(); } else if (t && t.focus) t.focus();
      } catch (e) {}
      updatePad();
    }
    function watchKeyboard() {
      var vv = window.visualViewport;
      var up = !!(vv && window.innerHeight - vv.height > 120);
      if (up !== kbUp) { kbUp = up; updatePad(); }
    }
    if (window.visualViewport) window.visualViewport.addEventListener('resize', watchKeyboard);

    // ---- reading the screen
    function screen() {
      var t = tt();
      if (!t || !t.buffer) return null;
      var buf = t.buffer.active, lines = [];
      for (var y = 0; y < t.rows; y++) {
        var line = buf.getLine(buf.viewportY + y);
        lines.push(line ? line.translateToString(true) : '');
      }
      return { lines: lines, cursor: { x: buf.cursorX, y: buf.cursorY } };
    }

    function attach() {
      var t = tt();
      if (t === current) { inputMode(); return; }
      subs.forEach(function (s) { try { s.dispose(); } catch (e) {} });
      subs = [];
      current = t;
      if (!t) return;
      var onChange = function () { schedule(); };
      try {
        if (t.onWriteParsed) subs.push(t.onWriteParsed(onChange));
        else if (t.onRender) subs.push(t.onRender(onChange));
        if (t.onCursorMove) subs.push(t.onCursorMove(onChange));
        if (t.onBell) subs.push(t.onBell(function () { ev('bump'); }));
      } catch (e) {}
      inputMode();
    }
    function schedule() {
      if (debounce) return;
      debounce = setTimeout(function () { debounce = null; update(); }, 60);
    }

    function update() {
      if (destroyed) return;
      var sc = screen();
      if (!sc) return;
      var sig = sc.lines.join('\n') + '\u0001' + sc.cursor.x + ',' + sc.cursor.y;
      if (sig === lastSig) return;
      lastSig = sig;
      var c = classify(sc.lines, sc.cursor);
      // The nation's race, when the game shows it (the builder's "National
      // Race: Human", the nation's own report): the site takes its colours
      if (window.conquerRace && (c.where === 'builder' || (c.where === 'report' && c.kind === 'nation'))) {
        var rc = conquerRace.detect(sc.lines.join('\n'), c.where === 'report');
        if (rc) conquerRace.seen(rc);
      }
      setState(c);
    }

    function setState(c) {
      var prev = state;
      var changed = prev.where !== c.where || prev.kind !== c.kind;
      state = c;
      if (changed) {
        if (c.where === 'map' || c.where === 'menu' || c.where === 'builder') rootWhere = c.where;
        var a = audio();
        try { if (a && a.screen) a.screen(c.where); } catch (e) {}
        if (c.where === 'report') {
          ev('open');
          if (c.kind === 'news') ev('news');
          if (c.kind === 'messages') ev('message');
        } else if (prev.where === 'report' && c.where === 'map') ev('close');
        if (c.where !== 'map') cancelMoves();
        // The keyboard opens by itself the first time the game asks for text
        if (c.where === 'prompt_text') {
          if (coarse && (!prefs.kbSeen || inApp) && !(opts.skipKeyboard && opts.skipKeyboard())) {
            var first = !prefs.kbSeen;
            prefs.kbSeen = true; save(); keyboard();
            if (first && inApp) showKbHint();
          }
        } else if (kbWanted && c.where !== 'builder') {
          kbWanted = false; inputMode();
        }
        applyCapture();
        paper(c.where === 'report' || c.where === 'builder');
      }
      if (c.turn != null) {
        if (lastTurn != null && c.turn !== lastTurn) ev('turn');
        lastTurn = c.turn;
      }
      if (c.combat && !prev.combat) ev('combat');
      renderBar(false);
    }

    // Reports and the builder are read on parchment: the stone's paper and
    // the terminal's own colours change together (theme.css .stone.parchment)
    var onPaper = null;
    function paper(on) {
      if (forced) on = false;
      if (on === onPaper) return;
      onPaper = on;
      if (stone) stone.classList.toggle('parchment', on);
      syncTerminal();
    }
    function syncTerminal() {
      var t = tt();
      if (!window.conquerRace || !t || !t.options) return;
      var next = conquerRace.terminal(!!onPaper), cur = t.options.theme || {}, merged = {}, k;
      for (k in cur) merged[k] = cur[k];
      for (k in next) merged[k] = next[k];
      try { t.options.theme = merged; } catch (e) {}
      // In ttyd's frame the page around the terminal takes the same colour
      try {
        var d = t.element && t.element.ownerDocument;
        if (d && d !== document) d.documentElement.style.background = d.body.style.background = next.background;
      } catch (e) {}
    }
    document.addEventListener('conquer:race', function () { setTimeout(syncTerminal, 0); });

    // The grid takes the pointer on the map, and on a phone's scaled stage
    // (pinch and pan); elsewhere the terminal gets the clicks and selection
    function applyCapture() {
      var on = state.where === 'map' || scaled;
      grid.classList.toggle('capture', on);
    }

    // ---- geometry: the grid exactly over the terminal's text area
    function measure() {
      var t = tt();
      var s = t && t.element && t.element.querySelector ? t.element.querySelector('.xterm-screen') : null;
      if (!s || !t.cols) return;
      var r = s.getBoundingClientRect(), x, y, w, h;
      if (host.tagName === 'IFRAME') {
        // inside the frame: its own pixels, which the stage's scale carries
        x = r.left + host.offsetLeft; y = r.top + host.offsetTop; w = r.width; h = r.height;
      } else {
        var sr = stage.getBoundingClientRect();
        var k = stage.offsetWidth ? sr.width / stage.offsetWidth : 1;
        x = (r.left - sr.left) / k; y = (r.top - sr.top) / k; w = r.width / k; h = r.height / k;
      }
      if (!w || !h) return;
      geom = { cw: w / t.cols, ch: h / t.rows, cols: t.cols, rows: t.rows };
      gx = x; gy = y;
      var st = grid.style;
      st.left = x + 'px'; st.top = y + 'px'; st.width = w + 'px'; st.height = h + 'px';
    }

    // ---- zoom and pan on a phone held upright
    var relayoutTimer = null;
    function layout() {
      var vw = viewport.clientWidth, vh = viewport.clientHeight;
      if (!vw || !vh) return;
      var was = scaled;
      var sideways = !!(window.matchMedia && window.matchMedia('(orientation: landscape) and (max-height: 500px)').matches);
      if (sideways !== shortScreen) { shortScreen = sideways; applyPrefs(); }
      scaled = vw < NATW && !shortScreen;
      viewport.classList.toggle('touch-scaled', scaled);
      if (!scaled) {
        zoom = 1; tx = 0; ty = 0; fit = 1;
        stage.style.width = ''; stage.style.height = '';
        stage.style.transform = '';
      } else {
        fit = Math.min(vw / NATW, vh / NATH);
        zoom = clamp(zoom, 1, MAXZOOM);
        var s = fit * zoom, w = NATW * s, h = NATH * s;
        tx = w <= vw ? (vw - w) / 2 : clamp(tx, vw - w, 0);
        ty = h <= vh ? 0 : clamp(ty, vh - h, 0);
        stage.style.width = NATW + 'px'; stage.style.height = NATH + 'px';
        stage.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + s + ')';
      }
      if (was !== scaled) {
        autoForce = true;
        applyCapture();
        if (scaled && !prefs.hintSeen) hint.hidden = false;
        if (!scaled) hint.hidden = true;
      }
      measure();
      if (opts.relayout) {
        clearTimeout(relayoutTimer);
        relayoutTimer = setTimeout(function () { try { opts.relayout(); } catch (e) {} measure(); }, 80);
      }
    }
    hintClose.addEventListener('click', function () { hint.hidden = true; prefs.hintSeen = true; save(); });

    // The app says once that the keyboard opens by itself (and where its button is)
    var kbHint = null;
    function showKbHint() {
      if (!kbHint) {
        kbHint = el('div', 'touch-hint touch-kbhint toast', { role: 'status' });
        var kt = el('span'), kc = el('button', 'key key-small', { type: 'button' });
        kc.textContent = '\u00d7';
        kc.addEventListener('click', function () { kbHint.hidden = true; });
        kbHint.appendChild(kt); kbHint.appendChild(kc);
        viewport.appendChild(kbHint);
        setTimeout(function () { if (kbHint) kbHint.hidden = true; }, 9000);
      }
      kbHint.firstChild.textContent = conquerI18n.t('app.kb_hint');
      kbHint.lastChild.setAttribute('aria-label', conquerI18n.t('app.hint_close'));
      kbHint.hidden = false;
    }

    // Held upright, a phone starts on the map zoomed to about 40 columns and
    // centred on the cursor (and follows it when it leaves the view); other
    // screens show the whole 80 columns. A pinch, a pan or a double tap is the
    // player's own view, which this leaves alone.
    function autoView() {
      if (!scaled || userView || destroyed) return;
      var vw = viewport.clientWidth, vh = viewport.clientHeight, force = autoForce;
      if (!vw || !vh) return;
      if (state.where !== 'map') {
        if (zoom !== 1 && !forced) { zoom = 1; tx = 0; ty = 0; stage.classList.add('touch-anim'); layout(); }
        autoForce = false; lastAuto = '';
        return;
      }
      var t = tt();
      if (!t || !t.buffer || !geom.cw || !gx && !gy && !grid.style.width) return;
      var c = t.buffer.active;
      var px = gx + (c.cursorX + 0.5) * geom.cw, py = gy + (c.cursorY + 0.5) * geom.ch;
      var key = px + ',' + py;
      if (!force && key === lastAuto) return;
      lastAuto = key; autoForce = false;
      if (!force && zoom > 1.01) {
        var s0 = fit * zoom, sx = px * s0 + tx, sy = py * s0 + ty;
        if (sx > vw * 0.15 && sx < vw * 0.85 && sy > vh * 0.15 && sy < vh * 0.85) return;
      }
      zoom = AUTOZOOM;
      var s1 = fit * zoom;
      tx = vw / 2 - px * s1; ty = vh / 2 - py * s1;
      stage.classList.toggle('touch-anim', !force);
      layout();
    }

    function setZoom(z, cx, cy, animate) {
      userView = true;
      // keep the point of the stage under (cx, cy) in the viewport where it is
      var s0 = fit * zoom, px = (cx - tx) / s0, py = (cy - ty) / s0;
      zoom = clamp(z, 1, MAXZOOM);
      var s1 = fit * zoom;
      tx = cx - px * s1; ty = cy - py * s1;
      stage.classList.toggle('touch-anim', !!animate);
      layout();
    }

    // ---- moving the cursor with keys, one every 35 ms
    function cancelMoves() { queue = ''; if (queueTimer) { clearInterval(queueTimer); queueTimer = null; } }
    function startMoves(keys) {
      cancelMoves();
      queue = keys;
      queueTimer = setInterval(function () {
        if (!queue) { cancelMoves(); return; }
        var k = queue.charAt(0);
        queue = queue.slice(1);
        step(k);
        if (!queue) cancelMoves();
      }, STEP_MS);
    }
    function moving() { return !!queue; }

    // A tap on a cell of the map: go to its sector
    function cellAt(e) {
      var r = grid.getBoundingClientRect();
      var w = parseFloat(grid.style.width) || r.width;
      var k = r.width / w || 1;
      var x = (e.clientX - r.left) / k, y = (e.clientY - r.top) / k;
      return { col: Math.floor(x / geom.cw), row: Math.floor(y / geom.ch), x: x, y: y };
    }
    function mapBounds() {
      // main.c: SCREEN_X_SIZE = (COLS - 21) / 2 sectors of two columns, SCREEN_Y_SIZE = LINES - 5 rows
      return { cols: 2 * Math.floor((geom.cols - 21) / 2), rows: geom.rows - 5 };
    }
    function doTap(e, cell) {
      if (state.where !== 'map') return;
      if (moving()) { cancelMoves(); return; }
      var b = mapBounds();
      if (cell.col < 0 || cell.row < 0 || cell.col >= b.cols || cell.row >= b.rows) return;
      var t = tt();
      if (!t || !t.buffer) return;
      var cur = t.buffer.active;
      var dx = Math.floor(cell.col / 2) - Math.floor(cur.cursorX / 2);
      var dy = cell.row - cur.cursorY;
      var keys = mapPath(dx, dy);
      if (keys) { startMoves(keys); if (inApp) buzz(false); }
      if (e && e.pointerType === 'mouse') focusTerm();
    }
    function inGutter(cell) {
      var b = mapBounds();
      return cell.col < 2 || cell.col >= b.cols - 2 || cell.row < 1 || cell.row >= b.rows - 1;
    }

    // ---- pointers on the grid: tap, pan, pinch, scroll
    var ptrs = {}, nptr = 0, g = null, lastTap = null, tapTimer = null, multi = false;
    function count() { return Object.keys(ptrs).length; }
    function two() {
      var ids = Object.keys(ptrs), a = ptrs[ids[0]], b = ptrs[ids[1]];
      return { d: Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2)), cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
    }
    function vpPoint(x, y) {
      var r = viewport.getBoundingClientRect();
      return { x: x - r.left, y: y - r.top };
    }
    function scrollKeys(dx, dy) {
      // one scroll key per 120 px of drag (H J K L: pages of the map); dragging
      // right shows what is to the west, as a map under the finger does
      g.ax += dx; g.ay += dy;
      while (g.ax <= -DRAG_PX) { g.ax += DRAG_PX; step('L'); }
      while (g.ax >= DRAG_PX) { g.ax -= DRAG_PX; step('H'); }
      while (g.ay <= -DRAG_PX) { g.ay += DRAG_PX; step('J'); }
      while (g.ay >= DRAG_PX) { g.ay -= DRAG_PX; step('K'); }
    }

    grid.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      try { grid.setPointerCapture(e.pointerId); } catch (x) {}
      ptrs[e.pointerId] = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, t: Date.now(), moved: false };
      stage.classList.remove('touch-anim');
      if (count() === 1) {
        multi = false;
        g = { mode: null, ax: 0, ay: 0, cell: cellAt(e) };
      } else if (count() === 2) {
        multi = true;
        var p = two();
        g = { mode: null, d0: p.d, cx0: p.cx, cy0: p.cy, z0: zoom, ax: 0, ay: 0, lx: p.cx, ly: p.cy };
        if (tapTimer) { clearTimeout(tapTimer); tapTimer = null; }
        lastTap = null;
      }
      e.preventDefault();
    });

    grid.addEventListener('pointermove', function (e) {
      var p = ptrs[e.pointerId];
      if (!p || !g) return;
      var dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY;
      if (count() === 1) {
        if (!p.moved && Math.sqrt(Math.pow(p.x - p.sx, 2) + Math.pow(p.y - p.sy, 2)) > SLOP) {
          p.moved = true;
          // zoomed in, a finger pans; the edges scroll the map otherwise
          if (scaled && zoom > 1.01) g.mode = 'pan';
          else if (state.where === 'map' && inGutter(g.cell)) g.mode = 'scroll';
          cancelMoves();
        }
        if (!p.moved) return;
        if (g.mode === 'pan') {
          userView = true;
          tx += dx; ty += dy; layout();
        } else if (g.mode === 'scroll') {
          scrollKeys(dx, dy);
        }
      } else if (count() === 2) {
        var q = two();
        if (!g.mode) {
          if (scaled && Math.abs(q.d - g.d0) > 24) g.mode = 'pinch';
          else if (state.where === 'map' && Math.sqrt(Math.pow(q.cx - g.cx0, 2) + Math.pow(q.cy - g.cy0, 2)) > 16) g.mode = 'twoscroll';
          else return;
        }
        if (g.mode === 'pinch') {
          userView = true;
          var c = vpPoint(q.cx, q.cy);
          var s0 = fit * zoom, px = (c.x - tx) / s0, py = (c.y - ty) / s0;
          zoom = clamp(g.z0 * q.d / g.d0, 1, MAXZOOM);
          var s1 = fit * zoom;
          tx = c.x - px * s1; ty = c.y - py * s1;
          layout();
        } else if (g.mode === 'twoscroll') {
          scrollKeys(q.cx - g.lx, q.cy - g.ly);
          g.lx = q.cx; g.ly = q.cy;
        }
      }
      e.preventDefault();
    });

    function release(e, cancelled) {
      var p = ptrs[e.pointerId];
      if (!p) return;
      delete ptrs[e.pointerId];
      var tap = !cancelled && !multi && !p.moved && count() === 0;
      if (count() === 0) { multi = false; }
      if (!tap) return;
      var cell = cellAt(e);
      if (scaled) {
        var now = Date.now();
        if (lastTap && now - lastTap.t < DOUBLE_MS && Math.abs(e.clientX - lastTap.x) < 30 && Math.abs(e.clientY - lastTap.y) < 30) {
          clearTimeout(tapTimer); tapTimer = null; lastTap = null;
          cancelMoves();
          var c = vpPoint(e.clientX, e.clientY);
          if (zoom > 1.01) setZoom(1, c.x, c.y, true);
          else setZoom(2, c.x, c.y, true);
          return;
        }
        lastTap = { t: now, x: e.clientX, y: e.clientY };
        // wait a moment in case it is the first half of a double tap
        tapTimer = setTimeout(function () { tapTimer = null; lastTap = null; doTap(e, cell); }, DOUBLE_MS - 40);
      } else {
        doTap(e, cell);
      }
    }
    grid.addEventListener('pointerup', function (e) { release(e, false); e.preventDefault(); });
    grid.addEventListener('pointercancel', function (e) { release(e, true); });
    grid.addEventListener('contextmenu', function (e) { e.preventDefault(); });

    // ---- the loop that keeps everything in step
    var ro = null;
    if (window.ResizeObserver) {
      ro = new ResizeObserver(function () { layout(); });
      ro.observe(viewport);
    }
    window.addEventListener('resize', onResize);
    function onResize() { layout(); }
    document.addEventListener('conquer:lang', onLang);
    function onLang() { lang = conquerI18n.lang(); renderBar(true); }
    function onFirstGesture() {
      // sound starts only after a gesture of the visitor
      var a = audio();
      if (prefs.sound && a && a.enable) { try { a.enable(true); if (a.setVolume) a.setVolume(prefs.volume); } catch (e) {} }
      document.removeEventListener('pointerdown', onFirstGesture, true);
      document.removeEventListener('keydown', onFirstGesture, true);
    }
    document.addEventListener('pointerdown', onFirstGesture, true);
    document.addEventListener('keydown', onFirstGesture, true);

    function tick() {
      if (destroyed) return;
      attach();
      update();
      measure();
      autoView();
      if (!speaker.hidden) paintSpeaker();
      watchKeyboard();
    }
    timer = setInterval(tick, 250);

    applyPrefs();
    renderBar(true);
    keepAwake(true);
    if (window.conquerI18n) conquerI18n.ready().then(function () { lang = conquerI18n.lang(); renderBar(true); });
    layout();
    tick();

    // ---- the API
    var api = {
      options: opts,
      refresh: function () { lastSig = ''; layout(); tick(); },
      where: function () { return state.where; },
      state: function () { return state; },
      // a screen the page knows better than the text does ("start": the
      // practice game's title, before the game runs); null: read the screen
      setMode: function (mode) {
        forced = mode || null;
        lastSig = '';
        if (forced) { state = { where: 'unknown', kind: '', items: [], turn: null, combat: false, prompt: '' }; }
        rendered = '';
        paper(false);
        renderBar(true);
        if (!forced) update();
      },
      keyboard: keyboard,
      theme: syncTerminal,
      toggleBar: function () {
        prefs.bar = !prefs.bar; save(); applyPrefs();
        if (opts.relayout) setTimeout(opts.relayout, 50);
        return prefs.bar;
      },
      barShown: function () { return !!prefs.bar; },
      destroy: function () {
        destroyed = true;
        keepAwake(false);
        clearInterval(timer);
        cancelMoves();
        subs.forEach(function (s) { try { s.dispose(); } catch (e) {} });
        if (ro) ro.disconnect();
        window.removeEventListener('resize', onResize);
        document.removeEventListener('keydown', onDocKey);
        document.removeEventListener('conquer:lang', onLang);
        [grid, crt, ui, hint, pad, sheet].forEach(function (n) { if (n && n.parentNode) n.parentNode.removeChild(n); });
        viewport.classList.remove('touch-on', 'touch-scaled', 'touch-scan');
        stage.style.cssText = '';
      }
    };
    return api;
  }

  conquerTouch.classify = classify;
  conquerTouch.whereAmI = function (lines, cursor) { return classify(lines, cursor).where; };
  conquerTouch.mapPath = mapPath;
  window.conquerTouch = conquerTouch;
})();
