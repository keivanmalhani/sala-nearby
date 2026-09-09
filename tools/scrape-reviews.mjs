// Read Google Maps reviews for every Sala Nearby cinema, through HIS already-running
// Chrome on 127.0.0.1:9222. Never launches a browser of its own.
//
// Why the DOM and not an API: /maps/rpc/listugcposts answers 403 to a hand-built pb even
// with his cookies attached, and Maps loads the first page of reviews into the document
// rather than over XHR, so nothing was captured by watching the network either. The
// rendered pane is what actually holds the reviews, so that is what this reads.
//
// One background tab is opened and reused for every cinema, then closed. newBackgroundTab,
// never newTab: a foreground tab would take over his screen 35 times.
import { readFileSync, writeFileSync } from 'node:fs';
// This scraper drives an already-running Chrome over the DevTools protocol. The CDP
// helper lives outside this repo, so point CDP_LIB at it:
//   CDP_LIB=/path/to/cdp.js node tools/scrape-reviews.mjs
// It is a dev tool for regenerating docs/cinema-reviews.json and is not needed to run
// or build the app.
const CDP_LIB = process.env.CDP_LIB;
if (!CDP_LIB) {
  console.error('set CDP_LIB to the path of a CDP helper exporting ' +
                'newBackgroundTab, attachId, closeTab and sleep');
  process.exit(2);
}
const { newBackgroundTab, attachId, closeTab, sleep } = await import(CDP_LIB);

const IN = process.argv[2];
const OUT = process.argv[3];
const TARGET = Number(process.env.TARGET || 100);
const ONLY = process.env.ONLY ? Number(process.env.ONLY) : null;

const places = JSON.parse(readFileSync(IN, 'utf8')).filter((p) => p.place_id);
const work = ONLY ? places.slice(0, ONLY) : places;

// Reads the header block. "4,4(4277)" in es-MX -- comma decimal, thousands separator is
// a non-breaking space or a comma depending on the locale Google decides to serve.
function readHeader() {
  const t = document.querySelector('div.F7nice')?.textContent || '';
  const m = t.match(/([\d]+[.,][\d]+)\s*\(([\d.,  \s]+)\)/);
  return {
    name: document.querySelector('h1')?.textContent || null,
    rating: m ? Number(m[1].replace(',', '.')) : null,
    reviews: m ? Number(m[2].replace(/[^\d]/g, '')) : null,
    raw: t,
  };
}

function openReviews() {
  const t = [...document.querySelectorAll('[role=tab]')]
    .find((x) => /rese/i.test((x.getAttribute('aria-label') || '') + x.textContent));
  if (!t) return false;
  t.click();
  return true;
}

// The review list is its own scroll container. Find it by the fact that it CONTAINS
// review cards and overflows -- matching on the class name would break the next time
// Google reshuffles its minified classes.
// Google's newer reviews layout renders the histogram and its own written summary first
// and loads no review card at all until something scrolls. Every pane-finder here starts
// from a review card, so with zero cards there is nothing to start from -- which is how
// eight cinemas, Cineteca Xoco among them, came back with a sample of 0 while their page
// loaded perfectly. This kicks every tall overflowing container instead.
function kickPanes() {
  for (const d of document.querySelectorAll('div')) {
    if (d.clientHeight > 250 && d.scrollHeight > d.clientHeight + 40) {
      d.scrollTop = d.scrollHeight;
      d.dispatchEvent(new Event('scroll', { bubbles: true }));
    }
  }
  return document.querySelectorAll('div[data-review-id]').length;
}

// Google writes its own one-paragraph summary of what reviewers say. It is the site's
// own synthesis over the whole corpus rather than over a 100-review sample, so it is
// worth keeping beside the counts.
function googleSummary() {
  const d = [...document.querySelectorAll('div')]
    .find((x) => /^La gente dice/.test((x.innerText || '').trim()));
  if (!d) return null;
  return d.innerText.split('\n')[0].trim().slice(0, 600);
}

// Setting scrollTop alone loaded exactly 20 reviews and stopped. Maps' loader listens
// for a scroll EVENT, so the event has to be dispatched by hand; with it the pane pages
// 20 at a time indefinitely. The jiggle is for the stall at a page boundary, where the
// loader wants a fresh scroll delta rather than the same scrollTop written again.
function scrollPane(jiggle) {
  const card = document.querySelector('div[data-review-id]');
  if (!card) return kickPanes();
  let el = card.parentElement;
  while (el && !(el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 150)) el = el.parentElement;
  if (!el) return -1;
  if (jiggle) {
    el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight * 3);
    el.dispatchEvent(new Event('scroll', { bubbles: true }));
  }
  el.scrollTop = el.scrollHeight;
  el.dispatchEvent(new Event('scroll', { bubbles: true }));
  return document.querySelectorAll('div[data-review-id]').length;
}

// The control is a button whose accessible name is exactly "Ver más". Matching the
// minified class instead left 30 of 80 reviews cut off at "... Más", and a truncated
// review is a review whose second half -- often the complaint -- was never read.
function expandAll() {
  let n = 0;
  for (const b of document.querySelectorAll('div[data-review-id] button')) {
    const t = (b.getAttribute('aria-label') || b.textContent || '').trim();
    if (/^(Ver más|Más|More)$/i.test(t)) { b.click(); n++; }
  }
  return n;
}

// Maps renders every review card TWICE -- 20 nodes for 10 reviews. Counting nodes
// doubles every sample and every keyword tally, so dedupe on the review id.
function harvest() {
  const seen = new Set();
  return [...document.querySelectorAll('div[data-review-id]')].filter((c) => {
    const k = c.getAttribute('data-review-id');
    if (!k || seen.has(k)) return false;
    seen.add(k); return true;
  }).map((c) => {
    const lab = c.querySelector('[role=img][aria-label*="estrella"]')?.getAttribute('aria-label') || '';
    const st = lab.match(/(\d)/);
    const body = c.querySelector('.MyEned')?.innerText
      || c.querySelector('.wiI7pd')?.innerText || '';
    const when = [...c.querySelectorAll('span')]
      .map((s) => s.textContent.trim())
      .find((t) => /^Hace |^hace |^\d+ (día|semana|mes|año)/.test(t)) || null;
    return { id: c.getAttribute('data-review-id'), stars: st ? Number(st[1]) : null, when, text: body.trim() };
  }).filter((r) => r.text);
}

const tab = await newBackgroundTab('about:blank');
const results = [];
try {
  const p = await attachId(tab);
  await p.send('Page.enable');

  for (const [i, c] of work.entries()) {
    // Cinemex's own API names its cinemas without the chain ("Insurgentes"), so the
    // chain has to be put back. Cineteca and the indie venues carry their full name.
    const bare = /^(cineteca|indie)/.test(String(c.id));
    const label = bare ? c.n : 'Cinemex ' + c.n;
    const url = `https://www.google.com/maps/place/?q=place_id:${c.place_id}&hl=es&gl=mx`;
    let rec = { id: c.id, sala_name: label, place_id: c.place_id, url, km: c.km, addr: c.a };
    try {
      await p.send('Page.navigate', { url });
      await sleep(7000);
      const head = await p.evaluate(readHeader);
      rec = { ...rec, ...head };
      const opened = await p.evaluate(openReviews);
      if (!opened) throw new Error('no Reseñas tab on the page');

      // A fixed sleep here cost four cinemas on the first pass: the pane had not rendered
      // a single card yet, scrollPane returned -1, and the cinema was written out with a
      // sample of 0 and no error against it. Wait for the cards instead of for the clock,
      // and say so plainly when they never arrive.
      rec.google_summary = await p.evaluate(googleSummary);

      let ready = 0;
      for (let k = 0; k < 20; k++) {
        ready = await p.evaluate(kickPanes);
        if (ready > 0) break;
        await sleep(1500);
      }
      if (!ready) throw new Error('the Reseñas pane rendered no review cards in 30s of scrolling');

      let last = 0, stalls = 0, n = 0;
      for (let k = 0; k < 60; k++) {
        n = await p.evaluate(scrollPane, stalls > 0);
        if (n < 0) break;
        if (n >= TARGET * 2) break;   // node count, and every review renders twice
        if (n === last) { if (++stalls >= 5) break; } else stalls = 0;
        last = n;
        await sleep(stalls > 0 ? 2600 : 1700);
      }
      rec.loaded = n;
      // Clicking re-renders the card, so one pass leaves some still folded. Repeat
      // until a pass finds nothing to click.
      for (let k = 0; k < 6; k++) {
        const e = await p.evaluate(expandAll);
        await sleep(1200);
        if (!e) break;
      }
      rec.sampled = await p.evaluate(harvest);
      rec.ok = rec.sampled.length > 0;
      console.log(`[${i + 1}/${work.length}] ${label.padEnd(36)} r=${rec.rating} n=${rec.reviews} sampled=${rec.sampled.length}`);
    } catch (e) {
      rec.ok = false; rec.error = String(e.message || e); rec.sampled = [];
      console.log(`[${i + 1}/${work.length}] ${label.padEnd(36)} FAILED ${rec.error}`);
    }
    results.push(rec);
    writeFileSync(OUT, JSON.stringify(results, null, 1));
  }
  p.close();
} finally {
  await closeTab(tab);
}
const ok = results.filter((r) => r.ok).length;
console.log(`\n${ok} of ${results.length} cinemas returned reviews`);
