#!/usr/bin/env python3
"""Colour that means something, and light mode you can read in daylight.

    /opt/homebrew/bin/python3 colours.py

Ask 2 from 12 September, "better coloring", done as the system written down in
docs/REDESIGN-2026-09-12.md rather than as a new palette. The dark theme he likes keeps its
look; what changes is what the colours are for.

WHAT CHANGES.

  - DISTANCES ARE BLUE. The projector-beam blue already in the tokens now marks place and
    distance: the metres on every cinema, the walking time on every movie row, and the
    location button. Amber stays selection and the number you act on.
  - FEATURES ARE FILLED, FACTS ARE OUTLINED. IMAX, Atmos, Platino and Subtitled keep their
    solid colour. Premium, Standard, 3D and Dubbed become quiet outlines, so the four that
    change a decision stand out from the ones that only describe the room. Dubbed lost its
    fill because it is the default in this city, not a feature.
  - LIGHT MODE PASSES CONTRAST. Measured against WCAG's 4.5:1 for small text, before this:
    the grey mono labels on the page ground read 3.73, on white 4.02, the amber count on the
    ground 4.21, and the Subtitled badge 4.40 -- all small type, all below the line. Each
    token moved as little as it needed to clear it, keeping its hue. Dark mode's grey
    labels read 4.34 on a card and are nudged too.

test-colours.mjs reads the tokens back out of the page, recomputes every pair, and pairs its
checks with 402eaf0.
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
if "#locbtn[aria-pressed=\"false\"] svg" in s:
    sys.exit("colours.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why, expect=1):
    global s
    n = s.count(before)
    if n != expect:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if n == 0 else "x%d, expected %d" % (n, expect), why, before[:140]))
    s = s.replace(before, after)


# ---- tokens: the least movement that clears 4.5:1 ---------------------------------------
swap("  --ink:#191310; --ink-2:#5C4F47; --ink-3:#8B7C72;",
     "  --ink:#191310; --ink-2:#5C4F47; --ink-3:#73655C;", "light grey labels 3.73 -> 5.21")
swap("  --lamp:#A9670C; --lamp-ink:#FFFFFF; --lamp-soft:#F7EBD6;",
     "  --lamp:#9A5C08; --lamp-ink:#FFFFFF; --lamp-soft:#F7EBD6;", "light amber 4.21 -> 4.99")
swap("  --tap:rgba(169,103,12,.10);", "  --tap:rgba(154,92,8,.10);", "the tap tint follows the amber")
swap("  --ok:#1E7C52; --ok-soft:#E2F0E8;", "  --ok:#18704A; --ok-soft:#E2F0E8;", "light Subtitled 4.40 -> 5.17")
swap("--ink:#F4EDE5; --ink-2:#BCADA2; --ink-3:#8A7C72;",
     "--ink:#F4EDE5; --ink-2:#BCADA2; --ink-3:#9A8C82;", "dark grey labels 4.34 -> 5.37, both dark blocks", expect=2)

# ---- badges: features filled, facts outlined ---------------------------------------------
swap('padding:2px 5px;border-radius:4px;line-height:1.35;white-space:nowrap;background:var(--sunk);color:var(--ink-2)}',
     'padding:2px 5px;border-radius:4px;line-height:1.35;white-space:nowrap;background:transparent;box-shadow:inset 0 0 0 1px var(--line);color:var(--ink-2)}',
     "a plain badge is an outline, drawn inset so no row changes height")
swap(".badge.imax{background:var(--beam);color:var(--ground)}",
     ".badge.imax{background:var(--beam);color:var(--ground);box-shadow:none}", "IMAX filled")
swap(".badge.atmos{background:var(--c-lux);color:var(--ground)}",
     ".badge.atmos{background:var(--c-lux);color:var(--ground);box-shadow:none}", "Atmos filled")
swap(".badge.plat{background:var(--c-big);color:var(--ground)}",
     ".badge.plat{background:var(--c-big);color:var(--ground);box-shadow:none}", "Platino filled")
swap(".badge.sub{background:var(--ok-soft);color:var(--ok)}",
     ".badge.sub{background:var(--ok-soft);color:var(--ok);box-shadow:none}", "Subtitled filled")
swap(".badge.dub{background:var(--sunk2);color:var(--ink-2)}",
     ".badge.dub{background:transparent;color:var(--ink-2)}", "Dubbed is the default here, so an outline")
# Its own rule, because test-coming-up.mjs pins the Last day rule's exact text.
swap(".badge.last{background:var(--lamp);color:var(--lamp-ink)}",
     ".badge.last{background:var(--lamp);color:var(--lamp-ink)}\n.badge.last{box-shadow:none}", "Last day filled")

# ---- distances in the beam colour -------------------------------------------------------
swap('.cin .far b{display:block;font-family:"IBM Plex Mono",monospace;font-size:15px;font-weight:600;letter-spacing:-.02em}',
     '.cin .far b{display:block;font-family:"IBM Plex Mono",monospace;font-size:15px;font-weight:600;letter-spacing:-.02em;color:var(--beam)}',
     "the metres on every cinema")
swap('.frow .at span{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--ink-3);',
     '.frow .at span{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--beam);',
     "the walking time on every movie row")
swap('.iconbtn[aria-pressed="true"] svg{stroke:var(--lamp-ink)}',
     '.iconbtn[aria-pressed="true"] svg{stroke:var(--lamp-ink)}\n'
     '/* The location button is about place, so it is drawn in the beam colour until it is on,\n'
     '   when it lights amber like every other control that is on. */\n'
     '#locbtn[aria-pressed="false"] svg{stroke:var(--beam)}',
     "the location button")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**Colour that means something.**" not in rd:
    rd = rd.replace(anchor,
        "- **Colour that means something.** Distances and walking times are blue everywhere;\n"
        "  IMAX, Atmos, Platino and Subtitled are solid badges and Premium, Standard, 3D and\n"
        "  Dubbed are outlines; amber is what is selected. Every small text colour clears WCAG's\n"
        "  4.5:1 in both themes, which light mode's grey labels and amber did not before.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("colours: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
