#!/usr/bin/env python3
"""The rooms that cost nothing, as a list rather than fifteen unlabelled dots.

    /opt/homebrew/bin/python3 free-rooms.py

Idea 17 in docs/IDEAS-2026-09-09.md. Thirteen of the forty-two audited venues are free
outright and two more are sometimes free -- the Goethe-Institut at "$50 / free" and the
Centro Cultural Jose Marti at "$22 / free" -- and every one of those facts is currently
locked inside a separate write-up reachable only by tapping the right coloured dot on the
map. Since the Guide tab was removed there is no list of venues anywhere in the app.

WHERE I DISAGREED WITH THE IDEA, AND IT IS THE NAME.

That write-up calls this "Free tonight". It cannot be. None of the fifteen publishes
showtimes a page like this can read -- that is why they are audit-only venues with no
sessions in the payload -- so the app has no idea what is on at any of them tonight or on
any other night. The heading says "Free screens" and the note says the app cannot see
their programme, because a screen headed "tonight" over a list that knows nothing about
tonight is the exact small lie this app is built not to tell.

THE SECOND THING I LEFT OUT ON PURPOSE. Several of these audits do carry a rhythm --
"Thursdays 17:00", "Tue and Fri 16:30", "Mondays 19:00" -- and pulling those out with a
regex was tempting, because the venue audit's own sala-versus-format check already reads
prose that way. Two of them are worded "(e.g. Saturdays 13:00)", which is an example
rather than a schedule, and three more sit in rows tagged likely with "2026 continuation
not confirmed" beside them. A weekday lifted out of that and printed on a row reads as a
timetable. The sentences are already on each venue's own sheet, in full, with the tag
that says how well they are known, and that is where they stay.

WHAT IS FREE IS READ OFF THE AUDIT, NOT LISTED HERE. The split is `price` being exactly
"free" against `price` merely mentioning it, so the two groups follow the research file
rather than a name written into the page. If a venue starts charging, editing the audit
moves it, and if every one of them did, the button disappears rather than opening an
empty sheet.

WHERE IT GOES. On the map, bottom left, which is the only pane with no words on it at
all and the pane these fifteen already live on as dots. It doubles as the caption the map
has not had since the legend was removed.
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


# ------------------------------------------------------------------- 1. the map caption
swap("""      <div class="mapctl chrome">""",
     """      <button class="mapfree chrome" id="freebtn" aria-haspopup="dialog"></button>
      <div class="mapctl chrome">""",
     "the free-screens button on the map")

# ------------------------------------------------------------------------- 2. the sheet
swap("""/* ===================== MAP ===================== */""",
     """/* ---------- the rooms that cost nothing ----------

   WHAT COUNTS AS FREE IS THE AUDIT'S OWN `price` FIELD, split on whether it says only
   "free" or merely mentions it. Nothing is listed here by name: a venue that starts
   charging leaves this list by having its audit edited, which is the only place that
   fact should live. Both groups are empty on a payload where nobody is free, and then
   the button does not render at all rather than opening an empty sheet. */
const FREE = V.map((v, i) => ({ v, i }))
  .filter(x => /free/i.test(String(x.v.price || "")));
const isFreeAlways = v => String(v.price || "").trim().toLowerCase() === "free";

function freeRows(list) {
  return list.map(({ v, i }) => {
    const F = far(km(origin, { lat: v.lat, lng: v.lng }));
    // The operator and what kind of room it is, which between them are the whole reason
    // to pick one of these over another: a Filmoteca satellite and a bar cineclub are
    // not the same evening.
    const what = [v.op, ...(v.f || [])].filter(Boolean).join(" \\u00b7 ");
    return `<button class="frow" data-venue="${i}">
      <span><span class="n">${esc(v.name)}</span>
        <span class="s">${esc(what)}</span>
        ${isFreeAlways(v) ? "" : `<span class="at"><b>${esc(v.price)}</b></span>`}</span>
      <span class="cnt"><b>${F.d}</b><em>${esc(F.w)}</em></span></button>`;
  }).join("");
}

function freeSheet() {
  const rows = FREE.map(x => ({ ...x, d: km(origin, { lat: x.v.lat, lng: x.v.lng }) }))
    .sort((a, b) => a.d - b.d);
  if (!rows.length) return;
  const always = rows.filter(x => isFreeAlways(x.v)), sometimes = rows.filter(x => !isFreeAlways(x.v));
  const near = far(rows[0].d);
  const head = `<div><h2>Free screens</h2><div class="addr">${always.length} rooms near
      here show films for nothing${sometimes.length
        ? `, and ${sometimes.length} more sometimes do` : ""}.</div></div>
    <div class="far"><b>${near.d}</b><em>nearest</em></div>`;
  // THE HONEST SENTENCE, and it is the reason this is not called "free tonight". These
  // venues are in the app because somebody audited them by hand; not one of them
  // publishes a machine-readable programme, which is exactly why they have no showtimes
  // anywhere else in the app either.
  const body = `<p class="plain">None of these publishes a programme this app can read,
      so it cannot tell you what is on tonight at any of them. What it can tell you is
      that they exist, how far they are, and what each one is &mdash; which is more than
      any ticketing app will.</p>
    <div class="sec"><h3>Free</h3></div>${freeRows(always)}
    ${sometimes.length ? `<div class="sec"><h3>Sometimes free</h3></div>${freeRows(sometimes)}` : ""}
    <div class="sec"><p class="note" style="margin:0">Tap any of them for the full
      write-up: how often it runs, what it programmes, and how well each of those is
      known. ${always.length + sometimes.length} of the ${V.length} audited venues are on
      this list.</p></div>`;
  openSheet(head, "", body, "var(--c-free)");
}

/* ===================== MAP ===================== */""",
     "the free-screens sheet")

# --------------------------------------------------------------------- 3. the label, once
swap("""S.day = todayIdx >= 0 ? todayIdx : 0;
renderDates(); renderFilters(); renderShows();""",
     """S.day = todayIdx >= 0 ? todayIdx : 0;
renderDates(); renderFilters(); renderShows();
// The button says how many, and the number is counted rather than written down. No free
// venues means no button, which is the only honest empty state for a caption.
if (FREE.length) $("freebtn").textContent = `${FREE.length} free screens`;
else $("freebtn").remove();""",
     "the free-screens button label")

# ------------------------------------------------------- 4. the dots the caption is about
# A caption in a colour that appears nowhere on the map is a caption about nothing. The
# free venues were green, the same green as Cine Tonala and the Chopo, which charge. So
# the same test that fills the sheet colours the dot, and the pill becomes a legend for
# exactly one colour rather than a legend for all four -- which is the thing he had
# removed. Green keeps its meaning and loses fifteen members: an independent you pay for.
swap("""const CAT = v => v.grp === "indie" ? "var(--c-art)"
  : (v.f || []).some(x => /IMAX|CinemeXtremo|4DX|ScreenX/i.test(x)) ? "var(--c-big)"
  : (v.f || []).some(x => /Platino|VIP/i.test(x)) ? "var(--c-lux)" : "var(--c-std)";""",
     """const CAT = v => /free/i.test(String(v.price || "")) ? "var(--c-free)"
  : v.grp === "indie" ? "var(--c-art)"
  : (v.f || []).some(x => /IMAX|CinemeXtremo|4DX|ScreenX/i.test(x)) ? "var(--c-big)"
  : (v.f || []).some(x => /Platino|VIP/i.test(x)) ? "var(--c-lux)" : "var(--c-std)";""",
     "the free venues get their own colour on the map")

# --------------------------------------------------------------------------- 5. the tap
swap("""  const ven = e.target.closest("[data-venue]"); if (ven) return venueSheet(+ven.dataset.venue);""",
     """  const ven = e.target.closest("[data-venue]"); if (ven) return venueSheet(+ven.dataset.venue);
  // After [data-venue], never before: the rows inside this sheet carry one, and a row tap
  // has to open that venue rather than redraw the list it was tapped from.
  if (e.target.closest("#freebtn")) return freeSheet();""",
     "opening the free-screens sheet")

# -------------------------------------------------------------------------- 6. the CSS
swap(""".mapctl button:active{background:var(--tap)}""",
     """.mapctl button:active{background:var(--tap)}
/* THE MAP'S ONLY WORDS. Bottom left, opposite the attribution, in the colour this palette
   has carried for free venues since the first build and never used. It is a caption as
   much as a control: the legend came off on his say-so and the map has said nothing about
   itself since. */
.mapfree{position:absolute;left:12px;bottom:calc(env(safe-area-inset-bottom,0px) + 12px);
  z-index:600;min-height:38px;padding:0 14px;border-radius:19px;background:var(--surface);
  border:1px solid var(--line);box-shadow:0 2px 10px rgba(0,0,0,.18);
  font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--c-free);font-weight:600}
.mapfree:active{background:var(--tap)}
/* An empty action bar is 25 pixels of padding and a rule under a heading. A sheet that
   has no single action -- fifteen venues have fifteen -- should not draw one. */
.sheet .go:empty{display:none}""",
     "the map caption styling")

open(PAGE, "w", encoding="utf-8").write(s)
print("free-rooms: 6 anchors replaced in docs/index.html")
