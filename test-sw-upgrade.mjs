// Run with: node test-sw-upgrade.mjs
// Model the Cache API so an upgrade can be checked without a network or browser cache.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const BASE = "https://sala.example/";
class Request {
  constructor(url, options = {}) {
    this.url = new URL(typeof url === "string" ? url : url.url, BASE).href;
    this.method = options.method || "GET";
    this.mode = options.mode || "same-origin";
    this.cache = options.cache;
  }
}
class Response {
  constructor(body, options = {}) {
    this.body = body;
    this.status = options.status ?? 200;
    this.ok = this.status >= 200 && this.status < 300;
    this.type = options.type || "basic";
    this.headers = options.headers || {};
  }
  clone() { return new Response(this.body, { status: this.status, type: this.type, headers: this.headers }); }
}
const key = req => new Request(req).url;
class Cache {
  entries = new Map();
  async match(req) { return this.entries.get(key(req)); }
  async put(req, response) { this.entries.set(key(req), response.clone()); }
  async delete(req) { return this.entries.delete(key(req)); }
  async keys() { return [...this.entries.keys()].map(url => new Request(url)); }
  async addAll(requests) {
    assert(requests.length > 0 && requests.every(req => req.cache === "reload"));
    // The fixture seeds each published shell; this models its successful precache.
  }
}
const registry = new Map();
const caches = {
  async keys() { return [...registry.keys()]; },
  async open(name) { if (!registry.has(name)) registry.set(name, new Cache()); return registry.get(name); },
  async delete(name) { return registry.delete(name); },
  async match(req) { for (const cache of registry.values()) { const hit = await cache.match(req); if (hit) return hit; } },
};
let listeners = new Map();
let networkCalls = 0;
let networkResult = null;
let skipWaitingCalls = 0;
const self = {
  location: { origin: BASE.slice(0, -1) },
  addEventListener(type, handler) { listeners.set(type, handler); },
  clients: { async claim() {} },
  async skipWaiting() { skipWaitingCalls++; },
};
const source = readFileSync("docs/sw.js", "utf8");
const version = Number(source.match(/const V = "sala-v(\d+)"/)[1]);
function loadWorker(v) {
  listeners = new Map();
  vm.runInNewContext(source.replace(/const V = "sala-v\d+"/, `const V = "sala-v${v}"`), {
    self, caches, Request, Response, URL,
    fetch: async () => {
      networkCalls++;
      if (networkResult) return networkResult.clone();
      throw new Error("offline");
    },
  });
}
loadWorker(version);
const put = async (name, url, body, options) => (await caches.open(name)).put(url, new Response(body, options));
const get = async (name, url) => (await caches.open(name)).match(url);

await put(`sala-v${version - 2}-tiles`, "https://tiles.openfreemap.org/old", "older tile");
await put(`sala-v${version - 1}-tiles`, "https://tiles.openfreemap.org/new", "new tile");
await put(`sala-v${version - 1}-tiles`, "https://tiles.openfreemap.org/error", "error", { status: 504 });
await put(`sala-v${version - 1}-posters`, BASE + "posters/1.jpg", "poster pixels");
await put(`sala-v${version - 1}-posters`, BASE + "posters/2.jpg", "opaque", { type: "opaque" });
await put(`sala-v${version - 1}-lib`, "https://cdnjs.cloudflare.com/map.js", "map code");
await put(`sala-v${version - 1}-shell`, BASE + "index.html", "old listing");
await put(`sala-v${version}-shell`, BASE + "index.html", "new listing");
await put("another-app-cache", BASE + "index.html", "another app");

async function install() {
  let installing;
  listeners.get("install")({ waitUntil(p) { installing = p; } });
  return installing;
}
await install();
let activation;
listeners.get("activate")({ waitUntil(p) { activation = p; } });
await activation;
networkCalls = 0;
assert.deepEqual(await caches.keys(), [`sala-v${version}-shell`, "another-app-cache",
  "sala-assets-v1-lib", "sala-assets-v1-tiles", "sala-assets-v1-posters"]);
assert.equal((await get(`sala-v${version}-shell`, BASE + "index.html")).body, "new listing");
assert.equal((await get("another-app-cache", BASE + "index.html")).body, "another app");
assert.equal((await get("sala-assets-v1-tiles", "https://tiles.openfreemap.org/new")).body, "new tile");
assert.equal(await get("sala-assets-v1-tiles", "https://tiles.openfreemap.org/old"), undefined);
assert.equal(await get("sala-assets-v1-tiles", "https://tiles.openfreemap.org/error"), undefined);
assert.equal((await get("sala-assets-v1-posters", BASE + "posters/1.jpg")).body, "poster pixels");
assert.equal(await get("sala-assets-v1-posters", BASE + "posters/2.jpg"), undefined);
assert.equal((await get("sala-assets-v1-lib", "https://cdnjs.cloudflare.com/map.js")).body, "map code");

async function offlineGet(url, mode) {
  let handled, lifetime;
  listeners.get("fetch")({ request: new Request(url, { mode }),
    respondWith(p) { handled = p; }, waitUntil(p) { lifetime = p; } });
  const result = await handled;
  if (lifetime) await lifetime;
  return result;
}
assert.equal((await offlineGet(BASE, "navigate")).body, "new listing");
assert.equal((await offlineGet("https://tiles.openfreemap.org/new")).body, "new tile");
assert.equal((await offlineGet(BASE + "posters/1.jpg")).body, "poster pixels");
assert.equal((await offlineGet("https://cdnjs.cloudflare.com/map.js")).body, "map code");
assert.equal(networkCalls, 2); // navigation and library background revalidation
const retained = await Promise.all(["sala-assets-v1-lib", "sala-assets-v1-tiles", "sala-assets-v1-posters"]
  .map(async name => [...(await caches.open(name)).entries.values()]));
const bodies = retained.flat().map(response => response.body);
const retainedBytes = bodies.reduce((sum, body) => sum + Buffer.byteLength(body), 0);
assert.equal(bodies.length, 3);
assert.equal(retainedBytes, 29);

// A second daily shell bump must leave the stable asset caches untouched.
await put(`sala-v${version + 1}-shell`, BASE + "index.html", "second listing");
loadWorker(version + 1);
await install();
let second;
listeners.get("activate")({ waitUntil(p) { second = p; } });
await second;
networkCalls = 0;
assert.equal(await get(`sala-v${version}-shell`, BASE + "index.html"), undefined);
assert.equal((await offlineGet(BASE, "navigate")).body, "second listing");
assert.equal((await offlineGet("https://tiles.openfreemap.org/new")).body, "new tile");
assert.equal((await offlineGet(BASE + "posters/1.jpg")).body, "poster pixels");
assert.equal((await offlineGet("https://cdnjs.cloudflare.com/map.js")).body, "map code");

// If storage runs out while copying, reject install before replacing the old worker.
await put(`sala-v${version + 1}-tiles`, "https://tiles.openfreemap.org/quota", "quota tile");
for (let i = 0; i < 105; i++)
  await put(`sala-v${version + 1}-lib`, `https://fonts.gstatic.com/font-${i}`, "font");
for (let i = 0; i < 305; i++)
  await put(`sala-v${version + 1}-posters`, BASE + `posters/film-${i}.jpg`, "poster");
await put(`sala-v${version + 2}-shell`, BASE + "index.html", "third listing");
const tileCache = await caches.open("sala-assets-v1-tiles");
const originalPut = tileCache.put;
tileCache.put = async () => { throw new Error("quota exceeded"); };
loadWorker(version + 2);
const skipsBeforeFailure = skipWaitingCalls;
await assert.rejects(install(), /quota exceeded/);
tileCache.put = originalPut;
assert.equal(skipWaitingCalls, skipsBeforeFailure);
assert((await caches.keys()).includes(`sala-v${version + 1}-tiles`));
assert((await caches.keys()).includes(`sala-v${version + 1}-shell`));
assert.equal((await get(`sala-v${version + 1}-tiles`, "https://tiles.openfreemap.org/quota")).body, "quota tile");

// A full cache must not turn a successful network asset into a synthetic 504.
tileCache.put = async () => { throw new Error("quota exceeded"); };
networkResult = new Response("live tile");
assert.equal((await offlineGet("https://tiles.openfreemap.org/live")).body, "live tile");
networkResult = null;
tileCache.put = originalPut;

// Retry after quota recovers: install migrates and trims, then activation removes old
// Sala caches.
await install();
let retry;
listeners.get("activate")({ waitUntil(p) { retry = p; } });
await retry;
assert.equal((await caches.open("sala-assets-v1-lib")).entries.size, 100);
assert.equal((await caches.open("sala-assets-v1-posters")).entries.size, 300);
assert.equal((await get("sala-assets-v1-posters", BASE + "posters/film-304.jpg")).body, "poster");
assert(!(await caches.keys()).includes(`sala-v${version + 1}-tiles`));
assert.equal((await offlineGet(BASE, "navigate")).body, "third listing");
console.log(`PASS: two upgrades retained ${bodies.length} reusable fixture assets (${retainedBytes} bytes), kept the newest shell and unrelated cache, skipped invalid entries, rejected a quota-blocked install, returned a live asset despite a full cache, then retried within 100 library and 300 poster entry caps`);
