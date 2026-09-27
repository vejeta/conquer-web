// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Screenshot video frames: node frames.js WIDTH HEIGHT page.html... writes
// page.png next to every page (used by video.py)
const { chromium } = require('playwright');

(async () => {
  const [w, h, ...pages] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: +w, height: +h } });
  for (const file of pages) {
    await page.goto('file://' + file);
    await page.screenshot({ path: file.replace(/\.html$/, '.png') });
  }
  await browser.close();
})();
