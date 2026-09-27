// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// The coach: the first-turn tutorial shown next to a game terminal, with
// buttons that press each step's keys. Used by game.html (the server game)
// and try/ (the game in the browser). The page provides the elements with
// the coach-* ids.
//
//   conquerCoach(term, relayout, stepsUrl)
//     term      function returning the xterm.js terminal (or null)
//     relayout  function called when the coach opens or closes
//     stepsUrl  the steps (tutorial/first-turn.json); for Spanish visitors
//               the Spanish ones next to it (first-turn.es.json)
function conquerCoach(term, relayout, stepsUrl) {
  // Coach: walks through the first-turn tutorial (tutorial/first-turn.json)
  // next to the terminal, and moves to the next step when the terminal
  // shows that step's screen
  var coach = document.getElementById('coach');
  var coachToggle = document.getElementById('coach-toggle');
  var COACH_STORE = 'conquer-coach';
  var steps = [], stepIndex = 0, stepScreen = null;
  var KEY_INPUT = { Space: ' ', Enter: '\r', Esc: '\x1b' };
  var es = window.conquerLang && conquerLang() === 'es';
  var T = es ? {
    count: 'Entrenador · paso %1 de %2', press: 'Pulsa', password: 'la contraseña de tu nación',
    next: 'Siguiente', finish: 'Terminar', Space: 'Espacio'
  } : {
    count: 'Coach · step %1 of %2', press: 'Press', password: 'your nation password',
    next: 'Next', finish: 'Finish', Space: 'Space'
  };
  if (es) stepsUrl = stepsUrl.replace(/\.json$/, '.es.json');

  function coachSave() {
    try { localStorage.setItem(COACH_STORE, JSON.stringify({ open: !coach.hidden, step: stepIndex })); } catch (e) {}
  }
  function coachLoad() {
    try { return JSON.parse(localStorage.getItem(COACH_STORE)) || {}; } catch (e) { return {}; }
  }
  function renderStep() {
    var st = steps[stepIndex];
    if (!st) return;
    // The screen the step started on: only a different one moves on
    stepScreen = screenText();
    document.getElementById('coach-count').textContent = T.count.replace('%1', stepIndex + 1).replace('%2', steps.length);
    document.getElementById('coach-progress').style.width = (100 * (stepIndex + 1) / steps.length) + '%';
    document.getElementById('coach-title').textContent = st.title;
    // Step texts are part of this site (tools/tutorial), not user content
    document.getElementById('coach-text').innerHTML = st.text;
    var box = document.getElementById('coach-keys');
    box.textContent = '';
    if (st.keys.length) {
      var label = document.createElement('span');
      label.textContent = T.press;
      box.appendChild(label);
    }
    st.keys.forEach(function (k) {
      if (k === 'password') {
        var typed = document.createElement('span');
        typed.className = 'typed';
        typed.textContent = T.password;
        box.appendChild(typed);
        return;
      }
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = T[k] || k;
      b.addEventListener('click', function () {
        var t = term();
        if (t) { t.input(KEY_INPUT[k] || k, true); t.focus(); }
      });
      box.appendChild(b);
    });
    document.getElementById('coach-back').disabled = stepIndex === 0;
    document.getElementById('coach-next').textContent = stepIndex === steps.length - 1 ? T.finish : T.next;
    coachSave();
  }
  function showCoach(show) {
    coach.hidden = !show;
    coachToggle.setAttribute('aria-expanded', String(show));
    if (show && !steps.length) {
      fetch(stepsUrl).then(function (r) { return r.json(); }).then(function (d) {
        steps = d.steps.map(function (s) { s.re = new RegExp(s.detect); return s; });
        steps.forEach(function (s) {
          s.unique = steps.filter(function (o) { return o.detect === s.detect; }).length === 1;
        });
        stepIndex = Math.min(coachLoad().step || 0, steps.length - 1);
        renderStep();
      }).catch(function () { coach.hidden = true; });
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
    if (coach.hidden || !steps.length) return;
    var text = screenText();
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
