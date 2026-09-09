#!/usr/bin/env python3
"""The map works with no signal only because Chrome still has MapLibre. Fix that.

    /opt/homebrew/bin/python3 offline-lib.py

FOUND BY WATCHING IT, not by reading the worker. Load the app once with a signal, visit
the three tabs, clear the browser's own HTTP cache, cut the network and reload. Everything
comes back -- 35 cinemas, 1,318 showings, 454 prices, the sheets, the map. Then look at
what is actually in the service worker's caches:

    sala-v23-shell    8
    sala-v23-posters  37
    sala-v23-tiles    11
    sala-v23-lib      5   <- five font FILES from fonts.gstatic.com, and nothing else

`typeof maplibregl` is "object" and the map draws, and maplibre-gl.min.js is in no cache
this app controls. It came from the browser's own HTTP cache, which is evictable, is
cleared by "clear website data", and is not the thing the README is promising when it says
the app works with no signal after the first launch.

WHY THE WORKER NEVER STORED IT, and it is a one-word bug. A plain `<script src>` to
another origin is a **no-cors** request, so `fetch(req)` inside the worker resolves to an
OPAQUE response: `status` 0 and `ok` false. Every branch in sw.js guards with
`if (r && r.ok)` -- correctly, and the tiles branch says so in a comment, because caching
an opaque response is caching something you cannot tell from an error. So the guard that
protects the tiles quietly refuses the one script the map cannot start without.

The font FILES are cached because `@font-face` fetches them in CORS mode by spec. The
Google Fonts STYLESHEET is a plain `<link>` and is opaque for the same reason, which is why
five font files are cached and the rule that names them is not.

THE FIX IS `crossorigin="anonymous"` ON THE THREE CROSS-ORIGIN TAGS. Checked before
changing anything rather than assumed -- both hosts already allow it:

    cdnjs.cloudflare.com/.../maplibre-gl.min.js   access-control-allow-origin: *
    fonts.googleapis.com/css2?...                 access-control-allow-origin: *

With the attribute the browser asks in CORS mode, the worker gets a real response with a
real status, and `if (r && r.ok)` lets it through.

sw.js does the other half: it warms those three URLs during install. Without that the
first launch still misses them, because a `<script>` in the head is fetched while the
worker is still installing and has not claimed the page yet -- so the runtime branch only
catches them on the SECOND launch, and "after the first launch" is what the README says.
The warm is deliberately not part of `addAll(PRECACHE)`: that call is atomic on purpose so
a half-cached shell is impossible, and a CDN hiccup must not be able to stop the app
installing offline support for its own page.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

s = open(PAGE, encoding="utf-8").read()


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:120]))
    s = s.replace(before, after, 1)


# Each of the three is a separate anchor rather than one regex, so a change to any of them
# fails loudly here instead of silently leaving one uncached.
swap('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">',
     '<!-- crossorigin ON ALL THREE, and it is what makes the app work with no signal.\n'
     '     A plain cross-origin <link> or <script> is a no-cors request, so the service\n'
     '     worker sees an OPAQUE response -- status 0, ok false -- and every branch in\n'
     '     sw.js correctly refuses to cache one. The result was that the map ran offline\n'
     '     purely on the browser\'s own HTTP cache, which is evictable. Both hosts send\n'
     '     access-control-allow-origin: *, checked, so asking in CORS mode costs nothing\n'
     '     and gives the worker a response it is allowed to keep. -->\n'
     '<link rel="stylesheet" crossorigin="anonymous" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap">',
     "the Google Fonts stylesheet")

swap('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.css">',
     '<link rel="stylesheet" crossorigin="anonymous" href="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.css">',
     "the MapLibre stylesheet")

swap('<script src="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.js"></script>',
     '<script crossorigin="anonymous" src="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.js"></script>',
     "the MapLibre script")

# ---------------------------------------------------------------- the tap target
# The coarse-pointer block already lifts every control in the app to 44 and says why:
# "Measured at 42x42 on a 390px viewport, which misses by two pixels in both directions.
# A short control and a narrow one fail a thumb the same way." The free-screens pill went
# in at 38 and was not in that block, so it was six pixels short of the rule the comment
# is about -- measured on a phone-shaped viewport with those rules applied.
swap("""  .mapctl button{width:44px;height:44px}""",
     """  .mapctl button{width:44px;height:44px}
  /* Same rule, same reason: this went in at 38 and is the only control in the app that
     was under the line. */
  .mapfree{min-height:44px}""",
     "the free-screens pill's tap target")

# ------------------------------------------------------------- a number and its noun
# Seen at 375 and again at 430: "from Thu 24 Sep - 7 dates 31" on one line and "cinemas"
# alone on the next. The count and the word it counts are one fact and should break as
# one. It is the same span on the Films rows, where it holds "4 min walk", so the rule
# goes on both rather than on the new one only.
swap(""".frow .at span{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--ink-3);letter-spacing:.02em}""",
     """.frow .at span{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--ink-3);letter-spacing:.02em;
  white-space:nowrap}""",
     "keeping a count on the same line as its noun")

open(PAGE, "w", encoding="utf-8").write(s)
print("offline-lib: 5 anchors replaced in docs/index.html")
