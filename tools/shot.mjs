#!/usr/bin/env node
// Screenshot the app the way his phone will actually render it.
//
//   node tools/shot.mjs <out.png> [--url URL] [--w 390] [--h 844] [--dsf 3]
//                       [--full] [--dark|--light] [--js "expression"] [--wait 1200]
//
// WHY THIS EXISTS RATHER THAN `chrome --screenshot`. That flag renders at the window
// size with a desktop device profile: no mobile flag, device-scale-factor 1, and on this
// Mac it laid the page out at about 498 CSS pixels while writing a 390-pixel-wide image,
// so the bottom tab bar and the right edge of every rail were cropped in the picture and
// nothing was wrong with the page. Two hours of that is two hours of chasing a bug that
// does not exist. CDP's Emulation.setDeviceMetricsOverride sets the LAYOUT viewport, which
// is the number the CSS actually responds to, and `mobile:true` is what makes
// `env(safe-area-inset-*)` and the visual viewport behave as they do on the phone.
//
// Touch is a SEPARATE call and this tool did not make it until 11 September, so
// `(pointer:coarse)` did not match and every tap-target rule in the app was inert in every
// screenshot taken here. See the comment beside the call.
//
// It launches its own headless Chrome on port 9333 with a throwaway profile. It never
// touches the automation Chrome on 9222 -- that one holds his logged-in tabs and a
// half-filled application is always one navigation away from being lost.
import { spawn } from "node:child_process";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;

const argv = process.argv.slice(2);
const out = argv.find(a => !a.startsWith("--"));
if (!out) {
  console.error("usage: node tools/shot.mjs <out.png> [--url URL] [--w N] [--h N] [--full]");
  process.exit(2);
}
const flag = (name, dflt) => {
  const i = argv.indexOf("--" + name);
  return i === -1 ? dflt : argv[i + 1];
};
const has = name => argv.includes("--" + name);

const url = flag("url", "http://127.0.0.1:8899/index.html");
const width = Number(flag("w", 390));
const height = Number(flag("h", 844));
const dsf = Number(flag("dsf", 3));
const settle = Number(flag("wait", 1400));
const js = flag("js", null);
const scheme = has("dark") ? "dark" : has("light") ? "light" : null;

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function waitForPort(deadlineMs = 20000) {
  const until = Date.now() + deadlineMs;
  while (Date.now() < until) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (r.ok) return await r.json();
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error(`headless Chrome never answered on ${PORT}`);
}

// One connection, many commands. Every send resolves on its own id so a slow screenshot
// cannot be matched to a fast Page.enable.
function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  const pending = new Map();
  const events = [];
  let id = 0;
  ws.addEventListener("message", ev => {
    const m = JSON.parse(ev.data);
    if (m.id !== undefined && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    } else if (m.method) {
      events.push(m.method);
    }
  });
  const open = new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve);
    ws.addEventListener("error", () => reject(new Error("CDP socket failed")));
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const mid = ++id;
      pending.set(mid, { resolve, reject });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
  return { ws, open, send, events };
}

const profile = await mkdtemp(join(tmpdir(), "sala-shot-"));
const chrome = spawn(CHROME, [
  "--headless=new",
  "--disable-gpu",
  // WITHOUT THIS THE MAP PANE CANNOT BE PHOTOGRAPHED AT ALL. MapLibre needs a WebGL
  // context, headless Chrome with --disable-gpu has none, and `new t.Map(...)` throws
  // "Failed to initialize WebGL" out of setTab("map") -- so a screenshot of that pane
  // came back as whatever was on screen before, with no error in the picture. This turns
  // on the software rasteriser, which is slow and correct.
  "--enable-unsafe-swiftshader",
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-extensions",
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  "about:blank",
], { stdio: "ignore", detached: false });

let code = 0;
try {
  await waitForPort();
  const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" })).json();
  const { ws, open, send } = connect(target.webSocketDebuggerUrl);
  await open;

  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", {
    width, height, deviceScaleFactor: dsf, mobile: true,
    screenWidth: width, screenHeight: height,
  });
  // AND THE TOUCH HALF, which setDeviceMetricsOverride does NOT do. The header above used
  // to claim `mobile: true` makes touch media queries behave as on the phone. It does not:
  // `matchMedia("(pointer:coarse)").matches` read FALSE with only that call, so the whole
  // `@media (pointer:coarse)` block -- every enlarged tap target in the app -- was inert in
  // every screenshot this tool has ever taken. Measured: the free-screens pill came back
  // 38 high instead of 44, the icon buttons 38 instead of 44 and the tab bar 54 instead of
  // 56, which is exactly the shape of a regression that never happened. Anyone checking a
  // tap target through this tool would have read the desktop size and believed it.
  await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await send("Emulation.setEmitTouchEventsForMouse", { enabled: true, configuration: "mobile" })
    .catch(() => {});   // not on every build; the media query comes from the call above
  if (scheme) {
    await send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-color-scheme", value: scheme }],
    });
  }

  await send("Page.navigate", { url });
  // Page.loadEventFired is not enough on its own here: the fonts arrive from Google and
  // the boot splash fades on a timer, so a screenshot taken at load shows the splash.
  await sleep(settle);
  if (js) await send("Runtime.evaluate", { expression: js, awaitPromise: true });
  if (js) await sleep(600);

  // The real layout width, so a cropped-looking picture can be told apart from a page
  // that genuinely overflows. This is the number the earlier flag-based screenshots lied
  // about, and printing it every time is what stops that mistake coming back.
  const measured = await send("Runtime.evaluate", {
    expression: "JSON.stringify({inner:innerWidth,doc:document.documentElement.scrollWidth,body:document.body.scrollWidth})",
    returnByValue: true,
  });

  const shot = await send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: has("full"),
  });
  await writeFile(out, Buffer.from(shot.data, "base64"));
  ws.close();

  const m = JSON.parse(measured.result.value);
  console.log(`${out}  viewport ${width}x${height}@${dsf}x  innerWidth ${m.inner}  scrollWidth ${m.doc}`);
  if (m.doc > m.inner) {
    console.log(`  OVERFLOW: the document is ${m.doc - m.inner}px wider than the screen`);
    code = 1;
  }
} catch (err) {
  console.error("shot failed:", err.message);
  code = 2;
} finally {
  chrome.kill("SIGTERM");
  await sleep(300);
  chrome.kill("SIGKILL");
  await rm(profile, { recursive: true, force: true });
}
process.exit(code);
