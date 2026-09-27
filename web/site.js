// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Links to the game server, for pages served by the game server itself or
// from another site (GitHub Pages). Load server.js first.
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
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fixLinks);
  else fixLinks();
})();
