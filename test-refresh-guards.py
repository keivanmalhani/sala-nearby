#!/usr/bin/env python3
"""Controls for the guards in refresh-showtimes.py.

Every guard in check() exists because something already shipped past it. A guard that
cannot be shown to fire is decoration, so each one here is given the exact broken payload
it was written for and required to complain -- and then given the real payload and
required to stay quiet.

    /opt/homebrew/bin/python3 test-refresh-guards.py
"""
import copy
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util

spec = importlib.util.spec_from_file_location(
    "refresh_showtimes", os.path.join(HERE, "refresh-showtimes.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


def load_published():
    page = open(os.path.join(HERE, "docs", "index.html"), encoding="utf-8").read()
    i = page.index("const SHOWS")
    j = page.index("=", i) + 1
    payload, _ = json.JSONDecoder().raw_decode(page[j:].lstrip())
    return payload


def complains_about(new, old, needle):
    problems, *_ = R.check(new, old)
    return any(needle in p for p in problems)


print("salaOf, both shapes of the room field")
check("auditorium_number 5 becomes 'Sala 5'", R.salaOf({"auditorium_number": "5"}) == "Sala 5")
check("a number that already says Sala is left alone",
      R.salaOf({"auditorium_number": "Sala 5"}) == "Sala 5")
check("an int is accepted", R.salaOf({"auditorium_number": 3}) == "Sala 3")
check("a missing room is empty, not 'Sala None'", R.salaOf({}) == "")
check("an empty room is empty", R.salaOf({"auditorium_number": ""}) == "")

print("\ncheck(), against the payload that is actually published")
live = load_published()
today_ok = live["days"] and live["days"][0] == date.today().isoformat()
problems, n_new, n_old, linked = R.check(copy.deepcopy(live), copy.deepcopy(live))
expected = 0 if today_ok else 1
check("the published payload compared to itself raises nothing"
      + ("" if today_ok else " (bar the stale-day line, which is correct today)"),
      len(problems) == expected)
check("it is a real payload, not an empty one", n_new > 1000)

print("\nthe ticket-id guard -- the one that was missing on 2026-09-08")
blank = copy.deepcopy(live)
for c in blank["cin"]:
    for s in c["s"]:
        s[5] = ""
check("a payload whose sessions lost their ticket ids is refused",
      complains_about(blank, live, "ticket id"))
check("and the message says what it costs, not what the field is called",
      complains_about(blank, live, "links nowhere"))

half = copy.deepcopy(live)
n = 0
for c in half["cin"]:
    for s in c["s"]:
        n += 1
        if n % 2 == 0:
            s[5] = ""
check("half of them going missing is refused too", complains_about(half, live, "ticket id"))

check("the real payload does NOT trip the ticket guard",
      not complains_about(copy.deepcopy(live), live, "ticket id"))

print("\nthe room-name guard")
norooms = copy.deepcopy(live)
for c in norooms["cin"]:
    for s in c["s"]:
        if len(s) > 6:
            s[6] = ""
check("losing every room name is refused", complains_about(norooms, live, "room names"))
check("the real payload does not trip it",
      not complains_about(copy.deepcopy(live), live, "room names"))

print("\ncinemex_only, so a Cinemex pull is not compared against a page holding Cineteca too")
cx = R.cinemex_only(live)
n_all = len(live["cin"])
n_ct = sum(1 for c in live["cin"] if str(c["id"]).startswith("cineteca-"))
check("there is Cineteca in the published page to remove", n_ct > 0)
check("it comes out", len(cx["cin"]) == n_all - n_ct)
check("no cineteca row survives",
      not any(str(c["id"]).startswith("cineteca-") for c in cx["cin"]))
check("its films come out with it", len(cx["films"]) < len(live["films"]))
check("every film still referenced by a surviving cinema is kept",
      {str(s[0]) for c in cx["cin"] for s in c["s"]} <= {str(k) for k in cx["films"]})
check("no Cinemex showtime was dropped",
      sum(len(c["s"]) for c in cx["cin"])
      == sum(len(c["s"]) for c in live["cin"] if not str(c["id"]).startswith("cineteca-")))
check("the original is untouched", len(live["cin"]) == n_all)
check("a Cinemex-only pull compared to the whole page WOULD be refused -- the bug",
      complains_about(copy.deepcopy(cx), live, "films"))
cx_problems = R.check(copy.deepcopy(cx), cx)[0]
check("and compared to the Cinemex half it raises nothing",
      len(cx_problems) == (0 if today_ok else 1))

print("\nthe guards that already existed, so a refactor cannot quietly drop them")
fewer = copy.deepcopy(live)
fewer["cin"] = fewer["cin"][:-5]
check("losing five cinemas is refused", complains_about(fewer, live, "cinemas"))

thin = copy.deepcopy(live)
for c in thin["cin"]:
    c["s"] = c["s"][: max(1, len(c["s"]) // 4)]
check("losing three quarters of the showtimes is refused",
      complains_about(thin, live, "showtimes"))

stale = copy.deepcopy(live)
stale["days"] = ["2020-01-01"] + stale["days"][1:]
check("a first day that is not today is refused", complains_about(stale, live, "not today"))

empty = copy.deepcopy(live)
empty["cin"][0]["s"] = []
check("a cinema that came back with nothing is refused",
      complains_about(empty, live, "no showtimes at all"))

print()
if fails:
    print("%d FAILED" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all controls pass")
