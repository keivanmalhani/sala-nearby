// Does the app admit it when its whole listing has run out?
//
//     node test-stale-listing.mjs
//
// The showtimes are baked into the page and the page ages on its own. `past-days.py` stops
// the rail offering a day that is over; this is the case it deliberately left open, where
// EVERY day is over and there is nothing left to offer. The app draws exactly what it
// always draws -- a rail, a count, rows of times with prices -- and every one of those
// times has already happened.
//
// The clock is computed from the payload rather than written down, so this keeps testing
// the same thing after every refresh. Three moments: today, where the sentence must not
// appear; the payload's own last day, where it must still not appear, because that day is
// live; and the day after it, where it must.
//
// That middle one is the check worth having. A guard that fires one day early would put
// "these showtimes have run out" over a board he could still buy a ticket from.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const SHOT = readFileSync(join(ROOT, "tools", "shot.mjs"), "utf8");

// A FIXED COMMIT, never HEAD: the one immediately before this change.
const BASELINE = "15a21cd";
const BEFORE = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/index.html`],
                            { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

let fails = 0;
const check = (name, ok, note) => {
  console.log(`  ${ok ? "ok  " : "FAIL"} ${name}${note ? `  (${note})` : ""}`);
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
  const a = src.indexOf(from), b = src.indexOf(to, a);
  if (a === -1 || b === -1) throw new Error(`span ${from.slice(0, 30)} not found`);
  return src.slice(a, b + to.length);
}
const decl = re => {
  const m = SRC.match(re);
  if (!m) throw new Error(`declaration ${re} not in the page`);
  return m[0];
};
const PAYLOAD = span(SRC, "const SHOWS=", "\n/* ====").replace(/\n\/\* ====$/, "");
const DAYS = JSON.parse(PAYLOAD.slice("const SHOWS=".length).replace(/;$/, "")).days;
const plusDays = (iso, n) => new Date(+new Date(iso + "T12:00:00") + n * 86400000)
  .toISOString().slice(0, 10);

/** The real functions against the real payload, with the clock replaced. */
function at(nowIso) {
  return new Function("RealDate", "NOW", `
    const Date = new Proxy(RealDate, {
      construct(T, a) { return a.length ? new T(...a) : new T(NOW); }
    });
    ${PAYLOAD}
    const DAYS = SHOWS.days;
    ${decl(/const esc = [\s\S]*?\);\n/)}
    ${decl(/const MON = \[[\s\S]*?\];/)}
    ${lift(SRC, "isPast")}
    ${lift(SRC, "dateAbs")}
    ${lift(SRC, "listingIsDead")}
    ${lift(SRC, "staleLine")}
    return { DAYS, listingIsDead, staleLine };
  `)(Date, nowIso);
}

const last = DAYS[DAYS.length - 1];
console.log(`  (payload runs ${DAYS[0]} to ${last})`);

console.log("section 1 -- it stays quiet while there is anything left to see");
const today = at(DAYS[0] + "T12:00:00");
check("on the payload's first day the listing is not dead", !today.listingIsDead());
check("   ... and nothing is drawn", today.staleLine() === "");
// THE OFF-BY-ONE THAT WOULD HURT. The last day is still a day he can buy a ticket for.
const onLast = at(last + "T12:00:00");
check("on its LAST day it is still not dead, because that day is live",
      !onLast.listingIsDead());
check("   ... and still nothing is drawn", onLast.staleLine() === "");

console.log("\nsection 2 -- and says so the day after the listing runs out");
const after = at(plusDays(last, 1) + "T12:00:00");
check("the day after the last day, the listing is dead", after.listingIsDead());
const line = after.staleLine();
check("   ... and a sentence is drawn", line.length > 0);
// Written out rather than waved at: the sentence has to carry the payload's LAST date and
// must not carry the date it is being read on, because "these have run out" beside today's
// date reads as though today is the thing that ran out.
const MONS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const asWritten = iso => {
  const d = new Date(iso + "T12:00:00");
  return `${["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getDay()]} ${d.getDate()} ${MONS[d.getMonth()]}`;
};
check(`it names the last date the page holds, ${asWritten(last)}`,
      line.includes(asWritten(last)));
check(`   ... and not the date it is being read on, ${asWritten(plusDays(last, 1))}`,
      !line.includes(asWritten(plusDays(last, 1))));
check("it says the cinema's own page is still live, because that is what he can act on",
      /live/.test(line) && /cinema/.test(line));
check("it does not claim to know anything it cannot -- no invented showtimes, no prices",
      !/\$/.test(line));
console.log("    " + line.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim());

console.log("\nsection 3 -- both lists carry it, so the two tabs cannot disagree");
check("the showtimes count line calls it", SRC.includes('$("scount").innerHTML = staleLine()'));
check("the films count line calls it", SRC.includes('$("fcount").innerHTML = staleLine()'));
check("the map does not, because venues do not go stale with the showtimes",
      (SRC.match(/staleLine\(\)/g) || []).length === 3);  // one definition, two call sites

console.log(`\nsection 4 -- none of this existed at ${BASELINE}, so the checks can fail`);
check("the baseline has no listingIsDead", !/function listingIsDead\(/.test(BEFORE));
check("the baseline has no staleLine", !/function staleLine\(/.test(BEFORE));
check("so a page whose every day was over said nothing at all",
      !BEFORE.includes("have run out"));

console.log("\nsection 5 -- the screenshot tool renders the phone's tap targets");
// NOT A STYLE POINT. `Emulation.setDeviceMetricsOverride` with mobile:true does NOT make
// `(pointer:coarse)` match, so until 11 September every screenshot from this tool rendered
// the app's desktop tap sizes: the free-screens pill measured 38 instead of 44, the icon
// buttons 38 instead of 44 and the tab bar 54 instead of 56. Anyone checking a tap target
// through it would have read a regression that was not there.
check("shot.mjs turns touch emulation on", SHOT.includes("Emulation.setTouchEmulationEnabled"));
check("   ... and says why, so nobody takes it out again",
      /pointer:coarse/.test(SHOT));

console.log(fails ? `\n${fails} FAILED` : "\nall checks pass");
process.exit(fails ? 1 : 0);
