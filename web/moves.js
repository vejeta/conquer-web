// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// How to move in Conquer, drawn: the eight letters on the keyboard, the same
// directions on the number pad, and on the map. Fills every element with
// data-moves (data-moves="compact": keyboard and map only, for narrow
// panels), in the visitor's language, or in data-moves-lang's.
// conquerMoves(root) fills the ones added later (the coach's steps).
(function () {
  var base = (document.currentScript && document.currentScript.src || '').replace(/moves\.js(\?.*)?$/, '');
  var catalogs = {};

  var CSS = [
    '.mv{color:var(--text,#e6edf3)}',
    '.mv-head{margin:0 0 12px}.mv-head strong{display:block;font-size:1.15em;margin-bottom:4px}',
    '.mv-head span{color:var(--muted,#8b949e);font-size:.95em;line-height:1.45}',
    '.mv-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:center}',
    '.mv-panel{border:1px solid var(--border,#30363d);border-radius:10px;padding:10px 12px;text-align:center;background:var(--panel,transparent)}',
    '.mv-panel b{display:block;margin:0 0 8px;font-size:.72em;letter-spacing:.08em;text-transform:uppercase;color:var(--muted,#8b949e);font-weight:600}',
    '.mv-eq{font-size:1.5em;color:var(--muted,#8b949e);font-weight:700}',
    '.mv-kb{display:inline-flex;flex-direction:column;gap:4px;align-items:flex-start}',
    '.mv-kr{display:flex;gap:4px}.mv-kr.r2{margin-left:9px}.mv-kr.r3{margin-left:24px}',
    '.mv-grid{display:inline-grid;grid-template-columns:repeat(3,var(--mv-k,40px));gap:4px}',
    '.mv-k{width:var(--mv-k,40px);height:var(--mv-k,40px);box-sizing:border-box;border-radius:6px;border:1px solid var(--border,#30363d);' +
      'display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1;' +
      'font:700 15px ui-monospace,"DejaVu Sans Mono",monospace;color:var(--muted,#8b949e);opacity:.55}',
    '.mv-k.on{opacity:1;border:2px solid var(--accent,#3fb950);border-bottom-width:3px;color:var(--accent,#3fb950)}',
    '.mv-k.on i{font-style:normal;font-size:13px;color:var(--text,#e6edf3);margin-top:2px}',
    '.mv-k.dir{opacity:1;color:var(--text,#e6edf3);font-size:19px}',
    '.mv-k.me{opacity:1;background:var(--accent,#3fb950);border-color:var(--accent,#3fb950);color:var(--bg,#0d1117);font:700 12px system-ui,sans-serif}',
    '.mv-note{margin:12px 0 0;color:var(--muted,#8b949e);font-size:.92em;line-height:1.5}',
    '.mv-note b{color:var(--text,#e6edf3)}',
    '@media (max-width:560px){.mv:not(.compact) .mv-eq{display:none}}',
    '.mv.compact{--mv-k:36px}.mv.compact .mv-k{font-size:14px}.mv.compact .mv-k.on i{font-size:12px}'
  ].join('\n');

  var DIR = { y: '↖', k: '↑', u: '↗', h: '←', l: '→', b: '↙', j: '↓', n: '↘' };
  function key(c, arrow) {
    return arrow ? '<span class="mv-k on">' + c + '<i>' + arrow + '</i></span>' : '<span class="mv-k">' + c + '</span>';
  }
  function row(cls, keys) {
    return '<div class="mv-kr ' + cls + '">' + keys.split('').map(function (c) { return key(c, DIR[c]); }).join('') + '</div>';
  }

  function html(T, compact) {
    var keyboard = '<div class="mv-panel"><b>' + T('keyboard') + '</b><div class="mv-kb">' +
      row('r1', 'tyuio') + row('r2', 'ghjkl') + row('r3', 'vbnm,') + '</div></div>';
    var pad = '<div class="mv-panel"><b>' + T('numpad') + '</b><div class="mv-grid">' +
      [['7', '↖'], ['8', '↑'], ['9', '↗'], ['4', '←'], ['5'], ['6', '→'], ['1', '↙'], ['2', '↓'], ['3', '↘']]
        .map(function (k) { return key(k[0], k[1]); }).join('') + '</div></div>';
    var map = '<div class="mv-panel"><b>' + T('map') + '</b><div class="mv-grid">' +
      ['↖', '↑', '↗', '←', null, '→', '↙', '↓', '↘'].map(function (a) {
        return a ? '<span class="mv-k dir">' + a + '</span>' : '<span class="mv-k me">' + T('you') + '</span>';
      }).join('') + '</div></div>';
    var eq = '<span class="mv-eq" aria-hidden="true">=</span>';
    return '<div class="mv-head"><strong>' + T('title') + '</strong><span>' + T('sub') + '</span></div>' +
      '<div class="mv-row">' + keyboard + eq + (compact ? '' : pad + eq) + map + '</div>' +
      '<p class="mv-note">' + T(compact ? 'arrows' : 'why') + '</p>';
  }

  function catalog(lang) {
    if (!catalogs[lang]) {
      catalogs[lang] = fetch(base + 'i18n/' + lang + '.json')
        .then(function (r) { return r.ok ? r.json() : {}; })
        .catch(function () { return {}; });
    }
    return catalogs[lang];
  }

  function fill(el) {
    var lang = el.getAttribute('data-moves-lang');
    var compact = el.getAttribute('data-moves') === 'compact';
    var got = lang
      ? catalog(lang).then(function (c) { return function (k) { return (c.moves || {})[k] || ''; }; })
      : window.conquerI18n.ready().then(function () { return function (k) { return window.conquerI18n.t('moves.' + k); }; });
    return got.then(function (T) {
      el.classList.add('mv');
      el.classList.toggle('compact', compact);
      el.setAttribute('role', 'figure');
      el.setAttribute('aria-label', T('title'));
      el.innerHTML = html(T, compact);
    });
  }

  function conquerMoves(root) {
    if (!document.getElementById('mv-style')) {
      var style = document.createElement('style');
      style.id = 'mv-style';
      style.textContent = CSS;
      document.head.appendChild(style);
    }
    (root || document).querySelectorAll('[data-moves]').forEach(fill);
  }
  window.conquerMoves = conquerMoves;

  // Another language: redraw the ones in the visitor's language
  document.addEventListener('conquer:lang', function () {
    document.querySelectorAll('[data-moves]:not([data-moves-lang])').forEach(fill);
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { conquerMoves(); });
  else conquerMoves();
})();
