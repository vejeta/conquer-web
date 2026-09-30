// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The coach: the first-turn tutorial shown next to a game terminal, with
// buttons that press each step's keys. Used by game.html (the server game)
// and try/ (the game in the browser). The page provides the elements with
// the coach-* ids.
//
//   conquerCoach(term, relayout, stepsUrl, builderUrl)
//     term        function returning the xterm.js terminal (or null)
//     relayout    function called when the coach opens or closes
//     stepsUrl    the steps (tutorial/first-turn.json); the ones in the
//                 visitor's language are next to it (first-turn.es.json)
//     builderUrl  optional: the steps of the game's nation builder
//                 (tutorial/found-nation.json). The coach switches to them
//                 while the builder is on screen, and opens by itself the
//                 first time it appears.
function conquerCoach(term, relayout, stepsUrl, builderUrl) {
  // Coach: walks through the first-turn tutorial (tutorial/first-turn.json)
  // next to the terminal, and moves to the next step when the terminal
  // shows that step's screen
  var coach = document.getElementById('coach');
  var coachToggle = document.getElementById('coach-toggle');
  var COACH_STORE = 'conquer-coach';
  var steps = [], stepIndex = 0, stepScreen = null;
  // The builder's own screens all carry this title line
  var BUILDER = /Nation Builder/;
  var BUILDER_SEEN = 'conquer-coach-builder';
  var track = 'main', loading = null;
  var KEY_INPUT = { Space: ' ', Enter: '\r', Esc: '\x1b' };
  // Texts: i18n/<language>.json, "coach" (site.js); the steps in the
  // visitor's language when the tutorial is written in it
  function T(key, params) { return conquerI18n.t('coach.' + key, params); }
  var lang = conquerI18n.lang();
  var translated = lang !== 'en' && conquerI18n.pageUrl('tutorial') !== 'tutorial.html';
  function localUrl(url) { return translated ? url.replace(/\.json$/, '.' + lang + '.json') : null; }

  function coachSave() {
    try { localStorage.setItem(COACH_STORE, JSON.stringify({ open: !coach.hidden, step: stepIndex, track: track })); } catch (e) {}
  }
  function coachLoad() {
    try { return JSON.parse(localStorage.getItem(COACH_STORE)) || {}; } catch (e) { return {}; }
  }
  function renderStep() {
    var st = steps[stepIndex];
    if (!st) return;
    // The screen the step started on: only a different one moves on
    stepScreen = screenText();
    document.getElementById('coach-count').textContent = T('count', { n: stepIndex + 1, total: steps.length });
    document.getElementById('coach-progress').style.width = (100 * (stepIndex + 1) / steps.length) + '%';
    document.getElementById('coach-title').textContent = st.title;
    // Step texts are part of this site (tools/tutorial), not user content
    document.getElementById('coach-text').innerHTML = st.text;
    var box = document.getElementById('coach-keys');
    box.textContent = '';
    if (st.keys.length) {
      var label = document.createElement('span');
      label.textContent = T('press');
      box.appendChild(label);
    }
    st.keys.forEach(function (k) {
      if (k === 'password') {
        var typed = document.createElement('span');
        typed.className = 'typed';
        typed.textContent = T('password');
        box.appendChild(typed);
        return;
      }
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = k === 'Space' ? T('space') : k;
      b.addEventListener('click', function () {
        var t = term();
        if (t) { t.input(KEY_INPUT[k] || k, true); t.focus(); }
      });
      box.appendChild(b);
    });
    document.getElementById('coach-back').disabled = stepIndex === 0;
    document.getElementById('coach-next').textContent = stepIndex === steps.length - 1 ? T('finish') : T('next');
    coachSave();
  }
  // Load the steps of a track ("main" or "builder") in the visitor's
  // language, then show step "at" (a number, or the step whose screen is
  // on the terminal now)
  function loadTrack(name, at) {
    var url = name === 'builder' ? builderUrl : stepsUrl;
    var get = function (u) { return fetch(u).then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); }); };
    track = name;
    loading = conquerI18n.ready().then(function () {
      var local = localUrl(url);
      return local ? get(local).catch(function () { return get(url); }) : get(url);
    }).then(function (d) {
      steps = d.steps.map(function (s) { s.re = new RegExp(s.detect); return s; });
      steps.forEach(function (s) {
        s.unique = steps.filter(function (o) { return o.detect === s.detect; }).length === 1;
      });
      if (at === 'screen') {
        var text = screenText();
        at = 0;
        // The last step whose screen shows: later prompts share a screen
        // with earlier ones (the builder asks under its table of points)
        for (var i = steps.length - 1; i >= 0; i--) if (steps[i].re.test(text)) { at = i; break; }
      }
      stepIndex = Math.max(0, Math.min(at || 0, steps.length - 1));
      loading = null;
      renderStep();
    }).catch(function () { loading = null; coach.hidden = true; });
    return loading;
  }
  function showCoach(show) {
    coach.hidden = !show;
    coachToggle.setAttribute('aria-expanded', String(show));
    if (show && !steps.length && !loading) {
      var saved = coachLoad();
      loadTrack(saved.track === 'builder' && builderUrl ? 'builder' : 'main', saved.step || 0);
    }
    coachSave();
    setTimeout(relayout, 50);
  }
  function screenText() {
    var t = term();
    if (!t || !t.buffer) return '';
    var buf = t.buffer.active, lines = [];
    for (var y = 0; y < t.rows; y++) {
      var line = buf.getLine(buf.viewportY + y);
      if (line) lines.push(line.translateToString(true));
    }
    return lines.join('\n');
  }
  // Follow the player: when the next step's screen appears, move there.
  // A player who takes another path is caught up by any of the next few
  // steps whose screen is unmistakable (its text belongs to that step only).
  setInterval(function () {
    if (loading) return;
    var text = screenText();
    // The nation builder on screen: its steps, and the coach opens by itself
    // the first time; when it is gone, back to the first turn
    if (builderUrl && text) {
      var building = BUILDER.test(text);
      if (building && track !== 'builder') {
        var seen = false;
        try { seen = localStorage.getItem(BUILDER_SEEN) === '1'; localStorage.setItem(BUILDER_SEEN, '1'); } catch (e) {}
        loadTrack('builder', 'screen');
        if (!seen && coach.hidden) showCoach(true);
        return;
      }
      if (!building && track === 'builder' && steps.length) {
        loadTrack('main', 0);
        return;
      }
    }
    if (coach.hidden || !steps.length) return;
    if (text === stepScreen) return;
    for (var i = stepIndex + 1; i < Math.min(stepIndex + 7, steps.length); i++) {
      if ((i === stepIndex + 1 || steps[i].unique) && steps[i].re.test(text)) {
        stepIndex = i;
        renderStep();
        return;
      }
    }
  }, 600);

  coachToggle.addEventListener('click', function () { showCoach(coach.hidden); });
  document.getElementById('coach-close').addEventListener('click', function () { showCoach(false); });
  document.getElementById('coach-back').addEventListener('click', function () {
    if (stepIndex > 0) { stepIndex--; renderStep(); }
  });
  document.getElementById('coach-next').addEventListener('click', function () {
    if (stepIndex < steps.length - 1) { stepIndex++; renderStep(); }
    else { stepIndex = 0; showCoach(false); }
  });
  // Open with ?coach (links from the tutorial), or as it was last time
  var coachState = coachLoad();
  if (/[?&]coach\b/.test(location.search)) { coachState.step = 0; try { localStorage.setItem(COACH_STORE, JSON.stringify(coachState)); } catch (e) {} showCoach(true); }
  else if (coachState.open) showCoach(true);
}
