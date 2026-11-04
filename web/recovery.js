// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The recovery code: the site keeps no email address, so this code is the
// only way back to an account whose password is forgotten. The first time an
// approved player reaches a signed-in page, the gate makes the code and sends
// it once (POST /account/api/init); this script shows it in a modal with Copy,
// Download .txt and "I have saved it". Pages that load it: game.html,
// admin.html, account.html and recover.html. Load site.js first.
//
//   conquerRecovery.init()                 asks the gate; shows the modal when a code was made.
//                                          Resolves with the gate's answer, {signedOut: true}
//                                          when the session is gone, or null when there is no gate.
//   conquerRecovery.show(account, code, cb) shows the modal for a code (cb after "I have saved it")
(function () {
  'use strict';

  var STYLE = [
    'dialog.rc-modal { max-width: min(34rem, calc(100vw - 2 * var(--s3, 12px))); width: 100%; padding: var(--s5, 24px); box-sizing: border-box;',
    '  background: var(--bg-2); color: var(--ink); border: var(--bezel, 3px) solid var(--phos, #6c6); border-radius: var(--radius, 6px); box-shadow: 0 12px 40px rgba(0, 0, 0, .7); }',
    'dialog.rc-modal::backdrop { background: rgba(0, 0, 0, .75); }',
    'dialog.rc-modal:not([open]) { display: none; }',
    '.rc-modal h2 { margin: 0 0 var(--s3, 12px); }',
    '.rc-modal p { margin: 0 0 var(--s4, 16px); }',
    '.rc-code { display: block; margin: 0 0 var(--s4, 16px); padding: var(--s3, 12px); text-align: center; user-select: all;',
    '  font: 700 clamp(1.3rem, 6vw, 1.9rem)/1.2 var(--font-mono, monospace); letter-spacing: .08em; color: var(--gold, #fc6);',
    '  background: var(--bg, #000); border: 1px solid var(--line); border-radius: var(--radius, 6px); overflow-wrap: anywhere; }',
    '.rc-actions { display: flex; flex-wrap: wrap; gap: var(--s3, 12px); }',
    '.rc-actions .key { flex: 1 1 auto; text-align: center; }'
  ].join('\n');

  function t(key, params) { return window.conquerI18n ? conquerI18n.t('account.' + key, params) : ''; }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function addStyle() {
    if (document.getElementById('rc-style')) return;
    var s = document.createElement('style');
    s.id = 'rc-style';
    s.textContent = STYLE;
    document.head.appendChild(s);
  }

  // Copy text to the clipboard: the API where the page may use it, else a
  // selected textarea. Resolves true when it worked.
  function copyText(text, fallbackNode) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, function () { return old(); });
    }
    return Promise.resolve(old());
    function old() {
      try {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;left:-1000px;top:0';
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand && document.execCommand('copy');
        document.body.removeChild(ta);
        if (!ok && fallbackNode && window.getSelection) {
          var range = document.createRange();
          range.selectNodeContents(fallbackNode);
          var sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(range);
        }
        return !!ok;
      } catch (e) { return false; }
    }
  }

  function download(name, text) {
    var blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }

  var current = null;   // the modal that is open

  function show(account, code, done) {
    addStyle();
    return conquerI18n.ready().then(function () {
      if (current) current.remove();
      var dlg = el('dialog', 'rc-modal');
      dlg.id = 'recovery-modal';
      dlg.setAttribute('aria-labelledby', 'rc-title');
      var title = el('h2'); title.id = 'rc-title';
      var text = el('p');
      var codeEl = el('code', 'rc-code', code); codeEl.id = 'recovery-code';
      var actions = el('div', 'rc-actions');
      var bCopy = el('button', 'key', ''); bCopy.type = 'button'; bCopy.id = 'rc-copy';
      var bDown = el('button', 'key', ''); bDown.type = 'button'; bDown.id = 'rc-download';
      var bSaved = el('button', 'key key-primary', ''); bSaved.type = 'button'; bSaved.id = 'rc-saved';
      var lost = el('p'); lost.style.marginTop = 'var(--s4, 16px)'; lost.className = 'help'; lost.id = 'rc-lost';
      // The app's web view may not save a file: Copy is enough there
      var inApp = !!(window.conquerApp && window.conquerApp.is);
      actions.appendChild(bCopy);
      if (!inApp) actions.appendChild(bDown);
      actions.appendChild(bSaved);
      [title, text, codeEl, actions, lost].forEach(function (n) { dlg.appendChild(n); });

      function words() {
        title.textContent = t('rc_title');
        text.textContent = t('rc_text');
        bCopy.textContent = t('rc_copy');
        bDown.textContent = t('rc_download');
        bSaved.textContent = t('rc_saved');
        lost.textContent = t('lost');
      }
      words();
      var onLang = function () { if (dlg.isConnected) words(); else document.removeEventListener('conquer:lang', onLang); };
      document.addEventListener('conquer:lang', onLang);

      bCopy.addEventListener('click', function () {
        copyText(code, codeEl).then(function (ok) {
          if (!ok) return;
          bCopy.textContent = t('rc_copied');
          setTimeout(function () { bCopy.textContent = t('rc_copy'); }, 1500);
        });
      });
      bDown.addEventListener('click', function () {
        download('conquer-recovery-code.txt', t('rc_file', { account: account, code: code }));
      });
      bSaved.addEventListener('click', function () {
        if (dlg.close) { try { dlg.close(); } catch (e) {} }
        dlg.remove();
        current = null;
        if (typeof done === 'function') done();
      });
      // The code is shown once: Escape does not close the window by accident
      dlg.addEventListener('cancel', function (e) { e.preventDefault(); });

      document.body.appendChild(dlg);
      current = dlg;
      if (typeof dlg.showModal === 'function') dlg.showModal();
      else dlg.setAttribute('open', '');
      bSaved.focus();
      return dlg;
    });
  }

  // Asks the gate for the account's state; a code made now is shown
  function init() {
    if (window.conquerRemote) return Promise.resolve(null);   // a copy of the pages elsewhere has no gate
    return fetch('/account/api/init', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
      credentials: 'same-origin', cache: 'no-store'
    }).then(function (r) {
      // No session: Apache answers with the sign-in page
      if (r.redirected && /\/login\.html/.test(r.url) || r.status === 401) return { signedOut: true };
      if (!r.ok) return null;
      return r.json().catch(function () { return null; });
    }).then(function (res) {
      if (res && res.ok && res.recovery_code) return show(res.account, res.recovery_code).then(function () { return res; });
      return res;
    }).catch(function () { return null; });
  }

  window.conquerRecovery = { init: init, show: show, copyText: copyText };
})();
