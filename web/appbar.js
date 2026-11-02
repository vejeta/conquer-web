// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The Android app's bar on the game pages (game.html, try/): in the app the
// site header gives way to a bar of at most 44 px with Home, Coach, Keyboard
// and a menu with the rest of the header's buttons and the options. Held
// sideways the bar folds away and a small tab at the top brings it back.
// Load it after site.js and touch.js; it does nothing outside the app.
(function () {
  'use strict';
  if (!window.conquerApp || !window.conquerApp.is || !document.body.classList.contains('game-page')) return;

  var header = document.getElementById('site-header');
  var home = document.getElementById('home');
  var coach = document.getElementById('coach-toggle');
  var peekTimer = null;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }
  function t(key, fallback) { return (window.conquerI18n && conquerI18n.t(key)) || fallback; }

  var bar = el('div', 'app-bar');
  bar.id = 'app-bar';
  bar.setAttribute('role', 'toolbar');
  var bHome = el('button', 'key key-small app-home');
  bHome.type = 'button'; bHome.id = 'app-home';
  var bCoach = el('button', 'key key-small'); bCoach.type = 'button'; bCoach.id = 'app-coach';
  var bKeys = el('button', 'key key-small'); bKeys.type = 'button'; bKeys.id = 'app-keyboard';
  bKeys.setAttribute('aria-label', 'Keyboard');
  var spacer = el('span', 'spacer');
  var bMenu = el('button', 'key key-small'); bMenu.type = 'button'; bMenu.id = 'app-menu';
  bMenu.setAttribute('aria-haspopup', 'true'); bMenu.setAttribute('aria-expanded', 'false');
  var list = el('div', 'app-menu');
  list.id = 'app-menu-list'; list.hidden = true;
  [bHome, bCoach, bKeys, spacer, bMenu].forEach(function (b) { bar.appendChild(b); });
  var handle = el('button', 'app-handle'); handle.type = 'button'; handle.id = 'app-handle';

  function labels() {
    bHome.textContent = '\u2039 ' + t('app.home', 'Home');
    bCoach.textContent = t('app.coach', 'Coach');
    bKeys.textContent = '\u2328 ' + t('game.keyboard', 'Keyboard');
    bMenu.textContent = '\u22ef ' + t('app.menu', 'Menu');
    handle.setAttribute('aria-label', t('app.show_bar', 'Show the menu bar'));
    handle.title = handle.getAttribute('aria-label');
  }
  labels();
  if (window.conquerI18n) conquerI18n.ready().then(labels);
  document.addEventListener('conquer:lang', labels);

  function peek() {
    bar.classList.add('peek');
    clearTimeout(peekTimer);
    peekTimer = setTimeout(function () { bar.classList.remove('peek'); showMenu(false); }, 5000);
  }
  handle.addEventListener('click', peek);

  bHome.addEventListener('click', function () {
    // The app's own Home (bridge "home"); in a browser, the page's link
    var go = function () { if (home && home.href) location.href = home.href; };
    if (window.conquerApp.has()) window.conquerApp.send({ type: 'home' }, go); else go();
  });
  bCoach.addEventListener('click', function () {
    if (coach) coach.click();
    bCoach.setAttribute('aria-expanded', String(!!coach && coach.getAttribute('aria-expanded') === 'true'));
  });
  bKeys.addEventListener('click', function () {
    if (window.touchLayer) window.touchLayer.keyboard();
  });

  // The rest of the header's buttons, as they are now (Next turn only when
  // the practice world offers it), and the options
  var EXTRA = ['turn', 'reset', 'moves-toggle', 'toggle-keys', 'toggle'];
  function showMenu(show) {
    if (show) {
      list.textContent = '';
      EXTRA.forEach(function (id) {
        var o = document.getElementById(id);
        if (!o || o.hidden) return;
        var b = el('button', 'app-item', o.textContent);
        b.type = 'button';
        b.addEventListener('click', function () {
          o.click();
          if (id === 'reset') { b.textContent = o.textContent; return; }   // two taps: ask again
          showMenu(false);
        });
        list.appendChild(b);
      });
      var gear = document.getElementById('touch-gear');
      if (gear) {
        var g = el('button', 'app-item', t('touch.options', 'Options'));
        g.type = 'button';
        g.addEventListener('click', function () { showMenu(false); gear.click(); });
        list.appendChild(g);
      }
    }
    list.hidden = !show;
    bMenu.setAttribute('aria-expanded', String(show));
  }
  bMenu.addEventListener('click', function () { showMenu(list.hidden); if (bar.classList.contains('peek')) peek(); });
  document.addEventListener('click', function (e) {
    if (!list.hidden && !list.contains(e.target) && e.target !== bMenu) showMenu(false);
  });

  bar.appendChild(list);
  document.body.insertBefore(bar, header ? header.nextSibling : document.body.firstChild);
  document.body.appendChild(handle);
})();
