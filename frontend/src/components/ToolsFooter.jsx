import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import api from "../api";
import { useI18n } from "../i18n";
import { SpeakButton } from "./ExercisePlayer";

function ToolSheet({ open, onClose, title, icon, children }) {
  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      <button type="button" className="absolute inset-0 bg-black/40" onClick={onClose} aria-label="Close" />
      <div className="relative mx-auto flex max-h-[85vh] w-full max-w-md flex-col rounded-t-3xl bg-white shadow-2xl sm:max-w-lg">
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
          <span className="text-2xl">{icon}</span>
          <h2 className="flex-1 text-lg font-extrabold text-slate-800">{title}</h2>
          <button type="button" onClick={onClose} className="text-2xl text-slate-400">
            ✕
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function TranslatorPanel({ onClose }) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    const q = text.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post("/tools/translate", { text: q });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || t("translateError"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ToolSheet open title={t("translator")} icon="🌐" onClose={onClose}>
      <p className="mb-3 text-xs font-semibold text-slate-500">{t("translatorHint")}</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t("translatePlaceholder")}
        rows={4}
        className="w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-[15px] text-slate-800 outline-none focus:border-teal-400"
      />
      <button
        type="button"
        disabled={loading || !text.trim()}
        onClick={submit}
        className="mt-3 w-full rounded-2xl bg-teal-600 py-3.5 font-extrabold text-white disabled:opacity-50 active:scale-[0.99]"
      >
        {loading ? "…" : t("translateBtn")}
      </button>
      {error && <p className="mt-3 text-sm font-semibold text-red-600">{String(error)}</p>}
      {result && (
        <div className="mt-4 space-y-3">
          <div className="rounded-2xl border border-teal-100 bg-teal-50 p-4">
            <div className="flex items-start gap-2">
              <SpeakButton text={result.spanish} />
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-teal-600">🇲🇽 {t("mexicanSpanish")}</p>
                <p className="mt-1 text-lg font-bold text-slate-800">{result.spanish}</p>
              </div>
            </div>
          </div>
          {result.note && (
            <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">{result.note}</p>
          )}
        </div>
      )}
    </ToolSheet>
  );
}

const TENSE_KEYS = {
  present: "tensePresent",
  preterite: "tensePreterite",
  imperfect: "tenseImperfect",
  future: "tenseFuture",
};

export function ConjugatorPanel({ onClose }) {
  const { t } = useI18n();
  const [verb, setVerb] = useState("");
  const [tense, setTense] = useState("present");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    const v = verb.trim();
    if (!v) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post("/tools/conjugate", { verb: v, tense });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || t("conjugateError"));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ToolSheet open title={t("conjugator")} icon="📝" onClose={onClose}>
      <p className="mb-3 text-xs font-semibold text-slate-500">{t("conjugatorHint")}</p>
      <input
        value={verb}
        onChange={(e) => setVerb(e.target.value)}
        placeholder={t("verbPlaceholder")}
        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-[15px] font-medium text-slate-800 outline-none focus:border-teal-400"
      />
      <div className="mt-3 flex flex-wrap gap-2">
        {Object.entries(TENSE_KEYS).map(([id, key]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTense(id)}
            className={`rounded-full px-3 py-1.5 text-xs font-bold ${
              tense === id ? "bg-teal-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {t(key)}
          </button>
        ))}
      </div>
      <button
        type="button"
        disabled={loading || !verb.trim()}
        onClick={submit}
        className="mt-3 w-full rounded-2xl bg-indigo-600 py-3.5 font-extrabold text-white disabled:opacity-50 active:scale-[0.99]"
      >
        {loading ? "…" : t("conjugateBtn")}
      </button>
      {error && <p className="mt-3 text-sm font-semibold text-red-600">{String(error)}</p>}
      {result && (
        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-100">
          <div className="bg-indigo-50 px-4 py-2 text-center">
            <p className="text-sm font-extrabold text-indigo-800">{result.infinitive}</p>
            <p className="text-[11px] font-semibold text-indigo-600">{t(TENSE_KEYS[result.tense] || "tensePresent")}</p>
          </div>
          <table className="w-full text-left text-sm">
            <tbody>
              {result.forms.map((row) => (
                <tr key={row.pronoun} className="border-t border-slate-100">
                  <td className="px-4 py-2.5 font-bold text-slate-500">{row.pronoun}</td>
                  <td className="px-4 py-2.5 font-extrabold text-slate-800">{row.form}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="border-t border-slate-100 px-4 py-2 text-[10px] font-medium text-slate-400">
            {t("noVosotros")}
          </p>
        </div>
      )}
    </ToolSheet>
  );
}
