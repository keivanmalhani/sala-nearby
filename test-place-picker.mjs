// Can he type where distances start, and does every suggestion tell him something true?
//
//     node test-place-picker.mjs
//
// The search, the walk count and the stored origin run for real against the real
// places.json and the real listing, lifted out of the page. Page checks are paired with
// e10405c, the commit before place-picker.py, so each is shown able to fail.

import { readFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = "e10405c";
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

console.log("1. the places file");
const placesPath = join(ROOT, "docs", "places.json");
check("docs/places.json exists", existsSync(placesPath));
const PJ = JSON.parse(readFileSync(placesPath, "utf8"));
const kinds = {};
PJ.p.forEach(r => { kinds[r[1]] = (kinds[r[1]] || 0) + 1; });
console.log(`       ${PJ.p.length} places, ${Math.round(readFileSync(placesPath).length / 1024)} KB: ${JSON.stringify(kinds)}`);
check("it holds the city, not a broken pull: 800+ colonias, 80+ Metro, 60+ Metrobus, 30+ landmarks",
      kinds.col >= 800 && kinds.m >= 80 && kinds.mb >= 60 && kinds.lm >= 30);
check("it credits OpenStreetMap", /OpenStreetMap/.test(PJ.src));

function world(src, storage) {
  const payload = JSON.parse(line(src, /const SHOWS=[^\n]+/).slice("const SHOWS=".length).replace(/;$/, ""));
  const ctx = {
    SHOWS: payload, localStorage: storage, JSON, Number, String, Array, Math,
    HOME: { lat: 19.4117, lng: -99.1690, name: "Parque Mexico" },
    fetch: async () => ({ ok: true, json: async () => PJ }),
  };
  vm.createContext(ctx);
  vm.runInContext([
    line(src, /const walkMin = [^\n]+/), line(src, /const WALK_MAX = [^\n]+/),
    lift(src, "walkable"), lift(src, "km"), lift(src, "far"), lift(src, "fold"),
    "let PLACES = null;",
    lift(src, "loadPlaces"), lift(src, "placeMatches"), lift(src, "reachFrom"), lift(src, "reachLine"),
    lift(src, "savedPlaces"), lift(src, "writeSaved"), lift(src, "savedOrigin"),
    "this.getPlaces = () => PLACES;",
  ].join("\n"), ctx);
  return ctx;
}
const store = init => {
  const m = new Map(Object.entries(init || {}));
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)),
           removeItem: k => m.delete(k), _m: m };
};

console.log("2. typing finds the places a person in Mexico City would type");
{
  let w = null;
  try { w = world(SRC, store()); await w.loadPlaces(); } catch (e) { console.log(`       (${e.message})`); }
  const top = q => (w ? w.placeMatches(q).map(p => `${p.n}/${p.k}`) : []);
  console.log(`       condesa -> ${top("condesa").slice(0, 3).join(", ")}   zocalo -> ${top("zocalo").slice(0, 2).join(", ")}   06700 -> ${top("06700").slice(0, 2).join(", ")}`);
  check("\"condesa\" finds Condesa first", !!w && /^Condesa\//.test(top("condesa")[0] || ""));
  check("accents do not matter: \"zocalo\" finds the Zocalo Metro", !!w && top("zocalo").some(x => /Zócalo/.test(x)));
  check("\"chilpancingo\" finds the Metro station", !!w && top("chilpancingo").includes("Chilpancingo/m"));
  check("a postcode finds its colonia: 06700 is Roma Norte", !!w && top("06700").includes("Roma Norte/col"));
  check("an empty box suggests nothing, and never more than eight", !!w && top("").length === 0 && top("a").length === 8);
}

console.log("3. every suggestion says something true about walking");
paired("from Parque Mexico the line counts the same cinemas the Walkable chip does, and names the nearest", src => {
  const w = world(src, store());
  const expected = w.SHOWS.cin.filter(c => w.walkable(w.km(w.HOME, { lat: c.lat, lng: c.lng }))).length;
  const text = w.reachLine(w.HOME);
  if (src === SRC) console.log(`       Parque Mexico: ${text}`);
  return text.startsWith(`${expected} cinemas within a walk · nearest `) && expected > 0;
});
paired("from somewhere with nothing in reach it says so rather than a zero", src => {
  const w = world(src, store());
  return w.reachLine({ lat: 19.30, lng: -99.30 }).startsWith("No cinema within a walk");
});

console.log("4. what is remembered, and what is refused");
paired("a chosen place comes back, and junk, a far-off point or a broken store is the park", src => {
  const good = world(src, store({ "sala.origin": JSON.stringify({ n: "Condesa", lat: 19.41145, lng: -99.17399 }) })).savedOrigin();
  const junk = world(src, store({ "sala.origin": "{nope" })).savedOrigin();
  const nowhere = world(src, store({ "sala.origin": JSON.stringify({ n: "Null Island", lat: 0, lng: 0 }) })).savedOrigin();
  const broken = world(src, { getItem() { throw new Error("private"); } }).savedOrigin();
  return good.name === "Condesa" && [junk, nowhere, broken].every(o => o.name === "Parque Mexico" && o.lat === 19.4117);
});
paired("saved places drop anything malformed and keep at most twelve", src => {
  const st = store({ "sala.places": JSON.stringify([{ l: "Home", n: "Condesa", lat: 19.41, lng: -99.17 }, { l: 3 }, null, { l: "x", n: "y", lat: "19", lng: 1 }]) });
  const w = world(src, st);
  const kept = w.savedPlaces();
  w.writeSaved(Array.from({ length: 20 }, (_, i) => ({ l: "p" + i, n: "p", lat: 19.4, lng: -99.1 })));
  return kept.length === 1 && kept[0].l === "Home" && JSON.parse(st._m.get("sala.places")).length === 12;
});

console.log("5. wired into the app");
paired("\"Distances from\" in the header is a button that opens the picker", src =>
  /<button class="from" id="fromopen" aria-haspopup="dialog"/.test(src) && /closest\("#fromopen"\)\) return placeSheet\(\)/.test(src));
paired("the chosen place is restored before the first list is drawn", src =>
  /origin = savedOrigin\(\); \$\("fromn"\)\.textContent = origin\.name;\n(?:[^\n]*\n){0,1}renderDates\(\); renderFilters\(\); renderShows\(\);/.test(src));
paired("the Movies line, Settings and the location button all use the chosen place, not the park", src =>
  lift(src, "whereFrom").includes('liveLoc ? "you" : origin.name')
  && src.includes('liveLoc = false; origin = savedOrigin();') && src.includes('data-origin="place"'));
paired("the picker credits OpenStreetMap and places.json is kept for no-signal use", src =>
  src.includes("Places from OpenStreetMap contributors, ODbL.")
  && readFileSync(join(ROOT, "docs", "sw.js"), "utf8").includes('"./places.json"'));

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
