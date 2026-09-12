#!/usr/bin/env python3
"""Walkable: only the cinemas within walking distance.

    /opt/homebrew/bin/python3 walkable.py

Idea 8 on the list he was given on 8 September -- "no walkable filter" -- and the next one
after starring a film. Thirty-five cinemas out to nine kilometres is more than anyone walks
to on a weeknight, and the app already knows which of them are a walk. A Walkable chip
stacks with the others, so "walkable, subtitled, starting soon" is a question it can answer.

WHERE THE LINE COMES FROM, because this app does not print a number it cannot defend.

Nobody has measured how far he is willing to walk, and this does not pretend to know. The
app already draws a line: every cinema row says "N min walk" up to forty minutes at
4.5 km/h and "N min drive" past it, and has since the first build. The chip uses exactly
that line, through one function, so a cinema can never be Walkable while its own row says
drive, or the other way round. Forty minutes is about three kilometres straight-line, and
the app already says 4.5 km/h is optimistic on Insurgentes. If the line is wrong it is wrong
in one place, WALK_MAX, and the rows, the leave-by time and the chip all move together.

IT FOLLOWS THE ORIGIN. Distances are from Parque Mexico until the location button is on, and
then from wherever the phone is. The chip asks its question of whichever origin is live, so
the button now recounts the chips too. Without that, turning location on far from the city
would leave Walkable lit over an empty list, which is the dead end renderFilters exists to
prevent.

IT IS NOT SAVED, for the reason Starting soon and Starred are not: the answer depends on
where the phone is, and that is not saved either. Restoring it would open the app on a
filter measured from somewhere it may no longer be.

The filters could not see which cinema a showing is at. Every call site of `passes` already
has the cinema in scope as `c`, so it goes through as the sixth argument, after the film id
starred.py added. test-walkable.mjs reads every call and fails on a short one, and
test-starred.mjs now finds the film id by position rather than by it being last.
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
if 'case "walk"' in s:
    sys.exit("walkable.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why, expect=1):
    global s
    n = s.count(before)
    if n != expect:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if n == 0 else "x%d, expected %d" % (n, expect), why, before[:120]))
    s = s.replace(before, after)


# ---- one walk-or-drive line, shared by the rows, leave-by and the chip ---------------------
swap('const walkMin = d => Math.max(1, Math.round(d / 0.075));   // 4.5 km/h\n',
     'const walkMin = d => Math.max(1, Math.round(d / 0.075));   // 4.5 km/h\n'
     '/* WHERE A WALK STOPS BEING A WALK. Every row says "min walk" up to here and "min drive"\n'
     '   past it, leave-by uses the same travel time, and the Walkable chip means exactly the\n'
     '   rows that say walk. Nobody measured how far he will go on foot: this is the line the\n'
     '   rows have always drawn, kept in one place so the three cannot disagree. Forty minutes\n'
     '   at 4.5 km/h is about three kilometres straight-line. */\n'
     'const WALK_MAX = 40;\n'
     'function walkable(d) { return walkMin(d) <= WALK_MAX; }\n',
     "one line for walk or drive")
swap('  return w <= 40 ? w : Math.round(d / 0.35);',
     '  return walkable(d) ? w : Math.round(d / 0.35);',
     "travelMin uses it")
swap('           w: w <= 40 ? w + " min walk" : Math.round(d / 0.35) + " min drive" };',
     '           w: walkable(d) ? w + " min walk" : Math.round(d / 0.35) + " min drive" };',
     "far uses it")

# ---- the filter itself -----------------------------------------------------------------
swap('function passesOne(key, fmtIdx, mins, dayIso, fid) {',
     'function passesOne(key, fmtIdx, mins, dayIso, fid, cin) {',
     "passesOne takes the cinema")
swap('    case "star": return isStarred(fid);',
     '    case "star": return isStarred(fid);\n'
     '    // A question about the CINEMA, measured from whichever origin is live, so it moves\n'
     '    // with the location button. No cinema means no answer, never a pass.\n'
     '    case "walk": return cin != null && walkable(km(origin, { lat: cin.lat, lng: cin.lng }));',
     "the walk case")
swap('function passes(fmtIdx, mins, dayIso, extra, fid) {',
     'function passes(fmtIdx, mins, dayIso, extra, fid, cin) {',
     "passes takes the cinema")
swap('if (!passesOne(k, fmtIdx, mins, dayIso, fid)) return false;',
     'if (!passesOne(k, fmtIdx, mins, dayIso, fid, cin)) return false;',
     "active chips see the cinema")
swap('!passesOne(extra, fmtIdx, mins, dayIso, fid)) return false;',
     '!passesOne(extra, fmtIdx, mins, dayIso, fid, cin)) return false;',
     "the extra chip sees the cinema")

swap('passes(x[1], x[3], DAYS[x[2]], null, x[0])', 'passes(x[1], x[3], DAYS[x[2]], null, x[0], c)',
     "filmRuns call site")
swap('passes(s[1], s[3], dayIso, k, s[0])', 'passes(s[1], s[3], dayIso, k, s[0], c)',
     "chip count call site")
swap('passes(s[1], s[3], dayIso, null, s[0])', 'passes(s[1], s[3], dayIso, null, s[0], c)',
     "active count, showtimes and films call sites", expect=3)

swap('["star", "Starred"], ["sub", "Subtitled"],',
     '["star", "Starred"], ["walk", "Walkable"], ["sub", "Subtitled"],',
     "the chip")
swap('JSON.stringify([...S.filters].filter(k => k !== "now" && k !== "star"))',
     'JSON.stringify([...S.filters].filter(k => k !== "now" && k !== "star" && k !== "walk"))',
     "Walkable is not saved as a standing filter")

# "walkable subtitled showings" is not English any more than "starting soon subtitled
# showings" was, so walking is a clause after the noun, like starting soon.
swap('  const head = w ? w + " " + noun : noun;\n',
     '  const head = (w ? w + " " + noun : noun) + (S.filters.has("walk") ? " within walking distance" : "");\n',
     "count line: 3 subtitled showings within walking distance")

# ---- the location button moves the origin, so it has to recount the chips ---------------
swap('    $("fromk").textContent = "Distances from"; $("fromn").textContent = HOME.name;\n'
     '    renderShows();',
     '    $("fromk").textContent = "Distances from"; $("fromn").textContent = HOME.name;\n'
     '    renderFilters(); renderShows();',
     "back to Parque Mexico recounts the chips")
swap('$("fromn").textContent = "Where you are standing";\n'
     '    renderShows();',
     '$("fromn").textContent = "Where you are standing";\n'
     '    // Walkable is measured from here now, so the chips are recounted BEFORE the list, the\n'
     '    // same order the date rail uses: a lit Walkable with nothing in reach is dropped rather\n'
     '    // than left lit over an empty page.\n'
     '    renderFilters(); renderShows();',
     "a live location recounts the chips")

open(PAGE, "w", encoding="utf-8").write(s)

# ---- the offline copy has to change name or an installed phone keeps the old page ------
sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**Walkable.**" not in rd:
    rd = rd.replace(anchor,
        "- **Walkable.** A chip that keeps only the cinemas whose own row says \"min walk\": up to\n"
        "  forty minutes at 4.5 km/h, about three kilometres, which is the line the rows have\n"
        "  always used to switch to a drive time. Nobody has measured how far is too far, so it\n"
        "  does not invent a new number, and the rows and the chip share one function so they\n"
        "  cannot disagree. It measures from wherever the distances do, so it follows the\n"
        "  location button, and like Starting soon it is not remembered between launches.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("walkable: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
