#!/usr/bin/env python3
"""When to leave, on the cinema he is looking at.

    /opt/homebrew/bin/python3 leave-by.py

Idea 1 in docs/IDEAS-2026-09-09.md, and the one thing on that list that changes the app
from a listings page into something that tells him what to do. He is about to live four
minutes from Cinemex Insurgentes and nineteen from Pabellon Cuauhtemoc, on foot. The app
gives him "20:30" and "19 min walk" and makes him do the subtraction every time.

WHERE I DISAGREED WITH THE IDEA, AND WHY.

That write-up proposes `REEL = {cinemex: 17, cineteca: 3}` -- an ad allowance added to the
billed time so a 20:30 showing reads "leave 20:17". Nobody has measured those numbers.
Its own text says Cinemex runs "roughly 15-20 minutes", and the direction of the error is
the bad one: an allowance that is too generous tells him to leave later than he should and
he walks in during the film. A leave-by computed against the BILLED time can only ever
make him early, and being early to a cinema costs nothing.

So there is no reel constant. The glossary says out loud that Cinemex reels tend to run
fifteen to twenty minutes, which is the honest shape of that fact -- context he can use
rather than arithmetic done for him on a number nobody checked.

WHERE IT GOES. On the cinema's own header, next to the travel time it is computed from,
once per cinema. Not on every chip: the file's own reasoning about the price tag says a
second line on every chip doubles the height of the list, and that is just as true here.
The chips carry it in their accessible label instead, so it is there for VoiceOver and
costs no pixels.
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


# ---------------------------------------------------------------- 1. one travel number
# far() already decides walk-or-drive; leave-by has to use the same decision or the two
# lines on the header disagree with each other.
swap("""const walkMin = d => Math.max(1, Math.round(d / 0.075));   // 4.5 km/h
function far(d) {
  const w = walkMin(d);
  return { d: d < 1 ? Math.round(d * 1000) + " m" : d.toFixed(1) + " km",
           w: w <= 40 ? w + " min walk" : Math.round(d / 0.35) + " min drive" };
}""",
     """const walkMin = d => Math.max(1, Math.round(d / 0.075));   // 4.5 km/h
/** Minutes to get there, by whichever means far() is about to name. One function, because
 *  a header that says "19 min walk" and a leave-by computed from a drive time would be two
 *  numbers contradicting each other on the same row. */
function travelMin(d) {
  const w = walkMin(d);
  return w <= 40 ? w : Math.round(d / 0.35);
}
function far(d) {
  const w = walkMin(d);
  return { d: d < 1 ? Math.round(d * 1000) + " m" : d.toFixed(1) + " km",
           w: w <= 40 ? w + " min walk" : Math.round(d / 0.35) + " min drive" };
}

/* WHEN TO LEAVE, against the BILLED time and nothing else.
   There is no ad-reel allowance in this subtraction on purpose. The reel is real -- a
   Cinemex feature typically starts fifteen to twenty minutes after the time on the ticket
   -- but nobody here has measured it, and an allowance that is too generous sends him out
   of the door late. Against the billed time the worst this can do is make him early.
   Returns null where the question does not apply: another day, or a showing already gone. */
function leaveBy(startMins, distKm, dayIso) {
  if (!isToday(dayIso)) return null;
  if (startMins < nowMins()) return null;          // it has already started
  return startMins - travelMin(distKm);            // may be in the past: that means leave now
}""",
     "the travel-time helper and leaveBy")

# ---------------------------------------------------------------- 2. the header line
swap("""    if (!byFilm.size) return "";
    withAny++;
    const F = far(c.dist);""",
     """    if (!byFilm.size) return "";
    withAny++;
    const F = far(c.dist);
    // The soonest showing here that he could still sit down for, across every film left
    // after the filters and the search -- so the line answers the question he is actually
    // asking while scanning this list: is this cinema still catchable.
    let nextStart = null;
    if (isToday(dayIso)) {
      for (const [, fm] of byFilm) {
        for (const [, list] of fm) {
          for (const x of list) {
            if (x[3] >= nowMins() && (nextStart === null || x[3] < nextStart)) nextStart = x[3];
          }
        }
      }
    }
    const lv = nextStart === null ? null : leaveBy(nextStart, c.dist, dayIso);""",
     "the soonest catchable showing per cinema")

swap("""        <span class="far"><b>${F.d}</b><em>${F.w}</em></span>
      </button>${films}</div>`;""",
     """        <span class="far"><b>${F.d}</b><em>${F.w}</em></span>
        ${lv === null ? "" : `<span class="lv${lv <= nowMins() ? " now" : ""}">${
          lv <= nowMins() ? "Leave now" : "Leave " + hhmm(lv)} for the ${hhmm(nextStart)}</span>`}
      </button>${films}</div>`;""",
     "the leave-by line on the cinema header")

# ---------------------------------------------------------------- 3. the chips' label
swap("""            return `<a class="${cls}" href="${href}" target="_blank" rel="noopener"
              aria-label="${esc(hhmm(s[3]))} ${esc(f.n)} ${esc(s[6] || "")}">${hhmm(s[3])}${""",
     """            // In the label rather than on the face of the chip. A second line on every
            // time would double the height of this list, which is the same objection the
            // price tag is grouped for -- but there is no cost to saying it out loud.
            const lvs = past ? null : leaveBy(s[3], c.dist, dayIso);
            return `<a class="${cls}" href="${href}" target="_blank" rel="noopener"
              aria-label="${esc(hhmm(s[3]))} ${esc(f.n)} ${esc(s[6] || "")}${
                lvs === null ? "" : lvs <= nowMins() ? ", leave now" : ", leave at " + hhmm(lvs)
              }">${hhmm(s[3])}${""",
     "the leave-by in each chip's accessible label")

# ---------------------------------------------------------------- 4. the CSS
swap(""".cin .far em{display:block;font-family:"IBM Plex Mono",monospace;font-size:10px;font-style:normal;color:var(--ink-3);letter-spacing:.06em;margin-top:2px;white-space:nowrap}""",
     """.cin .far em{display:block;font-family:"IBM Plex Mono",monospace;font-size:10px;font-style:normal;color:var(--ink-3);letter-spacing:.06em;margin-top:2px;white-space:nowrap}
/* WHEN TO LEAVE. Spans both columns under the name and the distance, because it is a
   sentence about the pair of them rather than a property of either. Amber only when the
   answer is "now" -- an urgent colour on every row is not urgency, it is wallpaper. */
.cin .lv{grid-column:1/-1;margin-top:7px;font-family:"IBM Plex Mono",monospace;font-size:10.5px;
  letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3)}
.cin .lv.now{color:var(--lamp);font-weight:600}""",
     "the leave-by styling")

open(PAGE, "w", encoding="utf-8").write(s)
print("leave-by: 5 anchors replaced in docs/index.html")
