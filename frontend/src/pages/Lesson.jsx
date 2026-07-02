import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import ExercisePlayer from "../components/ExercisePlayer";
import TheoryScreen from "../components/TheoryScreen";

export default function Lesson() {
  const { lessonId } = useParams();
  const navigate = useNavigate();
  const { t } = useI18n();
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
    return (
      <TheoryScreen
        lesson={lesson}
        onClose={() => navigate("/")}
        onStart={() => setShowTheory(false)}
      />
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
            {(finished.pesos_earned || 0) === 0 && finished.score >= 50 && (
              <p className="mt-2 text-[11px] leading-snug text-teal-100/90">{t("lessonNoNewPesos")}</p>
            )}
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
