#!/usr/bin/env python3
"""Replace Leaflet + Esri raster tiles with MapLibre GL + OpenFreeMap vector tiles.

    /opt/homebrew/bin/python3 swap-map.py

WHY. He sent a photograph of the map zoomed in and said "it's blurry af when I zoom in".
It was, and the reason was already written down in the page: Esri's Light Gray Canvas has
no tile above zoom 16 -- 17, 18 and 19 all return the same 2,521-byte "Map data not yet
available" image -- so Leaflet was stretching a zoom-16 picture across a zoom-18 view.
Stretching pixels is what blurry is.

WHY VECTOR RATHER THAN A DIFFERENT RASTER HOST. A raster host only moves the ceiling; the
blur comes back one zoom level higher. Vector tiles carry geometry rather than pixels, so
the renderer redraws roads and labels at whatever scale the screen is at and they are sharp
at every zoom, including past the source's own maxzoom of 14.

THE HOST, and it was checked rather than assumed, because this app has been bitten twice by
a tile server answering HTTP 200 with a refusal painted into the picture:

    OpenFreeMap    vector, no key       z14 tile, 333 KB of real protobuf     USED
    CARTO dark     raster @2x           200, and "API KEY REQUIRED" across it  refused
    OpenStreetMap  raster               200, a real map, but their usage policy
                                        forbids exactly this kind of app        refused
    Esri gray      raster               200, 2,521 bytes, "not yet available"   the bug

OpenFreeMap is free with no key and no request limit, run on OpenStreetMap data. Its
attribution is required and is set below.

WHAT THIS DOES NOT DO. It does not touch the venue data, the showtimes, the guide, the
sheet, or any of the design outside the map pane. Every anchor it edits is asserted first,
so if the page has moved underneath it the script stops instead of writing a broken file.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

s = open(PAGE, encoding="utf-8").read()
orig = s


def swap(before, after, why):
    global s
    if before not in s:
        sys.exit("ANCHOR GONE (%s):\n  %s" % (why, before[:120]))
    if s.count(before) != 1:
        sys.exit("ANCHOR NOT UNIQUE (%s): %d matches" % (why, s.count(before)))
    s = s.replace(before, after, 1)


# ---------------------------------------------------------------- 1. the library
swap('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>',
     '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.css">\n'
     '<script src="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.js"></script>',
     "the map library")

# ---------------------------------------------------------------- 2. Leaflet's own CSS
i = s.find(".leaflet-pane,.leaflet-tile,")
j = s.find("/* ============================================================\n   SALA NEARBY")
if i < 0 or j < 0 or j < i:
    sys.exit("could not find the inlined Leaflet stylesheet to remove")
s = s[:i] + s[j:]

# ---------------------------------------------------------------- 3. the two themed rules
swap(""".leaflet-tile-pane{filter:var(--tilefilter)}
.leaflet-control-attribution{background:color-mix(in srgb,var(--surface) 82%,transparent);color:var(--ink-3);font-size:9.5px;font-family:"IBM Plex Mono",monospace}
.leaflet-control-attribution a{color:var(--ink-2)}""",
     """/* MapLibre draws its own canvas, so the dark-mode tile filter that used to invert a
   light raster tile is gone -- the dark map is a real dark style now, not a photographic
   negative of a light one, which is why the labels are legible on it. */
.maplibregl-canvas{outline:none}
.maplibregl-ctrl-attrib{background:color-mix(in srgb,var(--surface) 82%,transparent)!important;color:var(--ink-3);font-size:9.5px;font-family:"IBM Plex Mono",monospace;padding:1px 6px;border-radius:6px 0 0 0}
.maplibregl-ctrl-attrib a{color:var(--ink-2);text-decoration:none}
.maplibregl-ctrl-bottom-right{z-index:400}
/* The venue dots. Real DOM elements rather than canvas circles, so they keep the tap
   target and the focus ring the rest of the app already has. */
.vdot{width:var(--s);height:var(--s);border-radius:50%;border:2px solid var(--dc);
  background:color-mix(in srgb,var(--dc) 55%,transparent);cursor:pointer;
  box-shadow:0 1px 4px rgba(0,0,0,.35)}
.vdot.hollow{background:color-mix(in srgb,var(--dc) 12%,transparent);border-width:1.5px}
.vdot:focus-visible{outline:2px solid var(--lamp);outline-offset:2px}
.homedot{width:13px;height:13px;border:3px solid var(--lamp);border-radius:50%;background:var(--surface)}
.homelbl{font:600 10px/1 "IBM Plex Mono",monospace;color:var(--ink-2);
  background:color-mix(in srgb,var(--surface) 88%,transparent);padding:3px 6px;border-radius:5px;
  transform:translateY(-26px);white-space:nowrap}""",
     "the themed map rules")

# ---------------------------------------------------------------- 4. initMap
start = s.find("function initMap() {")
end = s.find("/* ===================== GUIDE ===================== */")
if start < 0 or end < 0 or end < start:
    sys.exit("could not find initMap() to replace")

NEW_MAP = r'''function initMap() {
  if (map) return;

  // OPENFREEMAP, VECTOR, NO KEY. See swap-map.py for the three hosts that were tried and
  // why two of them are refusals wearing an HTTP 200. Two styles because the app has two
  // themes and a dark map should be a dark map rather than an inverted light one.
  const styleFor = () => document.documentElement.getAttribute("data-theme") === "light"
      || (!document.documentElement.getAttribute("data-theme")
          && !window.matchMedia("(prefers-color-scheme: dark)").matches)
    ? "https://tiles.openfreemap.org/styles/bright"
    : "https://tiles.openfreemap.org/styles/dark";

  map = new maplibregl.Map({
    container: "map",
    style: styleFor(),
    center: [HOME.lng, HOME.lat],           // MapLibre takes lng first, Leaflet took lat
    zoom: 13.1, minZoom: 11.5, maxZoom: 18.5,
    maxBounds: [[-99.34, 19.26], [-99.01, 19.56]],
    attributionControl: false,
    dragRotate: false, pitchWithRotate: false, touchPitch: false,
    // The whole point of this change: no upscaled raster anywhere.
    fadeDuration: 120,
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.AttributionControl({
    compact: false,
    customAttribution: "OpenFreeMap, OpenMapTiles, OpenStreetMap contributors",
  }), "bottom-right");

  // A circle of a real radius on the ground, as a polygon, because a styled circle layer
  // is sized in screen pixels and would stay the same size as you zoom -- which is the
  // opposite of what a "2 km from here" ring means.
  const ringOf = (m, steps) => {
    const pts = [], latR = m / 111320,
          lngR = m / (111320 * Math.cos(HOME.lat * Math.PI / 180));
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * 2 * Math.PI;
      pts.push([HOME.lng + lngR * Math.cos(t), HOME.lat + latR * Math.sin(t)]);
    }
    return pts;
  };

  map.on("load", () => {
    const lamp = getComputedStyle(document.documentElement).getPropertyValue("--lamp").trim();
    map.addSource("rings", { type: "geojson", data: { type: "FeatureCollection",
      features: [1000, 2000, 3000, 5000].map(r => ({ type: "Feature", properties: { r },
        geometry: { type: "LineString", coordinates: ringOf(r, 96) } })) } });
    map.addLayer({ id: "rings", type: "line", source: "rings",
      paint: { "line-color": lamp, "line-width": 1.1, "line-opacity": .40,
               "line-dasharray": [2, 6] } });
    mapReady = true;
    placeMarkers();
  });

  // The theme can change under a running map -- he flips it with the button in the header,
  // and iOS flips it at sunset on its own. setStyle drops every source and layer with it,
  // so the rings and the dots have to go back on after the new style loads.
  const themeWatch = () => {
    if (!map) return;
    map.setStyle(styleFor());
    map.once("styledata", () => {
      if (!map.getSource("rings")) {
        const lamp = getComputedStyle(document.documentElement).getPropertyValue("--lamp").trim();
        map.addSource("rings", { type: "geojson", data: { type: "FeatureCollection",
          features: [1000, 2000, 3000, 5000].map(r => ({ type: "Feature", properties: { r },
            geometry: { type: "LineString", coordinates: ringOf(r, 96) } })) } });
        map.addLayer({ id: "rings", type: "line", source: "rings",
          paint: { "line-color": lamp, "line-width": 1.1, "line-opacity": .40,
                   "line-dasharray": [2, 6] } });
      }
    });
  };
  window.addEventListener("sala:theme", themeWatch);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeWatch);

  $("keypanel").innerHTML = [
    ["var(--c-big)", "Large format: IMAX, CinemeXtremo, 4DX, ScreenX"],
    ["var(--c-lux)", "Recliners and waiter service: Platino, VIP"],
    ["var(--c-std)", "Ordinary multiplex"],
    ["var(--c-art)", "Independent, art house, free cineclub"],
  ].map(([c, t]) => `<div class="r"><i style="background:${c}"></i>${esc(t)}</div>`).join("") +
    `<div class="note">A hollow grey dot has live showtimes but was not audited by hand &mdash;
     it sits outside the original five-kilometre study.</div>`;
}

// Markers are DOM elements, so the dots keep a real tap target and a focus ring. 74 of them
// is well inside what this costs nothing for; a canvas layer would be faster and would lose
// the keyboard path.
let mapReady = false, markersPlaced = false;
function placeMarkers() {
  if (markersPlaced || !map) return;
  markersPlaced = true;

  const home = document.createElement("div");
  home.className = "homedot";
  new maplibregl.Marker({ element: home }).setLngLat([HOME.lng, HOME.lat]).addTo(map);
  const lbl = document.createElement("div");
  lbl.className = "homelbl";
  lbl.textContent = "Parque Mexico";
  new maplibregl.Marker({ element: lbl, anchor: "bottom" })
    .setLngLat([HOME.lng, HOME.lat]).addTo(map);

  V.forEach((v, i) => {
    const el = document.createElement("button");
    el.className = "vdot";
    el.style.setProperty("--dc", CAT(v));
    el.style.setProperty("--s", (v.dim ? 11 : 15) + "px");
    el.setAttribute("aria-label", v.name);
    el.addEventListener("click", (e) => { e.stopPropagation(); venueSheet(i); });
    new maplibregl.Marker({ element: el }).setLngLat([v.lng, v.lat]).addTo(map);
  });

  SHOWS.cin.filter(c => c.v == null).forEach(c => {
    const el = document.createElement("button");
    el.className = "vdot hollow";
    el.style.setProperty("--dc", "var(--ink-3)");
    el.style.setProperty("--s", "10px");
    el.setAttribute("aria-label", c.n || "Cinema");
    el.addEventListener("click", (e) => { e.stopPropagation(); cinemaSheet(c.id); });
    new maplibregl.Marker({ element: el }).setLngLat([c.lng, c.lat]).addTo(map);
  });
}

'''

s = s[:start] + NEW_MAP + s[end:]

# ---------------------------------------------------------------- 5. the map controls
swap('  if (t === "map") { initMap(); setTimeout(() => map && map.invalidateSize(), 60); }',
     '  if (t === "map") { initMap(); setTimeout(() => map && map.resize(), 60); }',
     "the resize on tab change")

swap('  if (e.target.closest("#zin")) return map && map.zoomIn();\n'
     '  if (e.target.closest("#zout")) return map && map.zoomOut();\n'
     '  if (e.target.closest("#recenter")) return map && map.setView([HOME.lat, HOME.lng], 14);',
     '  if (e.target.closest("#zin")) return map && map.zoomIn();\n'
     '  if (e.target.closest("#zout")) return map && map.zoomOut();\n'
     '  if (e.target.closest("#recenter"))\n'
     '    return map && map.easeTo({ center: [HOME.lng, HOME.lat], zoom: 13.1, duration: 450 });',
     "the zoom and recentre buttons")

if s == orig:
    sys.exit("nothing changed, which cannot be right")
open(PAGE, "w", encoding="utf-8").write(s)
print("swapped Leaflet for MapLibre; page is now %d bytes (was %d)" % (len(s), len(orig)))
