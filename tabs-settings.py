#!/usr/bin/env python3
"""Movies, Showtimes, Map, Settings -- and the theme toggle moves into Settings.

    /opt/homebrew/bin/python3 tabs-settings.py

Asks 3, 6 and 7 from 12 September, in his words: "Better tab layout, left to right:
Movies, Showtimes, Map, Settings", "the toggle in the top right of absolutely everything is
annoying", and "make a Settings tab". Written up with the other seven in
docs/REDESIGN-2026-09-12.md.

WHAT CHANGES.

  - The tab bar reads Movies, Showtimes, Map, Settings, and the app opens on Movies, the
    leftmost. "Films" becomes Movies on screen because that is his word; the internal key
    stays "films", because thirty places in the page already test S.tab === "films" and
    renaming a key nobody sees is risk with nothing on the other side.
  - The theme button leaves the header. Settings has Appearance with three choices, where the
    button had two: System follows the phone, and it is what no saved value means.
  - Settings also holds where distances are measured from -- Parque Mexico or where the
    phone is, the same thing the location button in the header does -- and when the
    showtimes were read. Language is NOT offered yet: a Spanish button that changes nothing
    is a dead control, and it arrives with the Spanish pass.

WHAT DOES NOT CHANGE. The panes stay in the page in their old order. The tab bar's order is
its own markup, and test-free-rooms.py pins the free-screens button between the map and
films panes, so moving sections round would break a guard for no visible difference.
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
if 'id="pane-settings"' in s:
    sys.exit("tabs-settings.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" % ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:140]))
    s = s.replace(before, after, 1)


# ---- header: no theme button ----------------------------------------------------------
swap('''    <button class="iconbtn" id="themebtn" aria-label="Switch between light and dark">
      <svg viewBox="0 0 24 24"><path d="M20.5 14.3A8.5 8.5 0 1 1 9.7 3.5a7 7 0 0 0 10.8 10.8z"/></svg>
    </button>
''', '', "the header theme button goes")

# ---- panes: Movies starts shown, Settings exists --------------------------------------
swap('<section class="pane on" id="pane-shows" role="tabpanel" aria-label="Showtimes">',
     '<section class="pane" id="pane-shows" role="tabpanel" aria-label="Showtimes">',
     "Showtimes no longer starts shown")
swap('<section class="pane" id="pane-films" role="tabpanel" aria-label="Films">',
     '<section class="pane on" id="pane-films" role="tabpanel" aria-label="Movies">',
     "Movies starts shown")
swap('''      <div id="filmlist"></div>
    </section>
''', '''      <div id="filmlist"></div>
    </section>

    <!-- SETTINGS -->
    <section class="pane" id="pane-settings" role="tabpanel" aria-label="Settings">
      <div class="set">
        <h2 class="seth">Settings</h2>
        <div class="setgrp">
          <h3>Appearance</h3>
          <div class="seg" role="radiogroup" aria-label="Appearance" id="themeseg">
            <button role="radio" aria-checked="true" data-theme-set="system">System</button>
            <button role="radio" aria-checked="false" data-theme-set="light">Light</button>
            <button role="radio" aria-checked="false" data-theme-set="dark">Dark</button>
          </div>
          <p class="setnote">System follows the phone, so the app goes dark when the phone does.</p>
        </div>
        <div class="setgrp">
          <h3>Distances from</h3>
          <div class="seg" role="radiogroup" aria-label="Distances from" id="originseg">
            <button role="radio" aria-checked="true" data-origin="home">Parque Mexico</button>
            <button role="radio" aria-checked="false" data-origin="here">Where I am</button>
          </div>
          <p class="setnote" id="originnote"></p>
        </div>
        <div class="setgrp">
          <h3>Showtimes</h3>
          <p class="setnote" id="setstamp"></p>
        </div>
      </div>
    </section>
''', "the Settings pane")

# ---- tab bar ---------------------------------------------------------------------------
swap('''    <button role="tab" data-tab="shows" aria-selected="true">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg><span>Showtimes</span></button>
    <button role="tab" data-tab="map" aria-selected="false">
      <svg viewBox="0 0 24 24"><path d="M9 3.5 3 6v14.5l6-2.5 6 2.5 6-2.5V3.5L15 6 9 3.5z"/><path d="M9 3.5V18M15 6v14.5"/></svg><span>Map</span></button>
    <button role="tab" data-tab="films" aria-selected="false">
      <svg viewBox="0 0 24 24"><rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M7 5v14M17 5v14M2.5 12h19"/></svg><span>Films</span></button>
''', '''    <button role="tab" data-tab="films" aria-selected="true">
      <svg viewBox="0 0 24 24"><rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="M7 5v14M17 5v14M2.5 12h19"/></svg><span>Movies</span></button>
    <button role="tab" data-tab="shows" aria-selected="false">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg><span>Showtimes</span></button>
    <button role="tab" data-tab="map" aria-selected="false">
      <svg viewBox="0 0 24 24"><path d="M9 3.5 3 6v14.5l6-2.5 6 2.5 6-2.5V3.5L15 6 9 3.5z"/><path d="M9 3.5V18M15 6v14.5"/></svg><span>Map</span></button>
    <button role="tab" data-tab="settings" aria-selected="false">
      <svg viewBox="0 0 24 24"><path d="M4 7h9M18 7h2M4 17h3M12 17h8"/><circle cx="15.5" cy="7" r="2.3"/><circle cx="9.5" cy="17" r="2.3"/></svg><span>Settings</span></button>
''', "the tab bar, in his order")

swap('.tabs{display:grid;grid-template-columns:repeat(3,1fr);',
     '.tabs{display:grid;grid-template-columns:repeat(4,1fr);', "four columns")
swap('.tabs button:active{background:var(--tap)}',
     '''.tabs button:active{background:var(--tap)}
/* SETTINGS. The same grouped-card language as the sheets, and the segmented controls light in
   the lamp colour a pressed chip already uses, so "chosen" looks the same everywhere. */
.set{max-width:720px;margin:0 auto;padding:18px 16px 32px}
.seth{font-size:28px;font-weight:800;letter-spacing:-.02em;line-height:1.1;margin:4px 2px 16px}
.setgrp{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.setgrp h3{font-family:"IBM Plex Mono",monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);font-weight:500;margin:0 0 10px 2px}
.seg{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:4px;padding:4px;border-radius:12px;background:var(--sunk);border:1px solid var(--line-2)}
.seg button{min-height:44px;border-radius:9px;font-size:14px;font-weight:600;color:var(--ink-2);padding:0 6px}
.seg button:active{background:var(--tap)}
.seg button[aria-checked="true"]{background:var(--lamp);color:var(--lamp-ink)}
.setnote{font-size:13px;line-height:1.5;color:var(--ink-2);margin:10px 2px 0}
.setnote b{color:var(--ink);font-weight:600}''', "Settings styles")

# ---- state and tab switching -----------------------------------------------------------
swap('\n  tab: "shows",', '\n  tab: "films",', "the app opens on Movies")
swap('  ["shows", "map", "films"].forEach(k =>', '  ["films", "shows", "map", "settings"].forEach(k =>',
     "four panes")
swap('  if (t === "films") renderFilms();\n}', '  if (t === "films") renderFilms();\n  if (t === "settings") renderSettings();\n}',
     "Settings draws when shown")

# ---- the theme, now three-way and in Settings ------------------------------------------
swap('''$("themebtn").addEventListener("click", () => {
  const cur = document.documentElement.dataset.theme ||
    (matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("sala.theme", next); } catch (e) {}
  // The map is a separate renderer with its own light and dark style sheets, and it cannot
  // see a CSS variable change. Tell it.
  window.dispatchEvent(new Event("sala:theme"));
});
''', '''/* SETTINGS. The theme left the header on 12 September -- "the toggle in the top right of
   absolutely everything is annoying" -- and came back here with a third choice the button
   never had. System follows the phone, and no saved value means System. */
function themeMode() {
  try {
    const t = localStorage.getItem("sala.theme");
    return t === "light" || t === "dark" ? t : "system";
  } catch (e) { return "system"; }
}
function setTheme(mode) {
  if (mode === "light" || mode === "dark") {
    document.documentElement.dataset.theme = mode;
    try { localStorage.setItem("sala.theme", mode); } catch (e) { /* this launch only */ }
  } else {
    delete document.documentElement.dataset.theme;
    try { localStorage.removeItem("sala.theme"); } catch (e) { /* nothing saved to clear */ }
  }
  // The map is a separate renderer with its own light and dark style sheets, and it cannot
  // see a CSS variable change. Tell it.
  window.dispatchEvent(new Event("sala:theme"));
  renderSettings();
}
function renderSettings() {
  const mode = themeMode();
  document.querySelectorAll("#themeseg [data-theme-set]").forEach(b =>
    b.setAttribute("aria-checked", String(b.dataset.themeSet === mode)));
  document.querySelectorAll("#originseg [data-origin]").forEach(b =>
    b.setAttribute("aria-checked", String((b.dataset.origin === "here") === liveLoc)));
  const note = $("originnote");
  if (note) note.textContent = liveLoc
    ? "Every distance, walking time and the Walkable chip are measured from where the phone is."
    : "Every distance, walking time and the Walkable chip are measured from Parque Mexico.";
  const st = $("setstamp");
  if (st) st.innerHTML = `Read <b>${esc(SHOWS.at.replace("T", " "))}</b> from Cinemex's and
    Cineteca Nacional's own listings. A snapshot, not a live feed: every time opens the cinema's
    own checkout, which is always current.`;
}
document.addEventListener("click", e => {
  const th = e.target.closest("#themeseg [data-theme-set]");
  if (th) return setTheme(th.dataset.themeSet);
  // The header's location button already knows how to find him, refuse, and put everything
  // back; pressing it is the whole implementation, and only when the choice would change.
  const og = e.target.closest("#originseg [data-origin]");
  if (og && (og.dataset.origin === "here") !== liveLoc) $("locbtn").click();
});
window.addEventListener("sala:origin", renderSettings);
''', "the theme handler becomes Settings")

swap("  // The theme can change under a running map -- he flips it with the button in the header,",
     "  // The theme can change under a running map -- he picks it in Settings,",
     "the map comment no longer points at a header button")

# ---- the location button tells Settings however it ends ---------------------------------
swap('''    renderFilters(); renderShows(); if (S.tab === "films") renderFilms();
    return;
  }''', '''    renderFilters(); renderShows(); if (S.tab === "films") renderFilms();
    window.dispatchEvent(new Event("sala:origin"));
    return;
  }''', "back to the park tells Settings")
swap('''    renderFilters(); renderShows(); if (S.tab === "films") renderFilms();
  }, () => {''', '''    renderFilters(); renderShows(); if (S.tab === "films") renderFilms();
    window.dispatchEvent(new Event("sala:origin"));
  }, () => {''', "a live location tells Settings")
swap('''    $("fromn").textContent = HOME.name + " (location refused)";
''', '''    $("fromn").textContent = HOME.name + " (location refused)";
    window.dispatchEvent(new Event("sala:origin"));
''', "a refusal tells Settings")

# ---- boot ------------------------------------------------------------------------------
swap('''S.day = liveIdxs.includes(todayIdx) ? todayIdx : (liveIdxs.length ? liveIdxs[0] : 0);
renderDates(); renderFilters(); renderShows();
''', '''S.day = liveIdxs.includes(todayIdx) ? todayIdx : (liveIdxs.length ? liveIdxs[0] : 0);
renderDates(); renderFilters(); renderShows();
// Movies is the leftmost tab and the one the app opens on, his order on 12 September.
setTab(S.tab); renderSettings();
''', "open through setTab")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**Four tabs.**" not in rd:
    rd = rd.replace(anchor,
        "- **Four tabs.** Movies, Showtimes, Map and Settings, left to right, opening on Movies.\n"
        "  Settings holds Appearance (System, Light, Dark), where distances are measured from,\n"
        "  and when the showtimes were read. The theme is no longer a button in the header.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("tabs-settings: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
