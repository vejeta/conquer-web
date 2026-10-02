# The landing page's war terminal

The top of the landing page (`web/index.html`) is the world map drawn like
the game screen on an amber monitor, with a staged war on it and a teletype
of world news. `web/hero.js` draws it; the news are the latest edition of the
game's newspaper (`status/status.json`), or example dispatches until the game
has news.

| File | What it is | Made by |
|------|------------|---------|
| `web/hero/map.json` | The default world (`conquer/lib/data`), turned half a turn so the page does not show where the nations are, and the staged war | `build-map.py` |
| `web/og-image.png` | The share image (1200x630) for link previews | `render-og.js` |
| `web/fonts/` | VT323 and IM Fell English SC, served by the site itself (SIL Open Font License, `OFL-*.txt`) | Google Fonts |

After generating a new default world:

```bash
# A built checkout of https://github.com/vejeta/conquer (for its headers)
tools/hero/build-map.py ~/src/conquer
# Needs Playwright (npm install playwright)
node tools/hero/render-og.js
```

The war (armies, battle, conquered sectors) is set in `build-map.py`, in the
world's own coordinates: choose sectors on land near the capitals of the new
world's nations. The share image names conquer.vejeta.com; `deploy-to-vps.sh`
points the page's link previews at the server it installs.
