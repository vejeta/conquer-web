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

  // Languages of the site. Each one has its texts in i18n/<code>.json (see
  // i18n/README.md); "pages" lists the long pages written in it, published
  // as <page>.<code>.html (English: <page>.html). dir: "rtl" for scripts
  // written right to left.
  var LANGUAGES = [
    { code: 'en', name: 'English', pages: ['guide', 'tutorial'] },
    { code: 'es', name: 'Español', pages: ['guide', 'tutorial'] },
    { code: 'de', name: 'Deutsch', pages: ['tutorial'] },
    { code: 'pt-br', name: 'Português (Brasil)', pages: ['tutorial'] },
    { code: 'pl', name: 'Polski', pages: ['tutorial'] },
    { code: 'ru', name: 'Русский', pages: ['tutorial'] },
    { code: 'zh', name: '简体中文', pages: ['tutorial'] }
  ];
  var STORE = 'conquer-lang';

  function language(code) {
    for (var i = 0; i < LANGUAGES.length; i++) if (LANGUAGES[i].code === code) return LANGUAGES[i];
    return null;
  }
  // "pt-BR" -> "pt-br", or "pt" if only that is on the site
  function match(tag) {
    tag = String(tag || '').toLowerCase();
    if (language(tag)) return tag;
    tag = tag.split('-')[0];
    return language(tag) ? tag : null;
  }

  // Language of the pages: ?lang=, then the choice made on the home page,
  // then the browser's languages, then English
  function pick() {
    var q = match(new URLSearchParams(location.search).get('lang'));
    if (q) return q;
    try {
      var saved = match(localStorage.getItem(STORE));
      if (saved) return saved;
    } catch (e) {}
    var wanted = navigator.languages || [navigator.language];
    for (var i = 0; i < wanted.length; i++) if (match(wanted[i])) return match(wanted[i]);
    return 'en';
  }

  var lang = pick();
  var base = (document.currentScript && document.currentScript.src || '').replace(/[^/]*$/, '');
  var texts = {};           // English, with the page's language on top
  var loaded = null, loadedLang = null;

  function load(code) {
    return fetch(base + 'i18n/' + code + '.json').then(function (r) {
      return r.ok ? r.json() : {};
    }).catch(function () { return {}; });
  }
  function merge(into, from) {
    Object.keys(from).forEach(function (k) {
      if (from[k] && typeof from[k] === 'object' && !Array.isArray(from[k])) {
        into[k] = merge(into[k] || {}, from[k]);
      } else if (from[k] !== '') {
        into[k] = from[k];
      }
    });
    return into;
  }

  // The texts of a page ("index", "game", "coach"...): a key missing in the
  // page's language falls back to English
  function ready() {
    if (!loaded || loadedLang !== lang) {
      var want = loadedLang = lang;
      loaded = Promise.all([load('en'), want === 'en' ? {} : load(want)]).then(function (both) {
        // The visitor may have chosen another language while these texts
        // were loading: only the latest choice sets the page's texts
        if (want === lang) texts = merge(merge({}, both[0]), both[1]);
        return texts;
      });
    }
    return loaded;
  }

  // t('index.more', { n: 3 }): the text with {n} filled in
  function t(key, params) {
    var v = key.split('.').reduce(function (o, k) { return o && o[k]; }, texts);
    if (typeof v !== 'string') return '';
    return v.replace(/\{(\w+)\}/g, function (m, k) { return params && k in params ? params[k] : m; });
  }

  // Link to a page in the visitor's language, when it is written in it
  function pageUrl(page, code) {
    code = code || lang;
    var l = language(code);
    return code === 'en' || !l || l.pages.indexOf(page) < 0 ? page + '.html' : page + '.' + code + '.html';
  }

  // Elements with data-i18n="page.key" get that text (static markup of
  // this site), data-i18n-title a tooltip, data-i18n-page="tutorial" the
  // link to that page in the visitor's language
  function apply(root) {
    root = root || document;
    var l = language(lang);
    // Pages written in one language (guide.es.html) have no data-i18n
    if (document.querySelector('[data-i18n]')) {
      document.documentElement.lang = lang;
      document.documentElement.dir = l.dir || 'ltr';
    }
    root.querySelectorAll('[data-i18n]').forEach(function (el) {
      var v = t(el.getAttribute('data-i18n'));
      if (v) el.innerHTML = v;
    });
    root.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      var v = t(el.getAttribute('data-i18n-title'));
      if (v) el.title = v;
    });
    root.querySelectorAll('[data-i18n-page]').forEach(function (el) {
      el.setAttribute('href', pageUrl(el.getAttribute('data-i18n-page')));
    });
    fixLinks();
  }

  function setLang(code) {
    if (!language(code)) return Promise.resolve(texts);
    try { localStorage.setItem(STORE, code); } catch (e) {}
    lang = code;
    return ready().then(function () {
      // A language chosen after this one wins; its own call applies it
      if (code === lang) apply();
      return texts;
    });
  }

  // Links to the game server, carrying the language: the game server may
  // be another site, which does not share the visitor's choice
  function fixLinks() {
    var links = document.querySelectorAll('a[data-server-link]');
    for (var i = 0; i < links.length; i++) {
      var link = links[i].getAttribute('data-server-link');
      if (lang !== 'en') link += (link.indexOf('?') < 0 ? '?' : '&') + 'lang=' + lang;
      links[i].href = window.conquerServerUrl(link);
    }
  }

  window.conquerI18n = {
    languages: LANGUAGES, ready: ready, t: t, apply: apply, setLang: setLang, pageUrl: pageUrl,
    lang: function () { return lang; }
  };
  window.conquerLang = function () { return lang; };

  // <span data-lang-links="guide"> lists the page in the other languages
  // it is written in, each in its own name
  function langLinks() {
    document.querySelectorAll('[data-lang-links]').forEach(function (el) {
      var page = el.getAttribute('data-lang-links'), here = document.documentElement.lang;
      el.textContent = '';
      LANGUAGES.forEach(function (l) {
        if (l.code === here || l.pages.indexOf(page) < 0) return;
        if (el.childNodes.length) el.appendChild(document.createTextNode(' · '));
        var a = document.createElement('a');
        a.href = pageUrl(page, l.code); a.hreflang = l.code; a.lang = l.code; a.textContent = l.name;
        el.appendChild(a);
      });
    });
  }

  function start() {
    fixLinks();
    langLinks();
    if (lang !== 'en' || document.querySelector('[data-i18n-page]')) ready().then(function () { apply(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
