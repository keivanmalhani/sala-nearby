#!/usr/bin/env node
// Does the app actually work with no signal after ONE launch?
//
//   python3 -m http.server 8899   # from docs/
//   node tools/offline-check.mjs
//
// WHY THIS EXISTS. Everything else in this repo checks the page. This checks the promise
// the README makes, which is a different thing and had been false in a way nothing could
// see: on 2026-09-09 the map worked offline out of the BROWSER'S OWN HTTP CACHE while
// maplibre-gl.min.js was in no cache this app controls. Reading sw.js does not show that
// -- the code looks right, and it is right, because `if (r && r.ok)` correctly refuses an
// opaque response. What shows it is opening the caches and looking.
//
// THE STEP THAT MAKES IT A REAL TEST is Network.clearBrowserCache before going offline.
// Without it an offline reload can be served entirely out of the disk cache and every
// assertion below passes on an app that would fail on the Metro. That is the same shape
// as every other trap written down in this project: the cheap signal sits beside the real
// one and diverges exactly where it matters.
import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9337;
const URL_ = process.env.SALA_URL || "http://127.0.0.1:8899/index.html";
const sleep = ms => new Promise(r => setTimeout(r, ms));

let fails = 0;
const check = (name, ok, detail) => {
  console.log(`  ${ok ? "ok  " : "FAIL"} ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!ok) fails++;
};

async function waitForPort(deadline = 25000) {
  const until = Date.now() + deadline;
  while (Date.now() < until) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); if (r.ok) return; } catch {}
    await sleep(200);
  }
  throw new Error("headless Chrome never answered");
}

const profile = await mkdtemp(join(tmpdir(), "sala-offline-"));
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--enable-unsafe-swiftshader",
  "--no-first-run", "--no-default-browser-check", "--disable-extensions",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, "about:blank"],
  { stdio: "ignore" });

try {
  await waitForPort();
  const t = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  const pending = new Map(); let thrown = []; let id = 0;
  ws.addEventListener("message", ev => {
    const m = JSON.parse(ev.data);
    if (m.id !== undefined && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result);
    } else if (m.method === "Runtime.exceptionThrown") {
      thrown.push((m.params.exceptionDetails.exception?.description
        || m.params.exceptionDetails.text || "").slice(0, 140));
    }
  });
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const mid = ++id; pending.set(mid, { resolve: res, reject: rej });
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  const js = async expr => {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || "threw");
    return r.result.value;
  };
  await send("Runtime.enable"); await send("Page.enable"); await send("Network.enable");
  await send("Emulation.setDeviceMetricsOverride",
    { width: 390, height: 844, deviceScaleFactor: 2, mobile: true, screenWidth: 390, screenHeight: 844 });

  // ONE expression, read twice: with a signal and then without. Defining it once is what
  // makes the comparison below mean anything.
  const READING = `JSON.stringify({
    cinemas: document.querySelectorAll("#showlist .cin").length,
    count: $("scount").textContent.trim(),
    prices: document.querySelectorAll("#showlist .pri").length,
    posters: document.querySelectorAll("#showlist .pw img").length,
    maplibre: typeof maplibregl,
    faces: document.fonts ? document.fonts.size : 0
  })`;

  console.log("section 1 -- ONE launch with a signal, and nothing else");
  await send("Page.navigate", { url: URL_ });
  await sleep(3200);
  await js(`localStorage.setItem("sala.install","done"); true`);
  const warm = JSON.parse(await js(`(async () => {
    const keys = await caches.keys(), counts = {};
    for (const k of keys) counts[k] = (await (await caches.open(k)).keys()).length;
    const lib = keys.find(k => k.endsWith("-lib"));
    const urls = lib ? (await (await caches.open(lib)).keys()).map(r => r.url) : [];
    return JSON.stringify({ counts, urls, controlled: !!navigator.serviceWorker.controller });
  })()`));
  console.log("  caches after one visit:", JSON.stringify(warm.counts));
  // What the page shows WITH a signal. Everything in section 2 is measured against this.
  const on = JSON.parse(await js(READING));
  console.log("  online: ", JSON.stringify(on));
  // A floor, so that "offline equals online" cannot pass on two empty pages.
  check("the page has something on it to begin with",
        on.cinemas > 5 && on.prices > 50 && on.posters > 20, on.count);
  check("the worker is controlling the page", warm.controlled);
  // THE ASSERTION THIS FILE EXISTS FOR. Before 2026-09-09 there was no lib cache at all
  // after one visit, so this is the line that was red.
  check("maplibre-gl.min.js is in a cache this app controls, after ONE visit",
        warm.urls.some(u => /maplibre-gl\.min\.js$/.test(u)),
        warm.urls.length + " urls in lib");
  check("so is its stylesheet", warm.urls.some(u => /maplibre-gl\.min\.css$/.test(u)));
  check("and the Google Fonts stylesheet, which names every face the page uses",
        warm.urls.some(u => u.indexOf("fonts.googleapis.com/css2") >= 0));

  console.log("\nsection 2 -- now cut the network, and the browser's own cache with it");
  thrown = [];
  // Without this the test cannot tell the service worker apart from the disk cache.
  await send("Network.clearBrowserCache");
  await send("Network.emulateNetworkConditions",
    { offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0 });
  await send("Page.navigate", { url: URL_ });
  await sleep(4200);
  await js(`localStorage.setItem("sala.install","done"); document.querySelectorAll("[role=dialog]").forEach(d=>d.remove()); true`);
  const off = JSON.parse(await js(READING));
  console.log("  offline:", JSON.stringify(off));
  // AGAINST THE ONLINE READING, NOT AGAINST A NUMBER. This line used to ask for at least
  // 30 cinemas and at least 100 prices -- both of them facts about 9 September, when the
  // page was built. On 11 September the same payload opens on a day with 29 cinemas on
  // it and the test went red on a calendar rather than on a defect. The question it is
  // actually asking is whether cutting the network changes what the page shows, and the
  // only answer that cannot decay is the same reading taken twice.
  check("the showtimes are all there", off.cinemas === on.cinemas && off.count === on.count,
        `${off.count} offline, ${on.count} online`);
  check("the prices came back, so detail.json was cached", off.prices === on.prices,
        `${off.prices} of ${on.prices}`);
  check("the posters came back", off.posters === on.posters, `${off.posters} of ${on.posters}`);
  check("MapLibre loaded with no network at all", off.maplibre === "object");
  check("the typeface rules survived, so it is not falling back to system fonts",
        off.faces > 10, off.faces + " faces");

  await js(`setTab("map"); true`); await sleep(2600);
  const mapOk = JSON.parse(await js(`JSON.stringify({
    canvas: !!document.querySelector("#map canvas"),
    markers: document.querySelectorAll(".vdot").length })`));
  check("and the map draws", mapOk.canvas, mapOk.markers + " markers");
  check("nothing threw on the way", thrown.length === 0, thrown[0] || "clean");
  ws.close();
} catch (e) {
  console.error("offline-check could not run:", e.message);
  console.error("is `python3 -m http.server 8899` running in docs/ ?");
  fails++;
} finally {
  chrome.kill("SIGTERM"); await sleep(300); chrome.kill("SIGKILL");
  await rm(profile, { recursive: true, force: true });
}
console.log();
if (fails) { console.log(`${fails} FAILED`); process.exit(1); }
console.log("all controls pass");
