#!/usr/bin/env python3
"""Compact the three research files into the one thing the page fetches.

    /opt/homebrew/bin/python3 build-detail.py
    /opt/homebrew/bin/python3 build-detail.py --dry-run

`docs/cinema-extras.json`, `docs/rooms.json` and `docs/cinema-reviews.json` are 572 KB
between them and are built to be read by a person: every value carries its source, its
confidence, the quote it came from, and the control that proves the source could have said
no. That is exactly right for a research file and wrong for something a phone downloads on
a cold launch over Telcel.

So this writes `docs/detail.json`, which holds only the values that reach the screen, in
the shortest shape that still renders. The three sources stay in `docs/` unchanged and
stay the citation: every number on screen can be traced back to a row in them, and the
page names the read date wherever it shows a price.

WHY NOT BAKE IT INTO THE PAGE. index.html is already 599 KB because the showtimes are in
it, and they have to be -- the first paint is a list of times. Nothing here is needed for
the first paint: a price, a seat count and a rating are what he reads after tapping a
cinema. So it is fetched the way `posters/index.json` already is, after the list is on
screen, and the service worker caches it with everything else so it is there offline from
the second launch.

WHAT IS DELIBERATELY LEFT OUT, and each of these is a decision rather than an oversight:

  - Cinemex snack menus. There are none. All 32 venues report an empty catalogue and the
    endpoint returns 400 when the parameter is missing, so the empty answer is real.
    Building a menu screen would mean typing 32 menus by hand.
  - The promo price per showing. Cinemex's $39 Mania arrives as a different ticket
    PRODUCT, and which film is in the slot decides whether it applies -- Miguel Angel de
    Quevedo priced Premium Espanol at $39 and Premium Subtitulada at $116 on the same day.
    So the promo is carried as a RULE with the operator's terms, and never as a number
    beside a time.
  - Temperature on 31 of the 39 venues. Only 8 read hot; the rest are "thin" or "no
    signal", and temperature is 2.3% of what reviewers write. A badge on all 39 would
    invent a signal for 31 of them.
  - Seat counts from the price rows. Those are incidental to whichever session was
    sampled. Seats come from rooms.json, which is one read per distinct room.
  - Row names, seat-map blank cells, session ids, quotes, controls and source notes. They
    are why the research files are trustworthy and they are not on screen.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
OUT = os.path.join(DOCS, "detail.json")

# Only the top themes reach the screen. Twelve per venue is a wall of text on a phone and
# the tail is all under ten per cent.
THEMES_SHOWN = 4


def load(name):
    p = os.path.join(DOCS, name)
    if not os.path.exists(p):
        raise SystemExit("missing %s -- run the build that writes it first" % p)
    return json.load(open(p, encoding="utf-8"))


def payload():
    src = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()
    m = re.search(r"^const SHOWS=", src, re.M)
    shows, _ = json.JSONDecoder().raw_decode(src, m.end())
    return shows


def n(x):
    """Whole pesos where the value is whole, which is all of them, and never a float
    ending in .0 taking three extra bytes on every row."""
    if x is None:
        return None
    return int(x) if float(x).is_integer() else round(float(x), 2)


def build():
    ex, rooms, revs, shows = (load("cinema-extras.json"), load("rooms.json"),
                              load("cinema-reviews.json"), payload())
    out = {"at": datetime.now().astimezone().isoformat()[:16],
           "src": "cinema-extras.json, rooms.json and cinema-reviews.json, in docs/"}

    # ---- the format dictionary, for the keys this app actually uses ------------------
    # A key that is named by the operator and described nowhere gets null, and the page
    # says so out loud. Four are in that state -- Confort, Infinity Vision, Market and
    # CinemeXtremo -- and 150 showtimes here are Infinity Vision, so it is not a corner
    # case that can be left blank and ignored.
    dic = dict(ex["formats"]["screening_attributes"])
    for k, v in ex["formats"]["complex_attributes"].items():
        dic.setdefault(k, v)
    used = set()
    for f in shows["fmts"]:
        used |= set(f.get("t") or [])
    out["fmt"] = {}
    for k in sorted(used):
        d = dic.get(k)
        if not d:
            continue
        out["fmt"][k] = {"es": d.get("display_name_es"), "en": d.get("plain_en"),
                         "conf": d.get("confidence"), "why": d.get("why")}

    # ---- loyalty --------------------------------------------------------------------
    L = ex["loyalty"]["cinemex"]
    out["loyalty"] = {
        "name": L.get("programme_name"),
        "tiers": [[t.get("name"), t.get("points_accrual_percent")] for t in L.get("tiers", [])],
        # Cinemex never states a points-to-pesos ratio anywhere in 8.4 MB of their own CMS,
        # so the page says the points are spendable and refuses to imply a value.
        "point_value": n((L.get("point_value") or {}).get("value_mxn")),
        "point_note": (L.get("point_value") or {}).get("note"),
        "packages": [],
    }
    for p in L.get("membership_packages", []):
        out["loyalty"]["packages"].append({
            "name": p.get("name"), "tickets": p.get("tickets_included"),
            "lo": n(p.get("price_mxn_low")), "hi": n(p.get("price_mxn_high")),
            "varies": bool(p.get("varies_by_venue")),
        })

    # ---- the midweek promo, as a rule ------------------------------------------------
    rules = ex["ticket_pricing"]["cinemex"].get("promo_rules") or []
    if rules:
        r = rules[0]
        out["promo"] = {"name": r.get("name"), "price": n(r.get("price_mxn")),
                        "days": r.get("days"), "window": r.get("window"),
                        "yes": r.get("applies_to_concepts") or [],
                        "no": (r.get("excluded_concepts") or []) + (r.get("excluded_formats") or []),
                        "also_no": r.get("also_excluded") or []}

    ct = ex["ticket_pricing"]["cineteca"]
    out["cineteca_price"] = {
        "general": n(ct.get("general_mxn")), "reduced": n(ct.get("reduced_mxn")),
        "reduced_for": ct.get("reduced_applies_to") or [],
        "cheap_days": (ct.get("cheap_days") or {}).get("days") or [],
        "cheap_price": n((ct.get("cheap_days") or {}).get("price_mxn")),
        "cheap_not": (ct.get("cheap_days") or {}).get("excluded") or [],
        "max_tickets": ct.get("max_tickets_per_session"),
    }

    # ---- per venue -------------------------------------------------------------------
    ven = {}
    prices = ex["ticket_pricing"]["cinemex"]["venues"]
    pkg_by_venue = {}
    for p in L.get("membership_packages", []):
        for vid, amt in (p.get("price_mxn_by_venue") or {}).items():
            pkg_by_venue.setdefault(vid, []).append([p.get("name"), n(amt)])

    for c in shows["cin"]:
        vid = str(c["id"])
        v = {}

        # price, PLAIN band only, keyed by the format label the page already prints
        pr, read = {}, set()
        for lab, bands in (prices.get(vid) or {}).items():
            b = bands.get("plain") or {}
            if b.get("adult_price_mxn") is None:
                continue
            pr[lab] = [n(b["adult_price_mxn"]), n(b.get("cheapest_price_mxn"))]
            if b.get("day_read"):
                read.add(b["day_read"])
        if pr:
            v["price"] = pr
            v["price_read"] = sorted(read)

        # rooms: name -> screen, seats, wheelchair spaces, rows. The room name is the
        # exact string the page already prints on a chip -- all 11,067 sessions that
        # carry one match a room here, checked rather than assumed.
        R = rooms["venues"].get(vid)
        if R:
            v["rooms"] = {r["room"]: [r.get("screen_number"), r.get("seats_total"),
                                      r.get("wheelchair_spaces"), r.get("rows")]
                          for r in R["rooms"]}

        if pkg_by_venue.get(vid):
            v["packages"] = sorted(pkg_by_venue[vid], key=lambda x: (x[1] or 0))

        fa = (ex["food_and_alcohol"].get(vid) or {})
        sm = fa.get("snack_menu") or {}
        if sm.get("available") and sm.get("menu"):
            v["menu"] = compact_menu(sm["menu"])
        # The bar is two different facts wearing one field. Seven Cinemex Platino sites
        # say only that drinks come to the seat; the two Cineteca sedes name the outlet and
        # carry a priced list. Keep both shapes rather than flattening to the sentence,
        # which is what the first version of this did and it threw away 34 priced rows.
        bar = fa.get("alcohol") or {}
        if bar.get("available"):
            v["bar"] = {"detail": bar.get("detail"), "outlet": bar.get("outlet")}
            items = [[i.get("name_es"), n(i.get("price_mxn")), i.get("kind")]
                     for i in (bar.get("items") or []) if i.get("price_mxn") is not None]
            if items:
                v["bar"]["items"] = items

        if v:
            ven[vid] = v

    # reviews, including the four independents that are on the map with no showtimes
    out["indie"] = []
    for r in revs:
        rid = str(r.get("id"))
        row = {}
        if r.get("rating") is not None:
            row["rating"] = r["rating"]
            row["n"] = r.get("review_count")
            row["sampled"] = r.get("sampled")
        th = [[t["theme"], round(t["pct"], 1)] for t in (r.get("themes") or [])][:THEMES_SHOWN]
        if th:
            row["themes"] = th
        t = r.get("temperature") or {}
        # ONLY the eight that read hot. See the module docstring.
        if t.get("verdict") == "hot" and t.get("evidence_hot"):
            e = t["evidence_hot"][0]
            row["hot"] = {"pct": t.get("pct_of_sample_hot"), "n": t.get("heat_mentions"),
                          "quote": e.get("quote"), "when": e.get("when")}
        if r.get("map_venue"):
            row["map"] = r["map_venue"]
            row["name"] = r.get("name")
            row["url"] = r.get("maps_url")
            out["indie"].append(row)
        elif row:
            ven.setdefault(rid, {}).update(row)

    out["ven"] = ven
    return out


def compact_menu(menu):
    """Cineteca's dulceria and bar, as name plus the prices, dropping the page numbers and
    the OCR provenance."""
    small = {}
    for section, items in menu.items():
        rows = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            ps = [[p.get("variant_es"), n(p.get("price_mxn"))]
                  for p in (it.get("prices") or []) if p.get("price_mxn") is not None]
            if it.get("price_mxn") is not None and not ps:
                ps = [[None, n(it["price_mxn"])]]
            if not ps:
                continue
            rows.append({"name": it.get("name"), "what": it.get("contents_es"), "p": ps})
        if rows:
            small[section] = rows
    return small


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    d = build()
    blob = json.dumps(d, separators=(",", ":"), ensure_ascii=False)

    src_bytes = sum(os.path.getsize(os.path.join(DOCS, f)) for f in
                    ("cinema-extras.json", "rooms.json", "cinema-reviews.json"))
    print("venues with detail : %d" % len(d["ven"]))
    print("  with a price     : %d" % sum(1 for v in d["ven"].values() if "price" in v))
    print("  with rooms       : %d (%d rooms)"
          % (sum(1 for v in d["ven"].values() if "rooms" in v),
             sum(len(v.get("rooms") or {}) for v in d["ven"].values())))
    print("  with a rating    : %d" % sum(1 for v in d["ven"].values() if "rating" in v))
    print("  reading hot      : %d" % sum(1 for v in d["ven"].values() if "hot" in v))
    print("  with a menu      : %d" % sum(1 for v in d["ven"].values() if "menu" in v))
    print("  with a bar       : %d (%d priced drinks)"
          % (sum(1 for v in d["ven"].values() if "bar" in v),
             sum(len((v.get("bar") or {}).get("items") or []) for v in d["ven"].values())))
    print("independents       : %d" % len(d["indie"]))
    print("formats described  : %d of %d used (%s have no published description)"
          % (sum(1 for f in d["fmt"].values() if f["en"]), len(d["fmt"]),
             ", ".join(k for k, f in d["fmt"].items() if not f["en"]) or "none"))
    print("detail.json        : %s bytes, from %s of research files (%.0f%%)"
          % (format(len(blob.encode()), ","), format(src_bytes, ","),
             100 * len(blob.encode()) / src_bytes))
    if a.dry_run:
        print("--dry-run: nothing written")
        return 0
    open(OUT, "w", encoding="utf-8").write(blob)
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
