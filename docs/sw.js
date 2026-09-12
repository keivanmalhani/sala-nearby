/* Sala Nearby, offline.
 *
 * The point of this file is that the app opens on the Metro with no signal. Three caches,
 * because the three kinds of thing here go stale on completely different clocks:
 *
 *   shell    the page, the icons, the manifest. Changes when I republish.
 *   lib      MapLibre and the Google fonts. Immutable, versioned in their own URLs.
 *   tiles    map data. Never changes, but there is an unbounded number of it.
 *   posters  one JPEG per film. Changes only when the film list does.
 *
 * The showtimes are baked into the page rather than fetched, so they ride along in the
 * shell and there is nothing separate to cache. They are a stamped snapshot either way;
 * every time chip links to Cinemex checkout, which is always live.
 */
// BUMPED ON EVERY PUBLISH, and it has to be. The activate handler deletes any cache whose
// name is not in the current set, so changing this is what makes a new version actually
// reach a phone that already has the old one. Without a bump the navigation handler answers
// from the cached shell first and he sees the previous build for one more launch -- which
// is exactly what happened while this change was being tested: the page on screen was two
// edits behind the file on disk.
const V = "sala-v38";
const SHELL = V + "-shell";
const LIB = V + "-lib";
const TILES = V + "-tiles";
const POSTERS = V + "-posters";
const TILE_MAX = 700;          // roughly all of Roma, Condesa, Juarez and Doctores at z16

const PRECACHE = [
  "./",
  "./index.html",
  "./places.json",
  "./manifest.webmanifest",
  "./favicon.svg",
  "./icons/icon-180.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

// THE THREE THINGS THE PAGE LOADS FROM SOMEBODY ELSE, warmed at install so that ONE
// launch with a signal is enough -- which is what the README promises and what was not
// true. They cannot be picked up by the fetch handler on a first visit: a <script> and a
// <link> in the head are requested while this worker is still installing and has not
// claimed the page, so the runtime branch below only ever caught them on the SECOND
// launch. Until 2026-09-09 it never caught the script at all, because a plain
// cross-origin tag is a no-cors request and `fetch` returns an opaque response that
// `r.ok` correctly refuses; index.html now asks for all three with crossorigin.
//
// Measured before this existed: the lib cache held five font FILES and neither
// maplibre-gl.min.js nor the stylesheet that names the fonts. The map still drew, out of
// the browser's own HTTP cache, which is evictable and is not a promise this app can make.
//
// KEEP IN STEP WITH index.html. test-offline-lib.py fails if any of these three URLs is
// not in the page verbatim, because a version bump in the page and not here would leave
// the app caching a library it no longer loads.
const LIB_WARM = [
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.css",
  "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap",
];

self.addEventListener("install", (e) => {
  // addAll is atomic: one 404 and NOTHING is cached, which is the honest behaviour --
  // a half-populated shell cache is an app that opens to a broken page offline.
  //
  // `cache: "reload"` IS LOAD-BEARING AND BUMPING THE VERSION ABOVE IS NOT ENOUGH WITHOUT
  // IT. GitHub Pages serves index.html with `cache-control: max-age=600`, so for ten
  // minutes after a publish the browser's own HTTP cache still holds the old file --
  // and a plain addAll is served from it. The result is the worst of both: a brand new
  // cache name, correctly installed, correctly claiming clients, holding the previous
  // build. Caught 2026-09-08 with `sala-v10-shell` serving a page stamped 10:04 with no
  // search box in it, twenty minutes after the search had gone live. "reload" makes each
  // of these go to the network.
  e.waitUntil(
    caches.open(SHELL)
      .then((c) => c.addAll(PRECACHE.map((u) => new Request(u, { cache: "reload" }))))
      // The library warm is DELIBERATELY NOT PART OF THAT addAll. addAll is atomic on
      // purpose so a half-populated shell is impossible, and that is the right shape for
      // our own files -- but it would also mean a hiccup at cdnjs stops the app from
      // caching its own page. So each of these is fetched on its own and a failure is
      // dropped: the worst case is the map needing a signal once more, which is where it
      // already was.
      .then(() => caches.open(LIB).then((c) => Promise.all(
        LIB_WARM.map((u) => fetch(u, { mode: "cors" })
          .then((r) => (r && r.ok ? c.put(u, r) : null))
          .catch(() => null))
      )))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keep = new Set([SHELL, LIB, TILES, POSTERS]);
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
  if (url.hostname === "tiles.openfreemap.org") {
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

  // THE POSTERS. Same origin, but they must be cached deliberately rather than falling
  // through to the read-only branch at the bottom -- that one answers from the cache and
  // otherwise goes to the network, so a poster never entered the cache at all and every
  // one of them was a broken image with no signal. Cache-first: a poster for a given film
  // id does not change, and refresh-posters.py writes a new file when a film does.
  if (url.origin === self.location.origin && url.pathname.indexOf("/posters/") >= 0) {
    e.respondWith((async () => {
      const c = await caches.open(POSTERS);
      const hit = await c.match(req);
      if (hit) return hit;
      try {
        const r = await fetch(req);
        if (r && r.ok) await c.put(req, r.clone());
        return r;
      } catch (_) { return new Response("", { status: 504 }); }
    })());
    return;
  }

  // MAPLIBRE AND THE FONTS. Both are versioned in their own URLs, so cache-first with a
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

  // THE CINEMA DETAIL. It needs its own branch for the same reason the posters do: the
  // read-only branch below answers from the cache and otherwise goes to the network, and
  // never PUTS anything, so detail.json would be re-fetched on every launch and would be
  // missing entirely with no signal -- prices, seat counts and ratings all quietly gone
  // underground, which is where he will be reading this.
  //
  // Cache-first with a background refresh rather than never-revalidated: unlike a poster,
  // its contents change when the build runs, and the copy on screen being one launch
  // behind is the right trade for a sheet that opens instantly.
  if (url.origin === self.location.origin && /\/detail\.json$/.test(url.pathname)) {
    e.respondWith((async () => {
      const c = await caches.open(SHELL);
      const hit = await c.match(req);
      const fresh = fetch(req).then((r) => {
        if (r && r.ok) c.put(req, r.clone());
        return r;
      }).catch(() => null);
      return hit || (await fresh) || new Response("null",
        { headers: { "Content-Type": "application/json" } });
    })());
    return;
  }

  // EVERYTHING ELSE ON OUR OWN ORIGIN: the icons and the manifest.
  if (url.origin === self.location.origin) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
  }
});
