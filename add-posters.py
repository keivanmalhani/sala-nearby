#!/usr/bin/env python3
"""Put the posters into the page: the films list, and the film sheet.

    /opt/homebrew/bin/python3 add-posters.py

He asked for "movie posters in integration with this". refresh-posters.py has already put
39 of them in docs/posters, verified as actual pictures rather than error pages. This wires
them into the two places a film is shown.

TWO THINGS THAT ARE NOT DECORATION.

`loading="lazy"` and explicit width/height on every poster. Without the dimensions the list
reflows as each image arrives, which on a phone means the row you were about to tap moves
out from under your thumb. With them the space is reserved before anything loads.

`onerror` hides the image rather than leaving the browser's broken-image glyph. A missing
poster should read as a film without a poster, not as a bug -- and a visibly broken image
is on Apple's own list of things that get an app rejected.

Every anchor is asserted, so if the page moves underneath this it stops rather than writing
something mangled.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

s = open(PAGE, encoding="utf-8").read()
orig = s


def swap(before, after, why):
    global s
    if s.count(before) != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if before not in s else "NOT UNIQUE", why, before[:110]))
    s = s.replace(before, after, 1)


# ---------------------------------------------------------------- 1. CSS
swap(""".frow{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;padding:13px 16px;border-bottom:1px solid var(--line-2);width:100%;text-align:left}""",
     """.frow{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;padding:13px 16px;border-bottom:1px solid var(--line-2);width:100%;text-align:left}
/* A film row carries its poster, so the grid gains a column. The guide's independent-venue
   rows use .frow too and have no poster, which is why the poster column only appears on
   rows that actually have one. */
.frow.haspos{grid-template-columns:52px 1fr auto}
.frow .pos{width:52px;height:78px;border-radius:5px;object-fit:cover;display:block;
  background:var(--sunk2);border:1px solid var(--line-2)}""",
     "the film row grid")

swap(""".frow .cnt em{display:block;font-style:normal;font-size:9.5px;color:var(--ink-3);letter-spacing:.06em;margin-top:2px}""",
     """.frow .cnt em{display:block;font-style:normal;font-size:9.5px;color:var(--ink-3);letter-spacing:.06em;margin-top:2px}
/* The poster at the top of a film's sheet. Kept small on purpose: the file is 346 px wide,
   so anything above about 120 pt would start to look soft on a 3x screen, which is the
   complaint this whole change exists to answer. */
.sheet .poshead{display:grid;grid-template-columns:88px 1fr;gap:14px;align-items:start}
.sheet .poshead img{width:88px;height:132px;border-radius:7px;object-fit:cover;display:block;
  background:var(--sunk2);border:1px solid var(--line-2)}
.sheet .syn{color:var(--ink-2);font-size:13px;line-height:1.5;margin-top:9px}""",
     "the sheet poster")

# ---------------------------------------------------------------- 2. the films list
swap("""    return `<button class="frow" data-film="${esc(r.fid)}">
      <span><span class="n">${esc(r.f.n)}</span>""",
     """    return `<button class="frow haspos" data-film="${esc(r.fid)}">
      <img class="pos" src="posters/${esc(r.fid)}.jpg" alt="" loading="lazy"
           width="52" height="78" onerror="this.style.visibility='hidden'">
      <span><span class="n">${esc(r.f.n)}</span>""",
     "the poster in the films list")

# ---------------------------------------------------------------- 3. the film sheet
swap("""  const head = `<div><h2>${esc(f.n)}</h2><div class="addr">${
    esc([f.o && f.o !== f.n ? f.o : "", f.d, f.r, (f.g || []).join(", "), f.dir].filter(Boolean).join(" · "))}</div></div>`;""",
     """  const syn = (POSTERS[fid] || {}).syn || "";
  const head = `<div class="poshead">
      <img src="posters/${esc(fid)}.jpg" alt="" width="88" height="132"
           onerror="this.style.visibility='hidden'">
      <div><h2>${esc(f.n)}</h2><div class="addr">${
    esc([f.o && f.o !== f.n ? f.o : "", f.d, f.r, (f.g || []).join(", "), f.dir].filter(Boolean).join(" · "))}</div>
      ${syn ? `<div class="syn">${esc(syn)}</div>` : ""}</div></div>`;""",
     "the poster and synopsis in the film sheet")

# ---------------------------------------------------------------- 4. the synopsis index
swap("""/* ===================== SHEETS ===================== */""",
     """/* THE SYNOPSES, fetched once rather than baked in. posters/index.json is written by
   refresh-posters.py alongside the images and holds Cinemex's own sinopsis for each film.
   It is same-origin, so the service worker caches it with everything else and it is there
   with no signal after the first visit. Starting as {} means a sheet opened before it
   lands simply shows no synopsis rather than throwing. */
let POSTERS = {};
fetch("posters/index.json").then(r => r.ok ? r.json() : {}).then(j => { POSTERS = j || {}; })
  .catch(() => {});

/* ===================== SHEETS ===================== */""",
     "the synopsis index")

if s == orig:
    sys.exit("nothing changed, which cannot be right")
open(PAGE, "w", encoding="utf-8").write(s)
print("posters wired in; page is now %d bytes (was %d)" % (len(s), len(orig)))
