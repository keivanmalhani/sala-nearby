// Does Walkable mean exactly what the cinema rows already say, and move with the origin?
//
//     node test-walkable.mjs
//
// One line of logic and three quiet ways to be wrong. It could draw its own line and call a
// cinema walkable while that cinema's row says "min drive". It could measure from Parque
// Mexico while the rows measure from where the phone is. Or a call site of `passes` could
// be left without the cinema, and the chip would count nothing there with no error to say
// why. Each is checked against the real functions lifted out of the page, and every check
// is paired with the commit before the feature, so each one is shown able to fail.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = "ec3fb35";   // the last commit before walkable.py
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
function liftConst(src, name) {
  const m = src.match(new RegExp(`const ${name} = [\\s\\S]*?;\\n`));
  if (!m) throw new Error(`const ${name} is not in the page`);
  return m[0];
}
function liftLine(src, re, what) {
  const m = src.match(re);
  if (!m) throw new Error(`${what} is not in the page`);
  return m[0];
}
const memStore = () => {
  const m = new Map();
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), _m: m };
};
const payload = src =>
  JSON.parse(liftLine(src, /const SHOWS=[^\n]+/, "the SHOWS payload").slice("const SHOWS=".length).replace(/;$/, ""));

const PARK = { lat: 19.4117, lng: -99.1690, name: "Parque Mexico" };
const NORTH = { lat: 19.5017, lng: -99.1690 };   // ten kilometres up the same meridian

/** Two cinemas: one 300 m from the park, one ten kilometres north. One subtitled format. */
const tiny = () => ({
  fmts: [{ t: [] }, { t: ["lang_sub"] }],
  films: { "1": { n: "A" }, "2": { n: "B" } },
  cin: [
    { id: 5, n: "Near", lat: 19.4140, lng: -99.1700, s: [[1, 0, 0, 600], [2, 1, 0, 700]] },
    { id: 6, n: "North", ...NORTH, s: [[1, 1, 0, 620]] },
  ],
});

function world(src, SHOWS) {
  const ctx = {
    console, JSON, Array, Set, Map, String, Number,
    localStorage: memStore(),
    S: { day: 0, filters: new Set(), tab: "shows", q: "", starred: new Set() },
    DAYS: ["2026-09-13"], SHOWS,
    origin: { ...PARK },
    isToday: () => false, nowMins: () => 0, matchesQuery: () => true, isStarred: () => false,
    esc: x => String(x),
  };
  vm.createContext(ctx);
  vm.runInContext([
    liftLine(src, /const walkMin = [^\n]+/, "walkMin"),
    liftLine(src, /const WALK_MAX = [^\n]+/, "WALK_MAX"),
    lift(src, "walkable"), lift(src, "km"), lift(src, "travelMin"), lift(src, "far"),
    liftConst(src, "FILTER_OPTS"), liftConst(src, "FILTER_WORD"), liftConst(src, "WORD_ORDER"),
    lift(src, "passesOne"), lift(src, "passes"), lift(src, "filterCounts"),
    lift(src, "saveFilters"), lift(src, "filterWords"), lift(src, "countLabel"),
  ].join("\n"), ctx);
  return ctx;
}

console.log("1. one line decides walk or drive, for the rows and for the chip");
paired("at every distance out to 10 km, walkable() agrees with the row's own label", src => {
  const w = world(src, tiny());
  for (let d = 0; d <= 10; d += 0.005) if (w.walkable(d) !== w.far(d).w.endsWith("min walk")) return false;
  return true;
});
paired("the line is where the rows switch: 3.03 km is a 40 min walk, 3.04 km a drive", src => {
  const w = world(src, tiny());
  return w.walkable(3.03) && w.far(3.03).w === "40 min walk"
      && !w.walkable(3.04) && /min drive$/.test(w.far(3.04).w)
      && w.travelMin(3.03) === 40 && w.travelMin(3.04) < 40;
});

console.log("2. the chip");
paired("Walkable passes a near cinema, refuses a far one, and refuses with no cinema", src => {
  const w = world(src, tiny());
  const [near, north] = w.SHOWS.cin;
  return w.passesOne("walk", 0, 600, "2026-09-13", 1, near) === true
      && w.passesOne("walk", 0, 600, "2026-09-13", 1, north) === false
      && w.passesOne("walk", 0, 600, "2026-09-13", 1) === false;
});
paired("its count is the showings in reach, and it stacks with Subtitled", src => {
  const w = world(src, tiny());
  const c = w.filterCounts();
  w.S.filters.add("sub");
  const c2 = w.filterCounts();
  return c.walk === 2 && c.all === 3 && c2.active === 2 && c2.walk === 1;
});

console.log("3. it follows the origin");
paired("measured from far away nothing is in reach; from the north cinema only it is", src => {
  const w = world(src, tiny());
  w.origin = { lat: 39.74, lng: -104.99, name: "a long way off" };
  const away = w.filterCounts().walk;
  w.origin = { ...NORTH, name: "north" };
  const north = w.filterCounts().walk;
  return away === 0 && north === 1;
});
paired("the location button recounts the chips before the list, both on and off", src => {
  const at = src.indexOf('$("locbtn").addEventListener("click", () => {');
  if (at === -1) throw new Error("the location button handler is not in the page");
  let depth = 0, j = src.indexOf("{", at);
  for (; j < src.length; j++) { if (src[j] === "{") depth++; else if (src[j] === "}" && --depth === 0) break; }
  return (src.slice(at, j).match(/renderFilters\(\); renderShows\(\);/g) || []).length === 2;
});

console.log("4. it is not remembered, and the count line is English");
paired("Walkable is never written back as a standing filter", src => {
  const w = world(src, tiny());
  w.S.filters.add("sub"); w.S.filters.add("walk");
  w.saveFilters();
  return w.localStorage._m.get("sala.filters") === JSON.stringify(["sub"]);
});
paired('the count line reads "subtitled showing within walking distance"', src => {
  const w = world(src, tiny());
  w.S.filters.add("walk"); w.S.filters.add("sub");
  const one = w.countLabel(1, 0);
  w.S.filters.add("now");
  const soon = w.countLabel(3, 0);
  return one === "subtitled showing within walking distance"
      && soon === "subtitled showings within walking distance starting in the next four hours";
});

console.log("5. every caller hands the cinema through");
paired("every passes( call has six arguments: the film id fifth, the cinema sixth", src => {
  const calls = [];
  const re = /(?<![\w.])passes\(/g;
  let m;
  while ((m = re.exec(src))) {
    if (src.slice(m.index - 9, m.index) === "function ") continue;
    let depth = 0, j = m.index + "passes".length, start = j + 1;
    const args = [];
    for (; j < src.length; j++) {
      const ch = src[j];
      if (ch === "(" || ch === "[" || ch === "{") depth++;
      else if (ch === ")" || ch === "]" || ch === "}") { if (--depth === 0) break; }
      else if (ch === "," && depth === 1) { args.push(src.slice(start, j).trim()); start = j + 1; }
    }
    args.push(src.slice(start, j).trim());
    calls.push({ args, text: src.slice(m.index, j + 1) });
  }
  const bad = calls.filter(c => c.args.length !== 6 || !/\[0\]$/.test(c.args[4]) || c.args[5] !== "c");
  if (bad.length && src === SRC) console.log("       short calls:", bad.map(b => b.text).join("  |  "));
  return calls.length >= 5 && bad.length === 0;
});

console.log("6. on the real listing");
check("the page still measures from the Parque Mexico this test uses",
      /const HOME = \{ lat: 19\.4117, lng: -99\.1690, name: "Parque Mexico" \}/.test(SRC));
check("every cinema in the listing carries coordinates, or it could never be walkable and nothing would say so",
      payload(SRC).cin.every(c => Number.isFinite(c.lat) && Number.isFinite(c.lng)));
paired("from Parque Mexico some cinemas are in reach and some are not", src => {
  const SHOWS = payload(src);
  const w = world(src, SHOWS);
  const inReach = SHOWS.cin.filter(c => w.walkable(w.km(w.origin, { lat: c.lat, lng: c.lng })));
  if (src === SRC) console.log(`       ${inReach.length} of ${SHOWS.cin.length} cinemas are walkable from Parque Mexico: `
                               + inReach.map(c => c.n).join(", "));
  return inReach.length > 0 && inReach.length < SHOWS.cin.length;
});

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
