#!/usr/bin/env python3
"""Controls for build-detail.py and the joins the page makes against detail.json.

    /opt/homebrew/bin/python3 test-detail.py

The failure this is written against is not a crash. It is a lookup that finds nothing:
`DETAIL.ven[String(c.id)]` returns undefined, every section returns "", and the sheet
renders exactly as it did before the feature existed. Nothing throws, nothing logs, and
the page looks finished. So every check here is a join, and each one is required to fail
when the key is wrong -- the red half is section 5.
"""
import collections
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

print("\nsection 7 -- a confidence label the page has never seen still gets a tag")
# cinema-data's warning, and it was right: this vocabulary is prose in a research file and
# it GREW from eight members to ten while the feature was being built. The two that
# arrived, format_level_inference and third_party_expired_page, are among the ones most in
# need of a hedge. A lookup that returns "" for an unrecognised label renders the
# strongest possible version of a claim: a bare sentence with nothing beside it.
ex = json.load(open(os.path.join(DOCS, "cinema-extras.json"), encoding="utf-8"))
vocab = set(ex["formats"]["vocabulary"])
mapped = set(re.findall(r"^\s{2}([a-z_]+):\s*\[\"[vlu]\"", SRC, re.M))
print("  (vocabulary has %d labels, the page maps %d)" % (len(vocab), len(mapped)))
unmapped = sorted(vocab - mapped)
check("every label in the vocabulary is mapped" + (": %s" % unmapped if unmapped else ""),
      not unmapped)
check("and the two that arrived late are among them",
      {"format_level_inference", "third_party_expired_page"} <= mapped)
# The red half: the fallback has to be reachable and has to produce a tag.
m = re.search(r"function srcTag\(conf\) \{(.*?)\n\}", SRC, re.S)
body = m.group(1) if m else ""
check("srcTag has a fallback branch at all", 'return `<span class="tag' in body.split("if (t)")[-1])
check("and the fallback renders the label rather than an empty string",
      "replace(/_/g" in body)
check("an absent confidence is the only case that renders nothing",
      body.strip().startswith("if (!conf) return \"\";"))
used = set(f.get("conf") for f in D["fmt"].values() if f.get("conf"))
check("every confidence in the live data is one the page maps: %s" % sorted(used),
      used <= mapped)

print("\nsection 8 -- the room table claims nothing about format")
# The ideas report proposed a per-sala format table. The fetched data disproves that
# shape: Parque Delta Sala 10 runs Atmos on 72 of 76 showtimes and plain Espanol
# Tradicional on the other four, so a room labelled by format mislabels real screenings.
# Format belongs to the showtime. This asserts the room data carries no format at all.
for vid, v in D["ven"].items():
    for name, r in (v.get("rooms") or {}).items():
        assert len(r) == 4, (vid, name, r)
check("a room record is exactly screen, seats, wheelchair, rows -- no format field",
      all(len(r) == 4 for v in D["ven"].values() for r in (v.get("rooms") or {}).values()))
check("no format-per-room list survived into the page's data",
      "formats_run_here" not in json.dumps(D))
rooms_src = json.load(open(os.path.join(DOCS, "rooms.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(DOCS, "rooms.json")) else None
if rooms_src:
    # rows must be the LETTERED row count, not len(layout): spacer entries inflate that,
    # and Antara Platino Sala 5 has 7 spacers against 8 real rows.
    bad = [(v["name"], rm["room"]) for v in rooms_src["venues"].values() for rm in v["rooms"]
           if rm.get("rows") != len(rm.get("row_names") or [])]
    check("the row count is the lettered rows, not the layout length" +
          (": %s" % bad[:3] if bad else ""), not bad)
    comp = {rm.get("companion_spaces") for v in rooms_src["venues"].values() for rm in v["rooms"]}
    check("companion spaces are zero everywhere, so the page states there are none rather "
          "than printing a column of zeros",
          comp == {0} and "companion seat" in SRC and "Companion" not in
          (re.search(r"<thead>.*?</thead>", SRC, re.S).group(0) if re.search(r"<thead>", SRC) else ""))
    alloc = {rm.get("assigned_seating") for v in rooms_src["venues"].values() for rm in v["rooms"]}
    check("assigned seating is universal, and the page says so without calling it a perk",
          alloc == {True} and "not something Platino or Premium buys you" in SRC)
check("the wheelchair line is about the seat map, not about the building",
      "fact about the seat map" in SRC and "cannot be got into" in SRC)

print("\nsection 9 -- Infinity Vision follows the film, measured from the payload")
# A newspaper says this is a Disney film certification rather than a Cinemex room type.
# The payload the page ships can check it, so the page states the measurement beside the
# claim instead of resting on the claim alone.
iv = [i for i, f in enumerate(S["fmts"]) if "infinity-vision" in (f.get("t") or [])]
sess = [(c, x) for c in S["cin"] for x in c["s"] if x[1] in iv]
films = {str(x[0]) for _, x in sess}
rooms = {(c["n"], str(x[6] or "")) for c, x in sess}
print("  (%d showings, %d film, %d rooms)" % (len(sess), len(films), len(rooms)))
check("it is on exactly one film, which is what makes it a film badge", len(films) == 1)
check("and on more than one room, or the question would not arise", len(rooms) > 1)
unflagged_everywhere = True
for cn, room in rooms:
    other = sum(1 for c in S["cin"] if c["n"] == cn
                for x in c["s"] if str(x[6] or "") == room and x[1] not in iv)
    if not other:
        unflagged_everywhere = False
check("every room carrying it also runs films without it -- so it is not the room",
      unflagged_everywhere)
check("the page derives that sentence rather than hardcoding it", "function ivFact()" in SRC)
check("and it withdraws the sentence if more than one film ever carries it",
      "films.size !== 1) return \"\"" in SRC)
check("and if a room ever runs nothing else", "if (!other) return \"\";" in SRC)
# The complex-level key is a dead entry in Cinemex's own dictionary -- applied to zero
# cinemas nationally -- so the page must never render it in place of the screening key.
comp = ex["formats"]["complex_attributes"].get("Infinity Vision")
check("the source still carries the dead complex-level entry", comp is not None)
check("but the page's dictionary uses the screening key, which is the one in the payload",
      "infinity-vision" in D["fmt"] and "Infinity Vision" not in D["fmt"])
check("and the screening key is the one carrying the description",
      bool(D["fmt"]["infinity-vision"].get("en")))

print("\nsection 10 -- an audit claim about a room is checked against the showtimes")
# A `verified` badge is a promise about how a fact was established, and one was sitting on
# "Sala 10 CinemeXtremo" while no showtime in the operator's own data carries that format.
V_BLOCK = SRC[SRC.index("const V=["):SRC.index("const PLAIN=")]
spec_rows = re.findall(r'\["([^"]+)","((?:[^"\\]|\\.)*)","([vlu])"\]', V_BLOCK)
print("  (%d audit rows across the venues)" % len(spec_rows))
# The rule must match the CLAIM'S SHAPE, not a format name. A rule that flagged any row
# naming a zero-showtime format hit 12 rows and 9 were fine -- "No Atmos, CX or IMAX sala"
# is a denial, and one row is titled "What it is not".
sala_is = re.compile(r"[Ss]ala\s*(\d+)\s*=?\s*(?:with\s+)?(CinemeXtremo|Infinity Vision|Dolby Atmos|IMAX|Platino|Premium|Atmos)")
asserts = [r for r in spec_rows if sala_is.search(r[1])]
denials = [r for r in spec_rows if re.search(r"\bNo (Atmos|VIP|IMAX)", r[1])]
print("  (%d rows assert a sala is a format, %d rows deny a format)"
      % (len(asserts), len(denials)))
check("some rows assert a sala is a format, or there is nothing to check", len(asserts) >= 3)
check("no denial is caught by the assertion rule",
      not [r for r in denials if sala_is.search(r[1])])
check("the page matches the claim shape rather than the format name",
      "SALA_IS" in SRC and "IS_IN_SALA" in SRC)
check("a new label was added for it rather than reusing the nearest fit",
      'named_not_in_times: ["l", "not in the showtimes"]' in SRC)
check("a venue with no showtimes here cannot be contradicted by them",
      "!cins.some(c => c.s.length)) return null" in SRC)
# THE POOLING BUG, which this had on its first run: an audited building can be two cinema
# rows whose sala names collide completely, and summing them reported Sala 3 as IMAX on
# 75 of 156 showings when it is 75 of 75 in the room the audit means.
check("the room check is per cinema row, never pooled across an audited building",
      "const per = cins.map(c =>" in SRC and "per.length > 1" in SRC)
byv = collections.defaultdict(list)
for c in S["cin"]:
    if c.get("v") is not None:
        byv[c["v"]].append(c)
shared = {vi: rows for vi, rows in byv.items() if len(rows) > 1}
print("  (%d audited buildings are two cinema rows each)" % len(shared))
check("such buildings exist, so the pooling bug was reachable", len(shared) >= 1)
collide = 0
for vi, rows in shared.items():
    names = [{str(x[6]).strip() for x in c["s"] if len(x) > 6 and str(x[6]).strip()} for c in rows]
    if names[0] & names[1]:
        collide += 1
check("and their sala names collide, which is what made it wrong (%d of %d)"
      % (collide, len(shared)), collide == len(shared))

print("\nsection 11 -- the service worker will actually keep it")
sw = open(os.path.join(DOCS, "sw.js"), encoding="utf-8").read()
check("detail.json has its own caching branch, not the read-only fall-through",
      "detail\\.json" in sw or "/detail.json" in sw)
check("and that branch puts it in a cache", re.search(r"detail\\?\.json.*?c\.put", sw, re.S) is not None)

print("\nsection 12 -- the page cannot claim a price was read in the future")
# It did. "One adult ticket, read from Cinemex's own checkout on 2026-09-11" on a page
# built on the 9th. The upstream field is `day_read` and it is the day of the SESSION
# whose checkout was opened -- the keys beside it are a session_id, an auditorium and a
# seat count -- so the sentence had the wrong subject, not the data the wrong value.
built = D.get("at", "")[:10]
days = sorted({d for v in D["ven"].values() for d in v.get("priced_session_day", [])})
print("  (detail.json built %s; sessions priced against %s)" % (built, ", ".join(days) or "none"))
check("the build date is there to compare against", len(built) == 10)
check("some venue carries a priced-session day", bool(days))
check("the field is no longer named as though it were the day of the reading",
      not any("price_read" in v for v in D["ven"].values()))
# The whole point: a session day AFTER the build date is normal and expected, because you
# price a screening that has seats left. It is only wrong when the page calls it a reading.
future = [d for d in days if d > built]
print("  (%d of %d priced sessions are later than the build, which is fine)"
      % (len(future), len(days)))
check("the page states the build date as the day of the reading",
      'DETAIL && DETAIL.at ? " on " + esc(DETAIL.at.slice(0, 10))' in SRC)
check("and names the session day as a session rather than a reading",
      "against a session on" in SRC)
check("the old sentence is gone",
      "read from Cinemex's own checkout on\n" not in SRC
      and "(d.price_read || [])" not in SRC)
# The red half: the sentence this replaced would put a future date after the word "on".
check("that sentence would have been the impossible claim, so this can fail",
      bool(future) or built in days)

print()
if fails:
    print("%d FAILED" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all controls pass")
