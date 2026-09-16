import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";
import { I18nProvider } from "./i18n";
import { AuthProvider } from "./auth";
import { appBase } from "./appBase";
import { ensureMobileViewport } from "./viewport";

ensureMobileViewport();
// bust cache: split large chunks for RU ISP 56KiB limit (raw)

const rootEl = document.getElementById("root");
rootEl?.setAttribute("data-app-booted", "1");
// Ready flag is set later by auth when the splash finishes (see auth.jsx).
// Beacon so server logs prove JS executed on the device.
try {
  fetch(`${appBase}/api/health?boot=1&v=4`, { cache: "no-store", credentials: "omit" }).catch(() => {});
} catch {
  /* ignore */
}

try {
  createRoot(rootEl).render(
    <StrictMode>
      <I18nProvider>
        <BrowserRouter basename={appBase || undefined}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </I18nProvider>
    </StrictMode>
  );
} catch (err) {
  console.error(err);
  if (rootEl) {
    rootEl.innerHTML =
      '<div style="min-height:100dvh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:24px;text-align:center;font-family:system-ui;background:#f8fafc">' +
      '<div style="font-size:2.5rem">⚠️</div>' +
      '<p style="font-weight:700;color:#0f766e">Не удалось запустить приложение</p>' +
      '<p style="font-size:14px;color:#64748b">Обновите страницу или откройте ссылку в Safari</p>' +
      '<button onclick="location.reload()" style="margin-top:8px;padding:12px 20px;border:0;border-radius:12px;background:#0f766e;color:#fff;font-weight:800">Обновить</button>' +
      "</div>";
  }
}
