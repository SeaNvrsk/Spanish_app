import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useI18n } from "../i18n";
import { TranslatorPanel, ConjugatorPanel } from "./ToolsFooter";
import { AngelicaPanel } from "./AngelicaChat";

const navClass = (active) =>
  `bottom-nav-item transition-colors active:bg-slate-50 ${active ? "text-teal-600" : "text-slate-400"}`;

export default function BottomNav() {
  const { t } = useI18n();
  const [panel, setPanel] = useState(null);

  return (
    <>
      <nav
        aria-label="Main navigation"
        className="fixed inset-x-0 bottom-0 z-20 w-full border-t border-slate-100 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:left-1/2 lg:max-w-lg lg:-translate-x-1/2"
      >
        <div className="grid grid-cols-6 items-stretch">
          <NavLink to="/" end className={({ isActive }) => navClass(isActive)} aria-label={t("learn")}>
            <span className="bottom-nav-icon" aria-hidden>📚</span>
            <span>{t("learn")}</span>
          </NavLink>

          <button type="button" onClick={() => setPanel("angelica")} className={navClass(panel === "angelica")} aria-label={t("angelica")}>
            <span className="bottom-nav-icon" aria-hidden>👩‍🎓</span>
            <span>{t("angelicaShort")}</span>
          </button>

          <button type="button" onClick={() => setPanel("translate")} className={navClass(false)} aria-label={t("translator")}>
            <span className="bottom-nav-icon" aria-hidden>🌐</span>
            <span>{t("translatorShort")}</span>
          </button>

          <NavLink to="/ranking" className={({ isActive }) => navClass(isActive)} aria-label={t("ranking")}>
            <span className="bottom-nav-icon" aria-hidden>🏆</span>
            <span>{t("ranking")}</span>
          </NavLink>

          <button type="button" onClick={() => setPanel("conjugate")} className={navClass(false)} aria-label={t("conjugator")}>
            <span className="bottom-nav-icon" aria-hidden>📝</span>
            <span>{t("conjugatorShort")}</span>
          </button>

          <NavLink to="/profile" className={({ isActive }) => navClass(isActive)} aria-label={t("profile")}>
            <span className="bottom-nav-icon" aria-hidden>👤</span>
            <span>{t("profile")}</span>
          </NavLink>
        </div>
      </nav>

      {panel === "translate" && <TranslatorPanel onClose={() => setPanel(null)} />}
      {panel === "conjugate" && <ConjugatorPanel onClose={() => setPanel(null)} />}
      {panel === "angelica" && <AngelicaPanel onClose={() => setPanel(null)} />}
    </>
  );
}
