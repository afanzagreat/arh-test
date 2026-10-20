'use strict';

const assert = require('node:assert/strict');
let chromium;
try {
  ({chromium} = require('playwright'));
} catch (error) {
  throw new Error('Playwright is required (install it in the repo or expose it through NODE_PATH).', {cause: error});
}

const base = process.env.PROTOTYPE_URL;
if (!base) {
  throw new Error('PROTOTYPE_URL is required and must be the hosted prototype URL.');
}

const langs = ['en', 'ar', 'fr', 'hi'];
const kinds = ['home', 'services', 'packages', 'works', 'about', 'quote'];
const route = (lang, kind) => `${lang === 'en' ? '/' : `/${lang}/`}${kind === 'home' ? '' : `${kind}.html`}`;

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {}),
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  let checks = 0;

  try {
    for (const width of [390, 1280]) {
      await page.setViewportSize({width, height: 900});
      for (const lang of langs) {
        for (const kind of kinds) {
          const response = await page.goto(new URL(route(lang, kind), base).href, {waitUntil: 'networkidle'});
          assert.equal(response.status(), 200, `${lang}/${kind} did not return 200`);
          const result = await page.evaluate(() => ({
            forbidden: document.querySelectorAll('.signal-console, .orbit-tracker, canvas').length,
            sparks: document.querySelectorAll('.studio-spark').length,
            overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
          }));
          assert.equal(result.forbidden, 0, `${lang}/${kind} contains tracker UI/canvas at ${width}px`);
          assert.equal(result.sparks, 1, `${lang}/${kind} must contain exactly one .studio-spark`);
          if (width === 390) assert.equal(result.overflow, false, `${lang}/${kind} overflows horizontally at 390px`);
          checks++;
        }
      }
    }

    await page.setViewportSize({width: 1280, height: 900});
    await page.goto(new URL(route('en', 'packages'), base).href, {waitUntil: 'networkidle'});
    await page.locator('[data-mode="once"]').click();
    assert.equal(await page.locator('#monthlyPlans').isVisible(), false);
    assert.equal(await page.locator('#oncePlans').isVisible(), true);
    assert.match(await page.locator('#oncePlans').innerText(), /209/);
    await page.locator('[data-plan="once_pro"]').click();
    assert.equal(await page.locator('#budget').inputValue(), 'once_pro');
    assert.equal(await page.locator('#existingWebsite').isDisabled(), true);
    await page.locator('#projectType').selectOption('Redesign existing site');
    assert.equal(await page.locator('#existingWebsite').isVisible(), true);
    assert.equal(await page.locator('#existingWebsite').getAttribute('required'), '');
    await page.locator('#name').fill('Accent Regression Test');
    await page.locator('#email').fill('accent@example.com');
    await page.locator('#existingWebsite').fill('https://example.com');
    await page.locator('#message').fill('A clearer local business website.');
    let posts = 0;
    const onRequest = request => { if (request.method() === 'POST') posts++; };
    page.on('request', onRequest);
    await page.locator('button[type="submit"]').click();
    assert.equal(await page.locator('#briefReview').isVisible(), true);
    assert.match(await page.locator('#briefDetails').innerText(), /https:\/\/example\.com/);
    assert.equal(posts, 0, 'quote submission must remain preview-only');
    page.off('request', onRequest);
    await page.locator('#projectType').selectOption('New website');
    assert.equal(await page.locator('#existingWebsite').inputValue(), '');
    assert.equal(await page.locator('#existingWebsite').isDisabled(), true);
    checks++;

    await page.emulateMedia({reducedMotion: 'reduce'});
    await page.goto(new URL('/', base).href, {waitUntil: 'networkidle'});
    assert.equal(await page.locator('.spark-orbit').evaluate(element => getComputedStyle(element).animationName), 'none');
    checks++;

    assert.deepEqual(errors, [], 'Uncaught browser errors');
    console.log(`PASS: ${checks} accent regression checks across 24 routes at desktop/mobile widths; no tracker overlays/canvases, one .studio-spark per page, preview-only quote flow, reduced motion, and 390px overflow coverage.`);
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exit(1);
});
