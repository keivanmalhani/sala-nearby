#!/usr/bin/env python3
"""Validate docs/cinema-extras.json.

    python3 test-cinema-extras.py              # check the real file
    python3 test-cinema-extras.py --selftest   # prove every check can go red

Six things it refuses, and each one is a way this file could quietly become wrong:

  1. A price that is a string. "$123.00" renders and never sorts, compares or adds up, and
     the bug shows up as a filter that silently matches nothing.
  2. A record with no `confidence`. The whole point of this file is that a reader can tell
     a quoted price from an inference; an uncovered record is a claim with no provenance.
  3. A `confidence` outside the declared vocabulary -- a typo makes a claim look weaker or
     stronger than it is.
  4. A venue id the app does not carry. A row nothing can render is dead weight that
     still has to be maintained, and it is how a neighbouring city's cinema gets in.
  5. A `source` naming an id that is not in `sources`. A dangling citation is worse than
     no citation, because it looks checked.
  6. A null price with no `note`. Null is allowed and is the honest answer for anything
     unsourced -- but a null with no reason beside it is indistinguishable from a bug.

`--selftest` plants one bad record per check and requires each to fire. A suite whose
checks cannot fail reports its own coverage as a number with nothing behind it.
"""

import argparse, copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "docs", "cinema-extras.json")
ROOMS = os.path.join(HERE, "docs", "rooms.json")
PAGE = os.path.join(HERE, "docs", "index.html")

# A dict holding any of these is asserting something about the world, so a `confidence`
# has to cover it -- on the dict itself or on one of its ancestors.
RECORD_MARKERS = {
    "price_mxn", "value_mxn", "adult_price_mxn", "cheapest_price_mxn", "general_mxn",
    "reduced_mxn", "price_mxn_low", "price_mxn_high", "points_accrual_percent",
    "plain_en", "available", "booking_fee_mxn",
}
PRICE_KEYS = {
    "price_mxn", "value_mxn", "adult_price_mxn", "cheapest_price_mxn", "general_mxn",
    "reduced_mxn", "price_mxn_low", "price_mxn_high", "booking_fee_mxn",
}
# Nulls that are a legitimate answer on their own, because the surrounding record already
# explains itself in prose. Everything else null needs a note.
PRICE_NULL_NEEDS_NOTE = {"value_mxn", "price_mxn"}



def vocabulary(doc):
    """The declared vocabulary is read out of the file, not restated here.

    Restating it would let the file and the validator drift apart and both look right --
    and the file explaining its own labels is the point of the section.
    """
    v = ((doc.get("formats") or {}).get("vocabulary")) or {}
    if not isinstance(v, dict) or len(v) < 3:
        sys.exit("formats.vocabulary is missing or implausibly small")


    return set(v)

VENUE_KEYED = [
    ("food_and_alcohol",),
    ("ticket_pricing", "cinemex", "venues"),
]


def app_venue_ids():
    page = open(PAGE, encoding="utf-8").read()
    i = page.find("const SHOWS=")
    if i < 0:
        sys.exit("docs/index.html has no SHOWS blob")
    j = page.find("\n", i)
    blob = json.loads(page[i + len("const SHOWS="):j].rstrip().rstrip(";"))
    return {str(c["id"]) for c in blob["cin"]}


def dig(doc, path):
    o = doc
    for p in path:
        if not isinstance(o, dict) or p not in o:
            return None
        o = o[p]
    return o


def check(doc, venues):
    vocab = vocabulary(doc)
    fails = []
    sources = set((doc.get("sources") or {}).keys())

    def walk(node, where, covered_by):
        if isinstance(node, dict):
            conf = node.get("confidence")
            if conf is not None:
                if conf not in vocab:
                    fails.append("%s: confidence %r is not in the declared vocabulary"
                                 % (where, conf))
                covered_by = where

            for k in ("source", "rules_source", "second_source"):
                v = node.get(k)
                if isinstance(v, str) and v not in sources:
                    fails.append("%s.%s: names source %r, which is not in `sources`"
                                 % (where, k, v))

            markers = RECORD_MARKERS & set(node)
            if markers and covered_by is None:
                fails.append("%s: asserts %s with no `confidence` covering it"
                             % (where, sorted(markers)))

            for k in PRICE_KEYS & set(node):
                v = node[k]
                if isinstance(v, str):
                    fails.append("%s.%s: price is a string (%r)" % (where, k, v))
                elif isinstance(v, bool):
                    fails.append("%s.%s: price is a boolean" % (where, k))
                elif v is None:
                    if k in PRICE_NULL_NEEDS_NOTE and not (node.get("note")
                                                           or node.get("why")):
                        fails.append("%s.%s: null price with no note saying why"
                                     % (where, k))
                elif not isinstance(v, (int, float)):
                    fails.append("%s.%s: price is %s, not a number"
                                 % (where, k, type(v).__name__))
                elif v < 0:
                    fails.append("%s.%s: negative price %r" % (where, k, v))

            for k, v in node.items():
                walk(v, "%s.%s" % (where, k), covered_by)
        elif isinstance(node, list):
            for n, v in enumerate(node):
                walk(v, "%s[%d]" % (where, n), covered_by)

    walk(doc, "$", None)

    for path in VENUE_KEYED:
        block = dig(doc, path)
        if not isinstance(block, dict):
            fails.append("%s: missing or not an object" % ".".join(path))
            continue
        for vid in block:
            if vid not in venues:
                fails.append("%s: venue id %r is not one docs/index.html carries"
                             % (".".join(path), vid))

    for pkg in (dig(doc, ("loyalty", "cinemex", "membership_packages")) or []):
        for vid in (pkg.get("price_mxn_by_venue") or {}):
            if vid not in venues:
                fails.append("loyalty package %r: venue id %r is not one the page carries"
                             % (pkg.get("name"), vid))

    declared = set((doc.get("app_venues") or {}).get("cinemex_ids") or []) | \
               set((doc.get("app_venues") or {}).get("cineteca_ids") or [])
    if declared != venues:
        fails.append("app_venues does not match the page: %s in the file only, %s in the "
                     "page only" % (sorted(declared - venues), sorted(venues - declared)))
    return fails


def check_rooms(doc, venues):
    """docs/rooms.json, on the same terms plus the arithmetic it can check itself.

    A seat count is the number this file exists to carry, so the parts have to add up to
    the total. Getting that wrong is the shape the earlier menu parser had -- a plausible
    number in the right field -- and a total that disagrees with its own breakdown is the
    one version of it a machine can catch.
    """
    fails = []
    sources = set((doc.get("sources") or {}).keys())
    ALLOWED = {"measured", "unknown", "operator_published", "third_party"}

    block = doc.get("venues")
    if not isinstance(block, dict):
        return ["rooms.json: `venues` is missing or not an object"]

    for vid, v in block.items():
        if vid not in venues:
            fails.append("rooms.json: venue id %r is not one docs/index.html carries" % vid)
        rooms = v.get("rooms")
        if not isinstance(rooms, list) or not rooms:
            fails.append("rooms.json %s: no rooms" % vid)
            continue
        if v.get("room_count") != len(rooms):
            fails.append("rooms.json %s: room_count %r but %d rooms listed"
                         % (vid, v.get("room_count"), len(rooms)))
        seen = set()
        for r in rooms:
            where = "rooms.json %s %s" % (vid, r.get("room"))
            if r.get("room") in seen:
                fails.append("%s: duplicate room -- the sweep did not deduplicate" % where)
            seen.add(r.get("room"))
            if r.get("confidence") not in ALLOWED:
                fails.append("%s: confidence %r not allowed here" % (where, r.get("confidence")))
            if isinstance(r.get("source"), str) and r["source"] not in sources:
                fails.append("%s: names source %r, not in `sources`" % (where, r["source"]))
            for k in ("seats_total", "seats_regular", "wheelchair_spaces",
                      "companion_spaces", "blank_cells", "rows"):
                x = r.get(k)
                if x is None:
                    continue
                if isinstance(x, bool) or not isinstance(x, int):
                    fails.append("%s.%s: %r is not an integer" % (where, k, x))
                elif x < 0:
                    fails.append("%s.%s: negative (%r)" % (where, k, x))
            parts = [r.get("seats_regular"), r.get("wheelchair_spaces"),
                     r.get("companion_spaces")]
            if r.get("seats_total") is not None and all(isinstance(p, int) for p in parts):
                if sum(parts) != r["seats_total"]:
                    fails.append("%s: seats_total %r but regular+wheelchair+companion is %d"
                                 % (where, r["seats_total"], sum(parts)))
            if r.get("seats_total") in (0, None) and not (r.get("note") or r.get("why")):
                fails.append("%s: no seat count and no note saying why" % where)
            if isinstance(r.get("row_names"), list) and isinstance(r.get("rows"), int):
                if len(r["row_names"]) != r["rows"]:
                    fails.append("%s: rows %d but %d row names"
                                 % (where, r["rows"], len(r["row_names"])))
            if not r.get("formats_run_here"):
                fails.append("%s: no formats recorded, so nothing put a showing in it"
                             % where)

    lf = doc.get("layout_field") or {}
    if lf.get("answer") is None or lf.get("confidence") not in ALLOWED:
        fails.append("rooms.json: layout_field must answer the assigned-seating question "
                     "and carry a confidence")
    if not doc.get("room_claims_cross_checked"):
        fails.append("rooms.json: the room-claim cross-check is missing")
    return fails


def report(name, fails):
    if fails:
        print("FAIL  %s" % name)
        for f in fails[:40]:
            print("   -", f)
        if len(fails) > 40:
            print("   ... and %d more" % (len(fails) - 40))
    else:
        print("ok    %s" % name)
    return not fails


def selftest(doc, venues):
    """Plant one bad record per check and require each to fire."""
    def plant(label, mutate, expect):
        bad = copy.deepcopy(doc)
        mutate(bad)
        fails = check(bad, venues)
        hit = [f for f in fails if expect in f]
        print("  %-46s %s" % (label, "caught" if hit else "*** NOT CAUGHT ***"))
        return bool(hit)

    def s_price(d):
        d["ticket_pricing"]["cineteca"]["general_mxn"] = "$70.00"

    def s_conf(d):
        d["food_and_alcohol"]["snack_stand_of_nowhere"] = {"available": True,
                                                           "source": "cineteca_faq"}

    def s_vocab(d):
        d["ticket_pricing"]["cineteca"]["confidence"] = "pretty_sure"

    def s_venue(d):
        d["food_and_alcohol"]["999999"] = copy.deepcopy(
            d["food_and_alcohol"][sorted(venues)[0]])

    def s_source(d):
        d["ticket_pricing"]["cineteca"]["source"] = "a_source_that_does_not_exist"

    def s_nullnote(d):
        pv = d["loyalty"]["cinemex"]["point_value"]
        pv["value_mxn"] = None
        pv.pop("note", None)

    def s_declared(d):
        d["app_venues"]["cinemex_ids"] = d["app_venues"]["cinemex_ids"][:-1]

    results = [
        plant("a price given as a string", s_price, "price is a string"),
        plant("a record with no confidence", s_conf, "no `confidence` covering it"),
        plant("a confidence outside the vocabulary", s_vocab, "not in the declared vocab"),
        plant("a venue id the app does not carry", s_venue, "is not one docs/index.html"),
        plant("a source id that is not in `sources`", s_source, "not in `sources`"),
        plant("a null price with no note", s_nullnote, "null price with no note"),
        plant("app_venues drifting from the page", s_declared, "does not match the page"),
    ]
    return all(results)


def selftest_rooms(doc, venues):
    def plant(label, mutate, expect):
        bad = copy.deepcopy(doc)
        mutate(bad)
        hit = [f for f in check_rooms(bad, venues) if expect in f]
        print("  %-46s %s" % (label, "caught" if hit else "*** NOT CAUGHT ***"))
        return bool(hit)

    first = sorted(doc["venues"])[0]

    def r0(d):
        return d["venues"][first]["rooms"][0]

    def s_sum(d):
        r0(d)["seats_regular"] = r0(d)["seats_regular"] + 7

    def s_str(d):
        r0(d)["seats_total"] = "142"

    def s_venue(d):
        d["venues"]["999999"] = copy.deepcopy(d["venues"][first])

    def s_dupe(d):
        rs = d["venues"][first]["rooms"]
        rs.append(copy.deepcopy(rs[0]))
        d["venues"][first]["room_count"] = len(rs)

    def s_rows(d):
        r0(d)["row_names"] = (r0(d)["row_names"] or [])[:-1]

    def s_zero(d):
        r0(d)["seats_total"] = 0
        r0(d).pop("note", None)
        r0(d).pop("why", None)

    def s_layout(d):
        d["layout_field"]["answer"] = None

    def s_claims(d):
        d["room_claims_cross_checked"] = []

    return all([
        plant("a seat breakdown that does not add up", s_sum, "regular+wheelchair+companion"),
        plant("a seat count given as a string", s_str, "is not an integer"),
        plant("a venue id the app does not carry", s_venue, "not one docs/index.html"),
        plant("the same room listed twice", s_dupe, "duplicate room"),
        plant("a row count that disagrees with row_names", s_rows, "row names"),
        plant("a zero seat count with no note", s_zero, "no seat count and no note"),
        plant("layout_field not answering the question", s_layout, "assigned-seating"),
        plant("the room-claim cross-check removed", s_claims, "cross-check is missing"),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="plant bad records and require every check to fire")
    args = ap.parse_args()

    if not os.path.exists(DATA):
        sys.exit("%s does not exist -- run build-cinema-extras.py" % DATA)
    doc = json.load(open(DATA, encoding="utf-8"))
    venues = app_venue_ids()
    print("%s\n%d venues in docs/index.html, %d sources declared\n"
          % (DATA, len(venues), len(doc.get("sources") or {})))

    good = report("docs/cinema-extras.json", check(doc, venues))

    rooms = None
    if os.path.exists(ROOMS):
        rooms = json.load(open(ROOMS, encoding="utf-8"))
        n = sum(v.get("room_count", 0) for v in (rooms.get("venues") or {}).values())
        good = report("docs/rooms.json (%d rooms)" % n, check_rooms(rooms, venues)) and good
    else:
        print("skip  docs/rooms.json is not built yet")

    if args.selftest:
        print("\nself-test -- every check must go red on a planted record:")
        if not selftest(doc, venues):
            print("\nFAIL  a check could not be made to fire, so it proves nothing")
            sys.exit(1)
        print("  all checks fired")
        if rooms is not None:
            print("\nself-test on rooms.json:")
            if not selftest_rooms(rooms, venues):
                print("\nFAIL  a rooms check could not be made to fire")
                sys.exit(1)
            print("  all rooms checks fired")

    sys.exit(0 if good else 1)


if __name__ == "__main__":
    main()
