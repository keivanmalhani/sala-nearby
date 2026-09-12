#!/usr/bin/env python3
"""Specific about IMAX: what each IMAX room in the app actually has, and how sure that is.

    /opt/homebrew/bin/python3 imax-rooms.py

Ask 10 from 12 September: "be specific about IMAX, e.g. IMAX 4K digital? IMAX 2K digital?
Screen size?". The answers come from docs/imax-specs.json, gathered room by room with a
source and a confidence for every field, and they are baked into the page from that file so
the two cannot drift.

WHAT IT CORRECTS. The format note on every film sheet said IMAX here is "a 4K laser projector
... every IMAX in Mexico is that kind". Cinemex itself names only Antara, Santa Fe, Parque
Delta and Parque Tezontle as laser. Encuentro Oceania's projector is not published, 4K is
stated by press rather than by Cinemex, and no screen height for Antara survives two sources
agreeing. The note now says only what holds everywhere -- IMAX's own digital 1.90:1 format,
none of the tall 1.43:1 rooms -- and the room says the rest.

WHERE IT SHOWS. Under the times on a film's sheet, where the seats line already names the
room: "Sala 3: 388 seats, 6 wheelchair · IMAX with Laser, 4K (press), IMAX 12-channel sound
(press), 1.90:1, screen size not published". "(press)" marks a likely fact, one said by
independent press or by Cinemex only for the chain, and anything unknown says so rather than
being left out, because "not published" is itself the answer to "screen size?".
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
SW = os.path.join(ROOT, "docs", "sw.js")
SPECS = os.path.join(ROOT, "docs", "imax-specs.json")
README = os.path.join(ROOT, "README.md")

s = open(PAGE, encoding="utf-8").read()
if "const IMAX_ROOMS =" in s:
    sys.exit("imax-rooms.py has already been applied to docs/index.html; nothing to do")
spec = json.load(open(SPECS, encoding="utf-8"))

FIELDS = ["label", "projection", "resolution", "sound", "aspect_ratio", "screen_area_m2", "billed_as"]
rooms = {}
for r in spec["rooms"]:
    if not r.get("has_showtimes_in_app") or not r.get("venue_id") or not r.get("room"):
        continue
    rooms["%s|%s" % (r["venue_id"], r["room"])] = {
        f: [r[f]["value"], r[f]["confidence"]] for f in FIELDS if isinstance(r.get(f), dict)}
if not rooms:
    sys.exit("imax-specs.json has no IMAX room with showtimes in the app -- nothing to show, nothing written")


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" % ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:140]))
    s = s.replace(before, after, 1)


table = json.dumps(rooms, ensure_ascii=False, separators=(",", ":"))
swap("const FORMAT_NOTE = {\n", r'''/* IMAX, ROOM BY ROOM. Ask 10 on 12 September: "IMAX 4K digital? IMAX 2K digital? Screen
   size?". Baked from docs/imax-specs.json by imax-rooms.py, where every value has a source
   and a confidence. Keyed "cinema id|room". Likely facts say "(press)"; unknown ones say "not
   published", because that is the honest answer to the question he asked. */
const IMAX_ROOMS = ''' + table + ''';
function imaxLine(cid, room) {
  const r = IMAX_ROOMS[String(cid) + "|" + room];
  if (!r) return "";
  const v = (k, fmt) => {
    const x = r[k];
    if (!x || x[1] === "unknown" || x[0] == null) return null;
    return (fmt ? fmt(x[0]) : String(x[0])) + (x[1] === "likely" ? " (press)" : "");
  };
  const parts = [
    v("label"),
    r.projection && r.projection[1] !== "unknown" ? v("projection", p => p + " projection") : "projector not published",
    v("resolution"), v("sound", x => x + " sound"), v("aspect_ratio"),
    r.screen_area_m2 && r.screen_area_m2[1] !== "unknown" ? v("screen_area_m2", a => "about " + a + " m² screen") : "screen size not published",
  ].filter(Boolean);
  return parts.join(", ");
}
const FORMAT_NOTE = {
''', "the IMAX room table")

swap('''  imax: ["IMAX with Laser",
    "A 4K laser projector, twelve channels of sound and a 1.90:1 screen. Every IMAX in "
    + "Mexico is that kind; the tall 1.43:1 rooms do not exist here. Parque Delta and "
    + "Antara are the two near Roma."],''',
     '''  imax: ["IMAX",
    "IMAX's own digital format: a 1.90:1 screen and IMAX's twelve-channel sound. None of the "
    + "tall 1.43:1 rooms exists in Mexico. Cinemex names Parque Delta and Antara as laser; "
    + "each room's own line under its times says what else is known about it."],''',
     "the format note stops claiming every IMAX is 4K laser")

swap('''        `${esc(k)}: ${r[1]} seats, ${r[2] ? r[2] + " wheelchair" : "no wheelchair space"}`''',
     '''        `${esc(k)}: ${r[1]} seats, ${r[2] ? r[2] + " wheelchair" : "no wheelchair space"}${
          imaxLine(c.id, k) ? " &middot; " + esc(imaxLine(c.id, k)) : ""}`''',
     "the room line names its IMAX specifics")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**IMAX, room by room.**" not in rd:
    rd = rd.replace(anchor,
        "- **IMAX, room by room.** Under the times on a film's sheet, an IMAX room says whether it\n"
        "  is laser, 4K, its sound and aspect ratio, and its screen size or that it is not\n"
        "  published, with \"(press)\" on anything Cinemex has not said itself. From\n"
        "  `docs/imax-specs.json`, where every value carries its source.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("imax-rooms: %d IMAX rooms baked in, sw cache now sala-v%d" % (len(rooms), int(m.group(1)) + 1))
