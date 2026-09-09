// Watch what Google Maps itself requests when a place's reviews load, so we can replay it.
import { newBackgroundTab, attachId, closeTab, sleep } from '/Users/keivanmalhani/dev/job_search/state/cdp.js';

const URL_ = 'https://www.google.com/maps/place/?q=place_id:ChIJtT_KWo7_0YURSJG8vHREjdw&hl=es&gl=mx';
const id = await newBackgroundTab('about:blank');
try {
  const p = await attachId(id);
  const seen = [];
  p.on('Network.requestWillBeSent', (e) => {
    const u = e.request.url;
    if (/listugcposts|listentitiesreviews|reviews|ugc/i.test(u)) seen.push(u);
  });
  await p.send('Network.enable');
  await p.send('Page.enable');
  await p.send('Page.navigate', { url: URL_ });
  await sleep(9000);
  // click the reviews tab if present
  const clicked = await p.evaluate(() => {
    const btns = [...document.querySelectorAll('button,[role=tab]')];
    const b = btns.find(x => /rese|review/i.test(x.textContent || '') || /rese|review/i.test(x.getAttribute('aria-label')||''));
    if (b) { b.click(); return b.textContent.trim().slice(0,40) || b.getAttribute('aria-label'); }
    return null;
  });
  await sleep(7000);
  console.log('clicked:', clicked);
  console.log('title:', await p.evaluate(() => document.title));
  console.log('--- matching requests:', seen.length);
  for (const u of seen.slice(0, 6)) console.log(u.slice(0, 900), '\n');
  p.close();
} finally { await closeTab(id); }
