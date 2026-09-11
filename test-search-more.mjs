// Does the search box find a film by its director, and does that claim survive the data?
//
//     node test-search-more.mjs
//
// The idea this came from warned that the two-line version of it -- add `dir` to the
// query -- would ship looking fixed and still return nothing for the most famous director
// playing in the city, because Cinemex published "Christopher Nola" with the n missing.
// So the test that matters is not "matchesQuery reads f.dir". It is: type the name a
// person would type, against the real payload, and require the film back.
//
// Section 4 is the honest half. One director field in this payload is truncated mid-word
// by Cinemex and nothing here repairs it, so the test asserts the miss rather than
// pretending it does not exist. A guard that only records the wins is how a known hole
// turns into a surprise later.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");

// A FIXED COMMIT, never HEAD: the one immediately before this change.
const BASELINE = "4d4c69c";
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

/** The real payload and the real matchesQuery, from whichever build is handed in. */
function boxOf(src) {
  const payload = span(src, "const SHOWS=", "\n/* ====").replace(/\n\/\* ====$/, "");
  return new Function(`
    ${payload}
    const S = { q: "" };
    ${lift(src, "fold")}
    ${lift(src, "matchesQuery")}
    return function find(q) {
      S.q = fold(q);
      return Object.entries(SHOWS.films).filter(([, f]) => matchesQuery(f)).map(([, f]) => f.n);
    };
  `)();
}
const now = boxOf(SRC), was = boxOf(BEFORE);

console.log("section 1 -- the search a person would actually type");
const nolanNow = now("nolan"), nolanWas = was("nolan");
console.log(`  ("nolan": ${nolanNow.length} now, ${nolanWas.length} at ${BASELINE})`);
check("typing a director's surname finds his film", nolanNow.length >= 1, nolanNow.join(", "));
check(`   ... and found nothing at ${BASELINE}, so this check can fail`, nolanWas.length === 0);
check("the film it finds is the one playing at twenty-five cinemas",
      nolanNow.some(n => /odisea/i.test(n)));

console.log("\nsection 2 -- the genre, because the payload is in Spanish and the chips are not");
const terror = now("terror");
check("typing a genre finds the films in it", terror.length >= 2, `${terror.length} films`);
check(`   ... and found nothing at ${BASELINE}`, was("terror").length === 0);

console.log("\nsection 3 -- and it did not become a box that matches everything");
check("a title still finds its film", now("odisea").length >= 1);
check("an original title still finds its film", now("odyssey").length >= 1);
check("nonsense finds nothing", now("zzzqqqxnotafilm").length === 0);
check("a one-letter query does not silently return the whole board",
      now("zzz").length === 0);

console.log("\nsection 4 -- the hole that is left, stated rather than hidden");
// Cinemex truncates this one mid-word: "Direccion 1990: Benjamin ". The first name is
// searchable and the surname is not, because the surname is not in the data anywhere.
const benjamin = now("benjamin");
check("the truncated director is findable by the part that survived",
      benjamin.length >= 1, benjamin.join(", "));
const raw = span(SRC, "const SHOWS=", "\n/* ====");
check("and the page still carries the truncation rather than a name nobody read",
      /Direcci[^"]*1990: Benjam[^"]*\s"/.test(raw));

console.log("\nsection 5 -- the box says what it searches");
check("the placeholder names the three fields",
      (SRC.match(/placeholder="Film, director, genre"/g) || []).length === 2);
check(`   ... and said only "Find a film" at ${BASELINE}`,
      (BEFORE.match(/placeholder="Find a film"/g) || []).length === 2);

console.log(fails ? `\n${fails} FAILED` : "\nall checks pass");
process.exit(fails ? 1 : 0);
