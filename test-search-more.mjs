// Search behavior against fixed films, independent of today's cinema listings.
//
//     node test-search-more.mjs

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

// Evaluate the page's actual search functions with data chosen to exercise every field.
const find = new Function(`
  const S = { q: "" };
  ${lift(SRC, "fold")}
  ${lift(SRC, "matchesQuery")}
  return (films, query) => {
    S.q = fold(query);
    return films.filter(f => matchesQuery(f)).map(f => f.n);
  };
`)();
const films = [
  { n: "La Odisea", o: "The Odyssey", dir: "Christopher Nolan", g: ["Drama"] },
  { n: "La Casa", o: "The House", dir: "Lucía Pérez", g: ["Terror"] },
  { n: "Señoritas", o: "Ladies", dir: "Ana Ruiz", g: ["Terror", "Misterio"] },
  // A source field cut mid-name is a missing-data limitation, not a search bug.
  { n: "Río Lejano", o: "Distant River", dir: "Direccion 1990: Benjamin ", g: ["Drama"] },
];
const names = q => find(films, q);

check("director surname finds the matching film", names("nolan").join() === "La Odisea");
check("genre finds both matching films", names("terror").join() === "La Casa,Señoritas");
check("Spanish title is searchable", names("odisea").join() === "La Odisea");
check("original title is searchable", names("odyssey").join() === "La Odisea");
check("accent folding works", names("senoritas").join() === "Señoritas");
check("surviving part of truncated director is searchable",
      names("benjamin").join() === "Río Lejano");
check("a missing surname is not invented", names("unpublishedsurname").length === 0);
check("nonsense does not match", names("zzzqqqxnotafilm").length === 0);
check("the placeholder names what search covers",
      (SRC.match(/placeholder="Movie, director, genre, cinema"/g) || []).length === 2);

console.log(fails ? `\n${fails} FAILED` : "\nall checks pass");
process.exit(fails ? 1 : 0);
