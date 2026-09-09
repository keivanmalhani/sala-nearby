#!/usr/bin/env python3
"""Controls for the free-screens list, each of which fails on the page before it.

    /opt/homebrew/bin/python3 test-free-rooms.py

Two things could be wrong here and neither would throw. The count could be written into
the page instead of counted, so that editing the audit changes the list and not the
caption; and the page could claim to know what is on tonight at fifteen venues whose
programmes it cannot read. Both are checked, and both are checked against the audit
itself rather than against a number restated here -- section 1 counts the free venues out
of the V array with a different tool than the page uses, so the two can disagree.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

# A FIXED COMMIT, never HEAD. See the same note in test-ui-pass.py: a baseline of HEAD
# stops being the before-state the moment the change is committed.
BASELINE = "1c787db"
NOW = open(PAGE, encoding="utf-8").read()


def at(rev, path):
    return subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (rev, path)],
                          capture_output=True, text=True, check=True).stdout


BEFORE = at(BASELINE, "docs/index.html")
fails = []


def check(name, ok):
    print("  %-4s %s" % ("ok" if ok else "FAIL", name))
    if not ok:
        fails.append(name)


def paired(name, fn):
    check(name, fn(NOW))
    check("   ... and not true at %s, so the check can fail" % BASELINE, not fn(BEFORE))


# The venue array, read as text rather than as data: the page filters `v.price` with a
# JavaScript regex, so counting it here with a Python one over the source is a genuinely
# separate route to the same number and the two can come apart.
def venue_prices(src):
    block = src[src.index("const V=["):src.index("\nconst PLAIN=")]
    return re.findall(r'price:"([^"]*)"', block)


print("section 1 -- what is free is counted out of the audit, not written down")
prices = venue_prices(NOW)
free = [p for p in prices if re.search("free", p, re.I)]
always = [p for p in prices if p.strip().lower() == "free"]
print("  (%d audited venues, %d mention free, %d are free outright: %s)"
      % (len(prices), len(free), len(always),
         ", ".join(sorted(set(p for p in free if p not in always)))))
check("the audit really does carry a pile of free venues", len(free) >= 10)
check("and a couple that are only sometimes free", 0 < len(free) - len(always) < 5)
check("every venue has a price field, so the filter is not silently skipping rows",
      len(prices) == NOW[NOW.index("const V=["):NOW.index("\nconst PLAIN=")].count("name:\""))

paired("the count on the button is derived from the array",
       lambda s: "$(\"freebtn\").textContent = `${FREE.length} free screens`" in s)
check("and no count is hardcoded anywhere near it",
      not re.search(r"(1[0-9]|[0-9]) free screens", NOW.replace("${FREE.length} free screens", "")))
paired("with no free venues the button is removed rather than left to open nothing",
       lambda s: 'else $("freebtn").remove();' in s)
paired("the two groups are split on the audit's own wording",
       lambda s: 'const isFreeAlways = v => String(v.price || "").trim().toLowerCase() === "free"' in s)

print("\nsection 2 -- it does not claim to know what is on")
paired("the sheet says outright that it cannot read their programmes",
       lambda s: "None of these publishes a programme this app can read" in s)



def uncommented(src):
    """The page with its own commentary taken out.

    The first version of the next check read the whole file and went red on the comment
    that explains why the feature is NOT called "free tonight" -- a check that cannot
    tell a claim from a note about a claim is checking the wrong text. Only whole-line
    `//` comments are dropped, so a `https://` inside a string is untouched.
    """
    return "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("//"))


check("the words 'free tonight' are in no string the page can render, "
      "because that is the one claim it cannot make",
      not re.search(r"free tonight", uncommented(NOW), re.I))
check("and the check is looking at text that could have carried it",
      "free screens" in uncommented(NOW).lower())
# The audits carry weekdays in prose -- "Thursdays 17:00", "(e.g. Saturdays 13:00)" -- and
# lifting those onto a row would turn an example into a timetable. Nothing here parses them.
check("no weekday is parsed out of the audit prose for these rows",
      "freeRows" in NOW and not re.search(
          r"freeRows[\s\S]{0,900}?(Mon|Tue|Wed|Thu|Fri|Sat|Sun)day", NOW))

print("\nsection 3 -- the caption is a legend for something on the map")
paired("free venues get the palette's own free colour", lambda s:
       'const CAT = v => /free/i.test(String(v.price || "")) ? "var(--c-free)"' in s)
check("which was defined and used by nothing before", "--c-free" in BEFORE
      and len(re.findall(r"var\(--c-free\)", BEFORE)) == 0)
paired("and the button is painted in it too, so the pill and the dots agree",
       lambda s: re.search(r"\.mapfree\{[^}]*color:var\(--c-free\)", s) is not None)
# Green still has to mean something afterwards, or one colour has been replaced by another
# rather than split in two.
indie_paid = [p for p in prices if not re.search("free", p, re.I)]
check("paying independents are still their own colour", 'v.grp === "indie" ? "var(--c-art)"' in NOW)
check("and there are some of them left to be it", len(indie_paid) > 0)

print("\nsection 4 -- the sheet holds together")
paired("an action bar with nothing in it is not drawn",
       lambda s: ".sheet .go:empty{display:none}" in s)
paired("a row inside it opens that venue rather than redrawing the list",
       lambda s: 'if (e.target.closest("#freebtn")) return freeSheet();' in s
       and s.index('const ven = e.target.closest("[data-venue]")')
       < s.index('if (e.target.closest("#freebtn"))'))
check("the button is in the map pane and not somewhere it makes no sense",
      NOW.index('id="freebtn"') > NOW.index('id="pane-map"')
      and NOW.index('id="freebtn"') < NOW.index('id="pane-films"'))

print("\nsection 5 -- nothing was broken on the way past")
check("the page is still one document",
      NOW.count("<body>") == 1 and NOW.rstrip().endswith("</body></html>"))
check("no anchor was replaced twice",
      NOW.count("function freeSheet(") == 1 and NOW.count('class="mapfree') == 1
      and NOW.count("const CAT = v =>") == 1)
check("the file grew rather than shrank", len(NOW) > len(BEFORE))

sw_now = open(os.path.join(ROOT, "docs", "sw.js"), encoding="utf-8").read()
v_now = re.search(r'const V = "(sala-v\d+)"', sw_now).group(1)
v_was = re.search(r'const V = "(sala-v\d+)"', at(BASELINE, "docs/sw.js")).group(1)
print("  (cache version %s, was %s)" % (v_now, v_was))
check("the cache name moved, or an installed phone keeps the old build", v_now != v_was)

print()
if fails:
    print("%d FAILED" % len(fails))
    for f in fails:
        print("   - " + f)
    sys.exit(1)
print("all controls pass")
