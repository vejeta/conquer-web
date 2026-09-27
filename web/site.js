// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Links to the game server, for pages served by the game server itself or
// from another site (GitHub Pages), and the language of the pages. Load
// server.js first.
(function () {
  var cfg = window.CONQUER_CONFIG || {};
  var server = (cfg.server || '').replace(/\/+$/, '');

  // URL of a path on the game server ("game.html", "status/status.json")
  window.conquerServerUrl = function (path) {
    return server ? server + '/' + path : path;
  };
  // True when these pages are not served by the game server
  window.conquerRemote = !!server;

  // <a data-server-link="game.html"> points at the game server
  function fixLinks() {
    var links = document.querySelectorAll('a[data-server-link]');
    for (var i = 0; i < links.length; i++) {
      links[i].href = window.conquerServerUrl(links[i].getAttribute('data-server-link'));
    }
  }
  // Language of the pages, "en" or "es": ?lang=, then the choice made on
  // the home page, then the browser's language
  window.conquerLang = function () {
    var q = new URLSearchParams(location.search).get('lang');
    if (q === 'en' || q === 'es') return q;
    try {
      var saved = localStorage.getItem('conquer-lang');
      if (saved === 'en' || saved === 'es') return saved;
    } catch (e) {}
    return (navigator.language || '').toLowerCase().indexOf('es') === 0 ? 'es' : 'en';
  };

  // Pages written in English carry their Spanish text in data-es (content)
  // and data-es-title (tooltip); swap them in for Spanish visitors
  function translate() {
    var els = document.querySelectorAll('[data-es]');
    if (!els.length || window.conquerLang() !== 'es') return;
    document.documentElement.lang = 'es';
    for (var i = 0; i < els.length; i++) els[i].innerHTML = els[i].getAttribute('data-es');
    els = document.querySelectorAll('[data-es-title]');
    for (i = 0; i < els.length; i++) els[i].title = els[i].getAttribute('data-es-title');
  }

  function ready() { fixLinks(); translate(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
})();
