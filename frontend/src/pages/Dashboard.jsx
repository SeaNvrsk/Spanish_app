import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useI18n, localized } from "../i18n";

function DayNode({ day, state, onClick }) {
  const base =
    "relative flex aspect-square w-full items-center justify-center rounded-xl text-sm font-extrabold shadow-sm transition active:scale-90 sm:h-12 sm:w-12 sm:rounded-2xl";
  let cls = "bg-slate-200 text-slate-400";
  let label = day.day_in_week;
  if (day.kind === "exam") label = "📝";
  if (day.kind === "capstone") label = "🎓";

  if (state === "completed") {
    cls = day.kind === "lesson" ? "bg-amber-400 text-white" : "bg-purple-500 text-white";
    if (day.kind === "lesson") label = "💰";
  } else if (state === "today") {
    cls =
      day.kind === "lesson"
        ? "bg-teal-500 text-white ring-4 ring-teal-200"
        : "bg-purple-500 text-white ring-4 ring-purple-200";
    if (day.kind === "lesson") label = "▶";
  } else if (state === "available") {
    cls =
      day.kind === "lesson"
        ? "bg-emerald-100 text-emerald-700 ring-2 ring-emerald-300"
        : "bg-purple-100 text-purple-700 ring-2 ring-purple-300";
    if (day.kind === "lesson") label = "↩";
  }

  return (
    <button
      disabled={state === "locked"}
      onClick={onClick}
      className={`${base} ${cls}`}
      title={state === "locked" && day.unlock_date ? day.unlock_date : `Day ${day.day}`}
    >
      {label}
      {day.has_theory && state !== "locked" && (
        <span className="absolute -right-1 -top-1 text-[10px]">📘</span>
      )}
    </button>
  );
}

export default function Dashboard() {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [review, setReview] = useState(null);
  const currentRef = useRef(null);

  const load = () => {
    setError(false);
    setData(null);
    api
      .get("/curriculum")
      .then(({ data }) => setData(data))
      .catch(() => setError(true));
    api.get("/review/status").then(({ data }) => setReview(data)).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (data && currentRef.current) {
      currentRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [data]);

  if (error)
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
        <div className="text-4xl">⚠️</div>
        <p className="mt-3 text-sm font-semibold text-slate-600">{t("loadError")}</p>
        <button
          onClick={load}
          className="mt-4 rounded-xl bg-teal-600 px-6 py-2.5 text-sm font-extrabold text-white active:scale-95"
        >
          {t("retry")}
        </button>
      </div>
    );
  if (!data) return <div className="p-10 text-center text-4xl">🌮</div>;

  const stateOf = (d) => {
    if (d.completed) return "completed";
    if (!d.unlocked) return "locked";
    if (d.is_today) return "today";
    return "available";
  };

  const scrollTarget =
    data.today_lesson_id ||
    (() => {
      const flat = [];
      data.levels.forEach((lvl) => lvl.weeks.forEach((w) => w.days.forEach((d) => flat.push(d))));
      const next = flat.find((d) => d.unlocked && !d.completed);
      return next?.id ?? null;
    })();

  return (
    <div className="px-4 py-4">
      <div className="mb-5 rounded-2xl bg-gradient-to-br from-teal-600 to-emerald-600 p-4 text-white shadow-lg">
        <p className="text-xs font-bold uppercase tracking-wide text-teal-100">{t("yourGoal")}</p>
        <p className="mt-0.5 text-xl font-extrabold sm:text-lg">🎯 {t("goalText")}</p>
        <p className="mt-1 text-sm text-teal-100 sm:text-xs">365 {t("day")} · 52 {t("week")}</p>
        {data.program_day > 0 && (
          <p className="mt-2 rounded-xl bg-white/15 px-3 py-2 text-xs font-semibold text-teal-50">
            📅 {t("calendarDay")} {data.program_day}
            {data.program_start_date && (
              <span className="text-teal-100"> · {t("since")} {data.program_start_date}</span>
            )}
          </p>
        )}
      </div>

      <p className="mb-4 text-center text-xs font-semibold text-slate-400 sm:text-sm">{t("catchUpHint")}</p>

      {review && review.total_cards > 0 && (
        <button
          onClick={() => navigate("/review")}
          className="mb-5 flex w-full items-center gap-3 rounded-2xl border border-indigo-100 bg-white p-4 text-left shadow-sm transition active:scale-[0.99]"
        >
          <span className="text-3xl">🧠</span>
          <div className="flex-1">
            <p className="text-sm font-extrabold text-slate-800">{t("dailyReview")}</p>
            <p className="text-xs text-slate-500">{t("reviewSubtitle")}</p>
          </div>
          {review.due > 0 ? (
            <span className="rounded-full bg-indigo-600 px-3 py-1 text-sm font-black text-white">{review.due}</span>
          ) : (
            <span className="text-xl">✓</span>
          )}
        </button>
      )}

      {data.levels.map((lvl) => (
        <section key={lvl.id} className="mb-8">
          <div className="mb-3 rounded-2xl bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-extrabold text-slate-800">{localized(lvl.title, lang)}</h2>
                <p className="text-xs text-slate-500">{localized(lvl.description, lang)}</p>
              </div>
              <span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-black text-teal-600">
                {lvl.months} {t("months")}
              </span>
            </div>
            <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-teal-500 transition-all" style={{ width: `${lvl.progress_percent}%` }} />
            </div>
            <p className="mt-1 text-right text-[11px] font-bold text-slate-400">
              {lvl.completed_lessons}/{lvl.total_lessons} {t("lessonsDone")}
            </p>
          </div>

          <div className="space-y-3">
            {lvl.weeks.map((w) => {
              const hasCurrent = w.days.some((d) => d.id === scrollTarget);
              const doneInWeek = w.days.filter((d) => d.completed).length;
              return (
                <div
                  key={w.week}
                  ref={hasCurrent ? currentRef : null}
                  className={`rounded-2xl border bg-white p-3 shadow-sm ${
                    hasCurrent ? "border-teal-300" : "border-slate-100"
                  }`}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span className="text-lg">{w.icon}</span>
                    <div className="flex-1">
                      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                        {t("week")} {w.week}
                        {w.is_review && (
                          <span className="ml-1 rounded bg-purple-100 px-1.5 py-0.5 text-purple-600">
                            {t("reviewWeek")}
                          </span>
                        )}
                      </p>
                      <p className="text-sm font-extrabold text-slate-700">{localized(w.theme, lang)}</p>
                    </div>
                    <span className="text-[11px] font-bold text-slate-400">
                      {doneInWeek}/{w.days.length}
                    </span>
                  </div>
                  <div className="grid grid-cols-7 gap-1 sm:gap-2">
                    {w.days.map((d) => (
                      <DayNode
                        key={d.id}
                        day={d}
                        state={stateOf(d)}
                        onClick={() => navigate(`/lesson/${d.id}`)}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
