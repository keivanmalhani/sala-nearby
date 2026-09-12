#!/usr/bin/env python3
"""Type where distances start: a neighbourhood, a station, a landmark or a postcode.

    /opt/homebrew/bin/python3 build-places.py      # docs/places.json, from OpenStreetMap
    /opt/homebrew/bin/python3 place-picker.py

Ask 5 from 12 September: "more options for where distances are measured from -- I wanna type
in there in a unique good way that's useful to a user".

WHAT HE GETS.
  - "Distances from" in the header is a button now, with a chevron, and opens a picker.
  - Typing matches 2,118 places OpenStreetMap knows within 15 km: every colonia, Metro,
    Metrobus, Tren Ligero and Cablebus station, the districts, and the museums and parks.
    Accents do not matter, "zocalo" finds Zocalo, and a five-digit postcode finds its colonia.
  - EVERY SUGGESTION SAYS HOW MANY CINEMAS ARE A WALK FROM THERE, and the nearest one with its
    time. That is the part no map search does, and it is the question the picker exists for:
    not "where is Condesa" but "what can I walk to from Condesa".
  - A chosen place stays chosen across launches, and can be saved under a name he picks,
    like Home. Saved places live only on the phone and nothing typed leaves it. Quick rows
    for "Where I am" and Parque Mexico stay at the top.

WHY BAKED IN AND NOT A GEOCODER. A geocoding service needs a signal, often a key, and sends
what he types to a third party. places.json is fetched once, precached by the service worker,
and searched on the phone.

HOW IT FITS WHAT IS THERE. The header's location button keeps working as before; turning it
off now returns to the chosen place rather than always to the park. Settings gains a third
choice beside Parque Mexico and Where I am, which opens the picker and then shows the chosen
place's name. whereFrom() names the real origin, so the Movies line says "near Condesa".
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "docs", "index.html")
SW = os.path.join(ROOT, "docs", "sw.js")
PLACES = os.path.join(ROOT, "docs", "places.json")
README = os.path.join(ROOT, "README.md")

if not os.path.exists(PLACES):
    sys.exit("docs/places.json is missing: run build-places.py first, or the picker has nothing to find")
s = open(PAGE, encoding="utf-8").read()
if "function placeSheet(" in s:
    sys.exit("place-picker.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" % ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:140]))
    s = s.replace(before, after, 1)


# ---- the location button returns to the chosen place, not always the park ----------------
swap('    liveLoc = false; origin = { ...HOME };\n', '    liveLoc = false; origin = savedOrigin();\n',
     "location off returns to the chosen place")
swap('    $("fromk").textContent = "Distances from"; $("fromn").textContent = HOME.name;\n',
     '    $("fromk").textContent = "Distances from"; $("fromn").textContent = origin.name;\n',
     "and says its name")
swap('    $("fromn").textContent = HOME.name + " (location refused)";\n',
     '    $("fromn").textContent = origin.name + " (location refused)";\n',
     "a refusal names where distances still start")
swap('  const who = liveLoc ? "you" : HOME.name;', '  const who = liveLoc ? "you" : origin.name;',
     "the Movies line names the chosen place")

# ---- header: the door in -------------------------------------------------------------------
swap('''    <div class="from">
      <span class="k" id="fromk">Distances from</span>
      <span class="n" id="fromn">Parque Mexico</span>
    </div>''', '''    <button class="from" id="fromopen" aria-haspopup="dialog" aria-label="Choose where distances are measured from">
      <span class="k" id="fromk">Distances from</span>
      <span class="n" id="fromn">Parque Mexico</span>
    </button>''', "Distances from becomes a button")

# ---- Settings: a third choice ----------------------------------------------------------------
swap('''            <button role="radio" aria-checked="false" data-origin="here">Where I am</button>
          </div>''', '''            <button role="radio" aria-checked="false" data-origin="here">Where I am</button>
            <button role="radio" aria-checked="false" data-origin="place">Somewhere else</button>
          </div>''', "Somewhere else in Settings")
swap('''  document.querySelectorAll("#originseg [data-origin]").forEach(b =>
    b.setAttribute("aria-checked", String((b.dataset.origin === "here") === liveLoc)));''',
     '''  const atHome = !liveLoc && origin.lat === HOME.lat && origin.lng === HOME.lng;
  document.querySelectorAll("#originseg [data-origin]").forEach(b => b.setAttribute("aria-checked", String(
    b.dataset.origin === "here" ? liveLoc : b.dataset.origin === "home" ? atHome : !liveLoc && !atHome)));
  const other = document.querySelector('#originseg [data-origin="place"]');
  if (other) other.textContent = !liveLoc && !atHome ? origin.name : "Somewhere else";''',
     "Settings shows which of the three is on")
swap('''    : "Every distance, walking time and the Walkable chip are measured from Parque Mexico.";''',
     '''    : "Every distance, walking time and the Walkable chip are measured from " + origin.name + ".";''',
     "the Settings note names the place")
swap('''  if (og && (og.dataset.origin === "here") !== liveLoc) $("locbtn").click();
});''', '''  if (og && (og.dataset.origin === "here") !== liveLoc) $("locbtn").click();
  if (og && og.dataset.origin === "place") return placeSheet();
  if (og && og.dataset.origin === "home" && !liveLoc) setOrigin(null);
});''', "the Settings choices reach the picker and the park")

# ---- the picker ----------------------------------------------------------------------------
swap('window.addEventListener("sala:origin", renderSettings);\n', r'''window.addEventListener("sala:origin", renderSettings);

/* WHERE DISTANCES START, TYPED. Ask 5 on 12 September: "I wanna type in there in a unique
   good way that's useful to a user". The places are OpenStreetMap's colonias, stations and
   landmarks, baked into places.json by build-places.py, so the picker works with no signal
   and nothing he types leaves the phone. Every suggestion answers the question the picker
   is for: how many cinemas are a walk from there, and which is nearest. */
let PLACES = null, LAST_HITS = [];
const PLACE_KIND = { col: "Neighbourhood", q: "Area", d: "District", m: "Metro", mb: "Metrobús",
                     tl: "Tren Ligero", cb: "Cablebús", sub: "Suburbano", lm: "Landmark" };
function loadPlaces() {
  if (PLACES) return Promise.resolve(PLACES);
  return fetch("places.json").then(r => (r.ok ? r.json() : null)).then(j => {
    PLACES = j && Array.isArray(j.p)
      ? j.p.map(r => ({ n: r[0], k: r[1], lat: r[2], lng: r[3], cp: r[4] || "", f: fold([r[0], ...r.slice(5)].join(" ")) }))
      : [];
    return PLACES;
  }).catch(() => (PLACES = []));
}
/** Best first: the name starts with it, then a word in it does, then it appears anywhere. A
 *  postcode matches its colonia. places.json is nearest-first, and the sort is stable, so
 *  within a rank the nearer place wins. */
function placeMatches(q) {
  const raw = String(q || "").trim(), f = fold(raw);
  if (!f || !PLACES) return [];
  const cp = /^\d{3,5}$/.test(raw);
  const ranked = [];
  for (const p of PLACES) {
    const r = cp ? (p.cp.startsWith(raw) ? 0 : -1)
      : p.f.startsWith(f) ? 0 : p.f.includes(" " + f) ? 1 : p.f.includes(f) ? 2 : -1;
    if (r >= 0) ranked.push([r, p]);
  }
  return ranked.sort((a, b) => a[0] - b[0]).slice(0, 8).map(x => x[1]);
}
function reachFrom(pt) {
  let n = 0, near = null, nd = Infinity;
  for (const c of SHOWS.cin) {
    const d = km(pt, { lat: c.lat, lng: c.lng });
    if (walkable(d)) n++;
    if (d < nd) { nd = d; near = c; }
  }
  return { n, near, nd };
}
function reachLine(pt) {
  const r = reachFrom(pt);
  const lead = r.n ? `${r.n} ${r.n === 1 ? "cinema" : "cinemas"} within a walk` : "No cinema within a walk";
  return r.near ? `${lead} · nearest ${r.near.n}, ${far(r.nd).w}` : lead;
}
function savedPlaces() {
  try {
    const a = JSON.parse(localStorage.getItem("sala.places") || "[]");
    return Array.isArray(a) ? a.filter(x => x && typeof x.l === "string" && typeof x.n === "string"
      && Number.isFinite(x.lat) && Number.isFinite(x.lng)) : [];
  } catch (e) { return []; }
}
function writeSaved(list) {
  try { localStorage.setItem("sala.places", JSON.stringify(list.slice(0, 12))); } catch (e) { /* this launch only */ }
}
/** The chosen place, or the park. A saved value that is not a place near this city -- junk,
 *  or 0,0 -- is the park, never a distance measured from the Gulf of Guinea. */
function savedOrigin() {
  try {
    const o = JSON.parse(localStorage.getItem("sala.origin") || "null");
    if (o && typeof o.n === "string" && Number.isFinite(o.lat) && Number.isFinite(o.lng)
        && km(HOME, { lat: o.lat, lng: o.lng }) < 40) return { lat: o.lat, lng: o.lng, name: o.n };
  } catch (e) { /* the park */ }
  return { ...HOME };
}
function setOrigin(p) {
  if (liveLoc) { liveLoc = false; $("locbtn").setAttribute("aria-pressed", "false"); }
  origin = p ? { lat: p.lat, lng: p.lng, name: p.n } : { ...HOME };
  try {
    if (p) localStorage.setItem("sala.origin", JSON.stringify({ n: p.n, lat: p.lat, lng: p.lng }));
    else localStorage.removeItem("sala.origin");
  } catch (e) { /* this launch only */ }
  $("fromk").textContent = "Distances from"; $("fromn").textContent = origin.name;
  renderFilters(); renderShows(); if (S.tab === "films") renderFilms();
  window.dispatchEvent(new Event("sala:origin"));
}
function placeSheet() {
  const head = `<div><h2>Distances from</h2>
      <div class="pksrch"><input id="pkq" type="search" inputmode="search" autocomplete="off" enterkeyhint="search"
        placeholder="Neighbourhood, Metro, postcode" aria-label="Type a neighbourhood, station, landmark or postcode"></div></div>`;
  openSheet(head, "", `<div id="pkbody"></div>`, "var(--beam)");
  renderPicker("");
  loadPlaces().then(() => renderPicker($("pkq") ? $("pkq").value : ""));
}
function renderPicker(q) {
  const box = $("pkbody");
  if (!box) return;
  const row = (attrs, name, kind, line, on) => `<button class="pkrow${on ? " on" : ""}" ${attrs}>
      <span class="pkn">${esc(name)}${kind ? `<em>${esc(kind)}</em>` : ""}</span>
      <span class="pkl">${esc(line)}</span></button>`;
  const atHome = !liveLoc && origin.lat === HOME.lat && origin.lng === HOME.lng;
  let html = "";
  if (!String(q).trim()) {
    const saved = savedPlaces();
    html += row('data-pick="here"', "Where I am", "", liveLoc ? "On now" : "Uses the phone's location", liveLoc)
      + row('data-pick="home"', HOME.name, "", reachLine(HOME), atHome);
    if (!atHome && !liveLoc && !saved.some(x => x.lat === origin.lat && x.lng === origin.lng))
      html += row('data-pick="current"', origin.name, "Now", reachLine(origin), true)
        + `<div class="pksave"><input id="pklabel" maxlength="24" autocomplete="off"
            placeholder="Name ${esc(origin.name)}, like Home" aria-label="A name for ${esc(origin.name)}">
            <button data-pick="save">Save</button></div>`;
    if (saved.length) html += `<div class="sec"><h3>Saved</h3></div>` + saved.map((x, i) =>
      `<div class="pksaved">${row(`data-pick="saved" data-i="${i}"`, x.l, x.n !== x.l ? x.n : "", reachLine(x),
        !liveLoc && origin.lat === x.lat && origin.lng === x.lng)}<button class="pkx" data-forget="${i}"
        aria-label="Forget ${esc(x.l)}">Forget</button></div>`).join("");
    html += `<p class="note pkhint">Type a neighbourhood, a Metro or Metrobús station, a landmark or a postcode.
      Every distance, walking time and the Walkable chip then start from there.</p>`;
  } else if (PLACES === null) {
    html = `<p class="note pkhint">Loading places</p>`;
  } else {
    LAST_HITS = placeMatches(q);
    html = LAST_HITS.length
      ? LAST_HITS.map((p, i) => row(`data-pick="place" data-i="${i}"`, p.n,
          PLACE_KIND[p.k] + (p.cp ? " · CP " + p.cp : ""), reachLine(p))).join("")
      : `<p class="note pkhint">Nothing called that within 15 km. Try a colonia, a station or a five-digit postcode.</p>`;
  }
  box.innerHTML = html + `<p class="note pkhint pksrc">Places from OpenStreetMap contributors, ODbL.</p>`;
}
document.addEventListener("click", e => {
  if (e.target.closest("#fromopen")) return placeSheet();
  const pk = e.target.closest("[data-pick]");
  if (pk) {
    const kind = pk.dataset.pick;
    if (kind === "here") { closeSheet(); if (!liveLoc) $("locbtn").click(); return; }
    if (kind === "home") { closeSheet(); return setOrigin(null); }
    if (kind === "current") return closeSheet();
    if (kind === "place") { const p = LAST_HITS[+pk.dataset.i]; if (p) { closeSheet(); setOrigin(p); } return; }
    if (kind === "saved") {
      const x = savedPlaces()[+pk.dataset.i];
      if (x) { closeSheet(); setOrigin({ n: x.n, lat: x.lat, lng: x.lng }); }
      return;
    }
    if (kind === "save") {
      const label = ((($("pklabel") || {}).value) || "").trim().slice(0, 24) || origin.name;
      const list = savedPlaces().filter(x => !(x.lat === origin.lat && x.lng === origin.lng));
      list.unshift({ l: label, n: origin.name, lat: origin.lat, lng: origin.lng });
      writeSaved(list);
      return renderPicker("");
    }
  }
  const fg = e.target.closest("[data-forget]");
  if (fg) { const list = savedPlaces(); list.splice(+fg.dataset.forget, 1); writeSaved(list); renderPicker(""); }
});
document.addEventListener("input", e => { if (e.target && e.target.id === "pkq") renderPicker(e.target.value); });
''', "the picker")

swap('''S.day = liveIdxs.includes(todayIdx) ? todayIdx : (liveIdxs.length ? liveIdxs[0] : 0);
''', '''S.day = liveIdxs.includes(todayIdx) ? todayIdx : (liveIdxs.length ? liveIdxs[0] : 0);
// Where distances start comes back before the first list is drawn, or the app would open
// measuring from the park and jump when it remembered.
origin = savedOrigin(); $("fromn").textContent = origin.name;
''', "the chosen place is restored before the first render")

# ---- styles ------------------------------------------------------------------------------
swap('.top .from{flex:1;min-width:0}', '''.top .from{flex:1;min-width:0;text-align:left;display:block;border-radius:10px;padding:3px 6px;margin:-3px -6px}
.top .from:active{background:var(--tap)}
/* The chevron is what says the name can be changed. Beam blue, because it is about place. */
.top .from .n::after{content:"";display:inline-block;width:6px;height:6px;margin-left:9px;
  border-right:1.8px solid var(--beam);border-bottom:1.8px solid var(--beam);transform:translateY(-3px) rotate(45deg)}
.pksrch{margin-top:10px}
.pksrch input,.pksave input{-webkit-appearance:none;appearance:none;width:100%;min-width:0;min-height:44px;border-radius:12px;
  border:1px solid var(--line);background:var(--ground);color:var(--ink);font:inherit;font-size:16px;padding:0 13px}
.pksrch input:focus,.pksave input:focus{outline:2px solid var(--beam);outline-offset:-1px;border-color:var(--beam)}
.pkrow{display:block;width:100%;text-align:left;padding:11px 18px;border-bottom:1px solid var(--line-2);min-height:54px}
.pkrow:active{background:var(--tap)}
.pkrow.on{box-shadow:inset 3px 0 0 var(--beam)}
.pkn{display:block;font-weight:700;font-size:15px;letter-spacing:-.01em;line-height:1.3}
.pkn em{font-style:normal;font-family:"IBM Plex Mono",monospace;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin-left:8px;font-weight:500}
.pkl{display:block;margin-top:3px;font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--beam);line-height:1.4}
.pksaved{display:grid;grid-template-columns:1fr auto;align-items:stretch;border-bottom:1px solid var(--line-2)}
.pksaved .pkrow{border-bottom:none}
.pkx{padding:0 16px;font-size:12.5px;color:var(--ink-2);min-height:44px}
.pksave{display:grid;grid-template-columns:1fr auto;gap:8px;padding:10px 18px 12px;border-bottom:1px solid var(--line-2)}
.pksave button{min-height:44px;border-radius:12px;background:var(--lamp);color:var(--lamp-ink);font-weight:700;padding:0 18px;font-size:14px}
.note.pkhint{padding:12px 18px 0;margin:0}
.note.pksrc{padding-bottom:18px;font-size:11px}''', "picker styles")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
if '"./places.json"' not in sw:
    if sw.count('  "./index.html",\n') != 1:
        sys.exit("sw.js: PRECACHE anchor not found, places.json would not work offline")
    sw = sw.replace('  "./index.html",\n', '  "./index.html",\n  "./places.json",\n', 1)
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**Type where distances start.**" not in rd:
    rd = rd.replace(anchor,
        "- **Type where distances start.** Tap \"Distances from\" and type a colonia, a Metro or\n"
        "  Metrobus station, a landmark or a postcode. Each suggestion says how many cinemas are\n"
        "  a walk from there and which is nearest. The places are OpenStreetMap's, baked into\n"
        "  `docs/places.json` by `build-places.py`, so it works offline and nothing typed leaves\n"
        "  the phone. A chosen place is remembered, and can be saved under a name like Home.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("place-picker: page patched, sw cache now sala-v%d, places.json precached" % (int(m.group(1)) + 1))
