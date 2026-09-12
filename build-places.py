#!/usr/bin/env python3
"""The places he can type into "Distances from": neighbourhoods, stations and landmarks.

    /opt/homebrew/bin/python3 build-places.py            # fetch, check, write docs/places.json
    /opt/homebrew/bin/python3 build-places.py --dry-run  # fetch and check, write nothing

Ask 5 from 12 September: "more options for where distances are measured from -- I wanna
type in there in a unique good way that's useful to a user". Typing needs something to
match against, and a geocoding service would need a signal and a key, and would send what
he types to a third party. So the places are baked in: one file the app loads when the
picker opens and the service worker keeps for no-signal use.

WHERE THEY COME FROM. OpenStreetMap, through the public Overpass API, within 15 km of Parque
Mexico: every colonia, quarter and district node, every Metro, Tren Ligero, Cablebus and
Suburbano station, every Metrobus stop, and museums, attractions and parks carrying a
Wikidata id within 8 km. OpenStreetMap data is ODbL, and the picker credits it.

WHAT IS DONE TO THEM.
  - "Colonia Condesa" is shown as "Condesa" and still found by either.
  - Metrobus stops are mapped once per platform and direction, so stops sharing a name within
    600 m are merged into one point at their centre. A name that recurs far apart stays as
    separate places, and the postcode OpenStreetMap carries tells them apart on screen.
  - Nothing is written if a count comes back implausibly small, because a half-empty file
    would make the picker silently fail to find ordinary places.

Rows are [name, kind, lat, lng, postcode, aliases...], nearest to the park first.
"""
from __future__ import annotations

import datetime
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs", "places.json")
PARK = (19.4117, -99.1690)
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
             "https://overpass.private.coffee/api/interpreter"]
UA = "sala-nearby-build/1.0 (keivanmalhani.github.io/sala-nearby)"
AROUND = "around:15000,%s,%s" % PARK
NEAR = "around:8000,%s,%s" % PARK
QUERIES = {
    "places": '[out:json][timeout:90];node["place"~"^(neighbourhood|suburb|quarter)$"](%s);out body;' % AROUND,
    "stations": '[out:json][timeout:90];(node["railway"="station"](%s);node["public_transport"="station"](%s););out body;' % (AROUND, AROUND),
    "metrobus": '[out:json][timeout:90];(node["network"~"Metrob",i](%s);node["operator"~"Metrob",i](%s););out body;' % (AROUND, AROUND),
    "landmarks": '[out:json][timeout:90];(nwr["tourism"~"^(museum|attraction)$"]["wikidata"](%s);'
                 'nwr["leisure"="park"]["wikidata"](%s););out center tags;' % (NEAR, NEAR),
}
# The least a real pull returns, measured on 12 September: 1,705 places, 139 Metro stations,
# 173 Metrobus names, 93 landmarks. Well under those means the query or the service broke.
MINIMUM = {"col": 800, "m": 80, "mb": 60, "lm": 30}


def km(a, b):
    r = math.pi / 180
    h = math.sin((b[0] - a[0]) * r / 2) ** 2 + math.cos(a[0] * r) * math.cos(b[0] * r) * math.sin((b[1] - a[1]) * r / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def overpass(query):
    last = None
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": query}).encode(), headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=120))["elements"]
        except Exception as e:  # a 504 from one mirror is a fact about that mirror
            last = e
            time.sleep(3)
    raise SystemExit("every Overpass mirror failed, last error: %s -- nothing written" % last)


def point(e):
    if "lat" in e:
        return (e["lat"], e["lon"])
    c = e.get("center")
    return (c["lat"], c["lon"]) if c else None


def station_kind(t):
    net = (t.get("network") or t.get("operator") or "").lower()
    if "metrob" in net:
        return "mb"
    if "tren ligero" in net:
        return "tl"
    if "cablebús" in net or "cablebus" in net:
        return "cb"
    if "suburbano" in net:
        return "sub"
    if "metro" in net:
        return "m"
    return None


def display(name):
    return re.sub(r"^(Colonia|Col\.)\s+", "", name).strip()


def main():
    raw = {}
    for key, q in QUERIES.items():
        raw[key] = overpass(q)
        time.sleep(2)

    rows = []   # (name, kind, lat, lng, cp, aliases)
    for e in raw["places"]:
        t, p = e.get("tags", {}), point(e)
        if not p or not t.get("name"):
            continue
        kind = {"neighbourhood": "col", "quarter": "q", "suburb": "d"}[t["place"]]
        aliases = [a for a in {t["name"], t.get("alt_name", ""), t.get("official_name", "")} if a and a != display(t["name"])]
        rows.append([display(t["name"]), kind, p[0], p[1], t.get("addr:postcode", ""), aliases])
    for e in raw["stations"]:
        t, p = e.get("tags", {}), point(e)
        k = station_kind(t)
        if p and t.get("name") and k and k != "mb":
            rows.append([t["name"], k, p[0], p[1], "", []])
    for e in raw["metrobus"] + [x for x in raw["stations"] if station_kind(x.get("tags", {})) == "mb"]:
        t, p = e.get("tags", {}), point(e)
        if p and t.get("name") and t.get("public_transport") in ("platform", "stop_position", "station"):
            rows.append([t["name"], "mb", p[0], p[1], "", []])
    for e in raw["landmarks"]:
        t, p = e.get("tags", {}), point(e)
        if p and t.get("name"):
            rows.append([t["name"], "lm", p[0], p[1], "", []])

    # Merge same kind + same name within 600 m into one point at their centre.
    merged = []
    for r in rows:
        if km(PARK, (r[2], r[3])) > 15.5:
            continue
        home = next((m for m in merged if m["k"] == r[1] and m["n"].lower() == r[0].lower()
                     and km((m["la"], m["lo"]), (r[2], r[3])) < 0.6), None)
        if home:
            home["pts"].append((r[2], r[3]))
            home["la"] = sum(x[0] for x in home["pts"]) / len(home["pts"])
            home["lo"] = sum(x[1] for x in home["pts"]) / len(home["pts"])
            home["cp"] = home["cp"] or r[4]
            home["al"] |= set(r[5])
        else:
            merged.append({"n": r[0], "k": r[1], "la": r[2], "lo": r[3], "cp": r[4], "al": set(r[5]), "pts": [(r[2], r[3])]})

    merged.sort(key=lambda m: km(PARK, (m["la"], m["lo"])))
    counts = {}
    for m in merged:
        counts[m["k"]] = counts.get(m["k"], 0) + 1
    print("places by kind:", counts)
    short = [k for k, floor in MINIMUM.items() if counts.get(k, 0) < floor]
    if short:
        raise SystemExit("REFUSING TO WRITE: too few %s (%s) -- a broken pull, not a smaller city"
                         % (", ".join(short), {k: counts.get(k, 0) for k in short}))

    out = {
        "at": datetime.date.today().isoformat(),
        "src": "OpenStreetMap contributors, ODbL, via the Overpass API",
        "kinds": {"col": "Neighbourhood", "q": "Area", "d": "District", "m": "Metro", "mb": "Metrobús",
                  "tl": "Tren Ligero", "cb": "Cablebús", "sub": "Suburbano", "lm": "Landmark"},
        "p": [[m["n"], m["k"], round(m["la"], 5), round(m["lo"], 5), m["cp"]] + sorted(m["al"]) for m in merged],
    }
    body = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    print("%d places, %d KB" % (len(out["p"]), len(body.encode()) // 1024))
    if "--dry-run" in sys.argv:
        print("dry run: nothing written")
        return
    open(OUT, "w", encoding="utf-8").write(body)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
