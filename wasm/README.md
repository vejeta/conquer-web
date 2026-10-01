# Conquer in the browser (WebAssembly)

`web/try/` runs Conquer entirely in the visitor's browser: no account, no
server, nothing installed. It is a private practice world (nation
`trainee`, password `train1`) kept in the browser's storage (IndexedDB),
with its own turn updates. Because it is plain static files, any static web
host can serve it.

The game and its turn update (`conquer` and `conqrun`) are compiled from
the game sources with [Emscripten](https://emscripten.org). The sources are
unchanged, except that the old `long time();` declarations are dropped in a
build copy. What the browser lacks comes from `shim/`:

- **curses** (`curses.h`, `shim.c`): the thirty-odd calls Conquer uses, on
  an 80x24 screen drawn on [xterm.js](https://xtermjs.org) with ANSI codes;
- **the keyboard**: the page queues keys and the game waits for them without
  freezing the page (Asyncify);
- **a user**: `conquer` (uid 1000), who owns the practice nation and may run
  turn updates; and `getpass`, `sleep` and the game's two `system()` calls.

The world file is a dump of C structures, and `long` is 4 bytes in
WebAssembly but 8 on the server, so the server's worlds cannot be used
here. `build.sh` makes the practice world with the WebAssembly `conqrun`
itself (compiled for Node), typing the answers of the world generator and
the nation builder (`make-world.js`).

## Building

```bash
source /path/to/emsdk/emsdk_env.sh
wasm/build.sh [path/to/conquer/gpl-release]   # default: clone and patch
```

It writes `web/try/conquer.{js,wasm}`, `conqrun.{js,wasm}` and
`web/try/world/`. A native C compiler is needed for the help files, and the
world generator reads its computer nations from `/conquer/lib`, which the
script creates.
