#!/usr/bin/env python3
"""What is on later, and what is on for the last time.

    /opt/homebrew/bin/python3 coming-up.py

Idea 6 in docs/IDEAS-2026-09-09.md -- "the screenings that happen once" -- built in the
one shape the data can actually carry.

WHERE I DISAGREED WITH THE IDEA, AND WHY IT MATTERS MORE HERE THAN ANYWHERE.

That write-up proposes "a view of everything playing exactly once or twice in the next
month", and cites 93 film-and-cinema pairs with a single session and 25 films with three
or fewer showings in thirty days. Those counts are real. The conclusion drawn from them
is not, and building the feature as described would have put a false sentence on his
phone.

**Cineteca publishes two days at a time.** Measured on the live payload: Cinemex carries
30 days, 2026-09-09 to 2026-10-14, and Cineteca carries 2026-09-09 and 2026-09-10 and
nothing else. Twenty-two of the twenty-three films with three or fewer showings are
Cineteca titles, and they are rare in this data for exactly one reason -- the listing
stops on Thursday. "El principe de Nanawa plays twice this month" would be a claim about
our fetch wearing the clothes of a claim about the cinema.

SO THE RARITY TEST IS NOT A COUNT, IT IS A QUESTION ABOUT THE LISTING: has a cinema
published a whole programming week that does not contain this film? Cinema weeks in
Mexico start on Thursday -- README.md and refresh-showtimes.py both say so, and it is why
a Tuesday pull sees less than a Thursday one -- so a complete week is seven consecutive
published days beginning on a Thursday. A film's run is over when EVERY cinema showing it
has published such a week after its last date. Cineteca has never published one, so no
Cineteca screening is ever called a last day, which is correct. Cinemex has published
three, so "Rebelion en la Granja plays 30 times today and is not in the next three weeks"
is a fact rather than an artefact.

The seven is the number of days in a week, not a threshold anybody picked.

The same test refuses PULP, and refusing it is the proof the test works: eight cinemas,
one date, Thursday 24 September, and Cinemex has published only to the 30th -- six days,
no complete week after it. So the row says what the listing says, "Thu 24 Sep, 1 date,
8 cinemas", and claims nothing about October.

WHAT GOES ON SCREEN. Two things, both in the Films tab:

  - a "Coming up" block under the day's films: every film whose first showing is after
    the day being looked at, ordered by that date, with its dates spelled out where there
    are one or two of them. Twenty films are in that state today and the app's only route
    to any of them is tapping along thirty day chips.
  - "Last day" on a film row, where the run is over and it ends on the day shown.

Search and the filters narrow both, so a search for "queen" on a day it does not play
now finds Queen: Budapest on 7 October instead of an empty screen.
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


# ------------------------------------------------------------------ 1. the run of a film
swap("""/* ---------- distance-aware cinema list ---------- */""",
     """/* ---------- how long a film's run is, and whether we can see the end of it ----------

   A COMPLETE PROGRAMMING WEEK IS THE UNIT, because a count of showings is not evidence
   of rarity. Cinema weeks here start on Thursday, which is why a Tuesday pull sees less
   than a Thursday one, so a complete week is seven consecutive published days beginning
   on a Thursday. `weekAfter` is the latest such week each cinema has published; a film's
   run can only be called finished when every cinema showing it has published a whole
   week that does not contain it.

   Cineteca publishes two days at a time -- 2026-09-09 and 2026-09-10 on this payload,
   against Cinemex's thirty -- so it has never published a complete week and nothing there
   is ever called a last day. That is the whole reason this is a week test and not a
   count: twenty-two of the twenty-three films with three or fewer showings are Cineteca
   titles, and they are rare in the data because the listing stops, not because the film
   does. */
const DOW_OF = i => new Date(DAYS[i] + "T12:00:00").getDay();   // 4 = Thursday
const WEEK_AFTER = new Map();     // cinema id -> latest complete Thu..Wed week it publishes
for (const c of SHOWS.cin) {
  const have = new Set(c.s.map(x => x[2]));
  let best = -1;
  for (const start of have) {
    if (DOW_OF(start) !== 4) continue;
    let whole = true;
    for (let k = 1; k < 7; k++) if (!have.has(start + k)) { whole = false; break; }
    // The seven days have to be seven CONSECUTIVE DATES, and a day index is only the
    // same thing as a date while the payload has no gaps in it. It does: the tail of the
    // advance window jumps 2026-10-04 to 2026-10-07. So the run of indices is checked
    // against the calendar rather than assumed to be one.
    if (whole && (new Date(DAYS[start + 6] + "T12:00:00") - new Date(DAYS[start] + "T12:00:00"))
        !== 6 * 86400000) whole = false;
    if (whole && start > best) best = start;
  }
  WEEK_AFTER.set(String(c.id), best);
}

/** Every film that survives the filters and the search, with the dates it plays on.
 *  ONE PASS over the payload rather than one per film, and the dates are the FILTERED
 *  ones on purpose: with Subtitled on, "1 date" means one subtitled date, which is the
 *  question he is actually asking. Whether a week has been PUBLISHED is a fact about the
 *  listing and is never filtered. */
function filmRuns() {
  const out = new Map();
  for (const c of SHOWS.cin) {
    const wk = WEEK_AFTER.get(String(c.id));
    for (const x of c.s) {
      if (!passes(x[1], x[3], DAYS[x[2]])) continue;
      if (!matchesQuery(SHOWS.films[x[0]])) continue;
      const k = String(x[0]);
      let r = out.get(k);
      if (!r) { r = { fid: k, days: new Set(), cin: new Set(), n: 0,
                      first: Infinity, last: -1, week: Infinity }; out.set(k, r); }
      r.days.add(x[2]); r.cin.add(c.id); r.n++;
      if (x[2] < r.first) r.first = x[2];
      if (x[2] > r.last) r.last = x[2];
      if (wk < r.week) r.week = wk;        // the weakest listing decides, never the best
    }
  }
  for (const r of out.values()) r.closed = r.week > r.last;
  return out;
}

/** "Thu 24 Sep", always, and "Tomorrow" only where a row is naming a day to go on. The
 *  day rail already says Today and Tomorrow, so a row reads the same way as the rail --
 *  but a sentence about how far a listing REACHES needs the date, because "Cineteca goes
 *  out to Tomorrow" is a sentence that stops being true overnight. */
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function dateAbs(i) {
  const d = new Date(DAYS[i] + "T12:00:00");
  return `${["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()]} ${d.getDate()} ${MON[d.getMonth()]}`;
}
function dateWords(i) {
  const L = dayLabel(DAYS[i], i);
  return L.b === "Today" || L.b === "Tomorrow" ? L.b : dateAbs(i);
}

/* ---------- distance-aware cinema list ---------- */""",
     "the week test, the run map and the date words")

# ------------------------------------------------------------- 2. the Films tab count line
swap("""  $("fcount").innerHTML = S.q""",
     """  // WHAT IS ON LATER. The app opens on today and the only way to find a one-night
  // screening three weeks out is to tap along the day rail, thirty chips of it. Twenty
  // of the eighty films in this payload are not on today at all.
  const runs = filmRuns();
  const later = S.filters.has("now") ? []
    : [...runs.values()].filter(r => r.first > S.day)
        .sort((a, b) => a.first - b.first || b.n - a.n);
  $("fcount").innerHTML = S.q""",
     "the coming-up set, computed once per render")

# The count line has to name it, or a block at the foot of sixty films is a block nobody
# scrolls to.
swap("""    ? `<b>${rows.length}</b> ${esc(nf)} matching &ldquo;${esc(S.q)}&rdquo; ${S.day === 0 ? "today" : "that day"}`
    : `<b>${rows.length}</b> ${esc(nf)} playing ${S.day === 0 ? "today" : "that day"} near you`;""",
     """    ? `<b>${rows.length}</b> ${esc(nf)} matching &ldquo;${esc(S.q)}&rdquo; ${S.day === 0 ? "today" : "that day"}`
    : `<b>${rows.length}</b> ${esc(nf)} playing ${S.day === 0 ? "today" : "that day"} near you`;
  if (later.length) $("fcount").innerHTML +=
    ` &middot; ${later.length} more start${later.length === 1 ? "s" : ""} later`;""",
     "the count line naming the later block")

# ------------------------------------------------------------------ 3. the Last day badge
swap("""        <span class="fm">${fmtBadges(r.types, 3)}</span></span>""",
     """        <span class="fm">${(() => {
          // LAST DAY, and only where the listing can support the word. The run has to be
          // finished -- every cinema playing it has published a whole week without it --
          // and it has to finish on the day being looked at. Nothing at Cineteca ever
          // qualifies, because two days is not a week, which is the point.
          const run = runs.get(String(r.fid));
          return run && run.closed && run.last === S.day
            ? `<span class="badge last">Last day</span> ` : "";
        })()}${fmtBadges(r.types, 3)}</span></span>""",
     "the last-day badge on a film row")

# ---------------------------------------------------------------- 4. the coming-up block
swap("""  }).join("") || `<div class="empty"><b>${S.q ? "No film called that" : "Nothing that day"}</b></div>`;""",
     """  }).join("") || `<div class="empty"><b>${S.q ? "No film called that" : "Nothing that day"}</b>${
    later.length ? `Nothing on this day, but ${later.length === 1 ? "one film starts" : later.length + " films start"} later.` : ""}</div>`;

  // The dates are read off the listing and nothing is called rare. A film with one date
  // in this payload has one date in this payload; whether it returns in October is a
  // question about a listing nobody has published yet, and the note at the foot says so
  // by naming how far each chain actually goes -- both numbers measured here rather than
  // written down, so the sentence cannot go stale the way a hardcoded count would.
  const lastDayOf = pred => {
    let m = -1;
    for (const c of SHOWS.cin) { if (!pred(c)) continue; for (const x of c.s) if (x[2] > m) m = x[2]; }
    return m;
  };
  const ctLast = lastDayOf(c => isCineteca(c.id)), cxLast = lastDayOf(c => !isCineteca(c.id));
  $("filmlist").innerHTML += later.length ? `<div class="up"><h3>Coming up</h3>${
    later.map(r => {
      const f = SHOWS.films[r.fid];
      const ds = [...r.days].sort((a, b) => a - b);
      const when = ds.length <= 2
        ? ds.map(dateWords).join(" and ")
        : `from ${dateWords(ds[0])} &middot; ${ds.length} dates`;
      return `<button class="frow haspos" data-film="${esc(r.fid)}" data-jump="${ds[0]}">
        ${posterCard(r.fid, f.n, "", false)}
        <span><span class="n">${esc(f.n)}</span>
          <span class="s">${esc([f.d, f.r, (f.g || []).join(", ")].filter(Boolean).join(" \\u00b7 "))}</span>
          <span class="at"><b>${when}</b> <span>${r.cin.size} ${
            r.cin.size === 1 ? "cinema" : "cinemas"}</span></span></span>
        <span class="cnt"><b>${r.n}</b><em>showings</em></span></button>`;
    }).join("")}<p class="note">These are the dates as each chain has published them, and
    the two windows are nothing like the same length.${cxLast >= 0
      ? ` Cinemex here goes out to ${esc(dateAbs(cxLast))}.` : ""}${ctLast >= 0
      ? ` Cineteca goes out to ${esc(dateAbs(ctLast))} and publishes two days at a time,
        so a Cineteca title with one date here has one date on the board rather than one
        date in its run.` : ""}</p></div>` : "";""",
     "the coming-up block under the day's films")

# --------------------------------------------------------------------- 5. tapping a row
# A row that only opened the sheet would show the film against the day he is on, which is
# a day it does not play -- an empty sheet under a row that just told him when it plays.
swap("""  const film = e.target.closest("[data-film]"); if (film) return filmSheet(film.dataset.film);""",
     """  const film = e.target.closest("[data-film]");
  if (film) {
    // A Coming up row carries the day it starts. Move the whole app to that day before
    // opening the sheet: the sheet lists cinemas for S.day, so without this it would open
    // empty under a row that had just said which day to go.
    if (film.dataset.jump != null) {
      S.day = +film.dataset.jump;
      renderDates(); renderFilters(); renderShows(); renderFilms();
    }
    return filmSheet(film.dataset.film);
  }""",
     "jumping to the day a coming-up film starts")

# -------------------------------------------------------------------------- 6. the CSS
swap(""".frow .cnt em{""",
     """/* COMING UP. Separated from the day's films by a rule and a mono heading, the same
   vocabulary the sheet sections already use, because it is a different question rather
   than more of the same answer. */
.up{border-top:1px solid var(--line);margin-top:10px;background:var(--sunk)}
.up h3{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--ink-3);font-weight:500;margin:0;padding:14px 16px 6px}
.up .frow{background:var(--surface)}
.up .note{padding:0 16px 18px;margin:9px 0 0}
/* The last-day badge borrows the format badge's shape and the lamp, which is the one
   colour in this palette that means act on this -- it is already the leave-now line and
   the showings count. NOT --c-big: that is the Platino badge, and a film can be both, so
   the two would be the same orange rectangle side by side on the same row. */
.badge.last{background:var(--lamp);color:var(--lamp-ink)}
.frow .cnt em{""",
     "the coming-up styling")

open(PAGE, "w", encoding="utf-8").write(s)
print("coming-up: 7 anchors replaced in docs/index.html")
