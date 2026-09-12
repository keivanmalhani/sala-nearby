#!/usr/bin/env python3
"""The Films line says where "near" is measured from.

    /opt/homebrew/bin/python3 films-line-origin.py

The Films tab has always read "17 films playing today near you". Every distance on the page
is from Parque Mexico until the location button is on, so "near you" was only true for
somebody standing in the park, and it went on saying it with Walkable lit while the
Showtimes line beside it said "within walking distance". Two lines, one filter, two
different claims.

Now it names the origin it is actually using -- "near Parque Mexico", or "near you" once the
location is live -- and with Walkable on it says "within walking distance of" either one.
The location button already redraws the Films list, so the words follow it.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
SW = os.path.join(ROOT, "docs", "sw.js")

s = open(PAGE, encoding="utf-8").read()
if "function whereFrom(" in s:
    sys.exit("films-line-origin.py has already been applied to docs/index.html; nothing to do")
if 'case "walk"' not in s:
    sys.exit("run walkable.py first: this line reads the Walkable chip")


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" % ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:120]))
    s = s.replace(before, after, 1)


swap('  return S.filters.has("now") ? head + " starting in the next four hours" : head;\n}\n',
     '  return S.filters.has("now") ? head + " starting in the next four hours" : head;\n}\n'
     '/** Where "near" is measured from, said as what it is: the park until the location button\n'
     ' *  is on, the phone after. With Walkable on it says walking distance, as the Showtimes\n'
     ' *  line does, so the two tabs never make different claims about one filter. */\n'
     'function whereFrom() {\n'
     '  const who = liveLoc ? "you" : HOME.name;\n'
     '  return S.filters.has("walk") ? "within walking distance of " + who : "near " + who;\n'
     '}\n',
     "whereFrom beside countLabel")
swap('playing ${isToday(dayIso) ? "today" : "that day"} near you`);',
     'playing ${isToday(dayIso) ? "today" : "that day"} ${esc(whereFrom())}`);',
     "the Films line")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)
print("films-line-origin: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
