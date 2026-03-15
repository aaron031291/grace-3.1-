import puppeteer from 'puppeteer';
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://localhost:8765/', { waitUntil: 'networkidle0', timeout: 10000 }).catch(e => errors.push('NAV: ' + e.message));
  await new Promise(r => setTimeout(r, 2000));

  if (errors.length) {
    console.log('ERRORS:', errors.map(e => e.substring(0, 300)));
  } else {
    console.log('NO PAGE ERRORS!');
  }

  const result = await page.evaluate(() => {
    const fns = ['renderGenesis', 'genesisLoadFile', 'genesisSaveFile', 'launchWithSpindle',
      'loadGenesis', 'poll', 'switchTab', 'switchRightTab',
      'triggerSpindleFix', 'pollActivityFeed', 'sendChat', 'toggleVoice',
      'appendChatMsg', 'formatNLP', 'speakResponse'];
    const r = {};
    fns.forEach(f => { try { r[f] = typeof eval(f); } catch (e) { r[f] = 'missing'; } });
    return r;
  }).catch(e => ({ error: e.message }));
  console.log('Functions:', JSON.stringify(result, null, 2));

  await browser.close();
})();
