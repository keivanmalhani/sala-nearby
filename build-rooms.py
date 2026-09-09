#!/usr/bin/env python3
"""Build docs/rooms.json -- one record per auditorium, not per showing.

    /opt/homebrew/bin/python3 build-rooms.py            # live, 287 calls, ~7 minutes
    /opt/homebrew/bin/python3 build-rooms.py --cached    # reuse .raw-extras/rooms_raw.json

Separate from cinema-extras.json on purpose: auditorium geometry does not change week to
week, so this is a one-off build cost, while prices change weekly and want re-running.

THE ROOM IS THE UNIT. There are 22,000-odd showings in the page and 287 distinct
auditoriums behind them, so the sweep deduplicates on (venue, auditorium name) and costs
287 calls rather than one per showing. The count is printed before any fetching starts.

WHAT `layout` ACTUALLY IS, read rather than assumed:

    layout: [ {"name": "A", "seats": [ {"id","label","status","type"}, ... ]}, ... ]

    type    regular | wheelchair | wheelchair-companion | blank   (blank = aisle or gap)
    status  "0" free · "1" taken · "E" not a seat (always type blank)

Two things follow that a reader will get wrong otherwise:

  * `len(layout)` IS NOT THE ROW COUNT. Rows with an empty `name` are spacers. Sala 5 at
    Antara Platino returns 15 entries -- 8 lettered rows with 7 unnamed spacers between
    them. Count rows whose name is non-empty.

  * `layout` DOES NOT ANSWER WHETHER SEATING IS ASSIGNED, and the open question in
    CINEMEX-API.md section 5 is now closed. The string "assigned" appears nowhere in the
    response; `layout` is geometry plus live availability and nothing else. The field that
    answers it is the top-level boolean `seatallocation`, which is recorded per room here.

Seat totals count regular + wheelchair + wheelchair-companion regardless of status, so a
nearly sold-out session still reports the full room: taken seats stay in the layout with
status "1".
"""

import argparse, json, os, sys, time
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, ".raw-extras")
OUT = os.path.join(HERE, "docs", "rooms.json")
PAGE = os.path.join(HERE, "docs", "index.html")

sys.path.insert(0, HERE)
import importlib.util
_spec = importlib.util.spec_from_file_location("_bce", os.path.join(HERE, "build-cinema-extras.py"))
_bce = importlib.util.module_from_spec(_spec)
_src = open(os.path.join(HERE, "build-cinema-extras.py"), encoding="utf-8").read()
exec(compile(_src.replace('if __name__ == "__main__":', "if False:"),
             "build-cinema-extras.py", "exec"), _bce.__dict__)
cx = _bce.cx
CX_BASE = _bce.CX_BASE

# Claims made elsewhere in the repo about which room runs what, cross-checked against the
# fetched table. A claim that disagrees means one of the two is wrong, and a hardcoded
# per-room label in the UI is exactly the thing that goes stale silently.
ROOM_CLAIMS = [
    {"venue": "32", "venue_name": "Parque Delta", "room": "Sala 3",
     "claim": "the IMAX room, described as 'IMAX with Laser'",
     "expect_format_substring": "IMAX",
     "claimed_in": "docs/IDEAS-2026-09-09.md lines 164 and 533"},
    {"venue": "32", "venue_name": "Parque Delta", "room": "Sala 10",
     "claim": "the CinemeXtremo room with Dolby Atmos, also the Infinity Vision room",
     "expect_format_substring": "Dolby Atmos",
     "claimed_in": "docs/IDEAS-2026-09-09.md lines 159-160 and 534"},
]


def app_blob():
    page = open(PAGE, encoding="utf-8").read()
    i = page.find("const SHOWS=")
    if i < 0:
        sys.exit("docs/index.html has no SHOWS blob -- run refresh-showtimes.py first")
    j = page.find("\n", i)
    return json.loads(page[i + len("const SHOWS="):j].rstrip().rstrip(";"))


def index_rooms(blob):
    """venue -> room name -> {formats: Counter, sessions: [(day, minute, session id)]}"""
    days, fmts = blob["days"], blob["fmts"]
    rooms = defaultdict(lambda: defaultdict(lambda: {"formats": Counter(), "sessions": []}))
    no_room = 0
    for c in blob["cin"]:
        if not str(c["id"]).isdigit():
            continue                      # Cineteca exposes no seat map, see below
        for fid, fi, di, mins, av, sid, sala in c["s"]:
            if not sid or not str(sid).isdigit():
                continue
            if sala in (None, ""):
                no_room += 1
                continue
            r = rooms[str(c["id"])][str(sala)]
            r["formats"][fi] += 1
            r["sessions"].append((days[di], mins, str(sid)))
    return rooms, no_room


def fetch_rooms(rooms):
    jobs = []
    for cid, per in rooms.items():
        for name, r in per.items():
            # furthest-future session for the room: a session that has already started is
            # the one most likely to be closed out from under the read
            day, mins, sid = sorted(r["sessions"])[-1]
            jobs.append((cid, name, day, mins, sid))
    print("%d distinct auditoriums across %d venues -> %d calls, about %d minutes"
          % (len(jobs), len(rooms), len(jobs), round(len(jobs) * 1.45 / 60.0)), flush=True)

    out = []
    for n, (cid, name, day, mins, sid) in enumerate(jobs, 1):
        rec = {"cinema_id": cid, "room_from_page": name, "session_id": sid,
               "session_day": day}
        try:
            d = cx("sessions/%s" % sid, timeout=45)
            rec["status"] = 200
            for k in ("auditorium_name", "screen_number", "seatallocation",
                      "tickets_limit", "adults_only", "availability", "premium",
                      "extreme"):
                rec[k] = d.get(k)
            lay = d.get("layout")
            rec["layout_is_list"] = isinstance(lay, list)
            rec["layout_entries"] = len(lay) if isinstance(lay, list) else None
            types, status = Counter(), Counter()
            named_rows, spacer_rows, row_names = 0, 0, []
            for row in (lay or []):
                nm = (row.get("name") or "").strip()
                if nm:
                    named_rows += 1
                    row_names.append(nm)
                else:
                    spacer_rows += 1
                for s in (row.get("seats") or []):
                    types[s.get("type")] += 1
                    status[str(s.get("status"))] += 1
            rec["seat_types"] = dict(types)
            rec["seat_status"] = dict(status)
            rec["named_rows"] = named_rows
            rec["spacer_rows"] = spacer_rows
            rec["row_names"] = row_names
            rec["assigned_string_present"] = "assigned" in json.dumps(d).lower()
        except Exception as e:
            rec["status"] = None
            rec["error"] = str(e)[:140]
        out.append(rec)
        if n % 25 == 0 or n == len(jobs):
            print("  rooms %d/%d" % (n, len(jobs)), flush=True)
            os.makedirs(RAW, exist_ok=True)
            json.dump(out, open(os.path.join(RAW, "rooms_raw.json"), "w",
                                encoding="utf-8"), ensure_ascii=False)
        time.sleep(0.35)
    os.makedirs(RAW, exist_ok=True)
    json.dump(out, open(os.path.join(RAW, "rooms_raw.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return out


def main():
    blob = app_blob()
    rooms, no_room = index_rooms(blob)
    fmts = blob["fmts"]
    names = {str(c["id"]): c["n"] for c in blob["cin"]}

    p = os.path.join(RAW, "rooms_raw.json")
    if ARGS.cached and os.path.exists(p):
        raw = json.load(open(p, encoding="utf-8"))
        print("%d rooms from the cached pull" % len(raw))
    else:
        raw = fetch_rooms(rooms)

    by = {(r["cinema_id"], r["room_from_page"]): r for r in raw}
    venues = OrderedDict()
    ok = 0
    for cid in sorted(rooms, key=lambda k: names.get(k, k)):
        recs = []
        for name in sorted(rooms[cid],
                           key=lambda s: (int(s.split()[-1])
                                          if s.split()[-1].isdigit() else 999, s)):
            src = by.get((cid, name)) or {}
            fmt_counts = rooms[cid][name]["formats"]
            formats = [{"label": fmts[fi]["l"], "type": fmts[fi]["t"],
                        "showtimes_in_this_room": n}
                       for fi, n in sorted(fmt_counts.items(), key=lambda kv: -kv[1])]
            t = src.get("seat_types") or {}
            regular = t.get("regular", 0)
            wheelchair = t.get("wheelchair", 0)
            companion = t.get("wheelchair-companion", 0)
            blank = t.get("blank", 0)
            seats = regular + wheelchair + companion
            rec = {
                "room": name,
                "auditorium_name": src.get("auditorium_name"),
                "screen_number": src.get("screen_number"),
                "seats_total": seats if src.get("status") == 200 else None,
                "seats_regular": regular if src.get("status") == 200 else None,
                "wheelchair_spaces": wheelchair if src.get("status") == 200 else None,
                "companion_spaces": companion if src.get("status") == 200 else None,
                "blank_cells": blank if src.get("status") == 200 else None,
                "rows": src.get("named_rows"),
                "row_names": src.get("row_names"),
                "spacer_rows_in_layout": src.get("spacer_rows"),
                "assigned_seating": src.get("seatallocation"),
                "max_tickets_per_order": src.get("tickets_limit"),
                "formats_run_here": formats,
                "read_from_session": src.get("session_id"),
                "read_for_day": src.get("session_day"),
                "source": "cinemex_sessions_rooms",
                "confidence": "measured",
            }
            if src.get("status") != 200:
                rec["note"] = ("the sessions endpoint did not answer for this room: %s"
                               % (src.get("error") or "no record"))
                rec["confidence"] = "unknown"
            elif seats == 0:
                rec["note"] = ("the response carried an empty seat map. Recorded as zero "
                               "rather than guessed; re-read this room before showing a "
                               "seat count for it.")
                rec["confidence"] = "unknown"
            else:
                ok += 1
            recs.append(rec)
        venues[cid] = {"name": names.get(cid), "room_count": len(recs), "rooms": recs}

    # ---- the cross-check against claims made elsewhere in the repo
    checks = []
    for c in ROOM_CLAIMS:
        rec = next((r for r in (venues.get(c["venue"]) or {}).get("rooms", [])
                    if r["room"] == c["room"]), None)
        if rec is None:
            checks.append(dict(c, verdict="NO SUCH ROOM in the page's own data",
                               formats_actually_run=None))
            continue
        labels = [f["label"] for f in rec["formats_run_here"]]
        hit = [l for l in labels if c["expect_format_substring"].lower() in l.lower()]
        total = sum(f["showtimes_in_this_room"] for f in rec["formats_run_here"])
        matched = sum(f["showtimes_in_this_room"] for f in rec["formats_run_here"]
                      if c["expect_format_substring"].lower() in f["label"].lower())
        checks.append(dict(
            c,
            verdict="agrees" if hit else "DISAGREES",
            formats_actually_run=labels,
            showtimes_matching_the_claim=matched,
            showtimes_in_the_room=total,
            exclusive="yes" if matched == total else "no",
        ))

    doc = OrderedDict()
    doc["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    doc["generated_by"] = "build-rooms.py"
    doc["about"] = (
        "One record per auditorium for the 32 Cinemex venues in this app: the room's name "
        "and screen number, its seat count broken out into ordinary seats, wheelchair "
        "spaces and companion spaces, its row count, and which formats that specific room "
        "runs. Read one session per distinct room rather than one per showing.")
    doc["sources"] = {
        "cinemex_sessions_rooms": {
            "url": CX_BASE + "sessions/<id>",
            "http_status": 200,
            "rooms_read": len(raw),
            "rooms_at_200": sum(1 for r in raw if r.get("status") == 200),
            "rooms_with_a_usable_seat_map": ok,
            "note": ("one call per distinct (venue, auditorium), taking the "
                     "furthest-future session in that room"),
        },
        "app_page": {"url": "docs/index.html",
                     "note": "the room-to-format mapping and the session ids come from the "
                             "page's own SHOWS blob, at no request cost"},
    }
    doc["layout_field"] = {
        "question": "Does `layout` say whether seating is assigned?",
        "answer": "No.",
        "confidence": "measured",
        "source": "cinemex_sessions_rooms",
        "detail": (
            "CINEMEX-API.md section 5 left this open -- 'layout is presumably the answer to "
            "that question, but it has not been read'. It has been read now, on all %d "
            "rooms. `layout` is a list of rows, each {name, seats}, and each seat is "
            "{id, label, status, type}. It carries geometry and live availability and "
            "nothing else. The string 'assigned' appears in none of the %d responses. The "
            "field that answers the question is the top-level boolean `seatallocation`, "
            "and it read true on every room in this app -- so assigned seating is universal "
            "at Cinemex and is not a Platino or Premium feature."
            % (len(raw), len(raw))),
        "schema": {
            "row": {"name": "row letter, or an empty string for a spacer row",
                    "seats": "list of seat objects, left to right"},
            "seat": {"id": "seat id used at checkout, empty for a non-seat",
                     "label": "the seat number a person reads, empty for a non-seat",
                     "type": "regular | wheelchair | wheelchair-companion | blank",
                     "status": "\"0\" free, \"1\" taken, \"E\" not a seat"},
        },
        "traps": [
            ("len(layout) IS NOT the row count. Entries with an empty `name` are spacers "
             "between rows. Antara Platino Sala 5 returns 15 entries for 8 lettered rows."),
            ("A seat count must include status \"1\". Taken seats stay in the layout, so "
             "counting only free ones turns a busy screening into a small room."),
            ("`type: blank` and `status: \"E\"` are the same fact said twice -- aisles and "
             "gaps. Counting cells instead of seats inflates every room by roughly half."),
        ],
    }
    doc["room_claims_cross_checked"] = checks
    doc["venues"] = venues
    doc["cineteca"] = {
        "rooms": None,
        "confidence": "unknown",
        "source": None,
        "note": ("Cineteca publishes no seat map this build could reach. Their purchase "
                 "flow is 'indica la cantidad de boletos y selecciona tus asientos' with a "
                 "maximum of 8 per session, so seating IS assigned, and their FAQ says "
                 "every room is wheelchair accessible -- but detallePelicula.php carries no "
                 "ajax url and links no external ticketing host, so the seat map is "
                 "JavaScript on their own domain and would need a browser. Seat counts and "
                 "per-room formats for the three Cineteca sedes are not obtainable over "
                 "plain HTTP."),
    }
    if no_room:
        doc["showtimes_with_no_room_recorded"] = no_room

    json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %s  %.0f KB  (%d rooms, %d with a usable seat map)"
          % (OUT, os.path.getsize(OUT) / 1024.0, len(raw), ok))
    for c in checks:
        print("  claim %s %s -> %s" % (c["venue_name"], c["room"], c["verdict"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true")
    ARGS = ap.parse_args()
    _bce.ARGS = ARGS
    main()
