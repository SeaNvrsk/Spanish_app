import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useI18n } from "../i18n";
import { TranslatorPanel, ConjugatorPanel } from "./ToolsFooter";

const navClass = (active) =>
  `flex min-w-0 flex-1 flex-col items-center gap-0.5 px-0.5 py-2 text-[10px] font-bold leading-tight transition-colors sm:text-xs ${
    active ? "text-teal-600" : "text-slate-400"
  }`;

export default function BottomNav() {
  const { t } = useI18n();
  const [panel, setPanel] = useState(null);

  return (
    <>
      <nav className="fixed bottom-0 left-1/2 z-20 w-full max-w-md -translate-x-1/2 border-t border-slate-100 bg-white pb-[env(safe-area-inset-bottom)] sm:max-w-lg">
        <div className="flex items-stretch">
          <NavLink to="/" end className={({ isActive }) => navClass(isActive)}>
            <span className="text-[1.35rem] leading-none sm:text-2xl">📚</span>
            <span className="max-w-full truncate">{t("learn")}</span>
          </NavLink>

          <button type="button" onClick={() => setPanel("translate")} className={navClass(false)}>
            <span className="text-[1.35rem] leading-none sm:text-2xl">🌐</span>
            <span className="max-w-full truncate">{t("translatorShort")}</span>
          </button>

          <NavLink to="/ranking" className={({ isActive }) => navClass(isActive)}>
            <span className="text-[1.35rem] leading-none sm:text-2xl">🏆</span>
            <span className="max-w-full truncate">{t("ranking")}</span>
          </NavLink>

          <button type="button" onClick={() => setPanel("conjugate")} className={navClass(false)}>
            <span className="text-[1.35rem] leading-none sm:text-2xl">📝</span>
            <span className="max-w-full truncate">{t("conjugatorShort")}</span>
          </button>

          <NavLink to="/profile" className={({ isActive }) => navClass(isActive)}>
            <span className="text-[1.35rem] leading-none sm:text-2xl">👤</span>
            <span className="max-w-full truncate">{t("profile")}</span>
          </NavLink>
        </div>
      </nav>

      {panel === "translate" && <TranslatorPanel onClose={() => setPanel(null)} />}
      {panel === "conjugate" && <ConjugatorPanel onClose={() => setPanel(null)} />}
    </>
  );
}
