#!/usr/bin/env python3
"""Cinemex truncates director names, so keep the longer spelling we already had.

    /opt/homebrew/bin/python3 director-truncation.py --dry-run
    /opt/homebrew/bin/python3 director-truncation.py

Run this after refresh-showtimes.py and refresh-cineteca.py, before committing.

WHAT IT IS FOR, MEASURED TWICE. Cinemex's `director` field is cut off at a fixed width.
On 11 September their pull carried "Christopher Nola" for La Odisea -- 181 showings, the
biggest film on the board -- and "Direccion 1990: Benjamin " with the surname sheared off
mid-word. Two days earlier the page read "Christopher Nolan", because Cineteca was also
showing the film and the two-chain merge takes the better of the two strings. Cineteca
publishes two days at a time, so the moment their run ended the repair went with it and
the name silently reverted.

That is why this is its own step rather than a line inside the merge: the merge can only
fix a name while both chains happen to be showing the same film, which is a coincidence
that expires.

THE RULE, AND WHY IT CANNOT INVENT ANYTHING. A name is restored only when the new value
is a strict PREFIX of the value the page already carried. That is the exact signature of
a fixed-width truncation and nothing else looks like it: a genuine correction by Cinemex
("Joe Russo" replacing "Anthony Russo") is not a prefix and passes straight through. The
restored string is one this project published before, from a source that spelled it out,
so nothing here is a name somebody guessed.

Two guards on top of that. The new value has to be at least four characters, because an
empty string is a prefix of everything and a film whose director was legitimately removed
would otherwise keep a stale one forever. And the old value has to be longer, not merely
different, so the repair only ever goes one way.

The repair is sticky: the page it writes becomes the comparison for the next refresh, so
a name recovered once survives every pull after it without Cineteca having to show the
film again.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
REF = os.environ.get("SALA_PREV_REF", "HEAD")


def payload(src: str) -> tuple[dict, int, int]:
    i = src.index("const SHOWS=")
    j = src.index("\n", i)
    return json.loads(src[i + len("const SHOWS="):j].rstrip(";")), i, j


def main() -> None:
    dry = "--dry-run" in sys.argv
    src = open(PAGE, encoding="utf-8").read()
    new, _, _ = payload(src)

    prev_src = subprocess.run(["git", "-C", ROOT, "show", "%s:docs/index.html" % REF],
                              capture_output=True, text=True)
    if prev_src.returncode != 0:
        sys.exit("cannot read %s:docs/index.html -- %s" % (REF, prev_src.stderr.strip()))
    old, _, _ = payload(prev_src.stdout)

    fixes = []
    for fid, f in new["films"].items():
        a = (f.get("dir") or "").strip()
        b = (old["films"].get(fid, {}).get("dir") or "").strip()
        if len(a) >= 4 and len(b) > len(a) and b.startswith(a):
            fixes.append((fid, f["n"], a, b))

    print("%d films in the payload, compared against %s" % (len(new["films"]), REF))
    if not fixes:
        print("no truncated director names to restore")
        return
    for fid, name, a, b in fixes:
        print("  %-40s %r -> %r" % (name[:40], a, b))
    if dry:
        print("--dry-run, nothing written")
        return

    # Rewrite in place by id, in the serialised payload, so nothing else about the line
    # can move. A whole-payload re-serialisation would reorder keys and rewrite 650 KB to
    # change eleven characters.
    i = src.index("const SHOWS=")
    j = src.index("\n", i)
    line = src[i:j]
    for fid, name, a, b in fixes:
        needle = '"%s":{' % fid
        at = line.index(needle)
        end = line.index('}', at)
        chunk = line[at:end]
        fixed = re.sub(r'("dir":")%s(")' % re.escape(a), lambda m: m.group(1) + b + m.group(2),
                       chunk, count=1)
        if fixed == chunk:
            sys.exit("could not rewrite dir for %s (%s)" % (fid, name))
        line = line[:at] + fixed + line[end:]
    open(PAGE, "w", encoding="utf-8").write(src[:i] + line + src[j:])
    print("docs/index.html patched: %d director names restored" % len(fixes))


if __name__ == "__main__":
    main()
