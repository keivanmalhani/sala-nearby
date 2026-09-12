#!/usr/bin/env python3
"""Swipe down on Movies or Showtimes to refresh.

    /opt/homebrew/bin/python3 pull-refresh.py

Ask 1 from 12 September: "swipe down to refresh, like most apps".

WHAT A PULL DOES, and why each part is there.
  - It asks the service worker to check for a new build. A new build installs, takes over,
    and the page reloads into it.
  - It fetches the page fresh and compares the showtimes stamp with the one on screen. The
    query string on that fetch keeps the worker's cache out of it; the worker's last branch
    answers a same-origin request from the cache and only then the network, so without it
    the pull would always read the copy it already has.
  - When the site's showtimes are newer it WRITES THAT PAGE INTO THE SHELL CACHE BEFORE
    RELOADING. The worker answers a navigation from the cached shell first, so a plain reload
    would put the old listings straight back on screen and look like the pull did nothing.
  - Otherwise it says "Up to date" with when the showtimes were read, and with no signal it
    says that, rather than a spinner that implies something happened.

It only fires from the very top of a list and only for a deliberate pull, and the map pane is
left alone, where dragging down means panning.
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
if "function refreshNow(" in s:
    sys.exit("pull-refresh.py has already been applied to docs/index.html; nothing to do")


def swap(before, after, why):
    global s
    n = s.count(before)
    if n != 1:
        sys.exit("ANCHOR %s (%s):\n  %s" % ("GONE" if n == 0 else "x%d NOT UNIQUE" % n, why, before[:140]))
    s = s.replace(before, after, 1)


swap('window.addEventListener("sala:origin", renderSettings);\n', r'''window.addEventListener("sala:origin", renderSettings);

/* SWIPE DOWN TO REFRESH. Ask 1 on 12 September, "like most apps". The listings are a
   snapshot published with the page, so a pull asks the site for a newer one. A new build
   comes through the service worker, which takes over and reloads the page. New showtimes on
   the same build come by fetching the page fresh -- the query string keeps the worker's
   cache out of it -- and are written into the shell cache BEFORE reloading, because the
   worker answers a navigation from that cache first and a plain reload would put the old
   listings straight back. Otherwise it says when these were read, and with no signal it
   says that instead of pretending. */
function stampOf(html) {
  // \x7B is an opening curly brace, written as an escape so the brace-matching lift in the
  // tests does not count one inside the regex. Keep literal braces out of this comment too.
  const m = String(html).match(/const SHOWS=\x7B"at":"([^"]+)"/);
  return m ? m[1] : null;
}
function refreshNow(say) {
  let done = false;
  const reload = () => { if (!done) { done = true; location.reload(); } };
  if (navigator.serviceWorker) {
    navigator.serviceWorker.addEventListener("controllerchange", reload, { once: true });
    navigator.serviceWorker.getRegistration().then(r => r && r.update()).catch(() => {});
  }
  const read = SHOWS.at.replace("T", " ");
  return fetch("index.html?fresh=" + Date.now(), { cache: "no-store" })
    .then(r => (r.ok ? r.text() : Promise.reject(new Error("HTTP " + r.status))))
    .then(async html => {
      const at = stampOf(html);
      if (!(at && at > SHOWS.at)) return say("Up to date · read " + read);
      say("New showtimes, loading");
      try {
        for (const k of await caches.keys()) {
          if (/-shell$/.test(k)) await (await caches.open(k)).put("./index.html",
            new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } }));
        }
      } catch (e) { /* no cache to write; the reload still gets the page from the network next time */ }
      reload();
    })
    .catch(() => say("No signal · listings read " + read));
}
(function pullToRefresh() {
  ["pane-films", "pane-shows"].forEach(id => {
    const pane = $(id);
    if (!pane) return;
    const ptr = document.createElement("div");
    ptr.className = "ptr";
    ptr.setAttribute("aria-live", "polite");
    pane.prepend(ptr);
    let y0 = null, dy = 0, busy = false;
    const PULL = 56;   // points of indicator, after the half-speed drag below
    pane.addEventListener("touchstart", e => {
      if (!busy && pane.scrollTop <= 0 && e.touches.length === 1) { y0 = e.touches[0].clientY; dy = 0; ptr.classList.add("drag"); }
    }, { passive: true });
    pane.addEventListener("touchmove", e => {
      if (y0 === null) return;
      dy = e.touches[0].clientY - y0;
      if (dy <= 0 || pane.scrollTop > 0) { ptr.style.height = "0px"; if (pane.scrollTop > 0) y0 = null; return; }
      e.preventDefault();   // at the top and pulling down: this is ours, not a scroll
      const h = Math.min(76, dy * 0.5);
      ptr.style.height = h + "px";
      ptr.textContent = h >= PULL ? "Release to refresh" : "Pull to refresh";
    }, { passive: false });
    pane.addEventListener("touchend", () => {
      if (y0 === null) return;
      ptr.classList.remove("drag");
      const go = dy * 0.5 >= PULL;
      y0 = null;
      if (!go) { ptr.style.height = "0px"; return; }
      busy = true;
      ptr.style.height = "44px";
      ptr.textContent = "Checking for new showtimes";
      refreshNow(msg => { ptr.textContent = msg; })
        .finally(() => setTimeout(() => { ptr.style.height = "0px"; busy = false; }, 2200));
    });
  });
})();
''', "refresh logic and the gesture")

swap('.tabs button:active{background:var(--tap)}', '''.tabs button:active{background:var(--tap)}
/* SWIPE TO REFRESH. Grows under the finger from nothing, in the beam colour, because it is
   about how fresh the listing is rather than a choice he is making. */
.ptr{height:0;overflow:hidden;display:grid;place-items:center;font-family:"IBM Plex Mono",monospace;font-size:10.5px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--beam);background:var(--surface);transition:height .22s ease}
.ptr.drag{transition:none}''', "refresh styles")

open(PAGE, "w", encoding="utf-8").write(s)

sw = open(SW, encoding="utf-8").read()
m = re.search(r'const V = "sala-v(\d+)";', sw)
if not m:
    sys.exit("sw.js: cache name not found, the page is patched but the cache was NOT bumped")
sw = sw.replace(m.group(0), 'const V = "sala-v%d";' % (int(m.group(1)) + 1), 1)
open(SW, "w", encoding="utf-8").write(sw)

rd = open(README, encoding="utf-8").read()
anchor = "- **When to leave.**"
if rd.count(anchor) == 1 and "**Swipe down to refresh.**" not in rd:
    rd = rd.replace(anchor,
        "- **Swipe down to refresh.** At the top of Movies or Showtimes, a pull checks the site for\n"
        "  a new build or newer showtimes and reloads into them, writing the new page into the\n"
        "  offline cache first so the reload does not put the old one back. Otherwise it says\n"
        "  when the showtimes were read, or that there is no signal.\n"
        + anchor, 1)
    open(README, "w", encoding="utf-8").write(rd)

print("pull-refresh: page patched, sw cache now sala-v%d" % (int(m.group(1)) + 1))
