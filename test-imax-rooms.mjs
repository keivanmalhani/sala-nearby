// Does each IMAX room say exactly what is known about it, and nothing that is not?
//
//     node test-imax-rooms.mjs
//
// imaxLine() runs for real on the table baked into the page, and the table is compared to
// docs/imax-specs.json so the two cannot drift. The "what not to say" list in that file is
// turned into checks. Paired with the commit that added pull-refresh.py, the one before this.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const SPEC = JSON.parse(readFileSync(join(ROOT, "docs", "imax-specs.json"), "utf8"));
const BASELINE = execFileSync("git", ["-C", ROOT, "log", "-1", "--format=%h", "--", "pull-refresh.py"], { encoding: "utf8" }).trim();
const BEFORE = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/index.html`], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

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
function world(src) {
  const table = src.match(/const IMAX_ROOMS = [^\n]+;\n/);
  if (!table) throw new Error("no IMAX_ROOMS in the page");
  const ctx = { String };
  vm.createContext(ctx);
  vm.runInContext(table[0] + lift(src, "imaxLine") + "\nthis.T = IMAX_ROOMS;", ctx);
  return ctx;
}

console.log("1. each room, as it reads on the sheet");
paired("Parque Delta Sala 3 says laser, marks 4K as press, and says its screen size is not published", src => {
  const t = world(src).imaxLine(32, "Sala 3");
  if (src === SRC) console.log(`       Parque Delta Sala 3: ${t}`);
  return /^IMAX with Laser, laser projection, 4K \(press\), IMAX 12-channel sound \(press\), 1\.90:1 \(press\), screen size not published$/.test(t);
});
paired("Antara Sala 5 gives its screen as about 300 m2 from press, and no height", src => {
  const t = world(src).imaxLine(76, "Sala 5");
  if (src === SRC) console.log(`       Antara Platino Sala 5: ${t}`);
  return t.includes("about 300 m² screen (press)") && !/height|13\.7|metres tall/.test(t);
});
paired("Encuentro Oceania never says laser, and says its projector is not published", src => {
  const t = world(src).imaxLine(410, "Sala 1");
  if (src === SRC) console.log(`       Encuentro Oceania Sala 1: ${t}`);
  return t.startsWith("IMAX, projector not published") && !/laser/i.test(t);
});
paired("a room that is not IMAX gets nothing added", src => world(src).imaxLine(30, "Sala 2") === "");

console.log("2. nothing the evidence rules out");
paired("nowhere says 1.43:1, 70mm or GT as a room's format, and no room is called 2K xenon", src => {
  const w = world(src);
  const lines = Object.keys(w.T).map(k => w.imaxLine(k.split("|")[0], k.split("|")[1])).join(" ");
  return !/1\.43|70 ?mm|IMAX GT|xenon|2K/i.test(lines);
});
paired("the film-sheet format note no longer says every IMAX in Mexico is 4K laser", src =>
  !src.includes("Every IMAX in ") && src.includes('imax: ["IMAX",') && /tall 1\.43:1 rooms exists in Mexico/.test(src));
check("the baked table matches docs/imax-specs.json for every room with showtimes",
  (() => {
    const w = world(SRC);
    const want = SPEC.rooms.filter(r => r.has_showtimes_in_app && r.venue_id && r.room);
    return want.length === Object.keys(w.T).length && want.every(r => {
      const got = w.T[`${r.venue_id}|${r.room}`];
      return got && ["label", "projection", "resolution", "sound", "aspect_ratio"].every(f =>
        !r[f] || (got[f][0] === r[f].value && got[f][1] === r[f].confidence));
    });
  })());
paired("the room line on the film sheet carries it", src =>
  src.includes('imaxLine(c.id, k) ? " &middot; " + esc(imaxLine(c.id, k)) : ""'));

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
