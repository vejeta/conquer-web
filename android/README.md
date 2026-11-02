<!--
SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Conquer for Android

The 1987 strategy game in the phone. The app is the website (`../web`) inside
[Cefrium](https://cefrium.com), a Chromium for Android, with a home screen,
a login for the game server and turn notifications.

- **Offline**: the practice world (the game compiled to WebAssembly), the
  tutorial, the guide and the hall of fame, all from the app's own copy of
  `web/`.
- **Online**: the shared game at <https://conquer.vejeta.com/game.html?app=1>
  (the touch page; the terminal it frames, `/play/`, has Basic
  authentication). "The website" opens the site in the system's browser.

The pages know they are in the app (`?app=1`, `window.cefriumQuery` or a
Cefrium user agent): no site header or footer, a compact bar (Home, Coach,
Keyboard, Menu), sound on by default, haptics through the bridge. Practice
opens `try/?app=1&autostart=1` and goes straight to the map. The game is shown
sideways (sensor landscape); the other screens follow the phone.

Package and application id: `com.vejeta.conquer`. Version 0.1.0.

## Build

You need JDK 25, the Android SDK with platform 37 and build-tools 37.0.0
(`ANDROID_HOME`), and the network for Gradle and Maven Central. The Gradle
wrapper (9.7.1) is committed.

```sh
cd android
./gradlew assembleDebug      # app/build/outputs/apk/debug/app-debug.apk
./gradlew installDebug       # to a device or emulator
```

The toolchain is the one Cefrium 0.17.0 asks for: AGP 9.4 with its built-in
Kotlin (no `org.jetbrains.kotlin.android` plugin), Gradle 9.7.1, JDK 25,
compileSdk 37, minSdk 29, 4 GB of Gradle heap, legacy `jniLibs` packaging.

The engine is large (about 150 MB per ABI). The debug build has `arm64-v8a`
(phones) and `x86_64` (the emulator on a PC); the release build only
`arm64-v8a`.

### The website copy

The Gradle task `copyWeb<Variant>` copies `../web` into the app's
`assets/web/` before the assets are merged. It leaves out `status/`,
`admin.html`, `signup.html`, `server.js` and the tutorial videos
(`tutorial/*.mp4`, `*.vtt`: they are H.264/AAC, which the royalty-free
engine used here does not decode; the pages hide their video links when the
file is missing). It writes its own `server.js` that sets
`CONQUER_CONFIG.server` to `https://conquer.vejeta.com`, so the "Play now"
links and the status of the bundled pages go to the real server.

### Release and signing

```sh
keytool -genkeypair -keystore conquer.keystore -alias conquer \
  -keyalg RSA -keysize 4096 -validity 10000
./gradlew bundleRelease      # app/build/outputs/bundle/release/app-release.aab
```

Sign the bundle with `jarsigner` (or `apksigner` for an APK built with
`assembleRelease`). Keep the keystore out of the repository: `*.keystore`
is in `.gitignore`. Upload an App Bundle rather than an APK, so that each
device downloads one ABI.

## How it works

### Loopback server

WebAssembly streaming and service workers do not work from `file://`, so the
bundled pages are served by `web/LoopbackServer.kt`: about 150 lines on a
`ServerSocket` bound to `127.0.0.1`. `http://127.0.0.1:PORT/` is a secure
context for Chromium.

- GET and HEAD, `Connection: close`, `Cache-Control: no-cache`, correct MIME
  types (`application/wasm` among them), 404 for what is not there, a
  redirect for a directory without its slash (`/try` to `/try/`).
- `..` and backslashes in the path are refused, and so is a `Host` header
  that is not `127.0.0.1:PORT` or `localhost:PORT` (DNS rebinding).
- The port is part of the page's origin, and the practice world lives in
  that origin's IndexedDB: the app saves the port and asks for it again on
  the next run, so the world stays. If another app took the port, any free
  one is used and the world starts again.
- It starts in `MainActivity.onCreate` and stops in `onDestroy`.

### Language

The home screen opens pages in the phone's language by adding `?lang=` (the
site's own parameter, see `web/site.js`) and choosing the language's
tutorial file (`tutorial.es.html`...). The seven languages of the site are
supported; the app's own texts (`res/values-*`) are in the same seven.

### Login for online play

Apache asks for Basic authentication on `/play/`. The browser screen sets
`CefriumBrowser.setHttpAuthHandler` (through `onBrowserReady` of
`CefriumView`):

1. The challenge is answered only for `conquer.vejeta.com`, never for another
   host or a proxy. It comes from the terminal's frame inside `game.html`
   (a sub-frame, and again for the WebSocket), so every challenge is answered,
   whatever frame asks.
2. With a saved account, it is sent at once, up to 4 times within 20 seconds.
   If the server keeps asking, the account was refused: the dialog opens with
   a warning.
3. Without an account, the dialog asks for it. "Remember me" is on by
   default and saves the account in `EncryptedSharedPreferences`
   (AES-256-GCM, key in the Android Keystore).
4. Settings on the home screen has "Forget account".

### Turn notifications

`work/TurnCheck.kt` is a WorkManager periodic job (every hour, network
required) that reads `https://conquer.vejeta.com/status/status.json`,
compares `turn` with the one it saw last and posts "Turn N has run". The
first check only remembers the turn. On Android 13 and later the app asks
for the `POST_NOTIFICATIONS` permission at start.

## JavaScript bridge

Pages call the app with `window.cefriumQuery`. The request is a JSON
string with a `type`. Only the app's own pages (the loopback origin of the
run) and `https://conquer.vejeta.com` may call it
(`QueryOriginPolicy.exactly`); a call from any other origin fails with
-403 and never reaches the app. Only the main frame can call.

```js
function app(request) {
  return new Promise(function (resolve, reject) {
    if (!window.cefriumQuery) return reject(new Error('not in the app'));
    window.cefriumQuery({
      request: JSON.stringify(request),
      onSuccess: function (r) { resolve(JSON.parse(r)); },
      onFailure: function (code, message) { reject(new Error(code + ' ' + message)); },
    });
  });
}

app({ type: 'haptic', ms: 8 });                       // vibrate 8 ms (1 to 500)
app({ type: 'keepAwake', on: true });                 // keep the screen on / let it sleep
app({ type: 'notify', title: 'Conquer', body: 'Your armies have arrived' });
app({ type: 'race', race: 'elf' });                   // the colours: human, elf, dwarf or orc
```

| `type`      | Fields                  | Does                                  |
|-------------|-------------------------|---------------------------------------|
| `haptic`    | `ms` (default 10)       | `Vibrator`, one shot                  |
| `keepAwake` | `on` (boolean)          | `FLAG_KEEP_SCREEN_ON` on or off       |
| `notify`    | `title`, `body`         | a local notification                  |
| `race`      | `race`                  | stores the race of the app's colours  |
| `home`      |                         | leaves the page for the home screen   |

The answer is `{"ok":true}`. Failures: `-1` bad request (not JSON, or an unknown race), `-2`
unknown `type`, `-3` notifications not allowed (no permission), `-403`
origin not allowed. The page also keeps the screen on by itself while the
address contains `/play/`, `/try/` or `/game.html`, and `navigator.vibrate` works in
Cefrium without the bridge (the app declares `VIBRATE`).

## Licences

- The app's code is GPL-3.0-or-later, like the rest of the repository; every
  file carries an SPDX header.
- The Cefrium SDK (`com.cefrium:cefrium-sdk-libre`, `cefrium-compose`) is
  LGPL-3.0-or-later; the app links to it dynamically as a library, and an
  APK built from this source can be rebuilt with another build of it.
- VT323 (`res/font/vt323.ttf`, converted from `web/fonts`) is under the SIL
  Open Font License 1.1: see `app/OFL-VT323.txt`.
