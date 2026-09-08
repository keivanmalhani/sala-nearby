#!/usr/bin/env python3
"""Teach the page that there is more than one cinema chain in it. Idempotent.

    /opt/homebrew/bin/python3 add-chain-links.py

WHY THIS IS A SCRIPT AND NOT A HAND EDIT. docs/index.html is generated -- build.py writes
it from the artifact, and refresh-showtimes.py, refresh-posters.py, swap-map.py and
refresh-cineteca.py all rewrite parts of it in place. A hand edit to its JavaScript
survives exactly until the next `git checkout -- docs/index.html`, which is how these
three functions were lost twice in one afternoon on 2026-09-08. Run this after anything
that regenerates the page; running it twice is a no-op.

WHAT IT CHANGES. Five call sites hardcoded Cinemex:

    https://cinemex.com/checkout/<id>   x2   the time chips, in two renderers
    https://cinemex.com/cinema/<id>     x2   "Live times & book" in two sheets
    "Cinemex"                           x1   the operator label under a venue name

All five were correct while every board was Cinemex. Cineteca Nacional's three sedes made
each one wrong, and the operator label was the visible one: "Cineteca Nacional Mexico
(Xoco)  Cinemex - no audit yet".

THE FUNCTIONS GO AT TOP LEVEL, and that is not style. The first attempt put them next to
the first call site, inside a renderer, and the second call site died with "chainOf is not
defined" -- a function declaration hoists to its own scope and no further. The page went
blank and a window.onerror handler registered after load reported no errors, because the
failure was at parse time.
"""
import os
import re
import subprocess
import sys
import tempfile

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "index.html")

HELPERS = '''/* TWO CHAINS NOW, so these are functions rather than a template repeated at five call
   sites. Cinemex sessions carry a bare checkout id; Cineteca's are written
   "cineteca:<sede>:<session>" because its ticketing lives on its own host and needs both
   numbers. Anything unrecognised falls back to Cinemex, which is what every row was
   until 2026-09-08. Written by add-chain-links.py -- edit that, not this. */
function ticketUrl(s) {
  const id = s[5];
  if (!id) return "#";
  const ct = String(id).match(/^cineteca:(\\d+):(\\d+)$/);
  if (ct) return `https://rbvfcn.cinetecanacional.net/Ticketing/visSelectTickets.aspx?cinemacode=${ct[1]}&txtSessionId=${ct[2]}&visLang=1`;
  return `https://cinemex.com/checkout/${encodeURIComponent(id)}`;
}
function cinemaUrl(c) {
  const ct = String(c.id).match(/^cineteca-(\\d+)$/);
  if (ct) return `https://www.cinetecanacional.net/cartelera.php?cinemaId=${ct[1]}`;
  return `https://cinemex.com/cinema/${encodeURIComponent(c.id)}`;
}
/* The operator for a cinema with no curated venue behind it. A default that is right for
   every row is not a default, it is an assumption waiting for the second case. */
function chainOf(c) {
  if (/^cineteca-/.test(String(c.id))) return "Cineteca Nacional";
  return "Cinemex";
}

'''

EDITS = [
    ('const href = s[5] ? `https://cinemex.com/checkout/${encodeURIComponent(s[5])}` : "#";',
     'const href = ticketUrl(s);', "the time chip's ticket link", 2),
    ('href="https://cinemex.com/cinema/${c.id}"',
     'href="${cinemaUrl(c)}"', "the venue sheet's live-times link", 1),
    ('href="https://cinemex.com/cinema/${live.id}"',
     'href="${cinemaUrl(live)}"', "the curated sheet's live-times link", 1),
    ('<span class="s">${esc(v ? (v.op + (c.p ? " · Platino" : "")) : "Cinemex" + (c.p ? " · Platino" : ""))}${v ? "" : " · no audit yet"}</span>',
     '<span class="s">${esc((v ? v.op : chainOf(c)) + (c.p ? " · Platino" : ""))}${v ? "" : " · no audit yet"}</span>',
     "the operator label", 1),
]


def js_is_valid(page):
    """node --check on every inline script. A parse error blanks the page silently."""
    for block in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', page, re.S):
        f = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False)
        f.write(block)
        f.close()
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        os.unlink(f.name)
        if r.returncode:
            return r.stderr[:400]
    return None


def main():
    page = open(PAGE, encoding="utf-8").read()
    already = len(re.findall(r"function (?:ticketUrl|cinemaUrl|chainOf)\(", page))
    if already == 3 and not any(old in page for old, _n, _l, _c in EDITS):
        print("already applied; nothing to do")
        return 0
    if already:
        sys.exit("partly applied (%d of 3 helpers present) -- that is not a state this "
                 "script created. Look before re-running." % already)

    anchor = re.search(r"\nfunction \w+\(", page)
    if not anchor:
        sys.exit("no top-level function to anchor the helpers before")
    page = page[:anchor.start() + 1] + HELPERS + page[anchor.start() + 1:]

    for old, new, label, expect in EDITS:
        n = page.count(old)
        if n != expect:
            sys.exit("expected %d of %s, found %d -- the page has changed shape"
                     % (expect, label, n))
        page = page.replace(old, new)
        print("  %d x %s" % (n, label))

    bad = js_is_valid(page)
    if bad:
        sys.exit("refusing to write, the result does not parse:\n%s" % bad)

    left = re.findall(r"https://cinemex\.com/(?:checkout|cinema)/\$\{", page)
    if len(left) != 2:                     # the two inside the helpers themselves
        sys.exit("%d hardcoded Cinemex links remain outside the helpers" % (len(left) - 2))

    open(PAGE, "w", encoding="utf-8").write(page)
    print("wrote docs/index.html: %s bytes" % format(len(page), ","))
    return 0


if __name__ == "__main__":
    sys.exit(main())
