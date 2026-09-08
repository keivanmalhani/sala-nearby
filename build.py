#!/usr/bin/env python3
"""Turn the published artifact into an installable PWA.

    /opt/homebrew/bin/python3 build.py <artifact.html>

Three things change and nothing else does. The design, the venue data, the showtimes and
every interaction are the artifact's, byte for byte.

1. THE 7.8 MB OF BAKED MAP TILES COME OUT. They were baked because a published artifact
   cannot fetch cross-origin -- its CSP blocks every image host. On our own domain there is
   no such rule, so the map goes back to being an ordinary tile layer and the page drops
   from 8,132,867 bytes to about 329,000. That is the single biggest reason it will
   feel like an app: it launches instantly instead of parsing eight megabytes of base64.

2. IT GETS A REAL HEAD. An artifact is wrapped in a skeleton whose head we cannot touch,
   so `apple-mobile-web-app-capable` could never be set -- which is exactly the tag iOS
   reads when you Add to Home Screen. Without it the icon opens in Safari with the address
   bar and the toolbar. With it, the thing opens full screen with no browser furniture at
   all, which is the whole of what "looks like an app" means on an iPhone.

3. IT GETS A SERVICE WORKER. The shell is cached on first load, so it opens with no signal
   at all, and map tiles are cached as he pans over them. Showtimes are a stamped snapshot
   either way, so nothing is lost by serving them from the cache.
"""
import re
import sys

SRC = sys.argv[1]
OUT = "/Users/keivanmalhani/dev/sala-nearby/docs/index.html"

s = open(SRC, encoding="utf-8").read()
body = s[s.find("<body>") + 6:].lstrip("\n")
body = body[:body.rfind("</body></html>")]

# The three head elements the artifact wrapper forced down into the body.
body = re.sub(r"<title>.*?</title>\s*", "", body, count=1)
body = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis[^>]*>\s*', "", body, count=1)
body = re.sub(r'<script src="https://cdnjs[^>]*></script>\s*', "", body, count=1)

# --- 1. the tiles ------------------------------------------------------------------
i = body.find("const TILES=")
assert i != -1, "TILES table not found"
j = body.find("\n", i)
tiles_bytes = j - i
body = body[:i] + body[j + 1:]

old_layer = re.search(
    r'  // The tiles are baked into the page.*?\.addTo\(map\);\n',
    body, re.S)
assert old_layer, "tile layer block not found"
new_layer = '''  // ESRI'S LIGHT GRAY CANVAS. The artifact baked 7.8 MB of base64 tiles into the page
  // because a published artifact's CSP blocks every image host; on our own domain the
  // layer can just be ordinary, and the service worker caches each tile the first time he
  // pans over it, so the map still works underground on Line 1 once he has seen an area.
  //
  // THREE FREE TILE HOSTS WERE TRIED AND TWO OF THEM ANSWER HTTP 200 WITH A REFUSAL
  // PAINTED INTO THE IMAGE. Same tile, same second:
  //
  //   Esri  Light Gray Canvas   200, 18 KB, a real map
  //   CARTO light_all           200, 24 KB, "API KEY REQUIRED" watermarked across it
  //   OpenStreetMap standard    200,  7 KB, "Access blocked -- App is not following the
  //                                          tile usage policy of OSM's volunteer servers"
  //
  // A status check cannot tell any of those apart. Only looking at the picture can, which
  // is why they were looked at.
  //
  // maxNativeZoom is 16 because 17 and up return a 2,521-byte tile reading "Map data not
  // yet available" -- identical byte-for-byte at 17, 18 and 19, which is the tell. Leaflet
  // upscales past it, which is what the artifact did with its baked tiles too.
  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/" +
              "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    maxNativeZoom: 16, maxZoom: 18, tileSize: 256,
    crossOrigin: true, keepBuffer: 4,
    attribution: "Esri, HERE, Garmin, OpenStreetMap contributors" }).addTo(map);
'''
body = body[:old_layer.start()] + new_layer + body[old_layer.end():]

# The artifact hardcoded "CARTO / OpenStreetMap" into the attribution control. We are not
# on CARTO any more, and crediting a source you do not use is worse than crediting none:
# the layer now carries its own correct attribution.
old_attr = 'map.attributionControl.setPrefix("").addAttribution("CARTO / OpenStreetMap");'
assert body.count(old_attr) == 1, "attribution line not found"
body = body.replace(old_attr, 'map.attributionControl.setPrefix("");')


# The dark-mode CSS filter is applied to the tile pane and still is, so a light basemap
# plus that existing filter keeps the artifact's palette in both themes.
assert "server.arcgisonline.com" in body

HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,maximum-scale=1">

<title>Sala Nearby</title>
<meta name="description" content="Every cinema within walking distance of Parque Mexico, with tonight's real showtimes.">

<!-- THE TAGS THAT MAKE IT AN APP AND NOT A PAGE. iOS reads these at the moment you tap
     Add to Home Screen. Without apple-mobile-web-app-capable the icon opens Safari with
     an address bar and a toolbar; with it there is no browser furniture at all. The
     status-bar style has to be black-translucent for the app to draw under the notch,
     which is what env(safe-area-inset-top) in the stylesheet is already compensating
     for -- the two only make sense together. -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Sala">
<meta name="format-detection" content="telephone=no">

<!-- Two, because the browser chrome is painted before any CSS runs and a single colour
     would flash the wrong ground on launch in one of the themes. -->
<meta name="theme-color" content="#FAF6F0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#14100E" media="(prefers-color-scheme: dark)">

<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/icon-180.png">
<link rel="icon" href="icons/icon-192.png" sizes="192x192">
<link rel="icon" href="favicon.svg" type="image/svg+xml">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>

<style>
:root{color-scheme:light dark}
html{-webkit-text-size-adjust:100%}
body{margin:0;padding:0}
img{max-width:100%}
[hidden]:not([hidden=until-found]){display:none!important}

/* THE LAUNCH SCREEN. iOS shows a white rectangle between the tap and the first paint
   unless you ship a splash image per device size, which is a dozen PNGs and a dozen
   media queries. This is the cheap version that covers every device: paint the app's
   own ground colour immediately, with the wordmark, and take it away on load. It is
   inside the document so it costs no extra request. */
#boot{position:fixed;inset:0;z-index:9999;display:grid;place-items:center;
      background:#FAF6F0;color:#191310;transition:opacity .28s ease}
#boot.gone{opacity:0;pointer-events:none}
#boot .w{font:800 30px/1 "Bricolage Grotesque",system-ui,-apple-system,sans-serif;
         letter-spacing:-.03em}
#boot .t{margin-top:9px;font:500 10px/1 ui-monospace,"IBM Plex Mono",Menlo,monospace;
         letter-spacing:.22em;text-transform:uppercase;color:#8B7C72}
@media (prefers-color-scheme:dark){#boot{background:#14100E;color:#F4EDE5}
  #boot .t{color:#8A7C72}}
</style>
</head>
<body>
<div id="boot"><div><div class="w">Sala Nearby</div><div class="t">Roma &middot; Condesa</div></div></div>
'''

TAIL = '''
<script>
// The launch screen goes as soon as the map and the lists exist, not on `load` -- `load`
// waits for every font and tile and would sit there for a second on a cold cellular
// connection. requestAnimationFrame twice guarantees one painted frame first, so the
// fade never reveals a half-built page.
requestAnimationFrame(function () { requestAnimationFrame(function () {
  var b = document.getElementById("boot");
  if (b) { b.classList.add("gone"); setTimeout(function () { b.remove(); }, 320); }
}); });

// Offline. Registered after load so it never competes with the first paint.
if ("serviceWorker" in navigator) {
  addEventListener("load", function () {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  });
}

// Add to Home Screen, offered once, only where the browser supports the prompt -- which
// is Android and desktop Chrome. iOS has no such API, so iOS gets the instructions
// instead, and only in Safari, and only when not already installed.
var deferred = null;
addEventListener("beforeinstallprompt", function (e) {
  e.preventDefault(); deferred = e; showInstall(function () {
    deferred.prompt(); deferred = null;
  });
});
(function () {
  var standalone = matchMedia("(display-mode: standalone)").matches
                || navigator.standalone === true;
  if (standalone || localStorage.getItem("sala.install") === "done") return;
  var ios = /iPad|iPhone|iPod/.test(navigator.userAgent)
         || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var safari = ios && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(navigator.userAgent);
  if (safari) setTimeout(function () { showInstall(null); }, 2600);
})();
function showInstall(onTap) {
  var d = document.createElement("div");
  d.setAttribute("role", "dialog");
  d.style.cssText = "position:fixed;left:12px;right:12px;bottom:calc(env(safe-area-inset-bottom,0px) + 70px);"
    + "z-index:1200;background:var(--surface);border:1px solid var(--line);border-radius:16px;"
    + "padding:14px 16px;box-shadow:0 8px 34px rgba(0,0,0,.28);display:grid;gap:9px;"
    + "font-family:'Bricolage Grotesque',system-ui,sans-serif;max-width:520px;margin:0 auto";
  d.innerHTML = '<div style="font-weight:700;font-size:15.5px;letter-spacing:-.01em">Put it on your home screen</div>'
    + '<div style="font-size:13.5px;line-height:1.45;color:var(--ink-2)">'
    + (onTap ? 'Installs like an app. No store, nothing to pay.'
             : 'Tap Share, then <b>Add to Home Screen</b>. It opens full screen with no browser bars, and works with no signal.')
    + '</div><div style="display:flex;gap:8px;margin-top:2px">'
    + (onTap ? '<button id="sala-ok" style="flex:1;min-height:44px;border-radius:11px;background:var(--lamp);color:var(--lamp-ink);font-weight:700;font-size:14px">Install</button>' : '')
    + '<button id="sala-no" style="flex:' + (onTap ? '0 0 34%' : '1') + ';min-height:44px;border-radius:11px;'
    + 'border:1px solid var(--line);background:var(--sunk);font-weight:600;font-size:14px">'
    + (onTap ? 'Not now' : 'Got it') + '</button></div>';
  document.body.appendChild(d);
  var close = function () { localStorage.setItem("sala.install", "done"); d.remove(); };
  d.querySelector("#sala-no").onclick = close;
  if (onTap) d.querySelector("#sala-ok").onclick = function () { close(); onTap(); };
}
</script>
</body></html>
'''

open(OUT, "w", encoding="utf-8").write(HEAD + body + TAIL)
print("tiles removed: %s bytes" % format(tiles_bytes, ","))
print("wrote %s: %s bytes" % (OUT, format(len(HEAD + body + TAIL), ",")))
