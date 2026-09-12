#!/usr/bin/env python3
"""A search box that suggests while he types, and can be cleared with one tap.

    /opt/homebrew/bin/python3 search-suggest.py

Ask 8 from 12 September: "make the search bar better". What was wrong with it, measured
rather than guessed: it filtered the list and did nothing else. Typing "insurg" emptied the
Movies list with "No film called that" while Cinemex Insurgentes sat 300 metres away, a
director or a genre only worked if spelt out in full, and on a phone the only way to clear it
was holding backspace.

WHAT IT DOES NOW.
  - Suggestions under the box from the second letter, in four groups: Movies (and how many
    cinemas show each), People (directors, with their film), Cinemas (with the walk from
    wherever distances start), and Genres (with how many movies). Accent-blind, best match
    first.
  - A movie opens its sheet and a cinema opens its sheet. They carry the same data-film and
    data-cin the lists already use, so the existing tap handler does it and nothing new can
    drift from it. A person or a genre fills the box and filters, as typing it would.
  - A clear button inside the box whenever there is something to clear.
  - The placeholder says it finds cinemas too, because a box is a promise about what it
    searches.

The list filter itself does not change. matchesQuery still asks only about the film, so
every count in the app means what it meant before.
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
if "function suggest(" in s:
    sys.exit("search-suggest.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why, expect=1):
    global s
    n = s.count(before)
    if n != expect:
        sys.exit("ANCHOR %s (%s):\n  %s" % ("GONE" if n == 0 else "x%d, expected %d" % (n, expect), why, before[:140]))
    s = s.replace(before, after)


swap('''      <div class="srch"><input id="q" type="search" inputmode="search" autocomplete="off"
        placeholder="Film, director, genre" aria-label="Find a film by title, director or genre"></div>''',
     '''      <div class="srch"><input id="q" type="search" inputmode="search" autocomplete="off" enterkeyhint="search"
        placeholder="Movie, director, genre, cinema" aria-label="Find a movie, director, genre or cinema">
        <button class="srx" data-clear="q" aria-label="Clear the search" hidden></button>
        <div class="sugg" id="q-sugg" hidden></div></div>''', "the Showtimes box")
swap('''      <div class="srch"><input id="qf" type="search" inputmode="search" autocomplete="off"
        placeholder="Film, director, genre" aria-label="Find a film by title, director or genre"></div>''',
     '''      <div class="srch"><input id="qf" type="search" inputmode="search" autocomplete="off" enterkeyhint="search"
        placeholder="Movie, director, genre, cinema" aria-label="Find a movie, director, genre or cinema">
        <button class="srx" data-clear="qf" aria-label="Clear the search" hidden></button>
        <div class="sugg" id="qf-sugg" hidden></div></div>''', "the Movies box")

swap('''["q", "qf"].forEach(id => {
  const el = $(id);
  if (el) el.addEventListener("input", onQuery);
});
''', r'''["q", "qf"].forEach(id => {
  const el = $(id);
  if (el) el.addEventListener("input", onQuery);
});

/* SUGGESTIONS. Ask 8 on 12 September, "make the search bar better". The box only ever
   filtered: "insurg" emptied the list while Cinemex Insurgentes was 300 metres away. Now it
   also suggests, in four groups, from the second letter. Movies and cinemas carry the same
   data-film and data-cin as the lists, so the tap handler that already opens those sheets
   opens these too; a person or a genre fills the box instead. */
let FILM_CINEMAS = null;
function filmCinemaCounts() {
  if (FILM_CINEMAS) return FILM_CINEMAS;
  FILM_CINEMAS = new Map();
  for (const c of SHOWS.cin) {
    const seen = new Set(c.s.map(x => String(x[0])));
    seen.forEach(fid => FILM_CINEMAS.set(fid, (FILM_CINEMAS.get(fid) || 0) + 1));
  }
  return FILM_CINEMAS;
}
function suggest(q) {
  const f = fold(q).trim();
  if (f.length < 2) return [];
  const rank = t => { const x = fold(t); return x.startsWith(f) ? 0 : x.includes(" " + f) ? 1 : x.includes(f) ? 2 : -1; };
  const best = (a, b) => a.r - b.r;
  const counts = filmCinemaCounts();
  const films = Object.entries(SHOWS.films)
    .map(([fid, x]) => ({ fid, x, r: Math.min(...[rank(x.n), rank(x.o || "")].map(v => (v < 0 ? 9 : v))) }))
    .filter(o => o.r < 9)
    .sort((a, b) => best(a, b) || (b.x.c || 0) - (a.x.c || 0)).slice(0, 4)
    .map(o => { const n = counts.get(String(o.fid)) || 0;
      return { g: "Movies", t: "film", id: o.fid, n: o.x.n, d: `at ${n} ${n === 1 ? "cinema" : "cinemas"}` }; });
  const people = new Map();
  for (const x of Object.values(SHOWS.films)) {
    if (!x.dir) continue;
    for (const who of String(x.dir).split(/\s*,\s*/)) {
      const r = rank(who);
      if (r >= 0 && who.length > 2) {
        const p = people.get(who) || { r, films: [] };
        p.films.push(x.n); people.set(who, p);
      }
    }
  }
  const dirs = [...people.entries()].sort((a, b) => a[1].r - b[1].r).slice(0, 2)
    .map(([who, p]) => ({ g: "People", t: "q", q: who, n: who, d: "Director of " + p.films.slice(0, 2).join(", ") }));
  const cins = SHOWS.cin.map(c => ({ c, r: rank(c.n) })).filter(o => o.r >= 0)
    .sort((a, b) => best(a, b) || km(origin, a.c) - km(origin, b.c)).slice(0, 3)
    .map(o => { const F = far(km(origin, { lat: o.c.lat, lng: o.c.lng }));
      return { g: "Cinemas", t: "cin", id: o.c.id, n: o.c.n, d: `${F.d} · ${F.w}` }; });
  const genres = new Map();
  for (const x of Object.values(SHOWS.films)) for (const g of x.g || []) if (rank(g) >= 0) genres.set(g, (genres.get(g) || 0) + 1);
  const gens = [...genres.entries()].sort((a, b) => rank(a[0]) - rank(b[0]) || b[1] - a[1]).slice(0, 2)
    .map(([g, n]) => ({ g: "Genres", t: "q", q: g, n: g, d: `${n} ${n === 1 ? "movie" : "movies"}` }));
  return [...films, ...dirs, ...cins, ...gens];
}
function renderSuggest(input) {
  const box = $(input.id + "-sugg"), clear = document.querySelector(`[data-clear="${input.id}"]`);
  if (clear) clear.hidden = !input.value;
  if (!box) return;
  const list = document.activeElement === input ? suggest(input.value) : [];
  if (!list.length) { box.hidden = true; box.innerHTML = ""; return; }
  let group = "";
  box.innerHTML = list.map(o => {
    const head = o.g !== group ? `<div class="sgh">${esc(o.g)}</div>` : "";
    group = o.g;
    const attr = o.t === "film" ? `data-film="${esc(String(o.id))}"` : o.t === "cin" ? `data-cin="${esc(String(o.id))}"`
      : `data-sgq="${esc(o.q)}" data-for="${input.id}"`;
    return `${head}<button class="sgr${o.t === "cin" ? " place" : ""}" ${attr}><b>${esc(o.n)}</b><em>${esc(o.d)}</em></button>`;
  }).join("");
  box.hidden = false;
}
["q", "qf"].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.addEventListener("input", () => renderSuggest(el));
  el.addEventListener("focus", () => renderSuggest(el));
  // Late enough that a tap on a suggestion lands first; the panel never steals the tap.
  el.addEventListener("blur", () => setTimeout(() => { const b = $(id + "-sugg"); if (b) b.hidden = true; }, 180));
  el.addEventListener("keydown", e => { if (e.key === "Enter") { el.blur(); } });
});
document.addEventListener("click", e => {
  const pick = e.target.closest(".sugg [data-film], .sugg [data-cin], .sugg [data-sgq]");
  if (pick) {
    const box = pick.closest(".sugg");
    if (pick.dataset.sgq != null) {
      const el = $(pick.dataset.for);
      el.value = pick.dataset.sgq;
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }
    box.hidden = true;
    document.activeElement && document.activeElement.blur && document.activeElement.blur();
    return;   // data-film and data-cin are opened by the lists' own handler
  }
  const clr = e.target.closest("[data-clear]");
  if (clr) {
    const el = $(clr.dataset.clear);
    el.value = "";
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.focus();
  }
});
''', "suggestions, the clear button and their taps")

swap('.srch input::placeholder{color:var(--ink-3)}',
     '''.srch input::placeholder{color:var(--ink-3)}
.srch{position:relative}
.srch input[type="search"]::-webkit-search-cancel-button{-webkit-appearance:none;display:none}
.srch input{padding-right:46px}
/* CLEAR. A drawn cross, 44 points square -- it measured 42 on the first render, under the
   line every other control clears -- inside the box's right edge. */
.srx{position:absolute;right:14px;bottom:3px;width:44px;height:44px;border-radius:0 12px 12px 0}
.srx::before,.srx::after{content:"";position:absolute;left:50%;top:50%;width:13px;height:1.8px;background:var(--ink-3);border-radius:1px}
.srx::before{transform:translate(-50%,-50%) rotate(45deg)}
.srx::after{transform:translate(-50%,-50%) rotate(-45deg)}
.srx:active{background:var(--tap)}
.sugg{position:absolute;left:14px;right:14px;top:calc(100% + 2px);z-index:60;background:var(--surface);border:1px solid var(--line);
  border-radius:14px;box-shadow:0 14px 34px rgba(0,0,0,.22);max-height:62vh;overflow-y:auto;overscroll-behavior:contain;padding:4px 0}
.sgh{font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);padding:9px 14px 3px}
.sgr{display:block;width:100%;text-align:left;padding:8px 14px;min-height:48px}
.sgr:active{background:var(--tap)}
.sgr b{display:block;font-weight:700;font-size:14.5px;letter-spacing:-.01em;line-height:1.25}
.sgr em{display:block;font-style:normal;font-family:"IBM Plex Mono",monospace;font-size:10.5px;color:var(--ink-3);margin-top:2px}
.sgr.place em{color:var(--beam)}''', "search styles")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**Search that suggests.**" not in rd:
    rd = rd.replace(anchor,
        "- **Search that suggests.** From the second letter the box suggests movies (with how many\n"
        "  cinemas show them), directors, cinemas (with the walk) and genres. A movie or a cinema\n"
        "  opens its sheet; a director or a genre filters the list. A clear button empties it.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("search-suggest: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
