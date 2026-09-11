#!/usr/bin/env python3
"""Is every drinks claim on the page a sentence that is actually in the audit?

    /opt/homebrew/bin/python3 test-bar.py

This guards the output of a local model, so it is deliberately built to need no model of
its own. The classification was made by qwen3:8b; what makes it safe to ship is not that
the model is trustworthy, it is that every row it produced can be checked against the
text it claims to have read, by a program, after the fact.

WHAT WOULD GO WRONG WITHOUT IT. A model that answers yes and invents its evidence is
indistinguishable from one that read carefully, and the failure would appear on his
screen as a sentence about a cinema he is standing outside. So: every quote in the table
has to appear, word for word and on word boundaries, in that venue's own write-up, and
every venue named has to be a venue that exists.

Section 4 is the pair that makes this a test rather than a restatement -- the same checks
run against the page as it stood before the change, where the table does not exist at all.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
BASELINE = "b884f10"  # a fixed commit, never HEAD

sys.path.insert(0, ROOT)
import bar as barmod  # noqa: E402  -- reuses the same reader the classifier used

SRC = open(PAGE, encoding="utf-8").read()
BEFORE = subprocess.run(["git", "-C", ROOT, "show", "%s:docs/index.html" % BASELINE],
                        capture_output=True, text=True, check=True).stdout

fails = 0


def check(name, ok):
    global fails
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        fails += 1


texts = barmod.venue_texts()
table = json.load(open(os.path.join(ROOT, "docs", "bar.json"), encoding="utf-8"))

print("section 1 -- the table is on the page and matches the file beside it")
check("the page carries a BAR table", "const BAR={" in SRC)
check("the venue sheet has a Drinks row", "<dt>Drinks</dt>" in SRC)
onpage = re.search(r"const BAR=\{(.*?)\n\};", SRC, re.S)
check("the table parses", onpage is not None)
if onpage:
    parsed = json.loads("{" + onpage.group(1).rstrip(",") + "}")
    check("the page and docs/bar.json say the same thing", parsed == table)

print("\nsection 2 -- every quote is genuinely in that venue's write-up")
print("  (%d venues carry a drinks claim, out of %d)" % (len(table), len(texts)))
for name, quote in sorted(table.items()):
    check("%-44s is a venue that exists" % name[:44], name in texts)
    if name not in texts:
        continue
    q, t = barmod.squash(quote), barmod.squash(texts[name])
    check("   ... and %r is word for word in it" % quote[:46],
          bool(re.search(r"\b%s\b" % re.escape(q), t)))

print("\nsection 3 -- the page does not make the stronger claim it cannot support")
# A venue missing from the table is one whose audit says nothing about a drink. The page
# must not turn that into "no bar", because the audit never established it.
check("nothing on the page says a venue has no bar",
      "No bar" not in SRC and "no bar on site" not in SRC.lower())
check("the drinks row only ever appears with a quote behind it",
      SRC.count("<dt>Drinks</dt>") == 1 and "BAR[v.name] ?" in SRC)

print("\nsection 4 -- and none of this was true at %s, so the checks can fail" % BASELINE)
check("the baseline has no BAR table", "const BAR={" not in BEFORE)
check("the baseline has no Drinks row", "<dt>Drinks</dt>" not in BEFORE)
check("so the seven venues that serve a drink were unreachable on screen", True
      if "Cine Tonala" in BEFORE and "<dt>Drinks</dt>" not in BEFORE else False)

print("\n%s" % ("%d FAILED" % fails if fails else "all checks pass"))
sys.exit(1 if fails else 0)
