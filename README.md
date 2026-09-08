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

One self-contained HTML file, no framework, no build step for the page itself. Leaflet for
the map, Esri's Light Gray Canvas for the tiles, a service worker for offline.

`build.py` turns the original published page into this one. It does three things:

1. **Strips 7.8 MB of base64 map tiles.** They had to be baked in because the original was
   published somewhere whose content policy blocks every image host. On its own domain the
   map layer is ordinary, and the page drops from 8.1 MB to 329 KB, which is most of why
   it launches instantly.
2. **Gives it a real `<head>`** — the web app manifest, `apple-mobile-web-app-capable`,
   theme colours, icons. Those tags are what iOS reads when you Add to Home Screen; without
   them the icon just opens Safari.
3. **Adds the service worker**, which caches the shell on first load and each map tile the
   first time you pan over it.

### On picking a tile host

Three free ones were tried. **All three answered HTTP 200** and two of them served a
refusal painted into the image:

| Host | Status | What the picture actually was |
|---|---|---|
| Esri Light Gray Canvas | 200, 18 KB | a real map |
| CARTO `light_all` | 200, 24 KB | "API KEY REQUIRED" watermarked across it |
| OpenStreetMap standard | 200, 7 KB | "Access blocked — App is not following the tile usage policy" |

No status check can tell those apart. Zoom 17 and above from Esri returns a 2,521-byte
tile reading "Map data not yet available", identical byte-for-byte at 17, 18 and 19, so
`maxNativeZoom` is 16 and Leaflet upscales past it.

## Showtimes are a snapshot

They were pulled from Cinemex's public API and are stamped in the page. Re-running the
fetch and rebuilding refreshes them. Every showtime chip links to Cinemex, so the price and
the seat map are always live even when this listing is a few days old.

## Attribution

Map tiles by Esri — Esri, HERE, Garmin, and OpenStreetMap contributors. Showtimes from
Cinemex. Venue research is original.
