// SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Render the share image, web/og-image.png (1200x630), from the landing
// page's map. Needs Playwright:  node tools/hero/render-og.js
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.join(__dirname, 'og.html'));
  const map = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'web', 'hero', 'map.json'), 'utf8'));
  const url = await page.evaluate((m) => window.drawShareImage(m), map);
  const out = path.join(__dirname, '..', '..', 'web', 'og-image.png');
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  console.log('wrote web/og-image.png');
  await browser.close();
})();
