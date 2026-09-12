// Does a pull actually get newer listings on screen, and say something true when it cannot?
//
//     node test-pull-refresh.mjs
//
// refreshNow() runs for real against a fake network, a fake service worker and a fake cache,
// including the case that matters most: newer showtimes must be written into the shell cache
// BEFORE the reload, because the worker answers a navigation from that cache first. Page
// checks are paired with the commit that added search-suggest.py, the one before this.

import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(ROOT, "docs", "index.html"), "utf8");
const BASELINE = execFileSync("git", ["-C", ROOT, "log", "-1", "--format=%h", "--", "search-suggest.py"], { encoding: "utf8" }).trim();
const BEFORE = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/index.html`],
                            { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });

let fails = 0;
const check = (name, ok) => { console.log(`  ${ok ? "ok  " : "FAIL"} ${name}`); if (!ok) fails++; };
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
async function pairedAsync(name, fn) {
  let now, then;
  try { now = !!(await fn(SRC)); } catch (e) { now = false; console.log(`       (${e.message})`); }
  try { then = !!(await fn(BEFORE)); } catch { then = false; }
  check(name, now);
  check(`   ... and not true at ${BASELINE}, so the check can fail`, !then);
}

const AT = "2026-09-11T15:49";
const page = at => `<html><script>const SHOWS={"at":"${at}","films":{}};</script></html>`;
function world(src, network) {
  const log = { said: [], reloads: 0, puts: [], order: [], swListeners: [], updated: 0 };
  const ctx = {
    SHOWS: { at: AT }, String, RegExp, Promise, Date, Error,
    location: { reload: () => { log.reloads++; log.order.push("reload"); } },
    navigator: { serviceWorker: {
      addEventListener: (t, cb) => log.swListeners.push([t, cb]),
      getRegistration: async () => ({ update: () => { log.updated++; } }),
    } },
    fetch: async (url, opts) => { log.url = url; log.opts = opts; return network(); },
    caches: {
      keys: async () => ["sala-v37-shell", "sala-v37-lib", "sala-v37-posters"],
      open: async name => ({ put: async (key, resp) => { log.puts.push([name, key, await resp.text()]); log.order.push("put"); } }),
    },
    Response: class { constructor(body) { this.b = body; } async text() { return this.b; } },
  };
  vm.createContext(ctx);
  vm.runInContext(lift(src, "stampOf") + "\n" + lift(src, "refreshNow"), ctx);
  return { ctx, log, run: () => ctx.refreshNow(m => log.said.push(m)) };
}
const ok = body => async () => ({ ok: true, status: 200, text: async () => body });

console.log("1. what a pull does");
await pairedAsync("newer showtimes are written into the shell cache, and only then the page reloads", async src => {
  const w = world(src, ok(page("2026-09-12T08:00")));
  await w.run();
  return w.log.said[0] === "New showtimes, loading" && w.log.reloads === 1
      && w.log.puts.length === 1 && w.log.puts[0][0] === "sala-v37-shell" && w.log.puts[0][1] === "./index.html"
      && w.log.puts[0][2].includes("2026-09-12T08:00") && w.log.order.join(",") === "put,reload";
});
await pairedAsync("the fresh fetch carries a query string and no-store, so no cache answers it", async src => {
  const w = world(src, ok(page(AT)));
  await w.run();
  return /^index\.html\?fresh=\d+$/.test(w.log.url) && w.log.opts && w.log.opts.cache === "no-store";
});
await pairedAsync("the same showtimes say Up to date with when they were read, and nothing reloads", async src => {
  const w = world(src, ok(page(AT)));
  await w.run();
  return w.log.said.join("|") === "Up to date · read 2026-09-11 15:49" && w.log.reloads === 0 && w.log.puts.length === 0;
});
await pairedAsync("no signal, or a server error, says so and changes nothing", async src => {
  const a = world(src, async () => { throw new TypeError("Failed to fetch"); });
  const b = world(src, async () => ({ ok: false, status: 503, text: async () => "" }));
  await a.run(); await b.run();
  return [a, b].every(w => w.log.said.join("|") === "No signal · listings read 2026-09-11 15:49" && w.log.reloads === 0);
});
await pairedAsync("a new build found by the service worker reloads the page, once", async src => {
  const w = world(src, ok(page("2026-09-12T08:00")));
  const p = w.run();
  const change = w.log.swListeners.find(([t]) => t === "controllerchange");
  if (change) change[1]();
  await p;
  return !!change && w.log.updated === 1 && w.log.reloads === 1;
});

console.log("2. the gesture");
check("both lists get it and the map does not",
      SRC.includes('["pane-films", "pane-shows"].forEach(id =>') && !/\["pane-films", "pane-shows", "pane-map"/.test(SRC));
check("   ... and there was no gesture at the baseline", !BEFORE.includes("function refreshNow("));
check("the pull can hold the page still: touchmove is not passive",
      /addEventListener\("touchmove", e => \{[\s\S]{0,400}e\.preventDefault\(\);[\s\S]{0,300}\}, \{ passive: false \}\)/.test(SRC));
check("it only starts from the very top of a list", SRC.includes("if (!busy && pane.scrollTop <= 0 && e.touches.length === 1)"));
check("the indicator has its styles", SRC.includes(".ptr{height:0;overflow:hidden;") && SRC.includes(".ptr.drag{transition:none}"));

const sw = readFileSync(join(ROOT, "docs", "sw.js"), "utf8").match(/sala-v(\d+)/);
const swBefore = execFileSync("git", ["-C", ROOT, "show", `${BASELINE}:docs/sw.js`], { encoding: "utf8" }).match(/sala-v(\d+)/);
check("the offline cache name moved on, so an installed phone takes the new page", +sw[1] > +swBefore[1]);

console.log(fails ? `\n${fails} FAILED` : "\nall passed");
process.exit(fails ? 1 : 0);
