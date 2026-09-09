/* Does the service worker's shell cache actually hold the build that is published?
 *
 * Paste this into the console on https://keivanmalhani.github.io/sala-nearby/ any time
 * after a publish. It is a real control, not a restatement: on the worker that shipped
 * before 2026-09-08 15:10 it FAILS, and that failure is how the bug was found.
 *
 * The bug it guards: GitHub Pages serves index.html with `cache-control: max-age=600`,
 * so for ten minutes after a publish the browser's own HTTP cache still holds the
 * previous file. `cache.addAll(PRECACHE)` inside the install handler goes through that
 * cache, so a correctly-bumped, correctly-activated worker can faithfully cache the old
 * page -- and then delete the cache that the next load would have replaced. Bumping the
 * version does nothing about it. Every count and every name looks right.
 *
 * Expected on a good worker:
 *   shell cache            sala-vN-shell
 *   cached bytes           474607
 *   network bytes          474607
 *   cached === network     true
 *   marker in cached copy  true
 */
(async () => {
  const MARKER = "passesOne";        // change to something the newest build introduced
  const say = (k, v) => console.log(("  " + k).padEnd(26) + v);

  const regs = await navigator.serviceWorker.getRegistrations();
  if (!regs.length) {
    console.log("no service worker registered -- load the page once with a signal first");
    return;
  }
  await navigator.serviceWorker.ready;

  const names = await caches.keys();
  const shell = names.find((n) => /-shell$/.test(n));
  say("shell cache", shell || "NONE FOUND");
  if (!shell) { console.log("FAIL: nothing is precached"); return; }

  const c = await caches.open(shell);
  const hit = (await c.match("./index.html")) || (await c.match("index.html"));
  if (!hit) { console.log("FAIL: index.html is not in the shell cache"); return; }
  const cached = await hit.text();

  // The HTTP cache is exactly what the bug hides behind, so the control has to bypass it.
  const net = await (await fetch("index.html", { cache: "reload" })).text();

  say("cached bytes", cached.length);
  say("network bytes", net.length);
  const same = cached === net;
  say("cached === network", same);
  say("marker in cached copy", cached.indexOf(MARKER) >= 0);

  if (same) {
    console.log("PASS -- the installed app is serving the published build");
  } else {
    // The rendered "Showtimes read ..." line does not exist in the source -- it is built
    // at render time from SHOWS.at -- so read that field instead, which is in the file.
    const at = (s) => (s.match(/"at":"([^"]+)"/) || [])[1] || "?";
    console.log("FAIL -- the app is serving an older build");
    say("cached pull", at(cached));
    say("published pull", at(net));
    console.log("  fix: the install handler must precache with " +
                "new Request(u, {cache: 'reload'})");
  }
})();
