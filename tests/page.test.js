// Opens loi-dong-am/index.html straight from disk in Chromium and uses it like a person would.
// Run: node --test tests/page.test.js   (needs Playwright and its Chromium)
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

const PAGE = pathToFileURL(path.join(__dirname, '..', 'loi-dong-am', 'index.html')).href;

test('the page works from disk', async t => {
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => {
    // Web fonts are optional: the page falls back to system fonts offline.
    if (m.type() === 'error' && !/fonts\.(googleapis|gstatic)\.com/.test(m.text())) errors.push(m.text());
  });
  await page.goto(PAGE);

  await t.test('opens with the sample song already rewritten', async () => {
    await page.waitForSelector('#out .w.changed');
    assert.match(await page.textContent('#meter'), /Đã đổi \d+\/50 từ/);
    assert.equal(await page.isHidden('#pop'), true);
  });

  await t.test('a word can be put back and changed again', async () => {
    const word = page.locator('#out .w.changed').first();
    const index = await word.getAttribute('data-i');
    await word.click();
    await page.waitForSelector('#pop:not([hidden])');
    await page.locator('#popOpts .pick', { hasText: 'giữ từ gốc' }).click();
    const back = page.locator(`#out .w[data-i="${index}"]`);
    assert.equal(await back.getAttribute('class'), 'w');
    await back.click();
    await page.fill('#popInput', 'Grayss');
    await page.press('#popInput', 'Enter');
    assert.match(await page.locator(`#out .w[data-i="${index}"]`).getAttribute('class'), /changed/);
    assert.equal(await page.isHidden('#pop'), true);
  });

  await t.test('pasted lyrics are rewritten and shown as text only', async () => {
    await page.fill('#src', '[Chorus]\nSilent night, holy night <img src=x onerror="window.hacked=1">');
    await page.waitForFunction(() => document.querySelector('#out').textContent.includes('Chorus'));
    await page.click('#lv-strong + label');
    assert.equal(await page.locator('#out img').count(), 0);
    assert.equal(await page.evaluate(() => window.hacked), undefined);
    const text = await page.textContent('#out');
    assert.match(text, /\[Chorus\]/);
    assert.doesNotMatch(text, /Silent night, holy night/);
  });

  await t.test('copy puts the rewritten lyrics on the clipboard', async () => {
    await page.click('#copy');
    await page.waitForFunction(() => document.querySelector('#status').textContent === 'Đã chép');
    // Windows keeps line breaks on the clipboard as \r\n.
    const copied = (await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n');
    assert.match(copied, /^\[Chorus\]\n/);
    assert.doesNotMatch(copied, /Silent night/);
  });

  await t.test('"remember" adds the word to the personal list and keeps it after a reload', async () => {
    await page.fill('#src', 'Silent night');
    await page.waitForFunction(() => document.querySelectorAll('#out .w').length === 2);
    await page.locator('#out .w').nth(1).click();
    await page.check('#popRemember');
    await page.fill('#popInput', 'nyght');
    await page.press('#popInput', 'Enter');
    assert.equal(await page.inputValue('#custom'), 'night = nyght');
    await page.reload();
    await page.waitForSelector('#out .w');
    assert.equal(await page.inputValue('#src'), 'Silent night');
    assert.equal(await page.locator('#out .w').nth(1).locator('ruby').evaluate(r => r.firstChild.textContent), 'nyght');
  });

  await t.test('"Thêm khoảng trống" splits syllables with spaces', async () => {
    await page.selectOption('#sample', 'jingle');
    await page.click('#m-space + label');
    await page.click('#lv-strong + label');
    const text = await page.evaluate(() => [...document.querySelectorAll('#out .line')].map(l => {
      const c = l.cloneNode(true);
      c.querySelectorAll('rt').forEach(rt => rt.remove());
      return c.textContent;
    }).join('\n'));
    assert.match(text, /In a one horse o pen sleigh/);
    assert.match(text, /A sleigh ing song to night!/);
    assert.match(text, /Jin gle bells, jin gle bells/);
    assert.equal(await page.isDisabled('#homo'), true);
    await page.locator('#out .w.changed').first().click();
    assert.match(await page.textContent('#popOpts'), /tách âm tiết/);
    await page.keyboard.press('Escape');
    await page.reload();
    await page.waitForSelector('#out .w.changed');
    assert.equal(await page.isChecked('#m-space'), true);
  });

  await t.test('fits a phone screen', async () => {
    await page.setViewportSize({ width: 380, height: 800 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= 380));
  });

  assert.deepEqual(errors, []);
});
