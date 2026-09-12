#!/usr/bin/env python3
"""Cast, country, year and trailer: is the data real, and does the page use it safely?

    /opt/homebrew/bin/python3 test-film-extras.py

The normaliser runs on the exact bad shapes seen on 12 September, and a naive version of it
is required to fail the same cases, so those checks are shown able to fail. The manifest is
read off disk rather than trusting that --meta ran. The page checks are paired with a390593,
the commit before film-extras.py, where each is required to be false.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "a390593"
NOW = open(os.path.join(ROOT, "docs", "index.html"), encoding="utf-8").read()
BEFORE = subprocess.run(["git", "-C", ROOT, "show", BASE + ":docs/index.html"],
                        capture_output=True, text=True, check=True).stdout

fails = 0


def check(name, ok):
    global fails
    print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not ok:
        fails += 1


def safe(fn, *a):
    try:
        return bool(fn(*a))
    except Exception as e:  # a check that throws is a check that did not pass
        return False


def paired(name, fn):
    check(name, safe(fn, NOW))
    check("   ... and not true at %s, so the check can fail" % BASE, not safe(fn, BEFORE))


def lift(src, name):
    at = src.index("function %s(" % name)
    depth = 0
    for j in range(src.index("{", at), len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[at:j + 1]
    raise ValueError("unbalanced " + name)


spec = importlib.util.spec_from_file_location("refresh_posters", os.path.join(ROOT, "refresh-posters.py"))
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

VID = "bSwiSOz6D40"
WATCH = "https://www.youtube.com/watch?v=" + VID


def rec(**info):
    return {"info": info}


def normaliser_cases(meta):
    return [
        ("the bare youtube.com home page is dropped", meta(rec(trailer="https://www.youtube.com/"))["trailer"] == ""),
        ("a plain watch url is kept as it is", meta(rec(trailer=WATCH))["trailer"] == WATCH),
        ("youtu.be and m.youtube.com with extra parameters come out as one watch url",
         meta(rec(trailer="https://youtu.be/" + VID))["trailer"] == WATCH
         and meta(rec(trailer="http://m.youtube.com/watch?feature=share&v=" + VID))["trailer"] == WATCH),
        ("an id one character too long is refused", meta(rec(trailer=WATCH + "X"))["trailer"] == ""),
        ("somewhere that is not YouTube is refused", meta(rec(trailer="https://example.com/watch?v=" + VID))["trailer"] == ""),
        ("the cast is cut to four names", meta(rec(cast="A, B, C, D, E, F"))["cast"] == "A, B, C, D"),
        ("a year is four digits or nothing", meta(rec(year=2026))["year"] == "2026" and meta(rec(year="20266"))["year"] == ""),
        ("a record with no info at all gives empty strings and does not throw",
         all(v == "" for v in meta({}).values())),
    ]


print("1. the normaliser, on the bad shapes seen on 12 September")
for name, ok in normaliser_cases(rp.film_meta):
    check(name, ok)


def naive(m):
    i = m.get("info") or {}
    return {"syn": i.get("sinopsis") or "", "cast": i.get("cast") or "", "country": i.get("country") or "",
            "year": str(i.get("year") or ""), "trailer": i.get("trailer") or ""}


naive_fails = sum(1 for _, ok in normaliser_cases(naive) if not ok)
check("   ... and a normaliser that keeps whatever Cinemex sends fails %d of those" % naive_fails, naive_fails >= 5)

print("2. the manifest on disk")
man = json.load(open(os.path.join(ROOT, "docs", "posters", "index.json"), encoding="utf-8"))
trailers = [e["trailer"] for e in man.values() if e.get("trailer")]
check("at least 40 films carry a trailer (%d of %d)" % (len(trailers), len(man)), len(trailers) >= 40)
check("every trailer on disk is a YouTube watch url with an 11-character id",
      all(rp.YOUTUBE.match(t) and t == WATCH.replace(VID, t[-11:]) for t in trailers))
check("at least 40 carry cast and country", sum(1 for e in man.values() if e.get("cast") and e.get("country")) >= 40)
check("no cast line runs past four names", all(len(e.get("cast", "").split(", ")) <= 4 for e in man.values()))

print("3. the page")
paired("the film sheet draws the made line from the synopsis file", lambda s:
       "const meta = POSTERS[fid] || {};" in lift(s, "filmSheet") and 'class="made"' in lift(s, "filmSheet"))
paired("the trailer button is drawn only when the page's own check passes, and goes in the bar", lambda s:
       r"/^https:\/\/www\.youtube\.com\/watch\?v=[\w-]{11}$/.test(meta.trailer" in lift(s, "filmSheet")
       and "openSheet(head, go + trailer," in lift(s, "filmSheet"))
paired("it opens YouTube in a new tab and nothing embeds a player", lambda s:
       'class="yt" href="${esc(yt)}" target="_blank" rel="noopener"' in s
       and "<iframe" not in s and "youtube.com/embed" not in s)

sw = open(os.path.join(ROOT, "docs", "sw.js"), encoding="utf-8").read()
sw_before = subprocess.run(["git", "-C", ROOT, "show", BASE + ":docs/sw.js"], capture_output=True, text=True).stdout
num = lambda t: int(t.split('sala-v', 1)[1].split('"', 1)[0])
check("the offline cache name moved on, so an installed phone takes the new page", num(sw) > num(sw_before))

print("\n%d FAILED" % fails if fails else "\nall passed")
sys.exit(1 if fails else 0)
