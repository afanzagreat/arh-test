'use strict';
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = process.env.PROTOTYPE_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  let checks = 0;
  const langs = ['en','ar','fr','hi'];
  const kinds = ['home','services','packages','works','about','quote'];
  const path = (l,k) => (l==='en'?'/':'/'+l+'/')+(k==='home'?'':k+'.html');
  for (const width of [390,1280]) {
    await page.setViewportSize({width,height:844});
    for (const lang of langs) for (const kind of kinds) {
      const response = await page.goto(base+path(lang,kind));
      assert.equal(response.status(),200);
      const result = await page.evaluate(() => ({lang:document.documentElement.lang,dir:document.documentElement.dir,overflow:document.documentElement.scrollWidth>innerWidth+1,h1:document.querySelectorAll('h1').length,empty:[...document.querySelectorAll('[data-i18n]')].filter(x=>!x.textContent.trim()).map(x=>x.dataset.i18n)}));
      assert.equal(result.lang,lang);assert.equal(result.dir,lang==='ar'?'rtl':'ltr');
      assert.equal(result.overflow,false,`${lang}/${kind} overflow at ${width}`);
      assert.equal(result.h1,1);assert.deepEqual(result.empty,[]);
      checks++;
    }
  }
  await page.setViewportSize({width:1280,height:900});
  for(const lang of langs){
    await page.goto(base+path(lang,'packages'));
    await page.locator('[data-mode="once"]').click();
    assert.equal(await page.locator('#monthlyPlans').isVisible(),false);
    assert.equal(await page.locator('#oncePlans').isVisible(),true);
    assert.match(await page.locator('#oncePlans').innerText(),/209/);
    await page.locator('[data-plan="once_pro"]').click();
    assert.equal(await page.locator('#budget').inputValue(),'once_pro');
    assert.equal(await page.locator('#existingWebsite').isDisabled(),true);
    await page.locator('#projectType').selectOption('Redesign existing site');
    assert.equal(await page.locator('#existingWebsite').isVisible(),true);
    assert.equal(await page.locator('#existingWebsite').getAttribute('required'),'');
    await page.locator('#name').fill('Prototype Test');
    await page.locator('#email').fill('prototype@example.com');
    await page.locator('#existingWebsite').fill('https://example.com');
    await page.locator('#message').fill('A clearer local business website.');
    let requests=0;
    const watch=r=>{if(r.method()==='POST')requests++;};
    page.on('request',watch);
    await page.locator('button[type="submit"]').click();
    assert.equal(await page.locator('#briefReview').isVisible(),true);
    assert.match(await page.locator('#briefDetails').innerText(),/https:\/\/example.com/);
    assert.equal(requests,0);page.off('request',watch);
    await page.locator('#projectType').selectOption('New website');
    assert.equal(await page.locator('#existingWebsite').inputValue(),'');
    assert.equal(await page.locator('#existingWebsite').isDisabled(),true);
    checks++;
  }
  for(const kind of kinds){
    await page.goto(base+path('en',kind)+'?plan=once_pro#test');
    await page.locator('#languageSelect').selectOption('ar');
    await page.waitForURL(base+path('ar',kind)+'?plan=once_pro#test');
    assert.equal(await page.locator('html').getAttribute('dir'),'rtl');checks++;
  }
  await page.setViewportSize({width:390,height:844});
  await page.goto(base+'/');
  await page.locator('#menuBtn').click();
  assert.equal(await page.locator('#menuBtn').getAttribute('aria-expanded'),'true');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#menuBtn').getAttribute('aria-expanded'),'false');checks++;
  assert.deepEqual(errors,[],'Uncaught browser errors');
  await browser.close();
  console.log(`PASS: ${checks} browser scenarios; 24 routes at desktop/mobile widths, 4 quote journeys, all page language switches, mobile menu; no POST requests or JS errors.`);
})().catch(e=>{console.error(e);process.exit(1);});
