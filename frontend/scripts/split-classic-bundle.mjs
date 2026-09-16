#!/usr/bin/env node
/**
 * Split the single IIFE bundle into transport-safe text parts and inject a
 * classic loader. This avoids ESM, blob URLs, import maps, and Service Workers.
 */
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const assets = path.join(dist, "assets");
const htmlPath = path.join(dist, "index.html");
const bundleName = "app.js";
const bundlePath = path.join(assets, bundleName);
const maxRawBytes = 16 * 1024;

function gzipSize(buffer) {
  return zlib.gzipSync(buffer, { level: 9 }).length;
}

function writeWithGzip(filePath, content) {
  const buffer = Buffer.from(content, "utf8");
  fs.writeFileSync(filePath, buffer);
  fs.writeFileSync(filePath + ".gz", zlib.gzipSync(buffer, { level: 9 }));
  return buffer;
}

if (!fs.existsSync(bundlePath)) {
  throw new Error(`Missing classic bundle: ${bundlePath}`);
}

const code = fs.readFileSync(bundlePath, "utf8");
const parts = [];
let offset = 0;

while (offset < code.length) {
  let end = Math.min(offset + 14_000, code.length);
  let part = code.slice(offset, end);
  while (Buffer.byteLength(part, "utf8") > maxRawBytes) {
    end -= 1_000;
    part = code.slice(offset, end);
  }
  parts.push(part);
  offset = end;
}

const partNames = parts.map((_, index) => `${bundleName}.p${index}`);
for (let index = 0; index < parts.length; index += 1) {
  const buffer = writeWithGzip(path.join(assets, partNames[index]), parts[index]);
  if (buffer.length > maxRawBytes) {
    throw new Error(`Part ${index} is too large: ${buffer.length}`);
  }
  console.log(
    `${partNames[index]} raw=${buffer.length} gzip=${gzipSize(buffer)}`,
  );
}

// Never expose the large file directly to the throttled route.
writeWithGzip(
  bundlePath,
  'throw new Error("Use the classic multipart loader");\n',
);

let html = fs.readFileSync(htmlPath, "utf8");
html = html.replace(
  /<script type="module" src="[^"]*\/assets\/app\.js"><\/script>\s*/g,
  "",
);
html = html.replace(/\s*<link rel="modulepreload"[^>]*>/g, "");

const publicPath = (process.env.VITE_BASE_PATH || process.env.PUBLIC_PATH || "/33642f34/").replace(/\/?$/, "/");
const builtAssetBase = `${publicPath}assets/`;
const loader = `
<!--espanol-classic-loader-->
<script>
(function () {
  window.__espanolLoaderActive = true;
  var BUILT_BASE = ${JSON.stringify(builtAssetBase)};
  var CACHE_KEY = "es_classic_bundle_v6";
  var PART_CACHE_PREFIX = "es_classic_part_v6_";
  var PARTS = ${JSON.stringify(partNames)};
  var bootedOk = false;
  var executed = false;
  function assetBases() {
    var bases = [];
    var path = location.pathname || "/";
    var dir = path.endsWith("/") ? path : path.replace(/\\/[^/]*$/, "/");
    if (!dir) dir = "/";
    try { bases.push(new URL("assets/", location.origin + dir).href); } catch (error) {}
    bases.push(location.origin + "/assets/");
    bases.push(location.origin + BUILT_BASE);
    var unique = [];
    for (var i = 0; i < bases.length; i += 1) {
      var base = bases[i];
      if (base && unique.indexOf(base) === -1) unique.push(base);
    }
    return unique;
  }
  function looksLikePart(text) {
    if (!text || text.length < 16) return false;
    var head = text.slice(0, 80).toLowerCase();
    if (head.indexOf("<!doctype") !== -1 || head.indexOf("<html") !== -1) return false;
    return true;
  }
  function looksLikeBundle(code) {
    return looksLikePart(code) && code.indexOf("createRoot") !== -1;
  }
  function clearCaches() {
    try {
      sessionStorage.removeItem(CACHE_KEY);
      for (var i = sessionStorage.length - 1; i >= 0; i -= 1) {
        var k = sessionStorage.key(i);
        if (k && k.indexOf("es_classic_") === 0) sessionStorage.removeItem(k);
      }
    } catch (error) {}
  }
  function fail(error) {
    var root = document.getElementById("root");
    if (!root) return;
    root.innerHTML =
      '<div style="min-height:100dvh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:24px;text-align:center;font-family:system-ui;background:#f8fafc">' +
      '<div style="font-size:2.5rem">⚠️</div>' +
      '<p style="font-weight:800;color:#0f766e;font-size:18px">Ошибка загрузки</p>' +
      '<p style="font-size:13px;color:#64748b;max-width:300px">' +
      String(error && error.message ? error.message : error).replace(/[<>]/g, "") +
      '</p><button onclick="location.reload()" style="margin-top:8px;padding:12px 20px;border:0;border-radius:12px;background:#0f766e;color:#fff;font-weight:800">Обновить</button></div>';
  }
  async function getPart(name) {
    try {
      var saved = sessionStorage.getItem(PART_CACHE_PREFIX + name);
      if (looksLikePart(saved)) return saved;
    } catch (error) {}
    var lastError;
    var bases = assetBases();
    for (var b = 0; b < bases.length; b += 1) {
      for (var attempt = 0; attempt < 3; attempt += 1) {
        var controller = new AbortController();
        var timer = setTimeout(function () { controller.abort(); }, 12000);
        try {
          var response = await fetch(bases[b] + name + "?v=classic6&a=" + attempt, {
            cache: "no-store",
            signal: controller.signal
          });
          if (!response.ok) throw new Error("HTTP " + response.status);
          var text = await response.text();
          clearTimeout(timer);
          if (!looksLikePart(text)) throw new Error("not js " + name);
          try {
            sessionStorage.setItem(PART_CACHE_PREFIX + name, text);
          } catch (error) {}
          return text;
        } catch (error) {
          clearTimeout(timer);
          lastError = error;
        }
      }
    }
    throw lastError || new Error("part failed " + name);
  }
  function execute(code) {
    if (!looksLikeBundle(code)) throw new Error("invalid bundle");
    executed = true;
    var script = document.createElement("script");
    script.text = code;
    document.head.appendChild(script);
  }
  (async function () {
    try {
      var root = document.getElementById("root");
      if (root) root.setAttribute("data-app-booted", "1");
      window.addEventListener("error", function (event) {
        fetch(
          BUILT_BASE.replace(/assets\\/$/, "") + "api/health?stage=classic-error&message=" +
            encodeURIComponent(String(event.message || "unknown").slice(0, 120)),
          { cache: "no-store" }
        ).catch(function () {});
      });
      if ("serviceWorker" in navigator) {
        try {
          var registrations = await navigator.serviceWorker.getRegistrations();
          await Promise.all(registrations.map(function (reg) {
            return reg.unregister();
          }));
        } catch (error) {}
      }
      var started = Date.now();
      var watchdog = setInterval(function () {
        if (bootedOk) {
          clearInterval(watchdog);
          return;
        }
        if (document.documentElement.getAttribute("data-espanol-ready") === "1") {
          bootedOk = true;
          clearInterval(watchdog);
          return;
        }
        var elapsed = Date.now() - started;
        if (executed && elapsed < 45000) return;
        if (!executed && elapsed < 60000) return;
        clearInterval(watchdog);
        clearCaches();
        fail("Stuck loading — cleared cache. Tap refresh.");
      }, 1000);
      try {
        var cached = sessionStorage.getItem(CACHE_KEY);
        if (looksLikeBundle(cached) && cached.length > 1000) {
          execute(cached);
          return;
        }
      } catch (error) {}
      var texts = new Array(PARTS.length);
      var nextPart = 0;
      async function worker() {
        while (nextPart < PARTS.length) {
          var index = nextPart++;
          texts[index] = await getPart(PARTS[index]);
        }
      }
      await Promise.all([worker(), worker(), worker()]);
      var code = texts.join("");
      try {
        sessionStorage.setItem(CACHE_KEY, code);
      } catch (error) {}
      execute(code);
    } catch (error) {
      console.error(error);
      clearCaches();
      fail(error);
    }
  })();
})();
</script>
<!--/espanol-classic-loader-->`.trim();

html = html.replace(
  /<!--espanol-boot-->[\s\S]*?<!--\/espanol-boot-->\s*/g,
  "",
);
html = html.replace(
  /<!--espanol-classic-loader-->[\s\S]*?<!--\/espanol-classic-loader-->\s*/g,
  "",
);
html = html.replace("</head>", `${loader}\n</head>`);
fs.writeFileSync(htmlPath, html);

// Remove obsolete worker so future requests cannot reinstall it.
for (const name of ["sw-espanol.js", "sw-espanol.js.gz"]) {
  const filePath = path.join(dist, name);
  if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
}

console.log(`Classic loader injected with ${parts.length} parts.`);
