import { useState } from "react";
import { nativeGloss } from "../i18n";

function KindBadge({ kind, t }) {
  const label =
    kind === "exam" || kind === "capstone" ? t("statsKindExam") : t("statsKindLesson");
  const color =
    kind === "exam" || kind === "capstone"
      ? "bg-amber-100 text-amber-800"
      : "bg-indigo-100 text-indigo-800";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${color}`}>
      {label}
    </span>
  );
}

export function EarningsSummary({ totals, t }) {
  if (!totals) return null;
  return (
    <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
      <div className="rounded-xl bg-indigo-50 p-3">
        <p className="text-[10px] font-bold uppercase text-indigo-500">{t("statsLessons")}</p>
        <p className="text-lg font-black text-indigo-700">${totals.pesos_lessons}</p>
      </div>
      <div className="rounded-xl bg-amber-50 p-3">
        <p className="text-[10px] font-bold uppercase text-amber-600">{t("statsExams")}</p>
        <p className="text-lg font-black text-amber-700">${totals.pesos_exams}</p>
      </div>
      <div className="rounded-xl bg-violet-50 p-3">
        <p className="text-[10px] font-bold uppercase text-violet-600">{t("statsReview")}</p>
        <p className="text-lg font-black text-violet-700">${Number(totals.pesos_review).toFixed(1)}</p>
      </div>
      <div className="rounded-xl bg-teal-50 p-3">
        <p className="text-[10px] font-bold uppercase text-teal-600">{t("statsTotal")}</p>
        <p className="text-lg font-black text-teal-700">${Number(totals.pesos_all).toFixed(1)}</p>
      </div>
    </div>
  );
}

export function LessonHistoryTable({ lessons, t, lang, compact = false }) {
  if (!lessons?.length) {
    return <p className="text-sm text-slate-500">{t("statsNoLessonsYet")}</p>;
  }
  const rows = [...lessons].reverse();
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-xs">
        <thead>
          <tr className="border-b border-slate-200 text-[10px] font-bold uppercase text-slate-400">
            <th className="py-2 pr-2">{t("lesson")}</th>
            <th className="py-2 pr-2">{t("statsType")}</th>
            {!compact && <th className="py-2 pr-2">{t("statsScore")}</th>}
            <th className="py-2 pr-2">{t("pesos")}</th>
            {!compact && <th className="py-2">{t("statsAttempts")}</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((l) => (
            <tr key={l.lesson_id} className="border-b border-slate-100">
              <td className="py-2 pr-2">
                <p className="font-bold text-slate-800">{nativeGloss(l.title, lang)}</p>
                <p className="text-[10px] text-slate-400">{l.lesson_id}</p>
              </td>
              <td className="py-2 pr-2">
                <KindBadge kind={l.kind} t={t} />
              </td>
              {!compact && (
                <td className="py-2 pr-2 font-semibold text-slate-600">
                  {l.best_score}% {"⭐".repeat(l.stars)}
                </td>
              )}
              <td className="py-2 pr-2 font-black text-amber-600">${l.pesos_earned}</td>
              {!compact && <td className="py-2 text-slate-500">{l.attempts}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DailyEarningsTable({ days, t }) {
  if (!days?.length) {
    return <p className="text-sm text-slate-500">{t("statsNoActivityYet")}</p>;
  }
  const rows = [...days].reverse();
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[420px] text-left text-xs">
        <thead>
          <tr className="border-b border-slate-200 text-[10px] font-bold uppercase text-slate-400">
            <th className="py-2 pr-2">{t("statsDay")}</th>
            <th className="py-2 pr-2">{t("statsLessons")}</th>
            <th className="py-2 pr-2">{t("statsReview")}</th>
            <th className="py-2 pr-2">{t("statsTotal")}</th>
            <th className="py-2">{t("lessonsCompleted")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <tr key={d.day} className="border-b border-slate-100">
              <td className="py-2 pr-2 font-semibold text-slate-700">{d.day}</td>
              <td className="py-2 pr-2 text-indigo-600">${d.pesos_lessons}</td>
              <td className="py-2 pr-2 text-violet-600">${Number(d.pesos_review).toFixed(1)}</td>
              <td className="py-2 pr-2 font-black text-teal-700">${Number(d.pesos_total).toFixed(1)}</td>
              <td className="py-2 text-slate-500">{d.lessons_completed}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MemberStatsPanel({ member, t, lang, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-3 text-left active:bg-slate-50"
      >
        <span className="text-2xl">{member.avatar}</span>
        <div className="min-w-0 flex-1">
          <p className="font-extrabold text-slate-800">{member.name}</p>
          <p className="text-xs text-slate-500">
            {member.lessons_completed} {t("lessonsDone")} · $
            {Number(member.earnings_totals?.pesos_all || 0).toFixed(1)} {t("statsTotal").toLowerCase()}
          </p>
        </div>
        <span className="text-slate-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-3 pb-3 pt-2">
          <EarningsSummary totals={member.earnings_totals} t={t} />
          <h3 className="mb-2 text-xs font-extrabold uppercase tracking-wide text-slate-500">
            {t("statsLessonHistory")}
          </h3>
          <LessonHistoryTable lessons={member.lesson_history} t={t} lang={lang} compact />
          <h3 className="mb-2 mt-4 text-xs font-extrabold uppercase tracking-wide text-slate-500">
            {t("statsDailyEarnings")}
          </h3>
          <DailyEarningsTable days={member.daily_earnings} t={t} />
        </div>
      )}
    </div>
  );
}
