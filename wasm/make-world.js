// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Create the practice world for the browser build with the browser build
// itself: the world file is a dump of C structures, so it must be written
// by a program with the same data layout (32-bit WebAssembly), not by the
// 64-bit server game. Runs conqrun (compiled for Node, with direct file
// access) twice, typing the answers of the world generator and of the
// nation builder.
//
// usage: node make-world.js conqrun-node.js OUTDIR
const path = require('path');
const fs = require('fs');

const [runner, outdir] = process.argv.slice(2).map((p) => path.resolve(p));
const createConqrun = require(runner);

const keys = (list) => list.join('').split('').map((c) => c.charCodeAt(0));

// World generator: 64x64, 60% water, the standard computer nations
const MAKE_WORLD = [' ', 'godpass\n', 'godpass\n', '\n', '64\n', '64\n', '60\n', '\n', 'y', 'y', '\n', '\n', '\n', '\n'];
// Nation builder: trainee (password train1), human king, good; three
// points of treasury, the rest in people
const ADD_NATION = ['trainee\n', 'train1\n', 'train1\n', 'Rowan\n', 'H', '1', '\n', ' ', 'G', 'Y',
  'j', ' ', ' ', ' ', '\x1b', 'y', ' ', 'y', 'y', ' ', ' ', ' '];

// With direct file access (NODERAWFS) the programs write straight to this
// process's output: build.sh keeps it in a log. Success is checked in the
// files they write.
function run(args, input) {
  return new Promise((resolve) => {
    createConqrun({
      conquerKeys: keys(input),
      conquerKeysClosed: true,
      noInitialRun: true,
      onExit: resolve,
    }).then((M) => M.callMain(args));
  });
}

(async () => {
  fs.mkdirSync(outdir, { recursive: true });
  const data = path.join(outdir, 'data');
  await run(['-m', '-d', outdir], MAKE_WORLD);
  if (!fs.existsSync(data)) {
    console.error('make-world: the world generator did not create a world');
    process.exit(1);
  }
  await run(['-a', '-d', outdir], ADD_NATION);
  if (!fs.readFileSync(data).includes('trainee')) {
    console.error('make-world: the nation builder did not add the practice nation');
    process.exit(1);
  }
  console.error('practice world written to ' + outdir);
})();
