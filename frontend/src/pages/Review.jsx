import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import ExercisePlayer from "../components/ExercisePlayer";

export default function Review() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [searchParams] = useSearchParams();
  const initialMode = searchParams.get("mode") === "practice" ? "practice" : "due";

  const [status, setStatus] = useState(null);
  const [queue, setQueue] = useState(null);
  const [mode, setMode] = useState(initialMode);
  const [started, setStarted] = useState(false);
  const [finished, setFinished] = useState(null);

  const loadQueue = (m) => {
    setQueue(null);
    api.get(`/review/queue?mode=${m}`).then(({ data }) => setQueue(data)).catch(() => setQueue({ count: 0, exercises: [], mode: m }));
  };

  useEffect(() => {
    api.get("/review/status").then(({ data }) => setStatus(data)).catch(() => setStatus({ total_cards: 0, due: 0, practice_available: 0 }));
  }, []);

  useEffect(() => {
    if (status) loadQueue(mode);
  }, [status, mode]);

  const handleFinish = async (results) => {
    try {
      const award = mode === "due";
      const { data } = await api.post("/review/grade", { items: results, award_pesos: award });
      setFinished({ ...data, mode });
      refresh();
    } catch {
      setFinished({ pesos_earned: 0, mode });
    }
  };

  if (!status || !queue) return <div className="p-10 text-center text-4xl">🌮</div>;

  if (started && !finished && queue.count > 0) {
    return <ExercisePlayer exercises={queue.exercises} kind="review" onFinish={handleFinish} />;
  }

  if (finished) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-gradient-to-b from-indigo-600 to-purple-700 px-5 py-8 text-center text-white sm:px-6">
        <div className="animate-pop text-7xl">🧠</div>
        <h1 className="mt-4 text-2xl font-extrabold">{t("reviewComplete")}</h1>
        {finished.mode === "due" && (finished.pesos_earned || 0) > 0 && (
          <div className="mt-6 rounded-2xl bg-white/15 px-8 py-5">
            <div className="text-4xl font-black">${finished.pesos_earned}</div>
            <div className="text-xs text-indigo-100">{t("pesos")}</div>
          </div>
        )}
        <button
          onClick={() => navigate("/")}
          className="mt-10 w-full max-w-xs rounded-xl bg-white py-3.5 font-extrabold text-indigo-700 shadow-lg active:scale-95"
        >
          {t("backToLessons")}
        </button>
      </div>
    );
  }

  const noCards = status.total_cards === 0;
  const dueEmpty = mode === "due" && queue.count === 0;
  const canPractice = status.practice_available > 0;

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      {noCards ? (
        <>
          <div className="text-6xl">📚</div>
          <h1 className="mt-4 text-xl font-extrabold text-slate-800">{t("noWordsYet")}</h1>
          <p className="mt-2 max-w-xs text-sm text-slate-500">{t("reviewNeedLessons")}</p>
          <button
            onClick={() => navigate("/")}
            className="mt-8 rounded-2xl bg-teal-600 px-8 py-3 font-extrabold text-white shadow-lg active:scale-95"
          >
            {t("backToLessons")}
          </button>
        </>
      ) : dueEmpty && mode === "due" ? (
        <>
          <div className="text-6xl">🎉</div>
          <h1 className="mt-4 text-xl font-extrabold text-slate-800">{t("noReviewTitle")}</h1>
          <p className="mt-2 max-w-xs text-sm text-slate-500">{t("noReviewText")}</p>
          {canPractice && (
            <button
              onClick={async () => {
                const { data: q } = await api.get("/review/queue?mode=practice");
                setQueue(q);
                setMode("practice");
                if (q.count > 0) setStarted(true);
              }}
              className="mt-8 w-full max-w-xs rounded-2xl bg-indigo-600 py-3.5 font-extrabold text-white shadow-lg active:scale-95"
            >
              {t("practiceAllWords")} ({status.practice_available}) →
            </button>
          )}
          <button
            onClick={() => navigate("/")}
            className="mt-3 w-full max-w-xs rounded-2xl border-2 border-slate-200 py-3 font-bold text-slate-600 active:scale-95"
          >
            {t("backToLessons")}
          </button>
        </>
      ) : (
        <>
          <div className="text-6xl">🧠</div>
          <h1 className="mt-4 text-2xl font-extrabold text-slate-800">
            {mode === "practice" ? t("practiceReview") : t("dailyReview")}
          </h1>
          <p className="mt-2 max-w-xs text-sm text-slate-500">
            {mode === "practice" ? t("practiceReviewSub") : t("reviewSubtitle")}
          </p>

          {(status.due > 0 || canPractice) && status.due > 0 && canPractice && (
            <div className="mt-4 flex w-full max-w-xs gap-2">
              <button
                type="button"
                onClick={() => setMode("due")}
                className={`flex-1 rounded-xl py-2 text-xs font-bold ${mode === "due" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
              >
                {t("reviewDueTab")} ({status.due})
              </button>
              <button
                type="button"
                onClick={() => setMode("practice")}
                className={`flex-1 rounded-xl py-2 text-xs font-bold ${mode === "practice" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}
              >
                {t("practiceTab")}
              </button>
            </div>
          )}

          {mode === "practice" && status.due > 0 && (
            <button
              type="button"
              onClick={() => setMode("due")}
              className="mt-4 text-sm font-bold text-indigo-600 underline"
            >
              ← {t("backToDueReview")} ({status.due})
            </button>
          )}

          <div className="mt-6 rounded-2xl bg-indigo-50 px-8 py-5">
            <div className="text-4xl font-black text-indigo-600">{queue.count}</div>
            <div className="text-xs font-bold text-indigo-400">
              {queue.count === 1 ? t("reviewDueOne") : t("reviewDueMany")}
            </div>
          </div>
          <button
            onClick={() => setStarted(true)}
            className="mt-8 w-full max-w-xs rounded-2xl bg-indigo-600 py-3.5 font-extrabold text-white shadow-lg active:scale-95"
          >
            {t("startReview")} →
          </button>
        </>
      )}
    </div>
  );
}
