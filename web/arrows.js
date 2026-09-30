// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Conquer (1987) moves with the letters of vi and rogue:
//
//     y k u        north-west  north  north-east
//     h   l        west               east
//     b j n        south-west  south  south-east
//
// and knows nothing of arrow keys: an arrow reaches it as Esc [ A, and the
// Esc cancels what the player was doing. So the arrow keys, and the number
// pad with NumLock off (Home, PageUp, End, PageDown for the diagonals), are
// sent as those letters. conquerArrows(term, send): send(letter) types it.
(function () {
  var MOVE = {
    ArrowUp: 'k', ArrowDown: 'j', ArrowLeft: 'h', ArrowRight: 'l',
    Home: 'y', PageUp: 'u', End: 'b', PageDown: 'n'
  };
  window.conquerArrows = function (term, send) {
    if (!term || !term.attachCustomKeyEventHandler || term._conquerArrows) return;
    term._conquerArrows = true;
    term.attachCustomKeyEventHandler(function (e) {
      var letter = MOVE[e.key];
      if (!letter || e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return true;
      if (e.type === 'keydown') send(letter);
      e.preventDefault();
      return false;
    });
  };
})();
