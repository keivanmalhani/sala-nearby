#!/usr/bin/env python3
"""A day that has already happened is not a choice.

    /opt/homebrew/bin/python3 past-days.py

WHAT IS WRONG TODAY. The page was built on 9 September, when day 0 of the snapshot was
that morning. It is the 11th. Opening the app puts "Wed 9/9" and "Thu 10/9" at the head
of the day rail, ahead of Today, and both of them are over. Tapping one lists showtimes
that finished two days ago with nothing on the row to say so -- the dimming that marks a
time as gone is scoped to `isToday`, so on a past day every chip looks live and bookable.

The first thing he sees when he opens his own app is two chips that lie, and he has to
scroll past them to reach today.

Refreshing the showtimes hides this for another two days and then it comes back. The
durable half is here: the rail offers days that have not been and gone, and the app opens
on the first of them. Both are still read off the sessions, so a payload with a gap in it
still only ever offers days that carry something.

THE FALLBACK IS DELIBERATE. If every day in the payload is in the past -- nobody refreshed
for a month -- the filter would leave an empty rail, and an empty rail says less than a
stale one. In that case it shows all of them, unchanged, because a person looking at a
month-old listing can at least see that it is a month old. There is no new empty state
and no new warning banner: the dates on the chips already say it.

AND THE SECOND BUG, which is the same bug wearing different clothes. The Films tab counts
with `S.day === 0 ? "today" : "that day"`. Day 0 was today on the morning the line was
written and has not been since. Right now, on today, the app says "83 films playing that
day near you". It asks the index whether it is today when there is a function three
hundred lines up that asks the date.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")

s = open(PAGE, encoding="utf-8").read()


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:120]))
    s = s.replace(before, after, 1)


# ------------------------------------------------------------------ 1. the two questions
# isPast is isToday's comparison with a different operator, and it is written out rather
# than derived (`!isToday && earlier`) so that reading one tells you what the other does.
swap("""function isToday(iso) {
  const d = new Date(iso + "T12:00:00"), t = new Date(); t.setHours(12, 0, 0, 0);
  return +d === +t;
}""",
     """function isToday(iso) {
  const d = new Date(iso + "T12:00:00"), t = new Date(); t.setHours(12, 0, 0, 0);
  return +d === +t;
}
function isPast(iso) {
  const d = new Date(iso + "T12:00:00"), t = new Date(); t.setHours(12, 0, 0, 0);
  return +d < +t;
}
/** The day indices worth putting on the rail: every day the payload has a session on,
 *  minus the ones that have already been and gone.
 *
 *  The snapshot is baked into the page and the page is opened on later days than the one
 *  it was built on -- two days later, the morning this was written. A chip for a day that
 *  is over is not a stale listing, it is a dead one: nothing on it can be bought, and the
 *  row-level dimming that marks a time as past only runs on today, so those chips look
 *  exactly like live ones.
 *
 *  When EVERY day is in the past the filter would empty the rail, so it returns all of
 *  them instead. A month-old listing that admits its dates beats a blank screen. */
function liveDayIdxs() {
  const have = new Set();
  SHOWS.cin.forEach(c => c.s.forEach(s => have.add(s[2])));
  const all = [...have].sort((a, b) => a - b);
  const live = all.filter(i => !isPast(DAYS[i]));
  return live.length ? live : all;
}""",
     "isPast and liveDayIdxs beside isToday")

# ------------------------------------------------------------------------- 2. the rail
# That comment has been wrong since the fortnight slice came out, which is the same class
# of thing as the bug underneath it: a line describing the code as it was on the day it
# was written. It goes with the build it describes.
swap("""  // Only days that actually carry sessions, and only the next fortnight -- the tail of
  // the advance-sales window is three lonely showings in mid-October and a date chip for
  // each of those is noise, not choice.
  const have = new Set();
  SHOWS.cin.forEach(c => c.s.forEach(s => have.add(s[2])));
""", "", "the rail's own day-set build, now liveDayIdxs's job")

swap("""  // `have` is built from the sessions themselves, so every chip on the rail is a day
  // with something on it. The rail scrolls; that is what it is for.
  const idxs = [...have].sort((a, b) => a - b);""",
     """  // liveDayIdxs reads the sessions themselves, so every chip on the rail is a day with
  // something on it that has not already happened. The rail scrolls; that is what it is
  // for.
  const idxs = liveDayIdxs();""",
     "the rail reads liveDayIdxs")

# --------------------------------------------------------------- 3. the day it opens on
swap("""/* start on today if the snapshot has it */
const todayIdx = DAYS.findIndex(isToday);
S.day = todayIdx >= 0 ? todayIdx : 0;""",
     """/* Start on today when the snapshot has it, and otherwise on the first day it still
   offers -- never on day 0, which is only today on the morning the payload was pulled. */
const todayIdx = DAYS.findIndex(isToday);
const liveIdxs = liveDayIdxs();
S.day = liveIdxs.includes(todayIdx) ? todayIdx : (liveIdxs.length ? liveIdxs[0] : 0);""",
     "the opening day")

# ------------------------------------------------------------------------ 4. the wording
swap("""`<b>${rows.length}</b> ${esc(nf)} matching &ldquo;${esc(S.q)}&rdquo; ${S.day === 0 ? "today" : "that day"}`""",
     """`<b>${rows.length}</b> ${esc(nf)} matching &ldquo;${esc(S.q)}&rdquo; ${isToday(dayIso) ? "today" : "that day"}`""",
     "the search count line says today when it is today")

swap("""`<b>${rows.length}</b> ${esc(nf)} playing ${S.day === 0 ? "today" : "that day"} near you`""",
     """`<b>${rows.length}</b> ${esc(nf)} playing ${isToday(dayIso) ? "today" : "that day"} near you`""",
     "the films count line says today when it is today")

open(PAGE, "w", encoding="utf-8").write(s)
print("docs/index.html patched: past days off the rail, and 'today' asks the date")
