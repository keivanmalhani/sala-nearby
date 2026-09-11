#!/usr/bin/env python3
"""Say the listing is out of date instead of quietly showing a dead one.

    /opt/homebrew/bin/python3 stale-listing.py

THE GAP THIS CLOSES. The showtimes are baked into the page, so the page goes stale on its
own while nobody is looking -- he goes away, nothing refreshes, and the snapshot ages past
its own last date. `past-days.py` already stopped the app offering a day that is over, and
it left one case deliberately open: when EVERY day in the payload is in the past there is
nothing left to offer, so the rail hands back the full list unchanged rather than going
blank.

That is the right thing to draw and the wrong thing to say. The app looks exactly as it
always does -- a day rail, a count, rows of times with prices -- and every one of those
times has already happened. Nothing on the screen distinguishes a listing from this
morning from one that ran out in November.

So this is the sentence that was missing. It fires only in that case, it names the date
the listing actually stops on, and it says what still works: the links go to the cinema's
own checkout, which is live whatever this page holds.

WHY IT IS NOT A DATE STAMP ON EVERY LAUNCH. A banner that is always there is furniture and
stops being read, and on a fresh payload it would be saying "this is fine" over and over.
The only moment the sentence carries information is the moment the listing is dead, and
that is the only moment it appears.

WHY IT IS NOT ON THE MAP TAB. The map is venues and walking distance and none of that goes
stale with the showtimes -- the cinemas are still there. Putting it on a tab it does not
apply to would be the same overreach as leaving it off the two where it does.
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


# ------------------------------------------------------------------------ 1. the question
swap("""/** The day indices worth putting on the rail:""",
     """/** Has this whole snapshot run out? True only when there is not one day left in it that
 *  has not already been and gone -- which is the case liveDayIdxs falls back on, and the
 *  one case where everything the app draws is a description of the past. */
function listingIsDead() {
  return DAYS.length > 0 && DAYS.every(isPast);
}
/** The sentence, or nothing at all. Built here rather than at each call site so the two
 *  tabs cannot drift into saying it differently. */
function staleLine() {
  if (!listingIsDead()) return "";
  return `<div class="stale"><b>These showtimes have run out.</b>
    The last day this page holds is ${esc(dateAbs(DAYS.length - 1))}, and everything on it
    has already played. Tapping a time still opens the cinema's own page, which is live.</div>`;
}

/** The day indices worth putting on the rail:""",
     "listingIsDead and staleLine, beside liveDayIdxs")

# ------------------------------------------------------------------- 2. on the two lists
swap("""  $("scount").innerHTML = `<b>${shown}</b> ${esc(lbl)}${""",
     """  $("scount").innerHTML = staleLine() + `<b>${shown}</b> ${esc(lbl)}${""",
     "the showtimes count line carries it")

swap("""  $("fcount").innerHTML = S.q""",
     """  $("fcount").innerHTML = staleLine() + (S.q""",
     "the films count line carries it")
swap("""    : `<b>${rows.length}</b> ${esc(nf)} playing ${isToday(dayIso) ? "today" : "that day"} near you`;""",
     """    : `<b>${rows.length}</b> ${esc(nf)} playing ${isToday(dayIso) ? "today" : "that day"} near you`);""",
     "closing the films count expression")

# ------------------------------------------------------------------------------ 3. style
# Amber rather than red: this is not an error, it is an old newspaper. It uses the tokens
# the rest of the page already defines so it follows the theme without a second palette.
swap("""/* An empty action bar is 25 pixels of padding and a rule under a heading.""",
     """.stale{display:block;margin:0 0 10px;padding:10px 12px;border-radius:10px;
  border:1px solid var(--c-free);background:var(--surface);color:var(--ink);
  font-family:"Bricolage Grotesque",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:13px;line-height:1.45;text-transform:none;letter-spacing:0}
.stale b{display:block;color:var(--c-free);margin-bottom:2px}
/* An empty action bar is 25 pixels of padding and a rule under a heading.""",
     "the stale banner's own rule")

open(PAGE, "w", encoding="utf-8").write(s)
print("docs/index.html patched: the page says when its listing has run out")
