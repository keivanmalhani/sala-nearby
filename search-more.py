#!/usr/bin/env python3
"""Search the director and the genre, not just the title.

    /opt/homebrew/bin/python3 search-more.py

Idea 19 in docs/IDEAS-2026-09-09.md. Typing "nolan" into the search box returns nothing
while La Odisea is playing at twenty-five cinemas with 276 showings, because the box reads
two fields and the director is not one of them. Neither is the genre, so "terror" finds
nothing either on a board carrying five horror films.

WHAT THAT IDEA WARNED ABOUT, AND WHERE IT NO LONGER APPLIES. It said adding `dir` to the
search would be a trap, because Cinemex published `"Christopher Nola"` -- truncated -- so
the two-line fix would ship looking correct and still return nothing for the most famous
director in the city. That was true on 9 September and it is not true now: merging the two
chains' entries for a film takes the better of the two director strings, and Cineteca
spells it out, so the payload reads "Christopher Nolan" today. The correction table that
idea called for is not needed for the case that motivated it.

ONE FIELD IS STILL VISIBLY BROKEN and nothing here repairs it: Juan Gabriel: Mi Primer
Bellas Artes carries "Reedicion 2026: Maria Jose Cuevas. Direccion 1990: Benjamin " with
the surname cut off mid-word by Cinemex. Searching "benjamin" finds it, searching the
surname does not. Inventing the rest of that name would be putting a fact on his screen
that nobody read anywhere, which is the one thing this app does not do.

THE PLACEHOLDER CHANGES TOO. A box labelled "Find a film" is a promise about what it
searches, and a person who has never typed a director's name into it has no way to learn
that it works.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

s = open(PAGE, encoding="utf-8").read()


def swap(before, after, why, count=1):
    global s
    n = s.count(before)
    if n != count:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if n == 0 else "x%d NOT %d" % (n, count), why, before[:120]))
    s = s.replace(before, after, count)


swap("""function matchesQuery(f) {
  if (!S.q) return true;
  return fold(f && f.n).includes(S.q) || fold(f && f.o).includes(S.q);
}""",
     """/** Four fields, in the order a person would think of them: the title he saw on a poster,
 *  the original title (which is how an English speaker knows a film released here under a
 *  Spanish name), the director, and the genre.
 *
 *  The genre is in the list because the payload is in Spanish and the chips are not: there
 *  are five horror films on this board and "terror" was the obvious thing to type. The
 *  director is in it because "nolan" returned nothing while La Odisea played at
 *  twenty-five cinemas.
 *
 *  Cinemex truncates some director strings mid-word -- one of them ends "Direccion 1990:
 *  Benjamin " -- so a surname search can still miss. That is a hole in their data and it
 *  is left as a hole rather than filled in with a name nobody read. */
function matchesQuery(f) {
  if (!S.q) return true;
  if (!f) return false;
  return fold(f.n).includes(S.q) || fold(f.o).includes(S.q) ||
         fold(f.dir).includes(S.q) || fold((f.g || []).join(" ")).includes(S.q);
}""",
     "matchesQuery reads four fields")

swap("""placeholder="Find a film" aria-label="Find a film\"""",
     """placeholder="Film, director, genre" aria-label="Find a film by title, director or genre\"""",
     "the search box says what it searches", count=2)

open(PAGE, "w", encoding="utf-8").write(s)
print("docs/index.html patched: the search box reads the director and the genre")
