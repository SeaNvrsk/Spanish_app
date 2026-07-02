import { useState } from "react";
import { useAuth } from "../auth";
import { useI18n, personalWelcomeKey } from "../i18n";

const RULES_VERSION = "v6";

function rulesKey(userId) {
  return `family_rules_${RULES_VERSION}_${userId}`;
}

export function hasAcceptedRules(userId) {
  return !!localStorage.getItem(rulesKey(userId));
}

function RuleBlock({ icon, title, children }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-extrabold text-slate-800">
        {icon} {title}
      </h3>
      <div className="space-y-2 text-[13px] leading-relaxed text-slate-600">{children}</div>
    </div>
  );
}

function PersonalWelcome({ name, t }) {
  const welcomeKey = personalWelcomeKey(name);
  if (!welcomeKey) return null;

  const paragraphs = t(welcomeKey).split("\n").filter(Boolean);
  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50 p-4 shadow-sm">
      <p className="mb-2 text-sm font-extrabold text-amber-900">💛 {t("rulesWelcomeTitle")}</p>
      <div className="space-y-2 text-[13px] leading-relaxed text-amber-950">
        {paragraphs.map((line) => (
          <p key={line.slice(0, 24)}>{line}</p>
        ))}
      </div>
    </div>
  );
}

export default function RulesGate({ children, forceShow = false, onClose }) {
  const { user } = useAuth();
  const { t } = useI18n();
  const [open, setOpen] = useState(() => forceShow || (user && !hasAcceptedRules(user.id)));

  if (!user) return children;

  const accept = () => {
    localStorage.setItem(rulesKey(user.id), new Date().toISOString());
    setOpen(false);
    onClose?.();
  };

  if (!open) return children;

  return (
    <>
      <div className="fixed inset-0 z-50 flex flex-col bg-gradient-to-b from-teal-700 to-emerald-800">
        <div className="flex-1 overflow-y-auto px-5 pb-6 pt-8">
          <div className="mx-auto w-full lg:max-w-md">
            <p className="text-center text-4xl">📜</p>
            <h1 className="mt-3 text-center text-2xl font-extrabold text-white">{t("rulesTitle")}</h1>
            <p className="mt-2 text-center text-sm text-teal-100">{t("rulesIntro")}</p>

            <div className="mt-6 space-y-3">
              <RuleBlock icon="👨‍👩‍👧‍👧" title={t("rulesFamilyTitle")}>
                <p>{t("rulesFamilyBody")}</p>
              </RuleBlock>

              <RuleBlock icon="💌" title={t("rulesCreatorTitle")}>
                <p>{t("rulesCreatorBody")}</p>
              </RuleBlock>

              <PersonalWelcome name={user.name} t={t} />

              <RuleBlock icon="$" title={t("rulesPesosTitle")}>
                <p>{t("rulesPesosLesson")}</p>
                <p>{t("rulesPesosExam")}</p>
                <p>{t("rulesPesosReview")}</p>
                <p>{t("rulesPesosRetry")}</p>
                <p>{t("rulesPesosMonth")}</p>
              </RuleBlock>

              <RuleBlock icon="🏆" title={t("rulesPlacesTitle")}>
                <p>{t("rulesPlacesIntro")}</p>
                <p>{t("rulesPlace1")}</p>
                <p>{t("rulesPlace2")}</p>
                <p>{t("rulesPlace3")}</p>
                <p className="mt-2 font-semibold text-slate-700">{t("rulesTie")}</p>
                <p className="text-xs text-slate-500">{t("rulesTieEx1")}</p>
                <p className="text-xs text-slate-500">{t("rulesTieEx2")}</p>
                <p className="text-xs text-slate-500">{t("rulesTieEx3")}</p>
                <p className="text-xs text-slate-400">{t("rulesCarryover")}</p>
              </RuleBlock>

              <RuleBlock icon="📦" title={t("rulesQuarterTitle")}>
                <p>{t("rulesQuarterBody")}</p>
                <p className="font-semibold text-amber-700">{t("rulesQuarterShip")}</p>
              </RuleBlock>

              {user.is_admin && (
                <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4">
                  <p className="text-sm font-extrabold text-violet-800">👑 {t("adminBadge")}</p>
                  <p className="mt-1 text-xs text-violet-600">{t("rulesAdminNote")}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="border-t border-white/20 bg-emerald-900/40 px-4 pb-[max(2rem,env(safe-area-inset-bottom))] pt-4 sm:px-5">
          <button
            onClick={accept}
            className="mx-auto block w-full rounded-2xl bg-white py-4 text-base font-extrabold text-teal-700 shadow-lg active:scale-[0.98] lg:max-w-md"
          >
            {t("rulesAccept")} →
          </button>
        </div>
      </div>
      {!forceShow && <div className="invisible">{children}</div>}
    </>
  );
}

/** Re-open rules from Profile settings. */
export function RulesModal({ open, onClose }) {
  if (!open) return null;
  return <RulesGate forceShow onClose={onClose}>{null}</RulesGate>;
}
