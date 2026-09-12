// Does every small text colour clear 4.5:1 in both themes, and does colour mean one thing?
//
//     node test-colours.mjs
//
// The tokens are read back out of the page rather than restated here, and every contrast
// ratio is recomputed with WCAG's own formula, so a later token change that quietly breaks
// a pair fails this. Checks are paired with 402eaf0, the commit before colours.py, where
// light mode's grey labels read 3.73:1 on the ground.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = "402eaf0";
const BEFORE = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/index.html`],
                            { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

let fails = 0;
const check = (name, ok) => { console.log(`  ${ok ? "ok  " : "FAIL"} ${name}`); if (!ok) fails++; };
const paired = (name, fn) => {
  let now, then;
  try { now = !!fn(SRC); } catch (e) { now = false; console.log(`       (${e.message})`); }
  try { then = !!fn(BEFORE); } catch { then = false; }
  check(name, now);
  check(`   ... and not true at ${BASELINE}, so the check can fail`, !then);
};

/** Token blocks: the light :root, and every block that starts the dark ground. */
function tokens(src) {
  const grab = block => Object.fromEntries([...block.matchAll(/--([a-z0-9-]+):(#[0-9A-Fa-f]{6})/g)].map(m => [m[1], m[2]]));
  const light = src.match(/:root\{\n\s*--ground:#FAF6F0[\s\S]*?\n\}/);
  const darks = [...src.matchAll(/--ground:#14100E[\s\S]*?--tap:[^;]+;/g)].map(m => m[0]);
  if (!light || darks.length < 2) throw new Error("token blocks not found");
  return { light: grab(light[0]), dark: grab(darks[1]), darkBlocks: darks };
}
const lum = hex => {
  const c = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(v => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// [foreground, background, what it is]. All of these are small text somewhere in the app.
const PAIRS = [
  ["ink-3", "ground", "grey mono labels on the page"], ["ink-3", "surface", "grey mono labels on a card"],
  ["ink-2", "ground", "secondary text and outlined badges"], ["lamp", "ground", "the amber count"],
  ["lamp-ink", "lamp", "text on a lit chip or tab"], ["ok", "ok-soft", "the Subtitled badge"],
  ["ground", "beam", "the IMAX badge"], ["ground", "c-lux", "the Atmos badge"], ["ground", "c-big", "the Platino badge"],
  ["beam", "ground", "distances on the page"], ["beam", "surface", "distances on a card"],
];

console.log("1. contrast, recomputed from the page's own tokens");
{
  const t = tokens(SRC);
  for (const theme of ["light", "dark"]) {
    const bad = PAIRS.filter(([f, b]) => ratio(t[theme][f], t[theme][b]) < 4.5);
    console.log(`       ${theme}: ` + PAIRS.map(([f, b, w]) => `${w} ${ratio(t[theme][f], t[theme][b]).toFixed(2)}`).join(" | "));
    if (bad.length) console.log(`       ${theme} below 4.5: ${bad.map(p => p[2]).join(", ")}`);
  }
}
paired("every small text pair clears 4.5:1 in light AND dark", src => {
  const t = tokens(src);
  return ["light", "dark"].every(th => PAIRS.every(([f, b]) => t[th][f] && t[th][b] && ratio(t[th][f], t[th][b]) >= 4.5));
});
check("the two dark token blocks (system dark and chosen Dark) are identical, so the choice cannot look different",
      (() => { const d = tokens(SRC).darkBlocks; return d.length === 2 && d[0].replace(/\s+/g, " ") === d[1].replace(/\s+/g, " "); })());

console.log("2. features filled, facts outlined");
paired("a plain badge is an inset outline, so it changes no row's height", src =>
  /\.badge\{[^}]*background:transparent;box-shadow:inset 0 0 0 1px var\(--line\)/.test(src));
paired("IMAX, Atmos, Platino, Subtitled and Last day are filled with no outline", src =>
  ["imax", "atmos", "plat", "sub"].every(k => new RegExp(`\\.badge\\.${k}\\{background:var\\([^)]+\\);color:var\\([^)]+\\);box-shadow:none\\}`).test(src))
  && src.includes(".badge.last{background:var(--lamp);color:var(--lamp-ink)}\n.badge.last{box-shadow:none}"));
paired("Dubbed is an outline, because it is the default here and not a feature", src =>
  /\.badge\.dub\{background:transparent;color:var\(--ink-2\)\}/.test(src));

console.log("3. blue means place");
paired("the metres on a cinema, the walking time on a movie row and the location button are beam blue", src =>
  /\.cin \.far b\{[^}]*color:var\(--beam\)\}/.test(src)
  && /\.frow \.at span\{[^}]*color:var\(--beam\)/.test(src)
  && src.includes('#locbtn[aria-pressed="false"] svg{stroke:var(--beam)}'));

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
