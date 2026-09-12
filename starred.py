#!/usr/bin/env python3
"""Star a film, and find it again.

    /opt/homebrew/bin/python3 starred.py

Idea 7 on the list he was given on 8 September -- "no way to star a film" -- and the only
one on that list still not built apart from the two the data cannot carry. He asked on 12
September for the app to keep moving, and this is the smallest thing that changes how it is
used rather than what it shows: 80 films, 35 cinemas and thirty days is a lot to scan for
the three things he actually wants to see.

WHAT IT DOES.

  - A Star button on every film's sheet, under the title. Tapping it again takes it off.
  - A "Starred" chip beside Starting soon, Subtitled and the room chips. It stacks with them
    like every other chip, so "starred, subtitled, IMAX" is a question the app can answer.
  - Starred films float to the top of both lists and carry a small star, so they are found
    without the chip too.
  - Stars are saved on the phone beside sala.filters, under the same rule: every read and
    write wrapped, and an unreadable value means nothing is starred rather than a page that
    throws.

TWO DECISIONS, BOTH AGAINST THE OBVIOUS VERSION.

The chip is NOT remembered between launches. Subtitled is, because it is a standing
preference in a city that dubs two showings in three. Starred is a way of looking, like
Starting soon, and restoring it would open the app on a list of three films with the other
seventy-seven quietly hidden. The stars themselves are remembered; the filter is not.

The filters could not see which film a showing belongs to. `passesOne` was written for
format and time questions only, so the film id is threaded through `passes` at every one of
its five call sites. A call site left on the old signature would count every showing as
unstarred and grey the chip out for no visible reason, so test-starred.mjs reads every call
in the page and requires the id on all of them.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
SW = os.path.join(ROOT, "docs", "sw.js")
README = os.path.join(ROOT, "README.md")

s = open(PAGE, encoding="utf-8").read()
if "sala.starred" in s:
    sys.exit("starred.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why, expect=1):
    global s
    n = s.count(before)
    if n != expect:
        sys.exit("ANCHOR %s (%s):\n  %s" %
                 ("GONE" if n == 0 else "x%d, expected %d" % (n, expect), why, before[:120]))
    s = s.replace(before, after)


STAR_PATH = "M12 3.3l2.6 5.5 6 .8-4.4 4.2 1.1 6L12 17l-5.3 2.8 1.1-6-4.4-4.2 6-.8z"

# ---- state ---------------------------------------------------------------------------
swap('// the search box, shared by both lists\n};',
     '// the search box, shared by both lists\n'
     '  starred: new Set(),   // film ids he has starred, as strings; saved as sala.starred\n};',
     "S gains a starred set")

swap('\nloadFilters();\n',
     '\nloadFilters();\n\n'
     '/* STARRED FILMS, his own short list, saved beside sala.filters under the same rule.\n'
     '   Ids are kept as strings: Cinemex ids are numbers and Cineteca\'s start with "ct-", and\n'
     '   the payload hands out both. A starred film that is not in this week\'s listing stays\n'
     '   starred, because it may be back in the next pull. */\n'
     'const STAR_SVG = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + STAR_PATH + '"/></svg>`;\n'
     'const STAR_MARK = `<svg class="stm" viewBox="0 0 24 24" role="img" aria-label="Starred"><path d="' + STAR_PATH + '"/></svg>`;\n'
     'function loadStarred() {\n'
     '  try {\n'
     '    const raw = localStorage.getItem("sala.starred");\n'
     '    if (!raw) return;\n'
     '    const saved = JSON.parse(raw);\n'
     '    if (!Array.isArray(saved)) return;\n'
     '    saved.forEach(id => { if (typeof id === "string" || typeof id === "number") S.starred.add(String(id)); });\n'
     '  } catch (e) { /* nothing starred yet, or storage refused */ }\n'
     '}\n'
     'function saveStarred() {\n'
     '  try { localStorage.setItem("sala.starred", JSON.stringify([...S.starred])); }\n'
     '  catch (e) { /* storage refused; the stars still work for this session */ }\n'
     '}\n'
     'function isStarred(fid) { return fid != null && S.starred.has(String(fid)); }\n'
     'function starBtn(fid) {\n'
     '  const on = isStarred(fid);\n'
     '  return `<button class="starbtn" data-star="${esc(String(fid))}" aria-pressed="${on}">${STAR_SVG}<span>${on ? "Starred" : "Star this film"}</span></button>`;\n'
     '}\n'
     'loadStarred();\n',
     "load, save and draw stars")

# The chip is a way of looking, not a preference, so it is never written back.
swap('JSON.stringify([...S.filters].filter(k => k !== "now"))',
     'JSON.stringify([...S.filters].filter(k => k !== "now" && k !== "star"))',
     "Starred is not saved as a standing filter")

# ---- the filter itself -----------------------------------------------------------------
swap('function passesOne(key, fmtIdx, mins, dayIso) {',
     'function passesOne(key, fmtIdx, mins, dayIso, fid) {',
     "passesOne takes the film id")
swap('case "plat": return t.includes("platinum");',
     'case "plat": return t.includes("platinum");\n'
     '    // The one chip that asks about the FILM rather than the format or the time, which is\n'
     '    // why every caller now hands the id through. No id means no answer, never a pass.\n'
     '    case "star": return isStarred(fid);',
     "the star case")
swap('function passes(fmtIdx, mins, dayIso, extra) {',
     'function passes(fmtIdx, mins, dayIso, extra, fid) {',
     "passes takes the film id")
swap('if (!passesOne(k, fmtIdx, mins, dayIso)) return false;',
     'if (!passesOne(k, fmtIdx, mins, dayIso, fid)) return false;',
     "active chips see the id")
swap('!passesOne(extra, fmtIdx, mins, dayIso)) return false;',
     '!passesOne(extra, fmtIdx, mins, dayIso, fid)) return false;',
     "the extra chip sees the id")

swap('passes(x[1], x[3], DAYS[x[2]])', 'passes(x[1], x[3], DAYS[x[2]], null, x[0])', "filmRuns call site")
swap('passes(s[1], s[3], dayIso, k)', 'passes(s[1], s[3], dayIso, k, s[0])', "chip count call site")
swap('passes(s[1], s[3], dayIso)', 'passes(s[1], s[3], dayIso, null, s[0])',
     "active count, showtimes and films call sites", expect=3)

swap('["now", "Starting soon"], ["sub", "Subtitled"],',
     '["now", "Starting soon"], ["star", "Starred"], ["sub", "Subtitled"],',
     "the chip")
swap('const FILTER_WORD = { sub: "subtitled",', 'const FILTER_WORD = { star: "starred", sub: "subtitled",',
     "count line word")
swap('const WORD_ORDER = ["sub", "imax", "atmos", "plat"];',
     'const WORD_ORDER = ["star", "sub", "imax", "atmos", "plat"];',
     "count line order: 3 starred subtitled showings")

# ---- starred first, and marked ---------------------------------------------------------
swap('.sort((a, b) => (SHOWS.films[b[0]].c || 0) - (SHOWS.films[a[0]].c || 0))',
     '.sort((a, b) => (isStarred(b[0]) - isStarred(a[0])) || (SHOWS.films[b[0]].c || 0) - (SHOWS.films[a[0]].c || 0))',
     "starred first inside each cinema")
swap('.filter(r => r.n && matchesQuery(r.f)).sort((a, b) => b.n - a.n);',
     '.filter(r => r.n && matchesQuery(r.f)).sort((a, b) => (isStarred(b.fid) - isStarred(a.fid)) || b.n - a.n);',
     "starred first in Films")
swap('<div class="fb"><div class="ft"><b>${esc(f.n)}</b>',
     '<div class="fb"><div class="ft"><b>${isStarred(fid) ? STAR_MARK : ""}${esc(f.n)}</b>',
     "star mark on the showtimes list")
n_rows = s.count('<span><span class="n">${esc(r.f.n)}</span>')
swap('<span><span class="n">${esc(r.f.n)}</span>',
     '<span><span class="n">${isStarred(r.fid) ? STAR_MARK : ""}${esc(r.f.n)}</span>',
     "star mark on film rows", expect=n_rows if n_rows in (1, 2) else 1)

# ---- the button ------------------------------------------------------------------------
swap('<div><h2>${esc(f.n)}</h2><div class="addr">${',
     '<div><h2>${esc(f.n)}</h2>${starBtn(fid)}<div class="addr">${',
     "Star button on the film sheet")

swap('const cin = e.target.closest("[data-cin]"); if (cin) return cinemaSheet(cin.dataset.cin);',
     '// Before [data-cin] and [data-film]: the button sits inside a sheet whose rows carry both.\n'
     '  const star = e.target.closest("[data-star]");\n'
     '  if (star) {\n'
     '    const id = star.dataset.star;\n'
     '    if (S.starred.has(id)) S.starred.delete(id); else S.starred.add(id);\n'
     '    saveStarred();\n'
     '    const on = S.starred.has(id);\n'
     '    star.setAttribute("aria-pressed", String(on));\n'
     '    star.querySelector("span").textContent = on ? "Starred" : "Star this film";\n'
     '    renderFilters(); renderShows();\n'
     '    if (S.tab === "films") renderFilms();\n'
     '    return;\n'
     '  }\n'
     '  const cin = e.target.closest("[data-cin]"); if (cin) return cinemaSheet(cin.dataset.cin);',
     "tap handler")

swap('.badge.last{background:var(--lamp);color:var(--lamp-ink)}',
     '.badge.last{background:var(--lamp);color:var(--lamp-ink)}\n'
     '/* STAR. 44 points tall like every other control he taps, and lit in the lamp colour the\n'
     '   pressed chips already use, so a starred film reads as the same kind of "on". */\n'
     '.starbtn{display:inline-flex;align-items:center;gap:7px;min-height:44px;margin:8px 0 4px;padding:0 14px;\n'
     '  border-radius:11px;border:1px solid var(--line);background:var(--sunk);color:var(--ink);\n'
     '  font:600 13.5px/1 "Bricolage Grotesque",system-ui,-apple-system,sans-serif}\n'
     '.starbtn svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linejoin:round}\n'
     '.starbtn:active{background:var(--tap)}\n'
     '.starbtn[aria-pressed="true"]{background:var(--lamp);border-color:var(--lamp);color:var(--lamp-ink)}\n'
     '.starbtn[aria-pressed="true"] svg{fill:currentColor}\n'
     '.stm{width:12px;height:12px;fill:var(--lamp);stroke:none;vertical-align:-1px;margin-right:5px}',
     "styles")

open(PAGE, "w", encoding="utf-8").write(s)

# ---- the offline copy has to change name or an installed phone keeps the old page ------
sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "Star a film" not in rd:
    rd = rd.replace(anchor,
        "- **Star a film.** Every film's sheet has a Star button, starred films sit at the top of\n"
        "  both lists with a small star, and a Starred chip stacks with the others. The stars are\n"
        "  saved on the phone; the chip is not, for the same reason Starting soon is not -- it is\n"
        "  a way of looking, and restoring it would open the app with most of the films hidden.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("starred: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
