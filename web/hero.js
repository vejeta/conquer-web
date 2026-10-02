// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The landing page's war terminal: the world map (hero/map.json, see
// tools/hero/README.md) drawn like the game screen on an amber monitor, a
// staged war on it and a teletype of world news. Also draws the share
// image (tools/hero/render-og.js).
(function () {
  var base = (document.currentScript && document.currentScript.src || '').replace(/[^/]*$/, '');
  var COLORS = {
    bg: '#110b04', water: '#3f2c12', flat: '#80581f', hill: '#9e6c27', mountain: '#bf8631',
    peak: '#dca24c', own: '#ffb340', bright: '#ffe2a8', war: '#ff5540'
  };
  var ALTITUDE = { '~': COLORS.water, '-': COLORS.flat, '%': COLORS.hill, '^': COLORS.mountain, '#': COLORS.peak };
  // One war: the armies march, fight, then the winner takes the sectors
  var CYCLE = 14000, MARCH = 5200, BATTLE = 2600;
  var AFTER = MARCH + BATTLE + 3000;  // a moment after the war, for still pictures

  function load() {
    return fetch(base + 'hero/map.json').then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); });
  }

  function sector(map, x, y) {
    var row = map.rows[y];
    if (!row || x < 0 || x >= map.w) return null;
    var i = x * 4;
    return { alt: row.charAt(i), des: row.charAt(i + 1), owner: parseInt(row.substr(i + 2, 2), 16) };
  }
  function ease(k) { return k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2; }

  // The map around (cx, cy) at a moment of the war. o: cell and row size in
  // pixels, font, time (ms), still (a picture: no blinking)
  function draw(ctx, map, w, h, o) {
    var war = map.war, cell = o.cell, rowH = o.rowH;
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, w, h);
    ctx.font = o.font;
    ctx.textBaseline = 'top';
    var cols = Math.ceil(w / cell) + 1, rows = Math.ceil(h / rowH) + 1;
    var x0 = Math.round(o.cx - cols / 2), y0 = Math.round(o.cy - rows / 2);
    var phase = o.time % CYCLE;
    var march = ease(Math.min(1, phase / MARCH));
    var fighting = o.still || (phase > MARCH && phase < MARCH + BATTLE);
    var won = phase >= MARCH + BATTLE;
    var taken = {};
    if (won) {
      var count = Math.min(war.conquered.length, Math.floor((phase - MARCH - BATTLE) / 180) + 1);
      war.conquered.slice(0, count).forEach(function (p) { taken[p[0] + ',' + p[1]] = true; });
    }

    // Water first, in a plain monospace: VT323's tilde is a tiny raised
    // mark that reads as an "N" on a map
    var size = parseFloat(o.font);
    ctx.font = Math.round(size * 0.8) + 'px ui-monospace, "DejaVu Sans Mono", monospace';
    ctx.fillStyle = COLORS.water;
    for (var wr = 0; wr < rows; wr++) {
      for (var wc = 0; wc < cols; wc++) {
        var ws = sector(map, x0 + wc, y0 + wr);
        if (ws && ws.alt === '~' && !ws.owner && ws.des === '-') ctx.fillText('~', wc * cell, wr * rowH + size * 0.12);
      }
    }
    ctx.font = o.font;

    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var x = x0 + c, y = y0 + r, s = sector(map, x, y);
        if (!s) continue;
        if (s.alt === '~' && !s.owner && s.des === '-' && !taken[x + ',' + y]) continue;
        // A sector shows its designation (city, fort...), else its owner's
        // mark, else its altitude, as on the game screen
        var ch = s.alt, color = ALTITUDE[s.alt] || COLORS.flat, lit = false;
        if (s.des && s.des !== '-') { ch = s.des; color = COLORS.own; lit = true; }
        else if (s.owner) { ch = map.nations[s.owner] || '?'; color = COLORS.own; }
        if (taken[x + ',' + y]) { ch = war.winner; color = COLORS.war; lit = true; }
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = lit ? 8 : 0;
        ctx.fillText(ch, c * cell, r * rowH);
      }
    }
    ctx.shadowBlur = 0;

    // Armies in reverse video, like the game's selected army
    var chw = ctx.measureText('M').width;
    war.armies.forEach(function (a) {
      if (won && a.defender) return;
      var k = a.defender ? 1 : march;
      var ax = Math.round(a.from[0] + (a.to[0] - a.from[0]) * k), ay = Math.round(a.from[1] + (a.to[1] - a.from[1]) * k);
      var px = (ax - x0) * cell, py = (ay - y0) * rowH;
      ctx.fillStyle = a.defender ? COLORS.bright : COLORS.own;
      ctx.shadowColor = COLORS.own; ctx.shadowBlur = 12;
      ctx.fillRect(px - 2, py, chw + 4, rowH);
      ctx.shadowBlur = 0;
      ctx.fillStyle = COLORS.bg;
      ctx.fillText(a.mark, px, py);
      if (!o.still && !won && Math.floor(o.time / 500) % 2 === 0) {
        ctx.strokeStyle = COLORS.own; ctx.lineWidth = 1;
        ctx.strokeRect(px - 5, py - 3, chw + 10, rowH + 6);
      }
    });

    // The battle: sparks around the battlefield
    if (fighting) {
      var bx = (war.battle[0] - x0) * cell, by = (war.battle[1] - y0) * rowH;
      var n = o.still ? 1 : (phase - MARCH) / BATTLE;
      ctx.fillStyle = COLORS.war; ctx.shadowColor = COLORS.war; ctx.shadowBlur = 16;
      [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1], [0, -2], [2, 0], [0, 2], [-2, 0]]
        .forEach(function (d, i) {
          if (o.still || (Math.sin(o.time / 90 + i * 1.7) > 0.1 && i < 4 + n * 8)) {
            ctx.fillText('*', bx + d[0] * cell, by + d[1] * rowH);
          }
        });
      ctx.fillText('!', bx, by);
      ctx.shadowBlur = 0;
    }
  }

  function reducedMotion() {
    return window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  // The map filling a canvas behind the hero, animated unless the visitor
  // asked for reduced motion
  function start(canvas, map) {
    var box = canvas.parentNode, ctx = canvas.getContext('2d');
    var still = reducedMotion(), size = null, begin = performance.now(), frameId = 0;
    function resize() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2), w = box.clientWidth, h = box.clientHeight;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var fs = w < 600 ? 18 : 22, font = fs + 'px VT323, ui-monospace, monospace';
      ctx.font = font;
      // A sector is a character and a space wide, as on the game screen
      size = { w: w, h: h, font: font, cell: Math.ceil(ctx.measureText('M').width * 2), rowH: Math.round(fs * 0.95) };
    }
    function frame(now) {
      var cols = size.w / size.cell, rows = size.h / size.rowH, b = map.war.battle;
      // Wide screens: the war on the right, above the teletype; phones: under the text
      var c = size.w > 820 ? { cx: b[0] - cols * 0.12, cy: b[1] + rows * 0.27 } : { cx: b[0], cy: b[1] - rows * 0.12 };
      draw(ctx, map, size.w, size.h, {
        cell: size.cell, rowH: size.rowH, font: size.font, cx: c.cx, cy: c.cy,
        time: still ? AFTER : now - begin, still: still
      });
      if (!still) frameId = requestAnimationFrame(frame);
    }
    resize();
    frameId = requestAnimationFrame(frame);
    var timer;
    window.addEventListener('resize', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { cancelAnimationFrame(frameId); resize(); frameId = requestAnimationFrame(frame); }, 120);
    });
    // Nothing to animate while the hero is off screen
    if (!still && window.IntersectionObserver) {
      new IntersectionObserver(function (e) {
        cancelAnimationFrame(frameId);
        if (e[0].isIntersecting) frameId = requestAnimationFrame(frame);
      }).observe(box);
    }
  }

  // Words of war, betrayal and loss, printed in red
  var HOT = /\b(war|jihad|hostile|betray\w*|battle\w*|attack\w*|destroy\w*|defeat\w*|captur\w*|kill\w*|slain|sack\w*|rebel\w*|treaty broken)\b/gi;
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  }
  function lineHtml(text) {
    return escapeHtml(text).replace(HOT, '<span class="hot">$1</span>');
  }

  // A teletype printing dispatches in a list, letter by letter; the first
  // ones are already printed, so the page is complete at rest
  function teletype(list) {
    var still = reducedMotion(), lines = [], dispatches = [], next = 0, timer = null, SHOW = 5;
    function render(typing) {
      list.textContent = '';
      lines.forEach(function (l, i) {
        var li = document.createElement('li'), age = lines.length - 1 - i;
        if (age >= 3) li.className = 'older'; else if (age >= 1) li.className = 'old';
        li.innerHTML = '&gt; ' + lineHtml(l.text.slice(0, l.shown));
        if (typing && i === lines.length - 1) {
          var caret = document.createElement('span'); caret.className = 'caret'; li.appendChild(caret);
        }
        list.appendChild(li);
      });
    }
    function typeNext() {
      var line = { text: dispatches[next % dispatches.length], shown: 0 };
      next++;
      lines.push(line);
      if (lines.length > SHOW) lines.shift();
      timer = setInterval(function () {
        line.shown++;
        render(true);
        if (line.shown >= line.text.length) {
          clearInterval(timer);
          timer = setTimeout(typeNext, 1900);
        }
      }, 34);
    }
    function set(items) {
      clearInterval(timer); clearTimeout(timer);
      dispatches = items.slice();
      var ready = still || dispatches.length <= 3 ? Math.min(SHOW, dispatches.length) : 3;
      lines = dispatches.slice(0, ready).map(function (t) { return { text: t, shown: t.length }; });
      next = ready;
      render(false);
      if (!still && dispatches.length > ready) timer = setTimeout(typeNext, 900);
    }
    return { set: set };
  }

  // The share image (1200x630): the map after the battle, the name, and
  // one dispatch; texts: { version, tagline: [line, line], dispatch, hot, site }
  function drawShare(canvas, map, texts) {
    var o = canvas.getContext('2d'), W = canvas.width, H = canvas.height;
    o.font = '30px VT323, monospace';
    var cell = Math.ceil(o.measureText('M').width * 2), rowH = 28, b = map.war.battle;
    draw(o, map, W, H, { cell: cell, rowH: rowH, font: '30px VT323, monospace', cx: b[0] - (W / cell) * 0.18, cy: b[1] - 1, time: AFTER, still: true });
    var g = o.createLinearGradient(0, 0, W, 0);
    g.addColorStop(0, 'rgba(17,11,4,.96)'); g.addColorStop(0.46, 'rgba(17,11,4,.78)'); g.addColorStop(0.68, 'rgba(17,11,4,0)');
    o.fillStyle = g; o.fillRect(0, 0, W, H);
    for (var y = 0; y < H; y += 3) { o.fillStyle = 'rgba(0,0,0,.22)'; o.fillRect(0, y + 2, W, 1); }
    o.textBaseline = 'alphabetic';
    o.fillStyle = '#c7862b'; o.font = '34px VT323, monospace';
    o.fillText(texts.version, 64, 120);
    o.fillStyle = '#f4e7c9'; o.font = '150px "IM Fell English SC", Georgia, serif';
    o.shadowColor = 'rgba(255,179,64,.45)'; o.shadowBlur = 24;
    o.fillText('Conquer', 56, 270);
    o.shadowBlur = 0;
    o.fillStyle = '#ffb340'; o.font = '40px "IM Fell English SC", Georgia, serif';
    texts.tagline.forEach(function (line, i) { o.fillText(line, 64, 350 + i * 48); });
    o.font = '38px VT323, monospace';
    o.fillStyle = '#ffb340'; o.fillText('> ' + texts.dispatch, 64, 520);
    o.fillStyle = '#ff5540'; o.shadowColor = '#ff5540'; o.shadowBlur = 10;
    o.fillText(texts.hot, 64 + o.measureText('> ' + texts.dispatch).width, 520);
    o.shadowBlur = 0;
    o.fillStyle = '#80581f'; o.font = '30px VT323, monospace';
    o.fillText(texts.site, 64, 580);
  }

  window.conquerHero = { load: load, start: start, teletype: teletype, drawShare: drawShare };
})();
