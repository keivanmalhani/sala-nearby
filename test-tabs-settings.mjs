// Movies, Showtimes, Map, Settings -- and the theme lives in Settings now.
//
//     node test-tabs-settings.mjs
//
// His words on 12 September: tabs "left to right: Movies, Showtimes, Map, Settings", and "the
// toggle in the top right of absolutely everything is annoying". Every check is paired with
// 2dc1dac, the commit before tabs-settings.py, so each one is shown able to fail. The theme
// logic runs for real in a small world, including the two ways storage can let it down.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = "2dc1dac";
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
const nav = src => {
  const m = src.match(/<nav class="tabs chrome"[\s\S]*?<\/nav>/);
  if (!m) throw new Error("no tab bar");
  return [...m[0].matchAll(/data-tab="(\w+)" aria-selected="(\w+)">[\s\S]*?<span>([^<]+)<\/span>/g)]
    .map(x => ({ tab: x[1], sel: x[2], label: x[3] }));
};

console.log("1. the tab bar, in his order");
paired("left to right it reads Movies, Showtimes, Map, Settings", src =>
  nav(src).map(t => t.label).join(",") === "Movies,Showtimes,Map,Settings"
  && nav(src).map(t => t.tab).join(",") === "films,shows,map,settings");
paired("Movies is the tab that starts selected, and its pane starts shown", src =>
  nav(src).filter(t => t.sel === "true").map(t => t.tab).join() === "films"
  && /<section class="pane on" id="pane-films"/.test(src) && /<section class="pane" id="pane-shows"/.test(src)
  && /\n  tab: "films",/.test(src));
paired("the bar is four equal columns, not three with a squeezed fourth", src =>
  /\.tabs\{display:grid;grid-template-columns:repeat\(4,1fr\)/.test(src));
paired("switching tabs shows every one of the four panes and draws Settings", src => {
  const f = lift(src, "setTab");
  return f.includes('["films", "shows", "map", "settings"]') && f.includes('if (t === "settings") renderSettings();');
});
paired("the app opens through setTab, so Movies is rendered on launch and not blank", src =>
  /renderDates\(\); renderFilters\(\); renderShows\(\);\n[\s\S]{0,160}setTab\(S\.tab\); renderSettings\(\);/.test(src));

console.log("2. the theme left the header");
paired("there is no theme button in the header and no handler for one", src =>
  !src.includes('id="themebtn"') && !src.includes('$("themebtn")'));
paired("Settings offers System, Light and Dark", src =>
  ['data-theme-set="system"', 'data-theme-set="light"', 'data-theme-set="dark"'].every(x => src.includes(x))
  && /id="pane-settings"/.test(src));

function world(src, storage) {
  const ctx = {
    document: { documentElement: { dataset: {} } },
    localStorage: storage, events: [],
    Event: class { constructor(t) { this.type = t; } },
    renderSettings: () => {},
  };
  ctx.window = { dispatchEvent: e => ctx.events.push(e.type) };
  vm.createContext(ctx);
  vm.runInContext(lift(src, "themeMode") + "\n" + lift(src, "setTheme"), ctx);
  return ctx;
}
const store = init => {
  const m = new Map(Object.entries(init || {}));
  return { getItem: k => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)),
           removeItem: k => m.delete(k), _m: m };
};
paired("Dark and Light are saved and applied, and the map is told", src => {
  const st = store(), w = world(src, st);
  w.setTheme("dark");
  const dark = w.document.documentElement.dataset.theme === "dark" && st._m.get("sala.theme") === "dark";
  w.setTheme("light");
  return dark && w.document.documentElement.dataset.theme === "light" && st._m.get("sala.theme") === "light"
      && w.events.filter(t => t === "sala:theme").length === 2;
});
paired("System clears both, so the page follows the phone again", src => {
  const st = store({ "sala.theme": "dark" }), w = world(src, st);
  w.document.documentElement.dataset.theme = "dark";
  w.setTheme("system");
  return !("theme" in w.document.documentElement.dataset) && !st._m.has("sala.theme") && w.themeMode() === "system";
});
paired("a garbage value reads as System, and a store that throws never breaks the page", src => {
  const junk = world(src, store({ "sala.theme": "sepia" }));
  const broken = world(src, { getItem() { throw new Error("private"); }, setItem() { throw new Error("no"); },
                              removeItem() { throw new Error("no"); } });
  broken.setTheme("dark");
  return junk.themeMode() === "system" && broken.themeMode() === "system"
      && broken.document.documentElement.dataset.theme === "dark";
});

console.log("3. where distances are measured from, in Settings too");
paired("the origin choice only presses the location button when it would change something", src =>
  /closest\("#originseg \[data-origin\]"\)[\s\S]{0,120}\(og\.dataset\.origin === "here"\) !== liveLoc\) \$\("locbtn"\)\.click\(\)/.test(src));
paired("every way the location button can end tells Settings, including a refusal", src => {
  const at = src.indexOf('$("locbtn").addEventListener("click", () => {');
  let depth = 0, j = src.indexOf("{", at);
  for (; j < src.length; j++) { if (src[j] === "{") depth++; else if (src[j] === "}" && --depth === 0) break; }
  return (src.slice(at, j).match(/dispatchEvent\(new Event\("sala:origin"\)\)/g) || []).length === 3
      && src.includes('window.addEventListener("sala:origin", renderSettings);');
});

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
