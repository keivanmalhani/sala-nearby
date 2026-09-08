# Sala Nearby

Every cinema within walking distance of Parque Mexico, with real showtimes, as an app you
install from the browser rather than from a store.

**https://keivanmalhani.github.io/sala-nearby/**

Open it on a phone, tap Share, then Add to Home Screen. It gets its own icon, opens full
screen with no browser bars, and works with no signal after the first launch.

## What it does

- **Showtimes** for 32 Cinemex screens within 9 km, filterable by day, by "starting soon",
  by subtitled-not-dubbed, and by IMAX. Every time links straight to Cinemex checkout,
  which is always current even when the listing here is not.
- **Map** of 42 venues, coloured by what kind of room they are, with walking distance from
  wherever you are. Tapping one opens its full write-up and a walking-directions link.
- **Films** index, and a **Guide** with the venue audit: screen sizes, projection, sound,
  and which claims are verified rather than assumed.

## How it is built

One self-contained HTML file, no framework, no build step for the page itself. MapLibre GL
for the map, OpenFreeMap's vector tiles, a service worker for offline.

`build.py` turns the original published page into this one. It does three things:

1. **Strips 7.8 MB of base64 map tiles.** They had to be baked in because the original was
   published somewhere whose content policy blocks every image host. On its own domain the
   map layer is ordinary, and the page drops from 8.1 MB to a few hundred KB, which is most of why
   it launches instantly.
2. **Gives it a real `<head>`** — the web app manifest, `apple-mobile-web-app-capable`,
   theme colours, icons. Those tags are what iOS reads when you Add to Home Screen; without
   them the icon just opens Safari.
3. **Adds the service worker**, which caches the shell on first load and each map tile the
   first time you pan over it.

### On picking a tile host

The map was Leaflet over Esri's Light Gray Canvas raster tiles until 8 September, when he
photographed it zoomed in and said it was blurry. It was. **Esri has no tile above zoom
16** — 17, 18 and 19 all return an identical 2,521-byte image reading "Map data not yet
available" — so Leaflet was stretching a zoom-16 picture across a zoom-18 view. Stretching
pixels is what blurry is.

A different raster host only moves the ceiling up a level. Vector tiles carry geometry
rather than pixels, so the renderer redraws roads and labels at whatever scale the screen
is at, and it is sharp at every zoom. That is why the map is now MapLibre GL over
OpenFreeMap — free, no key, no request limit, OpenStreetMap data.

Four hosts were looked at, and **three of the four answered HTTP 200**:

| Host | What came back | Verdict |
|---|---|---|
| OpenFreeMap vector | 333 KB of real protobuf at z14 | in use |
| CARTO `light_all` raster | 200, 24 KB, "API KEY REQUIRED" watermarked across it | refused |
| OpenStreetMap raster | 200, 7 KB, "Access blocked — not following the usage policy" | refused |
| Esri Light Gray Canvas | 200, 2,521 bytes, "Map data not yet available" above z16 | the bug |

**No status check separates any of those.** Only opening the picture does, which is why
they were opened. If the tile host is ever swapped again, look at a tile.

## Showtimes are a snapshot

They were pulled from Cinemex's public API and are stamped in the page. Every showtime chip
links to Cinemex checkout, so the price and the seat map are always live even when this
listing is a few days old.

To refresh them:

    /opt/homebrew/bin/python3 refresh-showtimes.py --dry-run   # fetch and check only
    /opt/homebrew/bin/python3 refresh-showtimes.py             # write into the page
    /opt/homebrew/bin/python3 refresh-posters.py               # posters for any new films
    # then bump the cache name in docs/sw.js, or an installed phone keeps the old build

The refresh refuses to write a payload that is materially worse than the published one --
fewer cinemas, a big drop in showtimes, fewer films, or a first day that is not today. An
empty answer from an API is a perfectly successful set of HTTP requests, and a page that
quietly lists nothing on Thursday looks exactly like a page that is fine.

**Cinema weeks in Mexico start on Thursday**, so a pull made on a Tuesday has the current
week in full and only advance sales past Wednesday. Refreshing on a Thursday or later gets
the most out of it. The 8 September pull went from 5,445 showings to 7,853 purely because
Thursday-to-Sunday had been published in between; Tuesday and Wednesday barely moved.

`CINEMEX-API.md` has the endpoints, the version-in-the-path trap, and why this runs at
build time rather than in the page.

## Attribution

Map tiles by OpenFreeMap, from OpenMapTiles and OpenStreetMap contributors. Showtimes and
posters from Cinemex's public web API. The venue audit — screen sizes, projection, sound,
which claims are verified rather than assumed — is original research.
