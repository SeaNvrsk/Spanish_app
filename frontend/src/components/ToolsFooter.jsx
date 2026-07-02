import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import api from "../api";
import { useI18n } from "../i18n";
import { useKeyboardInset } from "../useKeyboardInset";
import { SpeakButton } from "./ExercisePlayer";

function ToolSheet({ open, onClose, title, icon, children, footer }) {
  const sheetRef = useRef(null);
  const { keyboardInset } = useKeyboardInset(open);

  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    else document.body.style.overflow = "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    if (!open || !sheetRef.current) return undefined;
    const root = sheetRef.current;
    const onFocus = (e) => {
      if (e.target.matches("input, textarea")) {
        window.setTimeout(() => {
          e.target.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }, 280);
      }
    };
    root.addEventListener("focusin", onFocus);
    return () => root.removeEventListener("focusin", onFocus);
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex flex-col sm:justify-end">
      <button
        type="button"
        className="absolute inset-0 hidden bg-black/40 sm:block"
        onClick={onClose}
        aria-label="Close"
      />
      <div
        ref={sheetRef}
        className="relative flex min-h-0 w-full flex-1 flex-col bg-white sm:mx-auto sm:max-h-[min(85dvh,calc(100dvh-env(safe-area-inset-top)))] sm:max-w-lg sm:flex-none sm:rounded-t-3xl sm:shadow-2xl"
        style={{
          paddingBottom: keyboardInset
            ? `calc(${keyboardInset}px + env(safe-area-inset-bottom, 0px))`
            : "env(safe-area-inset-bottom, 0px)",
        }}
      >
        <div className="flex shrink-0 items-center gap-2 border-b border-slate-100 px-3 py-3 sm:gap-3 sm:px-5 sm:py-4">
          <span className="shrink-0 text-xl sm:text-2xl">{icon}</span>
          <h2 className="min-w-0 flex-1 truncate text-base font-extrabold text-slate-800 sm:text-lg">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="touch-target flex shrink-0 items-center justify-center rounded-full text-xl text-slate-400 active:bg-slate-100"
          >
            ✕
          </button>
        </div>
        <div
          className={`min-h-0 flex-1 px-3 py-3 sm:px-5 sm:py-4 ${
            footer ? "flex flex-col overflow-hidden" : "overflow-y-auto overscroll-y-contain"
          }`}
        >
          {children}
        </div>
        {footer}
      </div>
    </div>
  );
}

export { ToolSheet };

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
      <p className="mb-3 text-[11px] font-semibold leading-snug text-slate-500 sm:text-xs">{t("translatorHint")}</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t("translatePlaceholder")}
        rows={3}
        className="mobile-field w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-800 outline-none focus:border-teal-400"
      />
      <button
        type="button"
        disabled={loading || !text.trim()}
        onClick={submit}
        className="mobile-btn mt-3 w-full rounded-2xl bg-teal-600 font-extrabold text-white disabled:opacity-50 active:scale-[0.99]"
      >
        {loading ? "…" : t("translateBtn")}
      </button>
      {error && <p className="mt-3 text-sm font-semibold text-red-600">{String(error)}</p>}
      {result && (
        <div className="mt-4 space-y-3">
          <div className="rounded-2xl border border-teal-100 bg-teal-50 p-4">
            <div className="flex items-start gap-2">
              <SpeakButton text={result.spanish} />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold uppercase tracking-wide text-teal-600">🇲🇽 {t("mexicanSpanish")}</p>
                <p className="mt-1 break-words text-lg font-bold text-slate-800">{result.spanish}</p>
              </div>
            </div>
          </div>
          {result.note && (
            <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs font-medium leading-snug text-amber-900">{result.note}</p>
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
      <p className="mb-3 text-[11px] font-semibold leading-snug text-slate-500 sm:text-xs">{t("conjugatorHint")}</p>
      <input
        value={verb}
        onChange={(e) => setVerb(e.target.value)}
        placeholder={t("verbPlaceholder")}
        enterKeyHint="go"
        className="mobile-field w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 font-medium text-slate-800 outline-none focus:border-teal-400"
        onKeyDown={(e) => e.key === "Enter" && verb.trim() && submit()}
      />
      <div className="no-scrollbar -mx-1 mt-3 flex gap-2 overflow-x-auto px-1 pb-1">
        {Object.entries(TENSE_KEYS).map(([id, key]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTense(id)}
            className={`shrink-0 whitespace-nowrap rounded-full px-3 py-2 text-xs font-bold sm:py-1.5 ${
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
        className="mobile-btn mt-3 w-full rounded-2xl bg-indigo-600 font-extrabold text-white disabled:opacity-50 active:scale-[0.99]"
      >
        {loading ? "…" : t("conjugateBtn")}
      </button>
      {error && <p className="mt-3 text-sm font-semibold text-red-600">{String(error)}</p>}
      {result && (
        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-100">
          <div className="bg-indigo-50 px-4 py-2.5">
            <div className="flex items-center justify-center gap-2">
              <p className="truncate text-sm font-extrabold text-indigo-800">{result.infinitive}</p>
              <SpeakButton text={result.infinitive} small />
            </div>
            <p className="text-center text-[11px] font-semibold text-indigo-600">
              {t(TENSE_KEYS[result.tense] || "tensePresent")}
            </p>
          </div>
          <table className="w-full text-left text-sm">
            <tbody>
              {result.forms.map((row) => (
                <tr key={row.pronoun} className="border-t border-slate-100">
                  <td className="w-[34%] px-3 py-2 text-xs font-bold text-slate-500 sm:px-4 sm:text-sm">{row.pronoun}</td>
                  <td className="px-2 py-2 sm:px-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-extrabold text-slate-800">{row.form}</span>
                      <SpeakButton text={row.form} small />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="border-t border-slate-100 px-4 py-2 text-[10px] font-medium leading-snug text-slate-400">
            {t("noVosotros")}
          </p>
        </div>
      )}
    </ToolSheet>
  );
}
