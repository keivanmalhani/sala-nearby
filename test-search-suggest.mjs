// Does the search box suggest the right things, and does each suggestion do what it says?
//
//     node test-search-suggest.mjs
//
// suggest() runs for real against the real listing, lifted out of the page. Page checks are
// paired with the commit that added place-picker.py, the last one before this change, so
// each is shown able to fail.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = execFileSync("git", ["-C", ROOT, "log", "-1", "--format=%h", "--", "place-picker.py"], { encoding: "utf8" }).trim();
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
function lift(src, name) {
  const at = src.indexOf(`function ${name}(`);
  if (at === -1) throw new Error(`function ${name} is not in the page`);
  let depth = 0;
  for (let j = src.indexOf("{", at); j < src.length; j++) {
    if (src[j] === "{") depth++;
    else if (src[j] === "}" && --depth === 0) return src.slice(at, j + 1);
  }
  throw new Error(`unbalanced ${name}`);
}
const line = (src, re) => { const m = src.match(re); if (!m) throw new Error(`${re} not in the page`); return m[0]; };

function world(src) {
  const SHOWS = JSON.parse(line(src, /const SHOWS=[^\n]+/).slice("const SHOWS=".length).replace(/;$/, ""));
  const ctx = { SHOWS, Math, String, Object, Map, Set, origin: { lat: 19.4117, lng: -99.1690, name: "Parque Mexico" } };
  vm.createContext(ctx);
  vm.runInContext([line(src, /const walkMin = [^\n]+/), line(src, /const WALK_MAX = [^\n]+/),
    lift(src, "walkable"), lift(src, "km"), lift(src, "far"), lift(src, "fold"),
    "let FILM_CINEMAS = null;", lift(src, "filmCinemaCounts"), lift(src, "suggest")].join("\n"), ctx);
  return ctx;
}

console.log("1. what it suggests, on the real listing");
paired("\"odisea\" suggests La Odisea first, with how many cinemas show it", src => {
  const s = world(src).suggest("odisea");
  if (src === SRC) console.log(`       odisea -> ${JSON.stringify(s.slice(0, 2))}`);
  return s[0] && s[0].t === "film" && /Odisea/.test(s[0].n) && /^at \d+ cinemas?$/.test(s[0].d);
});
paired("\"nolan\" suggests the director, and filling the box with him is what the tap does", src => {
  const s = world(src).suggest("nolan").filter(o => o.g === "People");
  if (src === SRC) console.log(`       nolan -> ${JSON.stringify(s)}`);
  return s.length > 0 && s[0].t === "q" && /Nolan/.test(s[0].q) && /^Director of /.test(s[0].d);
});
paired("\"insurg\" suggests the cinema, with the walk from where distances start", src => {
  const s = world(src).suggest("insurg").filter(o => o.t === "cin");
  if (src === SRC) console.log(`       insurg -> ${JSON.stringify(s)}`);
  return s.length > 0 && /Insurgentes/.test(s[0].n) && / · \d+ min (walk|drive)$/.test(s[0].d);
});
paired("accents do not matter: \"accion\" suggests the Acción genre with a movie count", src => {
  const s = world(src).suggest("accion").filter(o => o.g === "Genres");
  return s.length > 0 && s[0].n === "Acción" && /^\d+ movies?$/.test(s[0].d);
});
paired("one letter suggests nothing, and nothing ever runs past eleven rows", src => {
  const w = world(src);
  return w.suggest("a").length === 0 && ["an", "la", "ci", "de"].every(q => w.suggest(q).length <= 11);
});

console.log("2. wired into both boxes");
paired("both boxes have a suggestion panel and a clear button", src =>
  ["q", "qf"].every(id => src.includes(`data-clear="${id}"`) && src.includes(`id="${id}-sugg"`)));
paired("a movie or cinema suggestion carries the lists' own data-film / data-cin, so the same handler opens it", src =>
  lift(src, "renderSuggest").includes('data-film="${esc(String(o.id))}"')
  && lift(src, "renderSuggest").includes('data-cin="${esc(String(o.id))}"'));
paired("the placeholder says it finds cinemas too, in both boxes", src =>
  (src.match(/placeholder="Movie, director, genre, cinema"/g) || []).length === 2);
paired("the list filter is unchanged, so every count means what it did", src =>
  lift(src, "matchesQuery") === lift(BEFORE, "matchesQuery") && src.includes("function suggest("));

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
