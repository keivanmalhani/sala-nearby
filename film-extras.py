#!/usr/bin/env python3
"""Cast, country, year and the trailer, on the film sheet.

    /opt/homebrew/bin/python3 refresh-posters.py --meta
    /opt/homebrew/bin/python3 film-extras.py

Idea 8 in docs/IDEAS-2026-09-09.md, "the fields already being thrown away". Measured on
12 September against the 46 Cinemex films in the page: cast on 46, country on 44, year on
45, a trailer on 45 -- and one of those 45 was the bare "https://www.youtube.com/", which
refresh-posters.py now drops. None of it reached the screen.

WHAT GOES ON THE SHEET.

  - One quiet line under the facts: "Corea del Sur, 2026 · with Jun Ji-hyun, Koo Kyo-hwan".
    Country is the part that changes a decision here -- whether a film is Mexican is often
    the reason to go -- so it leads.
  - A Trailer button in the bar beside "Walk to", as a link out to YouTube.

WHERE I DISAGREED WITH THE IDEA. It lists the distributor too. It is on all 46, and it is a
trade fact: "Zima Entertainment" does not change whether he goes, and a sheet he already
called cluttered does not need a fourth fact on that line. Left out on purpose.

LINK, NEVER EMBED, and the idea says so too. An embedded player breaks the promise that the
app works with no signal and puts a third party on a page that has none. The page also
re-checks the url shape before drawing the button, so a bad manifest cannot put a link to
anywhere else on his screen.

The data rides in posters/index.json beside the synopsis, which the page already fetches
once, so there is no new request and a Cineteca title -- which has none of these fields --
shows nothing rather than an empty line.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
SW = os.path.join(ROOT, "docs", "sw.js")
README = os.path.join(ROOT, "README.md")

s = open(PAGE, encoding="utf-8").read()
if 'class="made"' in s:
    sys.exit("film-extras.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" % ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:120]))
    s = s.replace(before, after, 1)


swap('  const syn = (POSTERS[fid] || {}).syn || "";\n',
     '  const syn = (POSTERS[fid] || {}).syn || "";\n'
     r'''  // CAST, COUNTRY, YEAR AND TRAILER, from the same file as the synopsis and missing the same
  // way: a Cineteca title, or a sheet opened before the file lands, shows none of it rather
  // than an empty line. The trailer is checked again here, so a bad manifest cannot draw a
  // button that goes anywhere but a YouTube video.
  const meta = POSTERS[fid] || {};
  const made = [[meta.country, meta.year].filter(Boolean).join(", "),
                meta.cast ? "with " + meta.cast : ""].filter(Boolean).join(" · ");
  const yt = /^https:\/\/www\.youtube\.com\/watch\?v=[\w-]{11}$/.test(meta.trailer || "") ? meta.trailer : "";
''',
     "meta read beside the synopsis")

swap('(f.g || []).join(", "), f.dir].filter(Boolean).join(" · "))}</div>\n',
     '(f.g || []).join(", "), f.dir].filter(Boolean).join(" · "))}</div>\n'
     '      ${made ? `<div class="made">${esc(made)}</div>` : ""}\n',
     "the made line under the facts")

swap('esc(far(km(origin, { lat: rows[0][0].lat, lng: rows[0][0].lng })).d)}</a>`\n    : "";\n',
     'esc(far(km(origin, { lat: rows[0][0].lat, lng: rows[0][0].lng })).d)}</a>`\n    : "";\n'
     '  // A link out, never an embed: a player breaks the no-signal promise and puts a third party\n'
     '  // on a page that has none. It sits in the bar beside Walk to.\n'
     '  const trailer = yt ? `<a class="yt" href="${esc(yt)}" target="_blank" rel="noopener">Trailer</a>` : "";\n',
     "the trailer link")
swap('openSheet(head, go, body + gloss, "var(--c-big)");',
     'openSheet(head, go + trailer, body + gloss, "var(--c-big)");',
     "the trailer goes in the bar")

swap('.sheet .go a.pri{background:var(--lamp);border-color:var(--lamp);color:var(--lamp-ink)}',
     '.sheet .go a.pri{background:var(--lamp);border-color:var(--lamp);color:var(--lamp-ink)}\n'
     '/* Trailer takes its own width and leaves the rest of the bar to Walk to, whose label is the\n'
     '   long one. */\n'
     '.sheet .go a.yt{flex:none;padding:0 18px}\n'
     '.sheet .made{color:var(--ink-2);font-size:12.5px;line-height:1.45;margin-top:5px}',
     "styles")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**Cast, country and trailer.**" not in rd:
    rd = rd.replace(anchor,
        "- **Cast, country and trailer.** A film's sheet says where it is from, when, and who is\n"
        "  in it, and has a Trailer button beside Walk to that opens YouTube rather than embedding\n"
        "  a player, so the app still works with no signal. Cinemex sends these for almost every\n"
        "  film; Cineteca sends none, and its sheets show nothing rather than an empty line.\n"
        "  `refresh-posters.py --meta` refreshes them without touching an image.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("film-extras: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
