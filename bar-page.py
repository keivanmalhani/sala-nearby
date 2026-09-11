#!/usr/bin/env python3
"""Put the drinks answer on each venue's own sheet.

    /opt/homebrew/bin/python3 bar.py        # writes docs/bar.json with a local model
    /opt/homebrew/bin/python3 bar-page.py   # and this puts it on the page

WHERE IT GOES. Last in the "What it is" list, after Operator, Rooms, Price, Best room,
Audio and Projection -- the picture and the sound are why he picks a cinema, and the bar
is the thing he checks once he has. Whether the building has one does not change with the
week's programme, which is what makes it that kind of fact.

THREE WORDS, NOT THE QUOTE. The first version printed the sentence the model quoted, and
on Cine Tonala that read "Bar on site -- plus a bar, a pizza kitchen and a bookstore"
directly underneath a paragraph containing those exact words. The evidence has to exist;
it does not have to be on the screen twice. It stays in the BAR table below, where the
guard reads it, and the paragraph above the list is the venue's own words about it.

Seven of forty-two. Nothing is written for the other thirty-five: a venue with no drinks
row is a venue whose write-up does not mention a drink, which is a weaker claim than "no
bar" and is the only one the audit can support.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
BARJSON = os.path.join(ROOT, "docs", "bar.json")

if not os.path.exists(BARJSON):
    sys.exit("docs/bar.json is not there -- run bar.py first (it needs qwen3:8b loaded)")
bar = json.load(open(BARJSON, encoding="utf-8"))
if not bar:
    sys.exit("docs/bar.json is empty, so there is nothing to say")

s = open(PAGE, encoding="utf-8").read()


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:120]))
    s = s.replace(before, after, 1)


rows = "".join('\n"%s":%s,' % (k.replace('"', '\\"'), json.dumps(v, ensure_ascii=False))
               for k, v in sorted(bar.items()))
swap("const SHOWS=",
     """/* WHICH VENUES SELL A DRINK, read out of the audit prose rather than typed twice.
   There is no machine-readable menu anywhere -- Cinemex publishes `candybar: false` on
   all seventy CDMX sites and its own dulceria page is a 404 -- so a snack list is not a
   thing this app can have. Whether a building has a bar is, and his own write-ups
   already said so in seven places that nothing on screen could reach.

   The value is the sentence the write-up uses, and it is kept here rather than printed:
   the sheet says "Bar on site" and the paragraph above it already says it in the venue's
   own words. Every line was quoted back verbatim by the model that found it and then
   checked against the source word for word, so a line in this table is a line that
   genuinely appears in that venue's audit -- which is what makes the three words on the
   screen safe to print. A venue missing from this table is one whose audit does not
   mention a drink, and that is not the same claim as "no bar". The page does not make
   the stronger one. */
const BAR={%s
};
const SHOWS=""" % rows,
     "the BAR table, before the payload")

swap("""    ${v.proj ? `<dt>Projection</dt><dd>${esc(v.proj)}</dd>` : ""}""",
     """    ${v.proj ? `<dt>Projection</dt><dd>${esc(v.proj)}</dd>` : ""}
    ${BAR[v.name] ? `<dt>Drinks</dt><dd>Bar on site</dd>` : ""}""",
     "the Drinks row on the venue sheet")

open(PAGE, "w", encoding="utf-8").write(s)
print("docs/index.html patched: %d venues carry a Drinks row" % len(bar))
