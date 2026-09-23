#!/usr/bin/env python3
"""Offline controls for refresh-showtimes.py's payload safety checks.

    python3 test-refresh-guards.py

The fixture has Cinemex and Cineteca venues, so it can prove that a Cinemex-only
pull must be compared to the Cinemex half. Dates and quantities are independent of
the listings currently published by GitHub Pages.
"""
import copy
import importlib.util
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
spec = importlib.util.spec_from_file_location(
    "refresh_showtimes", os.path.join(HERE, "refresh-showtimes.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


def complains_about(new, old, needle):
    problems, *_ = R.check(new, old)
    return any(needle in p for p in problems)


def fixture():
    today = date.today().isoformat()
    films = {}
    cinemas = []
    for n in range(9):
        c_id = str(100 + n) if n < 6 else "cineteca-%03d" % (n - 5)
        f_id = str(1000 + n) if n < 6 else "ct-%d" % n
        films[f_id] = {"n": "Film %d" % n, "dir": "Director %d" % n}
        cinemas.append({
            "id": c_id, "n": "Cinema %d" % n, "v": "venue-%d" % n,
            "s": [[f_id, 0, 0, 600 + 90 * i, "h", "ticket-%d-%d" % (n, i),
                   "Sala %d" % (i + 1)] for i in range(5)],
        })
    return {"at": today + "T12:00", "days": [today], "films": films, "cin": cinemas}


print("salaOf, both shapes of the room field")
check("auditorium_number 5 becomes 'Sala 5'", R.salaOf({"auditorium_number": "5"}) == "Sala 5")
check("an existing Sala prefix is left alone", R.salaOf({"auditorium_number": "Sala 5"}) == "Sala 5")
check("an int is accepted", R.salaOf({"auditorium_number": 3}) == "Sala 3")
check("a missing room is empty", R.salaOf({}) == "")

print("\nCinemex-only comparison uses the right baseline")
full = fixture()
cx = R.cinemex_only(full)
check("all three Cineteca cinemas are removed", len(full["cin"]) - len(cx["cin"]) == 3)
check("only Cinemex films remain", len(cx["films"]) == 6)
check("all Cinemex sessions survive", sum(len(c["s"]) for c in cx["cin"]) == 30)
check("the full fixture is unchanged", len(full["cin"]) == 9)
check("wrong full-board comparison refuses the Cinemex-only pull",
      complains_about(copy.deepcopy(cx), full, "cinemas")
      and complains_about(copy.deepcopy(cx), full, "films"))
check("correct Cinemex-only comparison accepts the same pull",
      R.check(copy.deepcopy(cx), cx)[0] == [])

print("\nDamaged Cinemex payloads are refused")
blank = copy.deepcopy(cx)
for c in blank["cin"]:
    for s in c["s"]:
        s[5] = ""
check("missing ticket ids are refused and described as dead links",
      complains_about(blank, cx, "ticket id") and complains_about(blank, cx, "links nowhere"))

half = copy.deepcopy(cx)
for c in half["cin"]:
    for s in c["s"][::2]:
        s[5] = ""
check("partial ticket-id loss is refused", complains_about(half, cx, "ticket id"))

norooms = copy.deepcopy(cx)
for c in norooms["cin"]:
    for s in c["s"]:
        s[6] = ""
check("losing room names is refused", complains_about(norooms, cx, "room names"))

fewer = copy.deepcopy(cx)
fewer["cin"] = fewer["cin"][:-3]
check("losing three cinemas is refused", complains_about(fewer, cx, "cinemas"))

thin = copy.deepcopy(cx)
for c in thin["cin"]:
    c["s"] = c["s"][:1]
check("losing most showtimes is refused", complains_about(thin, cx, "showtimes"))

few_films = copy.deepcopy(cx)
few_films["films"] = dict(list(few_films["films"].items())[:4])
check("losing a third of films is refused", complains_about(few_films, cx, "films"))

stale = copy.deepcopy(cx)
stale["days"] = ["2020-01-01"]
check("a stale first day is refused", complains_about(stale, cx, "not today"))

unlinked = copy.deepcopy(cx)
unlinked["cin"][0]["v"] = None
check("losing a venue link is refused", complains_about(unlinked, cx, "venue links"))

empty = copy.deepcopy(cx)
empty["cin"][0]["s"] = []
check("a cinema with no showtimes is refused",
      complains_about(empty, cx, "no showtimes at all"))

print()
if fails:
    print("%d FAILED" % len(fails))
    for failure in fails:
        print("  - " + failure)
    sys.exit(1)
print("all controls pass")
