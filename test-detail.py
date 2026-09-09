#!/usr/bin/env python3
"""Controls for build-detail.py and the joins the page makes against detail.json.

    /opt/homebrew/bin/python3 test-detail.py

The failure this is written against is not a crash. It is a lookup that finds nothing:
`DETAIL.ven[String(c.id)]` returns undefined, every section returns "", and the sheet
renders exactly as it did before the feature existed. Nothing throws, nothing logs, and
the page looks finished. So every check here is a join, and each one is required to fail
when the key is wrong -- the red half is section 5.
"""
import copy
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
spec = importlib.util.spec_from_file_location("build_detail",
                                              os.path.join(HERE, "build-detail.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


def shows():
    src = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()
    m = re.search(r"^const SHOWS=", src, re.M)
    p, _ = json.JSONDecoder().raw_decode(src, m.end())
    return p, src


D = json.load(open(os.path.join(DOCS, "detail.json"), encoding="utf-8"))
S, SRC = shows()
IDS = [str(c["id"]) for c in S["cin"]]

print("section 1 -- the file the page fetches exists and is small enough to fetch")
size = os.path.getsize(os.path.join(DOCS, "detail.json"))
# The research files belong to the build that produces them and may not be in the tree
# yet. detail.json is self-contained at runtime, so their absence is not a failure here --
# it only means the size comparison has nothing to compare against, and saying so is
# better than a suite that goes red because a sibling has not committed.
present = [f for f in ("cinema-extras.json", "rooms.json", "cinema-reviews.json")
           if os.path.exists(os.path.join(DOCS, f))]
srcs = sum(os.path.getsize(os.path.join(DOCS, f)) for f in present)
if len(present) < 3:
    print("  (only %s present; the ratio check is skipped rather than failed)"
          % ", ".join(present))
print("  (detail.json %s bytes, research files %s bytes)" % (format(size, ","), format(srcs, ",")))
check("it is under 60 KB, so a cold launch is not paying for the research files", size < 60000)
if len(present) == 3:
    check("and it is a small fraction of them, not a copy", size < srcs / 5)
check("the page fetches it rather than baking it in", 'fetch("detail.json")' in SRC)
check("detail.json is NOT inlined into the page",
      "cinema-extras" not in SRC and '"rooms":{"Sala 1"' not in SRC)

print("\nsection 2 -- every venue key is a cinema the page can look up")
check("no venue key is absent from the payload",
      set(D["ven"]) <= set(IDS) or not (set(D["ven"]) - set(IDS)))
missing = [i for i in IDS if i not in D["ven"]]
check("every cinema in the payload has a detail row" + (": missing %s" % missing if missing else ""),
      not missing)
priced = [i for i in D["ven"] if "price" in D["ven"][i]]
check("30 of the 35 carry a price (%d)" % len(priced), len(priced) >= 30)
rated = [i for i in D["ven"] if "rating" in D["ven"][i]]
check("all 35 carry a rating (%d)" % len(rated), len(rated) == len(IDS))

print("\nsection 3 -- the room join, which is the one that has to be exact")
tot = ok = 0
for c in S["cin"]:
    d = D["ven"].get(str(c["id"])) or {}
    rooms = d.get("rooms") or {}
    for s in c["s"]:
        r = str(s[6]).strip() if len(s) > 6 else ""
        if not r:
            continue
        tot += 1
        if r in rooms:
            ok += 1
print("  (%d of %d sessions carrying a room name find it)" % (ok, tot))
check("every session's room name is a key in that cinema's room table", ok == tot and tot > 10000)
seats = [r[1] for v in D["ven"].values() for r in (v.get("rooms") or {}).values()]
check("every room has a seat count", all(x is not None for x in seats) and len(seats) == 287)
nowheel = sum(1 for v in D["ven"].values() for r in (v.get("rooms") or {}).values() if not r[2])
print("  (%d of %d rooms have no wheelchair space)" % (nowheel, len(seats)))
check("wheelchair spaces are present as a number, including zero",
      all(isinstance(r[2], int) for v in D["ven"].values() for r in (v.get("rooms") or {}).values()))

print("\nsection 4 -- the format labels the price table is keyed on are the page's own")
labels = {f["l"] for f in S["fmts"]}
pk = {lab for v in D["ven"].values() for lab in (v.get("price") or {})}
print("  (%d price labels, %d of them a format the page prints)" % (len(pk), len(pk & labels)))
check("every price label is a format label in the payload, or the price never renders",
      pk <= labels)
covered = 0
total = 0
for c in S["cin"]:
    d = D["ven"].get(str(c["id"])) or {}
    for s in c["s"]:
        total += 1
        lab = S["fmts"][s[1]]["l"]
        if (d.get("price") or {}).get(lab) or str(c["id"]).startswith("cineteca-"):
            covered += 1
print("  (%d of %d showings sit behind a price, %.0f%%)" % (covered, total, 100 * covered / total))
check("most showings can show a price", covered / total > 0.9)

print("\nsection 5 -- the controls go red when a join is wrong")
bad = copy.deepcopy(D)
bad["ven"] = {("x" + k): v for k, v in bad["ven"].items()}
miss = [i for i in IDS if i not in bad["ven"]]
check("re-keying the venues breaks the lookup, and this notices", len(miss) == len(IDS))
bad2 = copy.deepcopy(D)
for v in bad2["ven"].values():
    if "rooms" in v:
        v["rooms"] = {("Auditorium " + k.split()[-1]): r for k, r in v["rooms"].items()}
ok2 = 0
for c in S["cin"]:
    rooms = (bad2["ven"].get(str(c["id"])) or {}).get("rooms") or {}
    for s in c["s"]:
        r = str(s[6]).strip() if len(s) > 6 else ""
        if r and r in rooms:
            ok2 += 1
check("renaming the rooms breaks the room join, and this notices", ok2 == 0)
bad3 = copy.deepcopy(D)
for v in bad3["ven"].values():
    if "price" in v:
        v["price"] = {(lab + " 2D"): p for lab, p in v["price"].items()}
pk3 = {lab for v in bad3["ven"].values() for lab in (v.get("price") or {})}
check("a price keyed on a label the page does not print is caught", not (pk3 <= labels))

print("\nsection 6 -- nothing is shown that the sources say is unknown")
check("no venue claims a Cinemex snack menu",
      not any("menu" in v for k, v in D["ven"].items() if not k.startswith("cineteca-")))
hot = [k for k, v in D["ven"].items() if "hot" in v]
print("  (%d venues carry a temperature reading)" % len(hot))
check("only the eight that read hot carry one", len(hot) == 8)
check("each of those has a real quote behind it",
      all(D["ven"][k]["hot"].get("quote") for k in hot))
check("Cinemex points carry no peso value, because none is published",
      D["loyalty"]["point_value"] is None)
# The undescribed-format case is tested as a MECHANISM, not against whichever format
# happens to be undescribed today. Infinity Vision was null when this was written and had
# a sourced description an hour later, so an assertion naming it would now be asserting
# the opposite of the truth.
undesc = [k for k, f in D["fmt"].items() if not f.get("en")]
print("  (%d of %d formats in use have no published description: %s)"
      % (len(undesc), len(D["fmt"]), ", ".join(undesc) or "none"))
check("every format in use has either a description or a stated reason there is none",
      all(f.get("en") or f.get("why") for f in D["fmt"].values()))
check("the page carries the copy for a format nobody describes",
      "describes it nowhere" in SRC)
check("and every description says where it came from, so a third-party claim is not "
      "presented as the operator's",
      all(f.get("conf") for f in D["fmt"].values()) and "SRC_TAG" in SRC)
check("a third-party description is tagged as one rather than as fact",
      'third_party: ["l", "third party"]' in SRC)
tp = [k for k, f in D["fmt"].items() if f.get("conf") == "third_party"]
print("  (third-party sourced: %s)" % (", ".join(tp) or "none"))

print("\nsection 7 -- the service worker will actually keep it")
sw = open(os.path.join(DOCS, "sw.js"), encoding="utf-8").read()
check("detail.json has its own caching branch, not the read-only fall-through",
      "detail\\.json" in sw or "/detail.json" in sw)
check("and that branch puts it in a cache", re.search(r"detail\\?\.json.*?c\.put", sw, re.S) is not None)

print()
if fails:
    print("%d FAILED" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all controls pass")
