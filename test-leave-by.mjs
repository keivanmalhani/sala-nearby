// Does the leave-by arithmetic actually point the right way?
//
//     node test-leave-by.mjs
//
// This runs the real functions rather than matching strings for them. `walkMin`,
// `travelMin` and `leaveBy` are lifted out of docs/index.html by name and evaluated with
// the clock and the calendar stubbed, so a wrong sign, a wrong unit or a wrong branch
// fails here instead of on his phone.
//
// The check the idea doc asked for, and it is the right one: an inverted subtraction is
// completely plausible on a single row. A cinema nineteen minutes away must give an
// earlier leave-by than one four minutes away, for the same showing. Section 2 asserts
// exactly that, and section 5 proves the whole harness can fail by feeding it the
// inverted function.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");

let fails = 0;
const check = (name, ok) => {
  console.log(`  ${ok ? "ok  " : "FAIL"} ${name}`);
  if (!ok) fails++;
};

/** Lift a top-level `function name(...) { ... }` out of the page by brace matching.
 *  A regex cannot do this: every one of these bodies contains braces. */
function lift(name) {
  const at = SRC.indexOf(`function ${name}(`);
  if (at === -1) throw new Error(`function ${name} is not in the page`);
  let i = SRC.indexOf("{", at), depth = 0;
  for (let j = i; j < SRC.length; j++) {
    if (SRC[j] === "{") depth++;
    else if (SRC[j] === "}" && --depth === 0) return SRC.slice(at, j + 1);
  }
  throw new Error(`function ${name} never closes`);
}

const WALK = SRC.match(/const walkMin = [^\n]+/);
if (!WALK) throw new Error("walkMin is not in the page");
// walkable.py moved the forty-minute line into WALK_MAX and walkable(), which travelMin calls.
const LINE = SRC.match(/const WALK_MAX = [^\n]+/);
if (!LINE) throw new Error("WALK_MAX is not in the page");

// NOW is 18:00 and today is 2026-09-09, for every case below.
const NOW = 18 * 60;
const harness = `
  const nowMins = () => ${NOW};
  const isToday = iso => iso === "2026-09-09";
  ${WALK[0]}
  ${LINE[0]}
  ${lift("walkable")}
  ${lift("travelMin")}
  ${lift("leaveBy")}
  ({ walkMin, travelMin, leaveBy })
`;
const F = eval(harness);

console.log("section 1 -- the travel time is the one far() would print");
// far() switches to driving above 40 minutes of walking; travelMin has to switch with it
// or the header says "19 min walk" beside a leave-by computed from a car.
check("a short hop is walked", F.travelMin(0.3) === F.walkMin(0.3));
check("and it is the four minutes the header shows for Insurgentes", F.travelMin(0.302) === 4);
check("1.4 km is nineteen minutes on foot", F.travelMin(1.4) === 19);
const longWalk = 40 * 0.075;                       // exactly the 40-minute boundary
check("the boundary case is still walked", F.travelMin(longWalk) === F.walkMin(longWalk));
check("but a genuinely far one switches to driving",
      F.travelMin(12) < F.walkMin(12) && F.travelMin(12) === Math.round(12 / 0.35));

console.log("\nsection 2 -- the subtraction points the right way");
// THE CASE THE IDEA DOC NAMED. Same showing, two distances; the far one must leave first.
const near = F.leaveBy(20 * 60 + 30, 0.302, "2026-09-09");
const farr = F.leaveBy(20 * 60 + 30, 1.4, "2026-09-09");
console.log(`  (20:30 showing -- 302 m leaves at ${(near / 60 | 0)}:${String(near % 60).padStart(2, "0")}, ` +
            `1.4 km leaves at ${(farr / 60 | 0)}:${String(farr % 60).padStart(2, "0")})`);
check("both are before the showing starts", near < 20 * 60 + 30 && farr < 20 * 60 + 30);
check("the further cinema has to leave earlier", farr < near);
check("four minutes away means four minutes before", near === 20 * 60 + 26);
check("nineteen minutes away means nineteen minutes before", farr === 20 * 60 + 11);

console.log("\nsection 3 -- there is no invented ad allowance in it");
// The idea doc proposed adding 17 minutes for the Cinemex reel. Nobody measured that, and
// too generous an allowance sends him out of the door late. A leave-by that is never
// after (start - travel) can only ever make him early.
check("the leave-by is never later than the walk alone would allow",
      F.leaveBy(20 * 60 + 30, 0.302, "2026-09-09") <= 20 * 60 + 30 - F.travelMin(0.302));
check("and no reel constant was added to the page",
      !/const REEL\s*=/.test(SRC));

console.log("\nsection 4 -- it declines to answer where the question does not apply");
check("another day gets nothing", F.leaveBy(20 * 60 + 30, 0.302, "2026-09-12") === null);
check("a showing that already started gets nothing",
      F.leaveBy(17 * 60 + 30, 0.302, "2026-09-09") === null);
// A leave-by in the past on a showing still to come is not an error -- it is "leave now",
// and the page renders it as that. It must come back as a number, not as null.
const late = F.leaveBy(NOW + 2, 1.4, "2026-09-09");
check("but a showing he can no longer make on time still answers", late !== null);
check("and it answers with a time already past, which the page reads as 'leave now'",
      late < NOW);
check("the page does render that case rather than dropping it",
      SRC.includes('lv <= nowMins() ? " now" : ""') && SRC.includes('"Leave now"'));

console.log("\nsection 5 -- the harness can fail");
// Everything above would also pass against a function that returned the right answers by
// accident. Feed it the inverted subtraction the doc warned about and require section 2
// to go red.
const bad = eval(`
  const nowMins = () => ${NOW};
  const isToday = iso => iso === "2026-09-09";
  ${WALK[0]}
  ${LINE[0]}
  ${lift("walkable")}
  ${lift("travelMin")}
  function leaveBy(startMins, distKm, dayIso) {
    if (!isToday(dayIso)) return null;
    if (startMins < nowMins()) return null;
    return startMins + travelMin(distKm);     // inverted on purpose
  }
  ({ leaveBy })
`);
const bNear = bad.leaveBy(20 * 60 + 30, 0.302, "2026-09-09");
const bFar = bad.leaveBy(20 * 60 + 30, 1.4, "2026-09-09");
check("the inverted version puts the leave-by after the showing", bNear > 20 * 60 + 30);
check("and gets the two cinemas the wrong way round", bFar > bNear);

console.log();
if (fails) { console.log(`${fails} FAILED`); process.exit(1); }
console.log("all controls pass");
