#!/usr/bin/env python3
"""The UI pass he asked for: a cleaner sheet, and the poster doing real work.

    /opt/homebrew/bin/python3 ui-pass.py

His words on 8 September were that the app still needed "a cleaner UI and posters more
integrated". Four things, each of them something a screenshot at 390 px actually showed.

1. THE SYNOPSIS BURIES THE SHOWTIMES. Coyote vs Acme's Spanish synopsis is 96 words and
   takes 300 of the 844 pixels on the screen, so opening a film pushes every cinema and
   every time below the fold. He opens this to decide where and when to go. Three lines
   with a "more" toggle keeps the synopsis without letting it own the sheet.

2. THE INSTALL PROMPT SITS ON TOP OF THE SHEET. It is z-index 1200 against the sheet's
   901, and on iOS it appears on a 2.6-second timer regardless of what he is doing -- so
   tapping a film within three seconds of launch gets a banner dropped over its showtimes.
   Both halves are fixed: it goes below the sheet, and it waits for the sheet to close.

3. THE FILM ROW RUNS TWO KINDS OF FACT TOGETHER. "1h38m - A - Comedia, Sci-Fi - nearest
   Insurgentes 302 m" is the film and the geography in one wrapped paragraph, and the
   second half is the part he acts on. It gets its own line.

4. THE POSTER IS A THUMBNAIL BESIDE THE TITLE AND NOTHING ELSE. In the sheet it now also
   sits behind the header as a blurred backdrop under a scrim, which is what makes a film
   sheet look like that film rather than like a form. Cheap: the image is already fetched
   for the thumbnail, so the backdrop costs no request. Films with no artwork -- 33 of the
   73, because Cineteca publishes none -- get no backdrop and are unchanged.

Every anchor is asserted. If the page has moved underneath this it stops rather than
writing something mangled, which is the convention the other build scripts here follow.
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


# ------------------------------------------------------------------ 1 + 4. sheet CSS
swap(""".sheet .poshead{display:grid;grid-template-columns:88px 1fr;gap:14px;align-items:start}
.sheet .poshead .pw{width:88px;height:132px;border-radius:7px;--pf:24px}
.sheet .syn{color:var(--ink-2);font-size:13px;line-height:1.5;margin-top:9px}""",
     """.sheet .poshead{position:relative;display:grid;grid-template-columns:88px 1fr;gap:14px;align-items:start;
  padding:14px 18px 16px;margin:0 -18px}
.sheet .poshead .pw{width:88px;height:132px;border-radius:7px;--pf:24px;box-shadow:0 4px 18px rgba(0,0,0,.32)}

/* THE POSTER, BEHIND ITS OWN HEADER. The image is already being fetched for the thumbnail
   in front of it, so this costs no request. Blurred hard and pushed under a scrim because
   it is a ground, not a picture -- at full strength it fights every word on top of it. The
   scrim is a gradient to the sheet's own surface colour so the header dissolves into the
   body rather than ending on a line. `overflow:hidden` on the header is what keeps the
   blur's soft edge from bleeding over the rounded top corners of the sheet. */
.sheet .poshead{overflow:hidden;isolation:isolate}
.sheet .poshead .bd{position:absolute;inset:-28px -28px auto;height:calc(100% + 56px);z-index:-1;
  background-position:center 22%;background-size:cover;filter:blur(26px) saturate(1.25);
  opacity:.30;transform:scale(1.08)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .sheet .poshead .bd{opacity:.34}}
:root[data-theme="dark"] .sheet .poshead .bd{opacity:.34}
.sheet .poshead .sc{position:absolute;inset:0;z-index:-1;
  background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 46%,transparent) 0%,
                                    color-mix(in srgb,var(--surface) 78%,transparent) 58%,
                                    var(--surface) 100%)}

/* THE SYNOPSIS, THREE LINES UNTIL HE ASKS FOR MORE. Coyote vs Acme's runs 96 words and
   pushed every showtime below the fold on a 390 px screen, which is the opposite of what
   this sheet is for. `-webkit-line-clamp` is the only thing that truncates on a line
   boundary rather than a character count, and it is supported everywhere this runs.
   The toggle is a real button so it is reachable by keyboard and reads to VoiceOver. */
.sheet .syn{color:var(--ink-2);font-size:13px;line-height:1.5;margin-top:9px}
.sheet .syn p{margin:0;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}
.sheet .syn.open p{-webkit-line-clamp:unset;display:block}
.sheet .syn .more{margin-top:5px;font-family:"IBM Plex Mono",monospace;font-size:9.5px;
  letter-spacing:.12em;text-transform:uppercase;color:var(--lamp);min-height:28px}
.sheet .syn .more:active{opacity:.6}""",
     "the sheet's poster head and synopsis")

# ------------------------------------------------------------------ 3. film row CSS
swap(""".frow .cnt{text-align:right;font-family:"IBM Plex Mono",monospace}""",
     """/* WHERE IT IS PLAYING IS NOT THE SAME KIND OF FACT AS HOW LONG IT IS. The two ran
   together into one wrapped grey paragraph -- "1h38m - A - Comedia, Sci-Fi - nearest
   Insurgentes 302 m" -- and the half he acts on was the tail of it. Own line, own colour,
   the distance in the same mono face the rest of the app measures distance in. */
.frow .at{display:block;margin-top:3px;font-size:12px;color:var(--ink-2);line-height:1.35}
.frow .at b{font-weight:600;color:var(--ink)}
.frow .at span{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--ink-3);letter-spacing:.02em}
.frow .cnt{text-align:right;font-family:"IBM Plex Mono",monospace}""",
     "the film row's where-it-is-playing line")

# ------------------------------------------------------------------ 1 + 4. sheet markup
swap("""  const head = `<div class="poshead">
      ${posterCard(fid, f.n, "", false)}
      <div><h2>${esc(f.n)}</h2><div class="addr">${
    esc([f.o && f.o !== f.n ? f.o : "", f.d, f.r, (f.g || []).join(", "), f.dir].filter(Boolean).join(" · "))}</div>
      ${syn ? `<div class="syn">${esc(syn)}</div>` : ""}</div></div>`;""",
     """  // The backdrop only exists where there is artwork to make one from. A film with no
  // poster gets the header it always had rather than an empty tinted box, which is the
  // same rule the placeholder initials already follow.
  const bd = hasArtwork(fid)
    ? `<div class="bd" style="background-image:url(posters/${esc(fid)}.jpg)"></div><div class="sc"></div>`
    : "";
  const head = `<div class="poshead">${bd}
      ${posterCard(fid, f.n, "", false)}
      <div><h2>${esc(f.n)}</h2><div class="addr">${
    esc([f.o && f.o !== f.n ? f.o : "", f.d, f.r, (f.g || []).join(", "), f.dir].filter(Boolean).join(" · "))}</div>
      ${syn ? `<div class="syn" id="syn"><p>${esc(syn)}</p>${
        // The toggle is only offered where there is something hidden to reveal. Three
        // lines at 13px over this column is about 150 characters; below that the clamp
        // never bites and a "more" button that reveals nothing is a small lie.
        syn.length > 150 ? `<button class="more" data-syn="1">Read more</button>` : ""}</div>` : ""}</div></div>`;""",
     "the film sheet header markup")

# The toggle. The sheet's click handler is delegated, so this joins it rather than binding
# a listener that would leak on every open.
swap("""function filmSheet(fid) {""",
     """/* Delegated, because the sheet's contents are replaced wholesale on every open and a
   listener bound to the button would be a new one each time with no removal. */
addEventListener("click", e => {
  const b = e.target.closest(".sheet .syn .more");
  if (!b) return;
  const box = b.closest(".syn");
  const open = box.classList.toggle("open");
  b.textContent = open ? "Read less" : "Read more";
});

function filmSheet(fid) {""",
     "the synopsis toggle handler")

# ------------------------------------------------------------------ 3. film row markup
swap("""      <span><span class="n">${esc(r.f.n)}</span>
        <span class="s">${esc([r.f.d, r.f.r, (r.f.g || []).join(", ")].filter(Boolean).join(" · "))}
          ${r.near ? "&middot; nearest " + esc(r.near.n) + (F ? " " + F.d : "") : ""}</span>
        <span class="fm">${fmtBadges(r.types, 3)}</span></span>""",
     """      <span><span class="n">${esc(r.f.n)}</span>
        <span class="s">${esc([r.f.d, r.f.r, (r.f.g || []).join(", ")].filter(Boolean).join(" · "))}</span>
        ${r.near ? `<span class="at"><b>${esc(r.near.n)}</b>${
          F ? ` <span>${esc(F.d)} &middot; ${esc(F.w)}</span>` : ""}</span>` : ""}
        <span class="fm">${fmtBadges(r.types, 3)}</span></span>""",
     "the film row's nearest-cinema line")

# ------------------------------------------------------------------ 2. the install prompt
swap("""  d.style.cssText = "position:fixed;left:12px;right:12px;bottom:calc(env(safe-area-inset-bottom,0px) + 70px);"
    + "z-index:1200;background:var(--surface);border:1px solid var(--line);border-radius:16px;\"""",
     """  // BELOW THE SHEET, NOT ABOVE IT. At 1200 against the sheet's 901 this banner covered
  // the showtimes of whatever he had just opened. 880 puts it under both the sheet and
  // its scrim and still above the map controls and the tab bar.
  d.style.cssText = "position:fixed;left:12px;right:12px;bottom:calc(env(safe-area-inset-bottom,0px) + 70px);"
    + "z-index:880;background:var(--surface);border:1px solid var(--line);border-radius:16px;\"""",
     "the install prompt's stacking")

swap("""  if (safari) setTimeout(function () { showInstall(null); }, 2600);""",
     """  // AND NOT WHILE HE IS READING SOMETHING. The prompt used to arrive on a bare 2.6
  // second timer, so tapping a film in the first three seconds got a banner dropped over
  // its showtimes. If a sheet is open when the timer fires, wait and offer it once the
  // sheet is closed instead.
  if (safari) setTimeout(function () {
    var sheet = document.getElementById("sheet");
    var open = function () { return sheet && sheet.getAttribute("aria-hidden") === "false"; };
    if (!open()) return showInstall(null);
    var iv = setInterval(function () {
      if (open()) return;
      clearInterval(iv);
      showInstall(null);
    }, 700);
  }, 2600);""",
     "the install prompt's timing")

open(PAGE, "w", encoding="utf-8").write(s)
print("ui-pass: 7 anchors replaced in docs/index.html")
