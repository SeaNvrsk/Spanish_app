import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import ExercisePlayer from "../components/ExercisePlayer";

export default function Review() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { refresh } = useAuth();

  const [queue, setQueue] = useState(null);
  const [started, setStarted] = useState(false);
  const [finished, setFinished] = useState(null);

  useEffect(() => {
    api.get("/review/queue").then(({ data }) => setQueue(data)).catch(() => setQueue({ count: 0, exercises: [] }));
  }, []);

  const handleFinish = async (results) => {
    try {
      const { data } = await api.post("/review/grade", { items: results, award_pesos: true });
      setFinished(data);
      refresh();
    } catch {
      setFinished({ pesos_earned: 0 });
    }
  };

  if (!queue) return <div className="p-10 text-center text-4xl">🌮</div>;

  if (started && !finished) {
    return <ExercisePlayer exercises={queue.exercises} kind="review" onFinish={handleFinish} />;
  }

  if (finished) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center bg-gradient-to-b from-indigo-600 to-purple-700 px-5 py-8 text-center text-white sm:px-6">
        <div className="animate-pop text-7xl">🧠</div>
        <h1 className="mt-4 text-2xl font-extrabold">{t("reviewComplete")}</h1>
        <div className="mt-6 rounded-2xl bg-white/15 px-8 py-5">
          <div className="text-4xl font-black">${finished.pesos_earned || 0}</div>
          <div className="text-xs text-indigo-100">{t("pesos")}</div>
        </div>
        <button
          onClick={() => navigate("/")}
          className="mt-10 w-full max-w-xs rounded-xl bg-white py-3.5 font-extrabold text-indigo-700 shadow-lg active:scale-95"
        >
          {t("backToLessons")}
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      {queue.count === 0 ? (
        <>
          <div className="text-6xl">🎉</div>
          <h1 className="mt-4 text-xl font-extrabold text-slate-800">{t("noReviewTitle")}</h1>
          <p className="mt-2 max-w-xs text-sm text-slate-500">{t("noReviewText")}</p>
          <button
            onClick={() => navigate("/")}
            className="mt-8 rounded-2xl bg-teal-600 px-8 py-3 font-extrabold text-white shadow-lg active:scale-95"
          >
            {t("backToLessons")}
          </button>
        </>
      ) : (
        <>
          <div className="text-6xl">🧠</div>
          <h1 className="mt-4 text-2xl font-extrabold text-slate-800">{t("dailyReview")}</h1>
          <p className="mt-2 max-w-xs text-sm text-slate-500">{t("reviewSubtitle")}</p>
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
