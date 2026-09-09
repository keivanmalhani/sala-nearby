#!/usr/bin/env python3
"""Controls for the UI pass, each of which fails on the page as it stood before it.

    /opt/homebrew/bin/python3 test-ui-pass.py

A styling change is the easiest kind of work to claim and the hardest to verify, because
nothing throws and the page still renders. So every check here is paired: the assertion
against the page on disk, and the same assertion against `git show HEAD~1:docs/index.html`,
which is required to FAIL. A check that passes on both versions is testing nothing.

The one thing this cannot check is whether it looks better, which is why the screenshots
at 390x844 in both themes are the real review and this is only the floor under them.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

NOW = open(PAGE, encoding="utf-8").read()
BEFORE = subprocess.run(
    ["git", "-C", ROOT, "show", "HEAD:docs/index.html"],
    capture_output=True, text=True, check=True).stdout

fails = []


def check(name, ok):
    print("  %-4s %s" % ("ok" if ok else "FAIL", name))
    if not ok:
        fails.append(name)


def paired(name, fn):
    """fn(src) -> bool. Required true on the page now and false on the page before."""
    a, b = fn(NOW), fn(BEFORE)
    check(name, a)
    check("   ... and it was not true before, so the check can fail", not b)


print("section 1 -- the install banner cannot cover a sheet")
# It was z-index 1200 against the sheet's 901, so the banner landed on top of whatever he
# had just opened. Read both numbers out of the page rather than restating them.
def sheet_z(src):
    m = re.search(r"\.sheet\{[^}]*?z-index:(\d+)", src)
    return int(m.group(1)) if m else -1


def banner_z(src):
    m = re.search(r'"position:fixed;left:12px;right:12px;bottom:calc\(env\(safe-area-inset-bottom,0px\) \+ 70px\);"\s*\+\s*"z-index:(\d+)', src)
    return int(m.group(1)) if m else -1


print("  (sheet z-index %d, banner z-index %d; before: %d and %d)"
      % (sheet_z(NOW), banner_z(NOW), sheet_z(BEFORE), banner_z(BEFORE)))
check("both numbers were actually found in the page", sheet_z(NOW) > 0 and banner_z(NOW) > 0)
paired("the banner sits below the sheet", lambda s: 0 < banner_z(s) < sheet_z(s))

# And it does not arrive on a bare timer over an open sheet.
paired("the iOS prompt waits for an open sheet to close",
       lambda s: 'aria-hidden") === "false"' in s and "clearInterval(iv)" in s)

print("\nsection 2 -- the synopsis does not own the sheet")
paired("the synopsis is clamped to three lines",
       lambda s: "-webkit-line-clamp:3" in s)
paired("and there is a class that un-clamps it",
       lambda s: ".sheet .syn.open p{-webkit-line-clamp:unset" in s)
paired("the toggle is delegated rather than bound per open",
       lambda s: 'e.target.closest(".sheet .syn .more")' in s)
# A "more" button that reveals nothing is a small lie, so it is conditional on length.
paired("the toggle is only offered when something is actually hidden",
       lambda s: "syn.length > 150" in s)

print("\nsection 3 -- the poster is behind its own header")
paired("the sheet header carries a backdrop element",
       lambda s: ".sheet .poshead .bd{" in s)
paired("under a scrim that lands on the sheet's own surface colour",
       lambda s: ".sheet .poshead .sc{" in s and "var(--surface) 100%" in s)
# 33 of the 73 films have no artwork -- Cineteca publishes none -- and a tinted empty box
# is worse than the header they had.
paired("and only where there is artwork to make one from",
       lambda s: re.search(r"const bd = hasArtwork\(fid\)\s*\n?\s*\?", s) is not None)

print("\nsection 4 -- the loud amber button is the cinema's, not the film's")
# Both cinema sheets keep `pri`; the film sheet's walk link gives it up. Count them.
def pri_walk_links(src):
    return len(re.findall(r'<a class="pri" href="\$\{gmaps\(', src))


print("  (%d walk links carry the primary style now, %d before)"
      % (pri_walk_links(NOW), pri_walk_links(BEFORE)))
paired("exactly the two cinema sheets keep it", lambda s: pri_walk_links(s) == 2)
paired("and the film sheet's link names the cinema instead of 'the nearest'",
       lambda s: ">Walk to ${esc(rows[0][0].n)}" in s)

print("\nsection 5 -- the film row separates the film from the geography")
paired("there is a line of its own for where it is playing",
       lambda s: ".frow .at{" in s)
paired("and the row no longer runs 'nearest' into the film's own facts",
       lambda s: '"&middot; nearest " + esc(r.near.n)' not in s)
# Metres and walking minutes are the same fact: walkMin() computes one from the other.
paired("the list carries the walking time and not both units",
       lambda s: re.search(r'<span class="at"><b>\$\{esc\(r\.near\.n\)\}</b>\$\{[\s\S]{0,600}?F \? ` <span>\$\{esc\(F\.w\)\}</span>`', s) is not None)

print("\nsection 6 -- the service worker will actually hand out the new build")
# Bumping the version is not sufficient on its own, but not bumping it is fatal: the shell
# is served from the cache and he would see the old page for another launch.
def swv(path_src):
    m = re.search(r'const V = "(sala-v\d+)"', path_src)
    return m.group(1) if m else None


sw_now = open(os.path.join(ROOT, "docs", "sw.js"), encoding="utf-8").read()
sw_before = subprocess.run(["git", "-C", ROOT, "show", "HEAD:docs/sw.js"],
                           capture_output=True, text=True, check=True).stdout
print("  (cache version %s, was %s)" % (swv(sw_now), swv(sw_before)))
check("the cache version moved with the page", swv(sw_now) != swv(sw_before))

print("\nsection 7 -- nothing was broken on the way past")
# The three things a text-substitution pass can silently destroy in a single-file app.
check("the page still parses as one document",
      NOW.count("<body>") == 1 and NOW.rstrip().endswith("</body></html>"))
check("no anchor was replaced twice, leaving a duplicated block",
      NOW.count("const bd = hasArtwork(fid)") == 1
      and NOW.count(".sheet .poshead .sc{") == 1)
# The backdrop's selector legitimately appears three times: the rule itself, and one
# opacity override per way of asking for dark. Both overrides are needed -- a viewer who
# has chosen dark explicitly gets `data-theme`, and one who is on the system default gets
# only the media query -- so this asserts the shape rather than uniqueness.
check("the backdrop is declared once and re-tinted for both ways of asking for dark",
      NOW.count(".sheet .poshead .bd{position:absolute") == 1
      and NOW.count('.sheet .poshead .bd{opacity:.34}') == 2
      and '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .sheet .poshead .bd{' in NOW
      and ':root[data-theme="dark"] .sheet .poshead .bd{' in NOW)
check("the file did not shrink, which a bad replace would show as",
      len(NOW) > len(BEFORE) - 200)

print()
if fails:
    print("%d FAILED" % len(fails))
    for f in fails:
        print("   - " + f)
    sys.exit(1)
print("all controls pass")
