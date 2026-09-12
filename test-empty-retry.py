#!/usr/bin/env python3
"""A cinema that answers with no showtimes is asked again before the refresh gives up on it.

    /opt/homebrew/bin/python3 test-empty-retry.py

The first scheduled refresh on GitHub, 12 September 2026, refused because Portal Centro came
back empty; the same endpoint gave 340 sessions from the laptop minutes later. movies_for()
runs here against a fake network with the sleeps removed, and a version without the retry is
run beside it on the same answers, so the check that matters is shown able to fail.

The second run refused too, with plain retries, because Cinemex answers through a shared
cache: the same URL gets the same stored reply. The cached network below is that, and the
old same-URL retry is run against it beside the new one.
"""
from __future__ import annotations

import importlib.util
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("refresh_showtimes", os.path.join(ROOT, "refresh-showtimes.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

fails = 0


def check(name, ok):
    global fails
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        fails += 1


FULL = [{"versions": [{"sessions": [{"id": 1}]}]}]
EMPTY_FILMS = [{"versions": [{"sessions": []}]}]


def network(*answers):
    calls = []

    def get(path):
        calls.append(path)
        return answers[min(len(calls) - 1, len(answers) - 1)]
    return get, calls


R.time.sleep = lambda s: None

get, calls = network([], EMPTY_FILMS, FULL)
R.get = get
got = R.movies_for(354)
check("empty, then films with no sessions, then the real listing: the real listing is kept", got == FULL)
check("   ... after exactly three asks of the same cinema",
      len(calls) == 3 and all(c.startswith("cinemas/354/movies") for c in calls))
check("   ... the first ask is the plain URL, so an ordinary refresh still uses the cache",
      calls[0] == "cinemas/354/movies")
check("   ... and each retry is a URL the cache has never seen",
      all("?_=" in c for c in calls[1:]) and len(set(calls)) == 3)


def cached_network(stored, fresh):
    """Cinemex's shared cache: a URL it has seen gets the stored reply, a new one the origin."""
    seen, calls = {}, []

    def get(path):
        calls.append(path)
        if path not in seen:
            seen[path] = stored if not seen else fresh
        return seen[path]
    return get, calls


# The second GitHub run, 12 Sep 15:04: three asks, all empty, while the origin had 340.
get, calls = cached_network([], FULL)
R.get = get
check("a cache holding an empty reply: the retries get past it to the real listing",
      R.movies_for(354) == FULL)
get, calls = cached_network([], FULL)
old = [get("cinemas/354/movies") for _ in range(3)]
check("   ... and the old retry, the same URL three times, got the stored empty reply every time",
      not any(R.has_sessions(m) for m in old))

get, calls = network([], EMPTY_FILMS, FULL)
once = get("cinemas/354/movies")
check("   ... and asking once, as the refresh did before, would have kept nothing", not R.has_sessions(once))

get, calls = network(FULL)
R.get = get
check("a cinema that answers properly is asked once", R.movies_for(30) == FULL and len(calls) == 1)

get, calls = network([])
R.get = get
check("a cinema that stays empty is still empty after three asks, so the guard still decides",
      R.movies_for(354) == [] and len(calls) == 3)

print("\n%d FAILED" % fails if fails else "\nall passed")
raise SystemExit(1 if fails else 0)
