// Does starring a film do what it says, and nothing it does not?
//
//     node test-starred.mjs
//
// The feature is small and the ways it can quietly go wrong are not. The filter code was
// written to ask about formats and times, never about which film a showing is, so the id
// had to be threaded through `passes` at every call site. One site left on the old
// signature would make the Starred chip count nothing there -- greyed out, or lit over a
// list that disagrees with its own number -- and no error would ever say why. Section 3
// reads every call in the page rather than trusting that all five were found.
//
// Every check is paired with the commit before the feature, so each one is shown able to
// fail rather than assumed to.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = "e2eaffe";   // the last commit before starred.py
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

/** A small world: three films, one cinema, one day, formats that are all plain. */
function world(src, storage) {
  const ctx = {
    console, JSON, Array, Set, Map, String, Number,
    localStorage: storage,
    S: { day: 0, filters: new Set(), tab: "shows", q: "", starred: new Set() },
    DAYS: ["2026-09-13"],
    SHOWS: { fmts: [{ t: ["lang_sub"] }], films: { "1": { n: "A" }, "2": { n: "B" }, "ct-9": { n: "C" } },
             cin: [{ id: 5, s: [[1, 0, 0, 600], [1, 0, 0, 720], [2, 0, 0, 660], ["ct-9", 0, 0, 700]] }] },
    isToday: () => false, nowMins: () => 0, matchesQuery: () => true,
    esc: x => String(x),
  };
  vm.createContext(ctx);
  const code = [
    liftConst(src, "FILTER_OPTS"),
    lift(src, "passesOne"), lift(src, "passes"), lift(src, "filterCounts"),
    lift(src, "loadStarred"), lift(src, "saveStarred"), lift(src, "isStarred"),
    lift(src, "saveFilters"),
    "this.FILTER_OPTS = FILTER_OPTS;",
  ].join("\n");
  vm.runInContext(code, ctx);
  return ctx;
}
const memStore = (init) => {
  const m = new Map(Object.entries(init || {}));
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), _m: m };
};

console.log("1. stars survive a relaunch, and a broken store never breaks the page");
paired("saved ids come back, numbers and ct- ids alike, as strings", src => {
  const w = world(src, memStore({ "sala.starred": JSON.stringify([1, "ct-9"]) }));
  w.loadStarred();
  return w.S.starred.has("1") && w.S.starred.has("ct-9") && w.S.starred.size === 2;
});
paired("garbage, a non-array and a throwing accessor all leave nothing starred", src => {
  for (const store of [memStore({ "sala.starred": "{not json" }), memStore({ "sala.starred": '{"a":1}' }),
                       { getItem() { throw new Error("private window"); }, setItem() { throw new Error("no"); } }]) {
    const w = world(src, store);
    w.loadStarred();
    if (w.S.starred.size !== 0) return false;
    w.S.starred.add("2"); w.saveStarred();   // must not throw either
  }
  return true;
});
paired("saving writes exactly the starred set", src => {
  const st = memStore();
  const w = world(src, st);
  w.S.starred.add("2"); w.S.starred.add("ct-9"); w.saveStarred();
  return JSON.stringify(JSON.parse(st._m.get("sala.starred")).sort()) === JSON.stringify(["2", "ct-9"]);
});

console.log("2. the chip");
paired("Starred passes a starred film and refuses the rest, and refuses with no id", src => {
  const w = world(src, memStore());
  w.S.starred.add("1");
  return w.passesOne("star", 0, 600, "2026-09-13", 1) === true
      && w.passesOne("star", 0, 600, "2026-09-13", 2) === false
      && w.passesOne("star", 0, 600, "2026-09-13") === false;
});
paired("the chip's count is the starred showings, and it stacks with Subtitled", src => {
  const w = world(src, memStore());
  w.S.starred.add("1"); w.S.starred.add("ct-9");
  const c = w.filterCounts();
  w.S.filters.add("sub");
  const c2 = w.filterCounts();
  return c.star === 3 && c.all === 4 && c2.star === 3;
});
paired("Starred is never written back as a standing filter", src => {
  const st = memStore();
  const w = world(src, st);
  w.S.filters.add("sub"); w.S.filters.add("star"); w.S.filters.add("now");
  w.saveFilters();
  return st._m.get("sala.filters") === JSON.stringify(["sub"]);
});

console.log("3. every caller hands the film id through");
paired("every passes( call in the page has five arguments, the last a film id", src => {
  const calls = [];
  const re = /(?<![\w.])passes\(/g;
  let m;
  while ((m = re.exec(src))) {
    if (src.slice(m.index - 9, m.index) === "function ") continue;
    let depth = 0, j = m.index + "passes".length, args = 1;
    for (; j < src.length; j++) {
      const ch = src[j];
      if (ch === "(" || ch === "[" || ch === "{") depth++;
      else if (ch === ")" || ch === "]" || ch === "}") { if (--depth === 0) break; }
      else if (ch === "," && depth === 1) args++;
    }
    calls.push({ args, text: src.slice(m.index, j + 1) });
  }
  const bad = calls.filter(c => c.args !== 5 || !/\[0\]\)$/.test(c.text));
  if (bad.length) console.log("       short calls:", bad.map(b => b.text).join("  |  "));
  return calls.length >= 5 && bad.length === 0;
});

console.log("4. it is on the screen");
paired("the film sheet draws a Star button and the tap handler toggles it", src =>
  /\$\{starBtn\(fid\)\}/.test(lift(src, "filmSheet"))
  && /closest\("\[data-star\]"\)[\s\S]{0,400}saveStarred\(\)/.test(src));
paired("starred films sort first in both lists", src =>
  /isStarred\(b\[0\]\) - isStarred\(a\[0\]\)/.test(lift(src, "renderShows"))
  && /isStarred\(b\.fid\) - isStarred\(a\.fid\)/.test(lift(src, "renderFilms")));

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
