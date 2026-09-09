// One-shot probe: can we read Google Maps reviews from inside his Chrome?
import { newBackgroundTab, attachId, closeTab, sleep } from '/Users/keivanmalhani/dev/job_search/state/cdp.js';

const FID = '0x85d1ff8e5aca3fb5:0xdc8d4474bcbc9148';
const id = await newBackgroundTab('https://www.google.com/maps/@19.41,-99.16,14z?hl=es');
try {
  const p = await attachId(id);
  await sleep(4000);
  const out = await p.evaluate(async (fid) => {
    const pb = `!1m6!1s${fid}!6m4!4m1!1e1!4m1!1e3!2m2!1i20!2s!5m2!1sABC!7e81!8m9!2b1!3b1!5b1!7b1!12m4!1b1!2b1!4m1!1e1!11m0!13m1!1e2`;
    const u = 'https://www.google.com/maps/rpc/listugcposts?authuser=0&hl=es&gl=mx&pb=' + pb;
    const r = await fetch(u, { credentials: 'include' });
    const t = await r.text();
    return { status: r.status, len: t.length, head: t.slice(0, 400) };
  }, FID);
  console.log(JSON.stringify(out, null, 1));
  p.close();
} finally { await closeTab(id); }
