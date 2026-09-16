#!/usr/bin/env node
/**
 * Rostelecom truncates near 56KiB. Large JS chunks are split into .pN parts.
 * A Service Worker (sw-espanol.js) concatenates parts on the device and serves
 * the original asset URLs — works on Safari (no blob:/importmap).
 */
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const MAX_RAW = 48 * 1024;
const MAX_GZIP = 45 * 1024;
const PART_RAW = 45_000;
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const assetsDir = path.join(root, "dist/assets");
const distDir = path.join(root, "dist");
const indexHtmlPath = path.join(distDir, "index.html");

function gzipSize(buf) {
  return zlib.gzipSync(buf, { level: 9 }).length;
}

function writeGz(filePath, buf) {
  fs.writeFileSync(filePath, buf);
  fs.writeFileSync(filePath + ".gz", zlib.gzipSync(buf, { level: 9 }));
}

function splitRaw(code) {
  const parts = [];
  let i = 0;
  while (i < code.length) {
    let end = Math.min(i + PART_RAW, code.length);
    if (end < code.length) {
      const nl = code.lastIndexOf("\n", end);
      if (nl > i + Math.floor(PART_RAW / 3)) end = nl + 1;
    }
    parts.push(code.slice(i, end));
    i = end;
  }
  const tooBig = parts.some((p) => {
    const buf = Buffer.from(p);
    return buf.length > MAX_RAW || gzipSize(buf) > MAX_GZIP;
  });
  if (!tooBig) return parts;
  const finer = Math.floor(PART_RAW / 2);
  const out = [];
  i = 0;
  while (i < code.length) {
    let end = Math.min(i + finer, code.length);
    if (end < code.length) {
      const nl = code.lastIndexOf("\n", end);
      if (nl > i + Math.floor(finer / 3)) end = nl + 1;
    }
    out.push(code.slice(i, end));
    i = end;
  }
  return out;
}

function detectBase(html) {
  const m = html.match(/(?:src|href)="(\/[^"]+)\/assets\/[^"]+"/);
  if (m) return m[1].replace(/\/$/, "") + "/";
  return "/";
}

function detectEntry(html) {
  const m = html.match(/src="([^"]*\/assets\/index-[^"]+\.js)"/);
  if (!m) throw new Error("Could not find entry script in index.html");
  return path.basename(m[1]);
}

if (!fs.existsSync(assetsDir)) {
  console.error("No assets dir:", assetsDir);
  process.exit(1);
}

const splits = {}; // name -> partCount

for (const name of fs.readdirSync(assetsDir)) {
  if (!name.endsWith(".js") || name.includes(".p")) continue;
  const full = path.join(assetsDir, name);
  const raw = fs.readFileSync(full);
  const gz = gzipSize(raw);
  if (raw.length <= MAX_RAW && gz <= MAX_GZIP) continue;

  const code = raw.toString("utf8");
  fs.writeFileSync(full + ".full", raw);

  const parts = splitRaw(code);
  for (let i = 0; i < parts.length; i++) {
    const buf = Buffer.from(parts[i], "utf8");
    const g = gzipSize(buf);
    writeGz(path.join(assetsDir, `${name}.p${i}`), buf);
    console.log(`  part ${name}.p${i} raw=${buf.length} gzip=${g}`);
    if (buf.length > MAX_RAW || g > MAX_GZIP) {
      console.error(`Part still too large: ${name}.p${i}`);
      process.exit(1);
    }
  }

  writeGz(
    full,
    Buffer.from(`throw new Error("Split chunk ${name}: service worker required");\n`, "utf8"),
  );
  splits[name] = parts.length;
  console.log(`split ${name}: raw=${raw.length} gzip=${gz} parts=${parts.length}`);
}

let html = fs.readFileSync(indexHtmlPath, "utf8");
const base = detectBase(html);
const entry = detectEntry(html);
const prefix = base.replace(/\/?$/, "/"); // /33642f34/
const assetsBase = prefix + "assets/";

if (!Object.keys(splits).length) {
  console.log("No large chunks to split.");
  process.exit(0);
}

const partsMap = {};
for (const [name, n] of Object.entries(splits)) {
  const key = assetsBase + name;
  partsMap[key] = Array.from({ length: n }, (_, i) => assetsBase + name + ".p" + i);
}

const sw = `/* Auto-generated: assemble large JS from .pN parts */
const PARTS = ${JSON.stringify(partsMap, null, 2)};

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const parts = PARTS[url.pathname];
  if (!parts) return;

  event.respondWith(
    (async () => {
      const texts = await Promise.all(
        parts.map(async (p, i) => {
          let lastErr;
          for (let a = 0; a < 4; a++) {
            try {
              const r = await fetch(p + "?a=" + a, { cache: "no-store" });
              if (!r.ok) throw new Error("HTTP " + r.status);
              const t = await r.text();
              if (t.length < 16) throw new Error("short");
              return t;
            } catch (e) {
              lastErr = e;
            }
          }
          throw lastErr || new Error("part fail " + i);
        }),
      );
      return new Response(texts.join(""), {
        headers: {
          "Content-Type": "text/javascript; charset=utf-8",
          "Cache-Control": "no-store",
        },
      });
    })(),
  );
});
`;

fs.writeFileSync(path.join(distDir, "sw-espanol.js"), sw);
writeGz(path.join(distDir, "sw-espanol.js"), Buffer.from(sw));

const boot = `
<script>
(async function () {
  var ENTRY = ${JSON.stringify(assetsBase + entry)};
  var SW_URL = ${JSON.stringify(prefix + "sw-espanol.js")};
  var SCOPE = ${JSON.stringify(prefix)};
  function showErr(msg) {
    var root = document.getElementById("root");
    if (!root) return;
    root.innerHTML = '<div style="min-height:100dvh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:24px;text-align:center;font-family:system-ui;background:#f8fafc"><div style="font-size:2.5rem">⚠️</div><p style="font-weight:800;color:#0f766e;font-size:18px">Ошибка загрузки</p><p style="font-size:13px;color:#64748b;max-width:300px">' +
      String(msg).replace(/[<>]/g, "") +
      '</p><button onclick="location.reload()" style="margin-top:8px;padding:12px 20px;border:0;border-radius:12px;background:#0f766e;color:#fff;font-weight:800">Обновить</button></div>';
  }
  function loadEntry() {
    var s = document.createElement("script");
    s.type = "module";
    s.src = ENTRY + "?v=sw1";
    s.onerror = function () { showErr("Не удалось запустить приложение"); };
    document.head.appendChild(s);
  }
  try {
    if (!("serviceWorker" in navigator)) {
      showErr("Нужен Safari / Chrome поновее");
      return;
    }
    var reg = await navigator.serviceWorker.register(SW_URL, { scope: SCOPE });
    await navigator.serviceWorker.ready;
    if (navigator.serviceWorker.controller) {
      loadEntry();
    } else {
      navigator.serviceWorker.addEventListener("controllerchange", function once() {
        navigator.serviceWorker.removeEventListener("controllerchange", once);
        loadEntry();
      });
      if (reg.active && !navigator.serviceWorker.controller) {
        location.reload();
      }
    }
  } catch (e) {
    console.error(e);
    showErr(e && e.message ? e.message : e);
  }
})();
</script>`.trim();

html = html.replace(/<script type="module" src="[^"]*\/assets\/index-[^"]+\.js"><\/script>\s*/g, "");
html = html.replace(/\s*<link rel="modulepreload"[^>]*>/g, "");
if (html.includes("<!--espanol-boot-->")) {
  html = html.replace(/<!--espanol-boot-->[\s\S]*?<!--\/espanol-boot-->/g, `<!--espanol-boot-->\n${boot}\n<!--/espanol-boot-->`);
} else {
  html = html.replace("</head>", `<!--espanol-boot-->\n${boot}\n<!--/espanol-boot-->\n</head>`);
}

fs.writeFileSync(indexHtmlPath, html);
console.log(`SW boot ready. entry=${entry} splits=${JSON.stringify(splits)}`);
