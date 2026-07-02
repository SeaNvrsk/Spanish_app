import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { useI18n, nativeGloss } from "../i18n";
import { SpeakButton } from "../components/ExercisePlayer";

export default function Vocabulary() {
  const { t, lang } = useI18n();
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.get("/vocabulary").then(({ data: d }) => setData(d)).catch(() => setData({ count: 0, words: [] }));
  }, []);

  if (!data) return <div className="p-10 text-center text-4xl">🌮</div>;

  const q = query.trim().toLowerCase();
  const words = data.words.filter((w) => {
    if (!q) return true;
    return (
      w.word_es.toLowerCase().includes(q) ||
      w.word_en.toLowerCase().includes(q) ||
      w.word_ru.toLowerCase().includes(q)
    );
  });

  return (
    <div className="min-w-0 px-3 py-3 sm:px-4 sm:py-4">
      <div className="mb-4 flex items-center gap-2">
        <Link to="/profile" className="rounded-full px-2 py-1 text-xl text-slate-400 active:bg-slate-100">
          ←
        </Link>
        <div className="min-w-0 flex-1">
          <h1 className="text-lg font-extrabold text-slate-800 sm:text-xl">{t("myVocabulary")}</h1>
          <p className="text-xs text-slate-500">
            {data.count} {t("wordsCount")}
          </p>
        </div>
      </div>

      {data.count > 0 && (
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("typeHere")}
          className="mb-3 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-800 outline-none focus:border-teal-500"
        />
      )}

      {words.length === 0 ? (
        <div className="rounded-2xl bg-white p-8 text-center shadow-sm">
          <div className="text-5xl">📇</div>
          <p className="mt-3 text-sm font-semibold text-slate-500">{t("noWordsYet")}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {words.map((w) => (
            <div
              key={w.word_es}
              className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-white px-3 py-3 shadow-sm sm:px-4"
            >
              <SpeakButton text={w.word_es} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-base font-extrabold text-slate-800">{w.word_es}</p>
                <p className="truncate text-sm font-semibold text-slate-500">
                  {nativeGloss({ en: w.word_en, ru: w.word_ru }, lang)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
