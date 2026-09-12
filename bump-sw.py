#!/usr/bin/env python3
"""Move the offline cache name on by one, so an installed phone takes the new page.

    python3 bump-sw.py

Every change to the page has to bump `const V` in docs/sw.js, or a phone that installed the
app keeps serving the old build. The patch scripts each do it inline; this is the same step
on its own, for the daily refresh on GitHub, which changes the listings without a patch.
"""
from __future__ import annotations

import os
import re
import sys

SW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "sw.js")
sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("docs/sw.js: cache name not found -- nothing bumped, an installed phone would keep the old page")
new = 'const V = "sala-v%d";' % (int(m.group(1)) + 1)
open(SW, "w", encoding="utf-8").write(sw.replace(m.group(0), new, 1))
print("sw cache now", new)
