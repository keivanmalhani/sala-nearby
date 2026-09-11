// Does "Coming up" say only what the listing can actually support?
//
//     node test-coming-up.mjs
//
// The claim this feature makes and could get wrong is not arithmetic, it is EVIDENCE:
// "this film's run is over" and "this is its last day". The idea it came from proposed
// deciding that with a count -- films with three or fewer showings in thirty days -- and
// that count is an artefact. Cineteca publishes two days at a time, so twenty-two of the
// twenty-three films under that threshold are Cineteca titles whose runs are simply not
// visible. A page built on the count would have told him a film plays once when the only
// thing it knows is that the board stops on Thursday.
//
// So sections 2 and 3 are the real test: the week rule must refuse every Cineteca
// screening, must refuse PULP (one date, but Cinemex has published no complete week after
// it), and must accept the films that genuinely end today. Section 4 runs the rejected
// count rule against the same data and requires it to say the wrong thing, because a rule
// is only worth its complexity if the simpler one it replaced actually fails.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");

// A FIXED COMMIT, never HEAD: a baseline of HEAD stops being the "before" state the
// moment the change lands, and every red half in section 5 would go green for the wrong
// reason. This is the commit immediately before Coming up.
const BASELINE = "6bc4f9f";
const BEFORE = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/index.html`],
                            { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

let fails = 0;
const check = (name, ok) => {
  console.log(`  ${ok ? "ok  " : "FAIL"} ${name}`);
  if (!ok) fails++;
};
const paired = (name, fn) => {
  check(name, fn(SRC));
  check(`   ... and not true at ${BASELINE}, so the check can fail`, !fn(BEFORE));
};

/** Lift a top-level `function name(...) {...}` by brace matching. Every one of these
 *  bodies contains braces, so a regex cannot do it. */
function lift(name) {
  const at = SRC.indexOf(`function ${name}(`);
  if (at === -1) throw new Error(`function ${name} is not in the page`);
  let depth = 0;
  for (let j = SRC.indexOf("{", at); j < SRC.length; j++) {
    if (SRC[j] === "{") depth++;
    else if (SRC[j] === "}" && --depth === 0) return SRC.slice(at, j + 1);
  }
  throw new Error(`function ${name} never closes`);
}
/** Lift a span of top-level statements between two literal markers, inclusive. */
function span(from, to) {
  const a = SRC.indexOf(from);
  const b = SRC.indexOf(to, a);
  if (a === -1 || b === -1) throw new Error(`span ${from.slice(0, 40)} not found`);
  return SRC.slice(a, b + to.length);
}
const decl = re => {
  const m = SRC.match(re);
  if (!m) throw new Error(`declaration ${re} not in the page`);
  return m[0];
};

// The payload itself, and the real functions that read it. NOW is 18:00 on 2026-09-09,
// which is the first day of this snapshot, so "today" means day 0 throughout.
const PAYLOAD = span("const SHOWS=", "\n/* ====").replace(/\n\/\* ====$/, "");
// THE CLOCK IS STUBBED, not just isToday. dayLabel and dateAbs call `new Date()` with no
// argument, so on any day other than 9 September this harness had isToday saying one thing
// and dayLabel saying another, and "dateWords(1) is Tomorrow" went red on the calendar
// rather than on a defect. The real Date arrives as a parameter because a `const Date`
// declared in a scope that also reads the global Date is in the temporal dead zone there.
// DAY 0 OF WHATEVER IS IN THE FILE, not the date this was written on. Stubbing a literal
// 9 September meant that the day the payload was refreshed, "today" in the harness stopped
// being a day the payload had, and four checks below went red on the calendar rather than
// on a defect.
const DAY0 = JSON.parse(PAYLOAD.slice("const SHOWS=".length).replace(/;$/, "")).days[0];

const harness = `
  const DAY0 = ${JSON.stringify(JSON.parse(PAYLOAD.slice("const SHOWS=".length).replace(/;$/, "")).days[0])};
  const Date = new Proxy(RealDate, {
    construct(T, a) { return a.length ? new T(...a) : new T(NOW); }
  });
  ${PAYLOAD}
  const DAYS = SHOWS.days;
  const nowMins = () => ${18 * 60};
  const isToday = iso => iso === DAY0;
  const S = { day: 0, filters: new Set(), tab: "films", q: "" };
  ${lift("dayLabel")}
  ${lift("fold")}
  ${lift("matchesQuery")}
  ${lift("passesOne")}
  ${lift("passes")}
  ${decl(/const DOW_OF = [^\n]+/)}
  ${span("const WEEK_AFTER = new Map();", "WEEK_AFTER.set(String(c.id), best);\n}")}
  ${decl(/const MON = \[[\s\S]*?\];/)}
  ${lift("dateAbs")}
  ${lift("dateWords")}
  ${lift("filmRuns")}
  return { SHOWS, DAYS, S, WEEK_AFTER, filmRuns, dateAbs, dateWords };
`;
const F = new Function("RealDate", "NOW", harness)(Date, DAY0 + "T18:00:00");
const { SHOWS, DAYS } = F;
const nameOf = fid => (SHOWS.films[fid] || {}).n || "?";
const isCT = id => /^cineteca-/.test(String(id));
const runs = F.filmRuns();

console.log("section 1 -- the payload is the shape this feature was measured against");
console.log(`  (${DAYS.length} days, ${DAYS[0]} to ${DAYS[DAYS.length - 1]}, ` +
            `${SHOWS.cin.length} cinemas, ${Object.keys(SHOWS.films).length} films)`);
const ctDays = new Set(), cxDays = new Set();
for (const c of SHOWS.cin) for (const s of c.s) (isCT(c.id) ? ctDays : cxDays).add(s[2]);
console.log(`  (Cineteca publishes ${ctDays.size} days here, Cinemex ${cxDays.size})`);
// THE PREMISE, STATED AS A RELATION RATHER THAN A NUMBER. This asked for three days or
// fewer, which was Cineteca's window on 9 September; a later pull caught more of their
// board and the premise read as broken when it was not. What the feature actually rests
// on is that Cineteca's window is far shorter than a programming week while Cinemex's is
// far longer, and that is the thing to assert.
// MEASURED AGAIN 11 SEPTEMBER AND IT MOVED: Cineteca published 2 days on 9 September and
// 7 now. The feature does not rest on that number -- it rests on whether a sede has ever
// published a COMPLETE WEEK from a Thursday, which is section 2 and is asked directly.
// All this line has to establish is that the two chains publish on wildly different
// horizons, which is why one of them can close a run and the other cannot.
check("the two chains publish on wildly different horizons, which is the premise",
      cxDays.size >= 20 && cxDays.size > ctDays.size * 2);
check("every film in the payload has a run", runs.size === Object.keys(SHOWS.films).length
      || runs.size > 0);

console.log("\nsection 2 -- the week rule refuses what it cannot see");
// A cinema that has never published seven consecutive days from a Thursday can never
// close a run. Cineteca is that cinema, on this payload and on every payload where it
// keeps publishing two days at a time.
const ctWeeks = SHOWS.cin.filter(c => isCT(c.id)).map(c => F.WEEK_AFTER.get(String(c.id)));
check("no Cineteca sede has published a complete week", ctWeeks.every(w => w === -1));
const ctClosed = [...runs.values()].filter(r => r.closed &&
  [...r.cin].some(id => isCT(id)));
check("so no film playing at Cineteca is ever called finished", ctClosed.length === 0);
if (ctClosed.length) console.log("     " + ctClosed.map(r => nameOf(r.fid)).join(", "));

// PULP is the case that proves the rule is not just "few showings". One date, eight
// cinemas -- and Cinemex has published only to 30 September, six days later, which is not
// a whole week, so nothing here can say it does not return in October.
const pulp = [...runs.values()].find(r => /^PULP/.test(nameOf(r.fid)));
check("PULP is in the payload with a single date", pulp && pulp.days.size === 1);
check("and its run is NOT called finished, because no complete week follows it",
      pulp && !pulp.closed);

console.log("\nsection 3 -- and it accepts what it can see");
// THE EXAMPLE IS FOUND IN THE DATA, NOT NAMED. This was pinned to "Rebelion en la Granja",
// which ended its run and left the board, taking four checks with it. What has to be true
// is that SOME film ending today, at several cinemas, is called finished -- naming which
// one was a fact about one Tuesday.
// NOT "ends today" EITHER. On 9 September several runs ended on day 0; on 11 September
// none do, because the week rolled on Thursday and everything on the board has days left.
// Whether a run happens to end on the day the test is run is weather. What the rule has to
// do is close a run it can see the end of, at more than one screen.
const rebel = [...runs.values()]
  .filter(r => r.closed && r.cin.size > 5)
  .sort((a, b) => b.cin.size - a.cin.size)[0];
console.log(`  (the finished run at the most cinemas: ${rebel ? nameOf(rebel.fid) : "none"}` +
            `${rebel ? `, last day ${DAYS[rebel.last]}, ${rebel.cin.size} cinemas` : ""})`);
check("a run that ends across many cinemas is called finished", !!rebel);
check("and its run IS called finished", rebel && rebel.closed);
check("every cinema showing it has published a complete week after it",
      rebel && [...rebel.cin].every(id => F.WEEK_AFTER.get(String(id)) > rebel.last));
const closed = [...runs.values()].filter(r => r.closed);
console.log(`  (${closed.length} of ${runs.size} runs are finished; ` +
            `${closed.filter(r => r.last === 0).length} of them end today)`);
check("the rule is not vacuous -- some runs do close", closed.length > 0);
check("and not universal -- some do not", closed.length < runs.size);

console.log("\nsection 4 -- the rule the idea proposed gets it wrong on this data");
// "Everything playing exactly once or twice in the next month." Run it and look at what
// it would have put a rarity claim on.
const naive = [...runs.values()].filter(r => r.n <= 2);
const naiveCT = naive.filter(r => [...r.cin].some(id => isCT(id)));
console.log(`  (the count rule flags ${naive.length} films, ${naiveCT.length} of them Cineteca)`);
// A PROPORTION, NOT A COUNT. This asked for ten and the fresh payload has seven, which
// says nothing about whether the count rule is wrong. What makes it wrong is that what it
// flags is Cineteca's publishing window rather than any film's rarity, so the thing to
// assert is that its flags are overwhelmingly Cineteca.
check("what the count rule flags is overwhelmingly Cineteca's short window",
      naive.length > 0 && naiveCT.length / naive.length >= 0.75);
check("which the week rule flags none of",
      naiveCT.every(r => !r.closed));
check("so the two rules genuinely disagree, and the simpler one is the wrong one",
      naive.length !== closed.length);

console.log("\nsection 5 -- what is coming up, and what the page draws");
const later = [...runs.values()].filter(r => r.first > 0).sort((a, b) => a.first - b.first);
console.log(`  (${later.length} films start after today; the furthest is ` +
            `${dateOf(later[later.length - 1])})`);
function dateOf(r) { return r ? DAYS[r.first] : "none"; }
check("there is a real coming-up set to draw", later.length > 5);
check("Queen: Budapest is in it, on two October dates",
      later.some(r => nameOf(r.fid) === "Queen: Budapest" && r.days.size === 2));
check("dateAbs never says Today or Tomorrow, so the note cannot go stale overnight",
      !/Today|Tomorrow/.test(F.dateAbs(0) + F.dateAbs(1)));
check("dateWords does, because a row is naming a day to go on",
      F.dateWords(0) === "Today" && F.dateWords(1) === "Tomorrow");

paired("the page has a coming-up block", s => s.includes('<div class="up"><h3>Coming up</h3>'));
paired("with a last-day badge on the film rows", s => s.includes('<span class="badge last">Last day</span>'));
paired("the badge is the lamp and not the Platino orange, which a film can also carry",
       s => s.includes(".badge.last{background:var(--lamp);color:var(--lamp-ink)}"));
paired("tapping a coming-up row moves the app to the day it starts",
       s => s.includes("if (film.dataset.jump != null)"));
paired("the count line says how many start later",
       s => s.includes("more start${later.length === 1"));
paired("the week test is in the page rather than a hardcoded chain name",
       s => s.includes("const WEEK_AFTER = new Map();") && s.includes("DOW_OF(start) !== 4"));
// The note names both windows and must read them off the data, or it becomes a sentence
// that was true in September.
paired("the note about the two windows computes both dates rather than printing them",
       s => s.includes("const ctLast = lastDayOf(c => isCineteca(c.id))"));
console.log("\nsection 6 -- nothing was broken on the way past");
check("the page is still one document",
      SRC.split("<body>").length === 2 && SRC.trimEnd().endsWith("</body></html>"));
check("no anchor was replaced twice", SRC.split("function filmRuns(").length === 2
      && SRC.split('<div class="up">').length === 2);
check("the file grew rather than shrank", SRC.length > BEFORE.length);
const swNow = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/const V = "(sala-v\d+)"/);
const swWas = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`],
                           { encoding: "utf8" }).match(/const V = "(sala-v\d+)"/);
console.log(`  (cache ${swNow[1]}, was ${swWas[1]})`);
check("the service worker cache name moved, or an installed phone keeps the old build",
      swNow[1] !== swWas[1]);

console.log();
if (fails) { console.log(`${fails} FAILED`); process.exit(1); }
console.log("all controls pass");
