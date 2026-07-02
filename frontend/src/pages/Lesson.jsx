import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api";
import { useI18n, localized } from "../i18n";
import { useAuth } from "../auth";
import ExercisePlayer, { SpeakButton } from "../components/ExercisePlayer";

export default function Lesson() {
  const { lessonId } = useParams();
  const navigate = useNavigate();
  const { t, lang } = useI18n();
  const { refresh } = useAuth();

  const [lesson, setLesson] = useState(null);
  const [finished, setFinished] = useState(null);
  const [showTheory, setShowTheory] = useState(false);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    setLesson(null);
    setLoadError(null);
    setFinished(null);
    setShowTheory(false);
    api
      .get(`/lessons/${lessonId}`)
      .then(({ data }) => {
        setLesson(data);
        setShowTheory(!!data.theory);
      })
      .catch((err) => {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 403) {
          setLoadError({
            locked: true,
            unlockDate: typeof detail === "object" ? detail.unlock_date : null,
          });
        } else {
          setLoadError({ locked: false });
        }
      });
  }, [lessonId]);

  if (loadError?.locked) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
        <div className="text-5xl">🔒</div>
        <p className="mt-4 text-lg font-extrabold text-slate-700">{t("lessonLocked")}</p>
        {loadError.unlockDate && (
          <p className="mt-2 text-sm text-slate-500">
            {t("unlocksOn")} {loadError.unlockDate}
          </p>
        )}
        <button
          onClick={() => navigate("/")}
          className="mt-8 rounded-xl bg-teal-600 px-8 py-3 font-extrabold text-white"
        >
          {t("backToLessons")}
        </button>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
        <div className="text-4xl">⚠️</div>
        <p className="mt-3 text-sm font-semibold text-slate-600">{t("loadError")}</p>
        <button onClick={() => navigate("/")} className="mt-4 text-teal-600 font-bold">
          {t("backToLessons")}
        </button>
      </div>
    );
  }

  if (!lesson) return <div className="p-10 text-center text-4xl">🌮</div>;

  const handleFinish = async (results, score) => {
    // Feed practiced words into the spaced-repetition scheduler.
    if (results.length) {
      api.post("/review/grade", { items: results, award_pesos: false }).catch(() => {});
    }
    try {
      const { data } = await api.post(`/lessons/${lessonId}/complete`, { lesson_id: lessonId, score });
      setFinished({ ...data, score });
      refresh();
    } catch {
      setFinished({ pesos_earned: 0, score });
    }
  };

  // ---------- Theory screen ----------
  if (showTheory && lesson.theory && !finished) {
    const th = lesson.theory;
    return (
      <div className="flex min-h-dvh flex-col bg-white">
        <div className="flex items-center gap-2 px-3 py-2.5 sm:px-4 sm:py-3">
          <button
            onClick={() => navigate("/")}
            className="touch-target flex shrink-0 items-center justify-center rounded-full text-xl text-slate-400 active:bg-slate-100"
            aria-label="Close"
          >
            ✕
          </button>
          <span className="truncate font-extrabold text-slate-700">{localized(lesson.theme, lang)}</span>
          {lesson.est_minutes && (
            <span className="ml-auto rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-600">
              ~{lesson.est_minutes} {t("minAbbr")}
            </span>
          )}
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto px-4 pb-4 sm:px-5 sm:pb-6">
          {th.day_focus && (
            <div className="rounded-2xl border-2 border-teal-200 bg-teal-50/80 p-4">
              <p className="text-[15px] font-bold text-teal-800">{localized(th.day_focus, lang)}</p>
            </div>
          )}
          <div className="rounded-2xl bg-teal-50 p-4">
            <p className="text-[15px] font-semibold text-slate-700">{localized(th.intro, lang)}</p>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-extrabold uppercase tracking-wide text-teal-600">
              📘 {t("grammarTitle")}
            </h3>
            <p className="text-[15px] leading-relaxed text-slate-700">{localized(th.grammar, lang)}</p>
          </div>
          {th.examples?.length > 0 && (
            <div>
              <h3 className="mb-2 text-sm font-extrabold uppercase tracking-wide text-teal-600">
                💬 {t("examplesTitle")}
              </h3>
              <div className="space-y-2">
                {th.examples.map((exm, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-xl border border-slate-100 bg-white p-3 shadow-sm">
                    <SpeakButton text={exm.es} />
                    <div>
                      <p className="font-bold text-slate-800">{exm.es}</p>
                      <p className="text-sm text-slate-500">{lang === "ru" ? exm.ru : exm.en}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {th.tip && (
            <div className="rounded-2xl bg-amber-50 p-4">
              <h3 className="mb-1 text-sm font-extrabold uppercase tracking-wide text-amber-600">
                🌵 {t("tipTitle")}
              </h3>
              <p className="text-[15px] font-semibold text-amber-800">{localized(th.tip, lang)}</p>
            </div>
          )}
        </div>
        <div className="sticky bottom-0 shrink-0 bg-white px-4 pb-safe pt-3 sm:px-5">
          <button
            onClick={() => setShowTheory(false)}
            className="w-full rounded-2xl bg-teal-600 py-4 font-extrabold text-white shadow-lg active:scale-95 sm:py-3.5"
          >
            {t("startExercises")} →
          </button>
        </div>
      </div>
    );
  }

  // ---------- Completion screen ----------
  if (finished) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-gradient-to-b from-teal-600 to-emerald-700 px-5 py-8 text-center text-white sm:px-6">
        <div className="animate-pop text-6xl sm:text-7xl">🎉</div>
        <h1 className="mt-4 text-xl font-extrabold sm:text-2xl">{t("lessonComplete")}</h1>
        <div className="mt-6 flex w-full max-w-sm flex-wrap justify-center gap-3">
          <div className="min-w-[5.5rem] flex-1 rounded-2xl bg-white/15 px-4 py-4 sm:px-6">
            <div className="text-2xl font-black sm:text-3xl">{finished.score}%</div>
            <div className="text-xs text-teal-100">score</div>
          </div>
          <div className="min-w-[5.5rem] flex-1 rounded-2xl bg-white/15 px-4 py-4 sm:px-6">
            <div className="text-2xl font-black sm:text-3xl">${finished.pesos_earned || 0}</div>
            <div className="text-xs text-teal-100">{t("pesos")}</div>
          </div>
        </div>
        <button
          onClick={() => navigate("/")}
          className="mt-8 w-full max-w-xs rounded-xl bg-white py-4 font-extrabold text-teal-700 shadow-lg active:scale-95 sm:mt-10 sm:py-3.5"
        >
          {t("backToLessons")}
        </button>
      </div>
    );
  }

  return <ExercisePlayer exercises={lesson.exercises} kind={lesson.kind} onFinish={handleFinish} />;
}
