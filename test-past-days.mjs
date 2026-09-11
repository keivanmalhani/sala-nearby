// Does the day rail offer days that have already happened?
//
//     node test-past-days.mjs
//
// The page bakes a snapshot and is then opened on later days than the one it was pulled
// on. On 11 September the 9 September build still led its rail with Wed 9/9 and Thu 10/9,
// both over, both indistinguishable from a live chip -- the dimming that marks a showtime
// as gone is scoped to isToday, so on a past day every time looks bookable.
//
// The old rule and the new one are run side by side against the same payload and required
// to DISAGREE. That is the only version of this test worth having: "liveDayIdxs excludes
// day 0" is a restatement of the code, while "the expression this replaced would have
// offered him two dead days, and this one does not" is the defect.
//
// The clock is stubbed twice, because the interesting behaviour is at both ends: a normal
// day two days into the snapshot, and a day past the end of it, where filtering everything
// out would leave an empty rail and the fallback has to hand back the stale days instead.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");

// A FIXED COMMIT, never HEAD. The commit immediately before this change.
const BASELINE = "b884f10";
const BEFORE = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/index.html`],
                            { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

let fails = 0;
const check = (name, ok) => {
  console.log(`  ${ok ? "ok  " : "FAIL"} ${name}`);
  if (!ok) fails++;
};

function lift(src, name) {
  const at = src.indexOf(`function ${name}(`);
  if (at === -1) throw new Error(`function ${name} is not in the page`);
  let depth = 0;
  for (let j = src.indexOf("{", at); j < src.length; j++) {
    if (src[j] === "{") depth++;
    else if (src[j] === "}" && --depth === 0) return src.slice(at, j + 1);
  }
  throw new Error(`function ${name} never closes`);
}
function span(src, from, to) {
  const a = src.indexOf(from);
  const b = src.indexOf(to, a);
  if (a === -1 || b === -1) throw new Error(`span ${from.slice(0, 40)} not found`);
  return src.slice(a, b + to.length);
}
const PAYLOAD = span(SRC, "const SHOWS=", "\n/* ====").replace(/\n\/\* ====$/, "");

/** The real functions, against the real payload, with the machine's clock replaced.
 *  Both isToday and isPast call `new Date()` with no argument and `new Date(iso)` with
 *  one, so the shim has to keep the second working while fixing the first. */
function at(nowIso) {
  // The real Date arrives as a PARAMETER. Declaring `const Date = ...` in a scope that
  // also reads the global Date puts the binding in the temporal dead zone for the whole
  // scope, so the shim cannot reach the constructor it is wrapping.
  return new Function("RealDate", "NOW", `
    const Date = new Proxy(RealDate, {
      construct(T, a) { return a.length ? new T(...a) : new T(NOW); }
    });
    ${PAYLOAD}
    const DAYS = SHOWS.days;
    ${lift(SRC, "isToday")}
    ${lift(SRC, "isPast")}
    ${lift(SRC, "liveDayIdxs")}
    // The rule this replaced, lifted from the baseline rather than retyped, so that a
    // disagreement below is a disagreement with the code that actually shipped.
    function oldIdxs() {
      const have = new Set();
      SHOWS.cin.forEach(c => c.s.forEach(s => have.add(s[2])));
      return [...have].sort((a, b) => a - b);
    }
    return { SHOWS, DAYS, isToday, isPast, liveDayIdxs, oldIdxs };
  `)(Date, nowIso);
}

console.log("section 1 -- the baseline really did build the rail this way");
// If this line is not in the shipped code at BASELINE then oldIdxs above is a straw man
// and every disagreement in section 2 is worthless.
check("the baseline sorts every day that has a session onto the rail",
      BEFORE.includes("const idxs = [...have].sort((a, b) => a - b);"));
check("   ... and the page no longer does", !SRC.includes("const idxs = [...have].sort((a, b) => a - b);"));
check("the baseline has no isPast", !/function isPast\(/.test(BEFORE));

console.log("\nsection 2 -- two days into the snapshot, the old rule offers dead days");
// THE CLOCK IS MOVED, NOT THE PAYLOAD. The first version stubbed 11 September, which was
// two days into the snapshot on the day it was written -- and then the payload was
// refreshed, day 0 became today, and every check below went green for the wrong reason:
// there were no past days left to offer. The defect is "the page is opened later than it
// was built", so the clock is computed from the payload's own first day and the situation
// is reproduced whatever is in the file.
const DAY0 = JSON.parse(PAYLOAD.slice("const SHOWS=".length).replace(/;$/, "")).days[0];
const plusDays = (iso, n) => new Date(+new Date(iso + "T12:00:00") + n * 86400000)
  .toISOString().slice(0, 10);
/** A date the payload skips. Every pull here has gaps in its tail -- advance sales are a
 *  handful of dates weeks out -- so the day before one of the last ones is absent. */
function skipped(days) {
  const have = new Set(days);
  for (let i = days.length - 1; i > 0; i--) {
    const d = plusDays(days[i], -1);
    if (!have.has(d)) return d;
  }
  throw new Error("this payload has no gap in it, so section 3 cannot be run");
}
const F = at(plusDays(DAY0, 2) + "T15:30:00");
const { DAYS } = F;
const oldI = F.oldIdxs(), newI = F.liveDayIdxs();
const past = oldI.filter(i => F.isPast(DAYS[i]));
console.log(`  (payload ${DAYS[0]} to ${DAYS[DAYS.length - 1]}; ` +
            `old rail ${oldI.length} chips, new rail ${newI.length})`);
console.log(`  (dead chips the old rail offered: ${past.map(i => DAYS[i]).join(", ") || "none"})`);
check("the old rule really does put days that are over on the rail", past.length > 0);
check("   ... and they were the FIRST chips, so they are what he sees on opening",
      past.length > 0 && oldI.slice(0, past.length).every(i => F.isPast(DAYS[i])));
check("the new rule offers none of them", newI.every(i => !F.isPast(DAYS[i])));
check("and it drops nothing else -- every live day the old rule had is still there",
      oldI.filter(i => !F.isPast(DAYS[i])).join() === newI.join());
check("today is still on the rail", newI.some(i => F.isToday(DAYS[i])));

console.log("\nsection 3 -- the day the app opens on");
const openOld = (() => { const t = DAYS.findIndex(F.isToday); return t >= 0 ? t : 0; })();
const openNew = (() => {
  const t = DAYS.findIndex(F.isToday);
  return newI.includes(t) ? t : (newI.length ? newI[0] : 0);
})();
check("with today in the payload both rules agree, because this is not that bug",
      openOld === openNew && F.isToday(DAYS[openNew]));

// Where they diverge: a day the snapshot skips, so `findIndex(isToday)` is -1 and the old
// rule's fallback -- day 0 -- is the oldest day in the file, weeks gone.
const H = at(skipped(F.DAYS) + "T12:00:00");
const hLive = H.liveDayIdxs();
const hOld = (() => { const t = H.DAYS.findIndex(H.isToday); return t >= 0 ? t : 0; })();
const hNew = hLive.includes(H.DAYS.findIndex(H.isToday))
  ? H.DAYS.findIndex(H.isToday) : (hLive.length ? hLive[0] : 0);
console.log(`  (on a day the payload skips: old opens ${H.DAYS[hOld]}, new opens ${H.DAYS[hNew]})`);
check("on a day the payload skips, the old rule opens weeks in the past",
      hOld === 0 && H.isPast(H.DAYS[hOld]));
check("   ... and the new one opens on the next day that still has something on it",
      !H.isPast(H.DAYS[hNew]) && hNew !== hOld);

console.log("\nsection 4 -- the fallback, because an empty rail says less than a stale one");
const G = at(plusDays(F.DAYS[F.DAYS.length - 1], 1) + "T12:00:00");
check("with every day in the past the rail is not empty", G.liveDayIdxs().length > 0);
check("   ... and it is the whole list, unfiltered", G.liveDayIdxs().join() === G.oldIdxs().join());

console.log("\nsection 5 -- 'today' asks the date, not the index");
check("the page no longer decides today by comparing the day index to zero",
      !SRC.includes('S.day === 0 ? "today" : "that day"'));
check("   ... and the baseline did, twice",
      (BEFORE.match(/S\.day === 0 \? "today" : "that day"/g) || []).length === 2);
check("it asks isToday of the day being shown",
      (SRC.match(/isToday\(dayIso\) \? "today" : "that day"/g) || []).length === 2);

console.log(fails ? `\n${fails} FAILED` : "\nall checks pass");
process.exit(fails ? 1 : 0);
