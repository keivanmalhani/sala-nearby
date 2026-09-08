/* Sala Nearby, offline.
 *
 * The point of this file is that the app opens on the Metro with no signal. Three caches,
 * because the three kinds of thing here go stale on completely different clocks:
 *
 *   shell    the page, the icons, the manifest. Changes when I republish.
 *   lib      Leaflet and the Google fonts. Immutable, versioned in their own URLs.
 *   tiles    map imagery. Never changes, but there is an unbounded number of it.
 *
 * The showtimes are baked into the page rather than fetched, so they ride along in the
 * shell and there is nothing separate to cache. They are a stamped snapshot either way;
 * every time chip links to Cinemex checkout, which is always live.
 */
const V = "sala-v2";
const SHELL = V + "-shell";
const LIB = V + "-lib";
const TILES = V + "-tiles";
const TILE_MAX = 700;          // roughly all of Roma, Condesa, Juarez and Doctores at z16

const PRECACHE = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./favicon.svg",
  "./icons/icon-180.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (e) => {
  // addAll is atomic: one 404 and NOTHING is cached, which is the honest behaviour --
  // a half-populated shell cache is an app that opens to a broken page offline.
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keep = new Set([SHELL, LIB, TILES]);
    for (const k of await caches.keys()) if (!keep.has(k)) await caches.delete(k);
    await self.clients.claim();
  })());
});

/** Keep a cache from growing without limit. Oldest-inserted first, which for map tiles is
 *  a decent proxy for least-recently-looked-at. */
async function trim(name, max) {
  const c = await caches.open(name);
  const keys = await c.keys();
  for (let i = 0; i < keys.length - max; i++) await c.delete(keys[i]);
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // NAVIGATION. Always answer from the cached shell first so a cold launch with no signal
  // is instant and works, then refresh it in the background for next time. A
  // network-first navigation would hang for the whole timeout underground, which is the
  // exact moment he is most likely to be opening this.
  if (req.mode === "navigate") {
    e.respondWith((async () => {
      const cached = await caches.match("./index.html");
      const fresh = fetch(req).then((r) => {
        if (r && r.ok) caches.open(SHELL).then((c) => c.put("./index.html", r.clone()));
        return r;
      }).catch(() => null);
      return cached || (await fresh) || new Response(
        "<h1>Offline</h1><p>Open Sala once with a signal and it will work without one after that.</p>",
        { headers: { "Content-Type": "text/html" } });
    })());
    return;
  }

  // MAP TILES. Cache-first and never revalidated: a tile at a given z/x/y is the same
  // picture forever, so a conditional request would be a round trip to be told nothing.
  if (url.hostname === "server.arcgisonline.com") {
    e.respondWith((async () => {
      const c = await caches.open(TILES);
      const hit = await c.match(req);
      if (hit) return hit;
      try {
        const r = await fetch(req);
        // Only real responses. An opaque one has status 0 and would be indistinguishable
        // from a cached error, which is how a permanently grey map happens.
        if (r && r.ok) { await c.put(req, r.clone()); trim(TILES, TILE_MAX); }
        return r;
      } catch (_) {
        return new Response("", { status: 504 });
      }
    })());
    return;
  }

  // LEAFLET AND THE FONTS. Both are versioned in their own URLs, so cache-first with a
  // quiet background refresh is safe and makes the second launch instant.
  if (url.hostname === "cdnjs.cloudflare.com"
      || url.hostname === "fonts.googleapis.com"
      || url.hostname === "fonts.gstatic.com") {
    e.respondWith((async () => {
      const c = await caches.open(LIB);
      const hit = await c.match(req);
      const fresh = fetch(req).then((r) => {
        if (r && r.ok) c.put(req, r.clone());
        return r;
      }).catch(() => null);
      return hit || (await fresh) || new Response("", { status: 504 });
    })());
    return;
  }

  // EVERYTHING ELSE ON OUR OWN ORIGIN: the icons and the manifest.
  if (url.origin === self.location.origin) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
  }
});
