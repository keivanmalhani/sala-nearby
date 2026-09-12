// The Spanish/English switch in Settings.
//
//     node test-language.mjs
//
// His words, 12 September: "do a Spanish slash English like language switch in the settings
// themselves". What makes this worth testing rather than eyeballing is that it is a
// translation LAYER over the rendered DOM, not a rewrite of each render function -- so the
// ways it can go wrong are not "a string is missing" but "it translated something it should
// never have touched". A film called "Map", a cinema called "Now", a synopsis containing the
// word "cinema": each of those is a real title in a real catalogue somewhere, and each would
// be a visible bug on his phone rather than an error anyone would see in a log.
//
// So the checks below are aimed at the boundaries, not at coverage of the dictionary:
//   1. the switch exists, is wired, and is in Settings where he asked for it
//   2. English is a no-op -- not "translates back correctly", but never runs at all
//   3. whole-string matching only, so source data (films, cinemas, people) cannot be hit
//   4. the patterns are anchored, which is what keeps them off prose
//   5. English comes back -- including the chrome no render function owns
//   6. the observer cannot loop, and idles entirely in English
//   7. the offline cache name moved, or an installed phone keeps serving the old page
//
// Every check is paired with 57f7797, the commit before the switch was written, so each one
// is shown able to fail rather than assumed to.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = "57f7797";   // the last commit before the language switch
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
// The dictionary and the pattern table are const declarations, not functions, so lift() by
// brace-matching from the opening bracket instead.
function liftConst(src, name, open, close) {
  const at = src.indexOf(`const ${name} = ${open}`);
  if (at === -1) throw new Error(`const ${name} is not in the page`);
  let depth = 0;
  for (let j = src.indexOf(open, at); j < src.length; j++) {
    if (src[j] === open) depth++;
    else if (src[j] === close && --depth === 0) return src.slice(at, j + 1) + ";";
  }
  throw new Error(`unbalanced ${name}`);
}

const store = init => {
  const m = new Map(Object.entries(init || {}));
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)),
           removeItem: k => m.delete(k), _m: m };
};

// A small world holding just the translation half: the dictionary, the patterns and the
// three pure functions over them. No DOM -- sections 2 and 3 are about what the functions
// decide, and a DOM would only add ways for the test itself to be wrong.
function transWorld(src, storage, navLang) {
  const ctx = { localStorage: storage, navigator: { language: navLang || "en-US" } };
  vm.createContext(ctx);
  vm.runInContext([
    lift(src, "langPref"),
    liftConst(src, "DICT_ES", "{", "}"),
    "const REVERSE_ES = {}; for (const k in DICT_ES) if (!(DICT_ES[k] in REVERSE_ES)) REVERSE_ES[DICT_ES[k]] = k;",
    lift(src, "dictTranslate"),
    liftConst(src, "PATTERNS", "[", "]"),
    lift(src, "patternTranslate"),
    lift(src, "translateOne"),
    // `const` at the top level of a vm script stays in the script's own lexical scope and
    // never becomes a property of the context, so the tables have to be handed out
    // explicitly or every assertion about them reads undefined.
    "this.DICT_ES = DICT_ES; this.PATTERNS = PATTERNS; this.REVERSE_ES = REVERSE_ES;",
  ].join("\n"), ctx);
  return ctx;
}

console.log("1. the switch is in Settings, and wired");
paired("Settings offers English and Espanol as a radio group", src =>
  /id="langseg"/.test(src)
  && src.includes('data-lang-set="en"') && src.includes('data-lang-set="es"')
  && /<div class="seg" role="radiogroup" aria-label="Language" id="langseg">/.test(src));
paired("the language group sits inside the Settings pane, not the header", src => {
  const pane = src.indexOf('id="pane-settings"');
  const seg = src.indexOf('id="langseg"');
  return pane !== -1 && seg > pane && !/id="langbtn"/.test(src);
});
paired("clicking either button calls setLang, the same way the theme buttons work", src =>
  /closest\("#langseg \[data-lang-set\]"\)[\s\S]{0,80}setLang\(lg\.dataset\.langSet\)/.test(src));
paired("renderSettings ticks the button that matches the saved language", src => {
  const f = lift(src, "renderSettings");
  return f.includes('#langseg [data-lang-set]') && f.includes('b.dataset.langSet === lang');
});
paired("the page declares its own language on boot, so a screen reader gets it right", src =>
  /document\.documentElement\.lang = langPref\(\) === "es" \? "es" : "en";/.test(src));

console.log("\n2. English is a no-op, not a translation back");
paired("in English, neither the dictionary nor the patterns translate anything", src => {
  const w = transWorld(src, store({ "sala.lang": "en" }));
  // Every key and every pattern subject must come back null -- not "unchanged", null,
  // meaning the caller never writes to the node at all.
  const keys = Object.keys(w.DICT_ES);
  const untouched = keys.every(k => w.patternTranslate(k) === null);
  return w.langPref() === "en"
      && untouched
      && w.patternTranslate("12 min walk") === null
      && w.dictTranslate("Movies") === null;
});
paired("in Spanish the same calls do translate, so the no-op above is a real branch", src => {
  const w = transWorld(src, store({ "sala.lang": "es" }));
  return w.langPref() === "es"
      && w.dictTranslate("Movies") === "Películas"
      && w.patternTranslate("12 min walk") === "12 min caminando";
});
paired("going back to English re-renders rather than un-translating", src => {
  const f = lift(src, "setLang");
  // The comment explains why; this asserts the code actually does it, because an
  // un-translate of a sentence with numbers in it is where this design would break.
  return /renderDates\(\); renderFilters\(\); renderShows\(\);/.test(f)
      && f.includes("renderSettings();") && f.includes("translateApp();");
});

console.log("\n3. source data cannot be translated by accident");
paired("the dictionary matches whole strings only, so a film named after a chip is safe", src => {
  const w = transWorld(src, store({ "sala.lang": "es" }));
  // "Map" and "Now" are dictionary keys AND plausible titles. As substrings inside a longer
  // title they must not match; only the exact string may. That whole-string rule is the
  // entire defence for source data, so it is asserted from both directions.
  return w.dictTranslate("Map") === "Mapa"
      && w.dictTranslate("Map of the Human Heart") === null
      && w.dictTranslate("Cinema Paradiso") === null
      && w.dictTranslate("The Settings") === null
      && w.dictTranslate("Settings ") === null;   // trailing space is a different string
});
paired("a synopsis mentioning cinemas and films is left alone by the patterns", src => {
  const w = transWorld(src, store({ "sala.lang": "es" }));
  const prose = "A projectionist in a small cinema teaches a boy about films, 3 min walk from home.";
  return w.translateOne(prose) === null;
});
paired("every pattern is anchored at both ends", src => {
  const w = transWorld(src, store({ "sala.lang": "es" }));
  return w.PATTERNS.length > 0
      && w.PATTERNS.every(([re]) => re.source.startsWith("^") && re.source.endsWith("$"));
});
paired("a real composed line still translates, so the anchoring did not kill the feature", src => {
  const w = transWorld(src, store({ "sala.lang": "es" }));
  return w.translateOne("3 cinemas, nearest first") === "3 cines, el más cercano primero"
      && w.translateOne("1 cinema, nearest first") === "1 cine, el más cercano primero";
});

console.log("\n4. the preference survives a hostile browser");
paired("a garbage saved value falls back to the phone's own language", src => {
  const junkEs = transWorld(src, store({ "sala.lang": "sepia" }), "es-MX");
  const junkEn = transWorld(src, store({ "sala.lang": "sepia" }), "en-GB");
  return junkEs.langPref() === "es" && junkEn.langPref() === "en";
});
paired("a localStorage that throws still gives a language rather than breaking", src => {
  const broken = transWorld(src,
    { getItem() { throw new Error("private mode"); }, setItem() { throw new Error("no"); },
      removeItem() { throw new Error("no"); } }, "es-419");
  return broken.langPref() === "es";
});
paired("with nothing saved, a Spanish phone opens in Spanish and an English one in English", src => {
  return transWorld(src, store(), "es-MX").langPref() === "es"
      && transWorld(src, store(), "en-US").langPref() === "en"
      && transWorld(src, store(), "").langPref() === "en";
});

console.log("\n5. English comes back, including the parts no render function owns");
// The bug this catches, found by driving the real page rather than here: the tab labels,
// the Settings headings, the search placeholder and nineteen aria-labels are written once
// in the markup, so setLang's re-render never restores them. After Spanish then English the
// tabs still read Películas, Horarios, Mapa, Ajustes. These assertions are source-level
// because the repo has no DOM harness -- they check the mechanism is wired at all three
// points, each of which was absent when the bug existed.
paired("what a node said in English is remembered before it is first translated", src => {
  const f = lift(src, "translateNode");
  return f.includes("rememberText(n, raw)") && f.includes("rememberAttr(el, a, v)")
      && /const _origText = new WeakMap\(\)/.test(src) && /const _origAttr = new WeakMap\(\)/.test(src);
});
paired("the original is only recorded once, so a second pass cannot overwrite it", src => {
  const t = lift(src, "rememberText"), a = lift(src, "rememberAttr");
  return t.includes("if (!_origText.has(n))") && a.includes("if (!(a in m))");
});
paired("going back to English replays what was remembered, for text and attributes", src => {
  const f = lift(src, "restoreEnglish");
  return f.includes("_origText.has(n)") && f.includes("n.nodeValue = _origText.get(n)")
      && f.includes("_origAttr.get(el)") && f.includes("el.setAttribute(a, m[a])");
});
paired("setLang actually calls it, and only when leaving Spanish", src =>
  /if \(v !== "es"\) restoreEnglish\(document\.body\);/.test(lift(src, "setLang")));
paired("English is a hard no-op in the dictionary, not a reverse lookup", src => {
  const f = lift(src, "dictTranslate");
  // The reverse pass would rewrite any node whose text equals a Spanish word in the table.
  // Film and format names arrive from Cinemex in Spanish and refresh daily, so this must
  // return before consulting anything.
  return /if \(langPref\(\) !== "es"\) return null;/.test(f) && !f.includes("REVERSE_ES");
});

console.log("\n6. the observer cannot loop, and idles in English");
paired("translateApp raises a guard the observer checks before re-entering", src => {
  const f = lift(src, "translateApp");
  return /_translating = true/.test(f) && /finally \{ _translating = false; \}/.test(f)
      && /new MutationObserver\(\(\) => \{ if \(!_translating\) translateApp\(\); \}\)/.test(src);
});
paired("the guard is released even if a translation throws", src =>
  /try \{ translateNode\(document\.body\); \} finally \{ _translating = false; \}/.test(lift(src, "translateApp")));
paired("the observer is only connected while Spanish is on", src => {
  const f = lift(src, "observeLang");
  return f.includes("_langObserver.disconnect()") && f.includes('if (langPref() === "es")')
      && lift(src, "setLang").includes("observeLang();");
});

console.log("\n7. an installed phone will actually take this");
const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`],
                              { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so his installed app takes the new page",
      +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
