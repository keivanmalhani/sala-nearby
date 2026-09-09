#!/usr/bin/env python3
"""The offline promise, checked statically and then actually measured.

    /opt/homebrew/bin/python3 test-offline-lib.py

Two halves, and the second is the one that matters. The static half guards the thing that
will silently rot: sw.js warms three URLs by hand and index.html loads them, and a version
bump in one and not the other leaves the app caching a library it no longer uses. The
runtime half opens a headless browser, loads the app once with a signal, clears the
browser's own HTTP cache, cuts the network and reloads -- which is the only way to tell
the service worker apart from the disk cache, and telling those apart is exactly what was
wrong.

The server is started here if it is not already up, because a control that skips is not a
control that passed.
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
PAGE = os.path.join(DOCS, "index.html")
SW = os.path.join(DOCS, "sw.js")
PORT = 8899

# The commit immediately before the offline fix.
BASELINE = "d5a0d2a"
NOW = open(PAGE, encoding="utf-8").read()
SWNOW = open(SW, encoding="utf-8").read()


def at(rev, path):
    return subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (rev, path)],
                          capture_output=True, text=True, check=True).stdout


fails = []


def check(name, ok, detail=""):
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", name, ("  (%s)" % detail) if detail else ""))
    if not ok:
        fails.append(name)


print("section 1 -- the page asks for its three outside files in a mode the worker can cache")
# A plain cross-origin <script> or <link> is a no-cors request, so `fetch` inside the
# worker resolves to an opaque response -- status 0, ok false -- and every branch in sw.js
# correctly refuses to store one. crossorigin is what turns it into a real response.
TAGS = [
    ("the MapLibre script", r'<script crossorigin="anonymous" src="https://cdnjs\.cloudflare\.com[^"]*maplibre-gl\.min\.js">'),
    ("the MapLibre stylesheet", r'<link rel="stylesheet" crossorigin="anonymous" href="https://cdnjs\.cloudflare\.com[^"]*maplibre-gl\.min\.css">'),
    ("the Google Fonts stylesheet", r'<link rel="stylesheet" crossorigin="anonymous" href="https://fonts\.googleapis\.com[^"]*">'),
]
BEFORE = at(BASELINE, "docs/index.html")
for name, pat in TAGS:
    check(name + " carries crossorigin", re.search(pat, NOW) is not None)
    check("   ... and did not at %s, so the check can fail" % BASELINE,
          re.search(pat, BEFORE) is None)
# And nothing that actually FETCHES A RESOURCE was left behind without it. Scoped to
# scripts and stylesheets on purpose: `<link rel="preconnect">` opens a socket and
# downloads nothing, so it has no response to cache and needs no crossorigin. The first
# version of this check matched the preconnect and went red on a line that is correct.
left = [t for t in re.findall(r'<(?:script|link)\b[^>]*>', NOW)
        if re.search(r'(?:src|href)="https://(?:cdnjs|fonts\.googleapis)', t)
        and "crossorigin" not in t
        and ("<script" in t or 'rel="stylesheet"' in t)]
check("no cross-origin script or stylesheet is left without it", not left, "; ".join(left)[:90])
# The check has to be able to see a tag at all, or it is passing on an empty list.
check("and it is looking at tags that could have carried one",
      len([t for t in re.findall(r'<(?:script|link)\b[^>]*>', NOW)
           if re.search(r'(?:src|href)="https://', t)]) >= 4)

print("\nsection 2 -- sw.js warms exactly what the page loads")
warm = re.search(r"const LIB_WARM = \[(.*?)\];", SWNOW, re.S)
check("the warm list is in the worker", warm is not None)
urls = re.findall(r'"(https://[^"]+)"', warm.group(1)) if warm else []
print("  (%d warmed urls)" % len(urls))
check("there are three of them", len(urls) == 3)
for u in urls:
    # THE DRIFT GUARD. A MapLibre version bump in the page and not here would leave the
    # app dutifully caching a library it does not load, and the map would still work --
    # out of the browser cache, which is the bug this whole change is about.
    check("the page loads it verbatim: ..." + u[-46:], u in NOW)
sw_before = at(BASELINE, "docs/sw.js")
check("there was no warm list at %s, so the check can fail" % BASELINE,
      "LIB_WARM" not in sw_before)

print("\nsection 3 -- the warm cannot take the shell install down with it")
# addAll is atomic on purpose so a half-populated shell is impossible. A cdnjs hiccup must
# not be able to stop the app caching its own page, so each warm is fetched separately and
# a failure is dropped.
check("the warm is not inside the atomic addAll",
      re.search(r"c\.addAll\(PRECACHE[^)]*\)\)\)\s*\n\s*//", SWNOW) is not None
      or "addAll(LIB_WARM" not in SWNOW)
check("each url is fetched on its own and a failure is dropped",
      ".catch(() => null))" in SWNOW and "LIB_WARM.map(" in SWNOW)
check("and only a real response is stored", "r && r.ok ? c.put(u, r)" in SWNOW)

print("\nsection 4 -- what the phone-size pass found")
# The coarse-pointer block lifts every control in the app to 44 and says why. The
# free-screens pill went in at 38 and was not in it. Measured with those rules applied to
# a 390-point viewport, it was the only control in the app under the line.
coarse = NOW[NOW.index("@media (pointer:coarse){"):]
coarse = coarse[:coarse.index("\n}")]
check("the free-screens pill is in the coarse-pointer block", ".mapfree{min-height:44px}" in coarse)
check("   ... and was not at %s" % BASELINE,
      ".mapfree{min-height:44px}" not in at(BASELINE, "docs/index.html"))
# Every other control is already covered, and this asserts the block is the reason rather
# than luck: pull the rule for the time chips and the day chips out and read the number.
for sel, want in [(r"\.t\{min-height:(\d+)px", 44), (r"\.rail button\{min-height:(\d+)px", 44),
                  (r"\.iconbtn\{width:(\d+)px", 44)]:
    m = re.search(sel, coarse)
    check("the coarse block still lifts %s to %d" % (sel.split("{")[0].replace("\\", ""), want),
          m is not None and int(m.group(1)) >= want, m.group(1) + "px" if m else "not found")

# "from Thu 24 Sep - 7 dates 31" on one line and "cinemas" alone on the next, seen at 375
# and at 430. A count and the word it counts are one fact.
check("a count cannot be split from its noun",
      re.search(r"\.frow \.at span\{[^}]*white-space:nowrap", NOW, re.S) is not None)
check("   ... and could be at %s" % BASELINE,
      re.search(r"\.frow \.at span\{[^}]*white-space:nowrap",
                at(BASELINE, "docs/index.html"), re.S) is None)

print("\nsection 5 -- the cache name moved")
v_now = re.search(r'const V = "(sala-v\d+)"', SWNOW).group(1)
v_was = re.search(r'const V = "(sala-v\d+)"', sw_before).group(1)
check("the cache name moved, or an installed phone keeps the old build",
      v_now != v_was, "%s, was %s" % (v_now, v_was))

print("\nsection 6 -- and now measure it, rather than reading it")
served = subprocess.Popen if False else None
sock = socket.socket()
up = sock.connect_ex(("127.0.0.1", PORT)) == 0
sock.close()
proc = None
if not up:
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=DOCS,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        s2 = socket.socket()
        if s2.connect_ex(("127.0.0.1", PORT)) == 0:
            s2.close()
            break
        s2.close()
        time.sleep(0.25)
    print("  (started a server on %d for this run)" % PORT)
try:
    node = shutil.which("node")
    if not node:
        check("node is available to run the browser half", False)
    else:
        r = subprocess.run([node, os.path.join(ROOT, "tools", "offline-check.mjs")],
                           capture_output=True, text=True, cwd=ROOT, timeout=180)
        for line in r.stdout.rstrip().split("\n"):
            print("  | " + line)
        check("the app works offline after one launch, with the browser cache cleared",
              r.returncode == 0, (r.stderr or "").strip()[:120])
finally:
    if proc:
        proc.terminate()

print()
if fails:
    print("%d FAILED" % len(fails))
    for f in fails:
        print("   - " + f)
    sys.exit(1)
print("all controls pass")
