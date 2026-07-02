import { useEffect, useMemo, useRef, useState } from "react";
import api from "../api";
import { useI18n, nativeGloss } from "../i18n";
import { useSpeak } from "../tts";
import { WordImage } from "./WordImage";

export function normalize(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[¿?¡!.,;:"']/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function SpeakButton({ text, big }) {
  const { speak, speaking } = useSpeak();
  return (
    <button
      onClick={() => speak(text)}
      className={`flex items-center justify-center rounded-full bg-teal-500 text-white shadow-lg shadow-teal-500/40 transition active:scale-90 ${
        big ? "h-20 w-20 text-4xl" : "h-11 w-11 text-xl"
      } ${speaking ? "animate-pulse" : ""}`}
      aria-label="play audio"
    >
      🔊
    </button>
  );
}

// ------- Pronunciation (record → OpenAI transcription → score) -------
function SpeakExercise({ ex, onResult }) {
  const { t, lang } = useI18n();
  const [state, setState] = useState("idle"); // idle | recording | checking | result | error
  const [result, setResult] = useState(null); // {score, transcript, passed}
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    setState("idle");
    setResult(null);
  }, [ex.id]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop());
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" });
        await submit(blob);
      };
      mediaRef.current = mr;
      mr.start();
      setState("recording");
    } catch {
      setState("error");
    }
  };

  const stop = () => {
    if (mediaRef.current && mediaRef.current.state !== "inactive") mediaRef.current.stop();
    setState("checking");
  };

  const submit = async (blob) => {
    const fd = new FormData();
    fd.append("target", ex.es);
    fd.append("audio", blob, "speech.webm");
    try {
      const { data } = await api.post("/pronunciation/check", fd);
      setResult(data);
      setState("result");
    } catch {
      setState("error");
    }
  };

  const barColor = result && result.score >= 80 ? "bg-green-500" : result && result.score >= 60 ? "bg-amber-500" : "bg-red-400";

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-6 py-5">
        <span className="text-3xl font-black text-slate-800">{ex.es}</span>
        <SpeakButton text={ex.audio} />
      </div>
      <p className="text-sm font-semibold text-slate-500">{nativeGloss(ex.translations, lang)}</p>

      {state === "result" && result && (
        <div className="w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between text-sm font-bold text-slate-600">
            <span>{t("pronScore")}</span>
            <span>{result.score}%</span>
          </div>
          <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100">
            <div className={`h-full rounded-full ${barColor}`} style={{ width: `${result.score}%` }} />
          </div>
          <p className="mt-3 text-sm text-slate-500">
            {result.passed && result.asr_corrected ? (
              <>
                {t("pronAccepted")}:{" "}
                <span className="font-semibold text-slate-700">“{result.transcript || ex.es}”</span>
              </>
            ) : (
              <>
                {t("weHeard")}:{" "}
                <span className="font-semibold text-slate-700">“{result.transcript || "…"}”</span>
              </>
            )}
          </p>
          <p className={`mt-1 text-sm font-extrabold ${result.passed ? "text-green-600" : "text-amber-600"}`}>
            {result.passed ? t("greatAccent") : t("closePron")}
          </p>
        </div>
      )}

      {state === "error" && (
        <p className="text-center text-sm font-semibold text-slate-400">{t("micHint")}</p>
      )}

      {/* Controls */}
      {state === "idle" && (
        <button
          onClick={start}
          className="flex h-24 w-24 items-center justify-center rounded-full bg-rose-500 text-4xl text-white shadow-xl shadow-rose-500/40 transition active:scale-90"
        >
          🎙️
        </button>
      )}
      {state === "recording" && (
        <button
          onClick={stop}
          className="flex h-24 w-24 animate-pulse items-center justify-center rounded-full bg-rose-600 text-4xl text-white shadow-xl"
        >
          ⏹️
        </button>
      )}
      {state === "checking" && <div className="py-6 text-2xl">⏳ {t("checkingPron")}</div>}

      {state === "idle" && <p className="text-sm font-semibold text-slate-500">{t("tapToRecord")}</p>}
      {state === "recording" && <p className="text-sm font-semibold text-rose-500">{t("recordingNow")}</p>}

      {/* Result actions */}
      {(state === "result" || state === "error") && (
        <div className="flex w-full gap-3">
          <button
            onClick={() => { setState("idle"); setResult(null); }}
            className="flex-1 rounded-2xl border-2 border-slate-200 py-3 font-extrabold text-slate-600 active:scale-95"
          >
            {t("tryAgain")}
          </button>
          <button
            onClick={() => onResult(result ? result.passed : true)}
            className="flex-1 rounded-2xl bg-teal-600 py-3 font-extrabold text-white shadow-lg active:scale-95"
          >
            {state === "error" ? t("iSaidIt") : t("continue")}
          </button>
        </div>
      )}
    </div>
  );
}

export default function ExercisePlayer({ exercises, kind, onFinish }) {
  const { t, lang } = useI18n();
  const { speak } = useSpeak();

  const [idx, setIdx] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [scoredTotal, setScoredTotal] = useState(0);
  const [selected, setSelected] = useState(null);
  const [typed, setTyped] = useState("");
  const [status, setStatus] = useState("idle");
  const [infoOpen, setInfoOpen] = useState(false);
  const [infoLoading, setInfoLoading] = useState(false);
  const [infoData, setInfoData] = useState(null);
  const [infoError, setInfoError] = useState(false);
  const resultsRef = useRef([]);
  const autoSpoke = useRef(null);
  const finishedRef = useRef(false);

  const ex = exercises[idx];
  const total = exercises.length;
  const progressPct = Math.round((idx / total) * 100);

  useEffect(() => {
    if (ex && ex.type === "listen" && autoSpoke.current !== ex.id) {
      autoSpoke.current = ex.id;
      const tmo = setTimeout(() => speak(ex.audio), 350);
      return () => clearTimeout(tmo);
    }
  }, [ex, speak]);

  useEffect(() => {
    setInfoOpen(false);
    setInfoData(null);
    setInfoError(false);
    setInfoLoading(false);
  }, [ex?.id]);

  const options = useMemo(() => ex?.options || [], [ex]);
  if (!ex) return null;

  const isScored = ex.type !== "flashcard";

  const recordResult = (ok) => {
    resultsRef.current.push({
      word_es: ex.es || ex.answer || "",
      word_en: ex.translations?.en || "",
      word_ru: ex.translations?.ru || "",
      correct: ok,
    });
  };

  const finish = () => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    const score = scoredTotal > 0 ? Math.round((correctCount / scoredTotal) * 100) : 100;
    onFinish(resultsRef.current, score);
  };

  const advance = () => {
    setStatus("idle");
    setSelected(null);
    setTyped("");
    setInfoOpen(false);
    setInfoData(null);
    setInfoError(false);
    if (idx + 1 < total) setIdx(idx + 1);
    else finish();
  };

  const spanishTarget = ex.es || ex.answer || "";
  const glossEn = ex.translations?.en || "";
  const glossRu = ex.translations?.ru || "";

  const loadInfo = async () => {
    if (!spanishTarget) return;
    setInfoOpen(true);
    if (infoData && !infoError) return;
    setInfoLoading(true);
    setInfoError(false);
    try {
      const { data } = await api.post("/tools/explain", {
        spanish: spanishTarget,
        context_en: glossEn,
        context_ru: glossRu,
      });
      setInfoData(data);
    } catch {
      setInfoError(true);
      setInfoData(null);
    } finally {
      setInfoLoading(false);
    }
  };

  const evaluate = () => {
    let ok = false;
    if (ex.type === "translate" || ex.type === "cloze") ok = normalize(typed) === normalize(ex.answer);
    else ok = selected != null && selected === ex.answer;
    setStatus(ok ? "correct" : "wrong");
    setScoredTotal((n) => n + 1);
    if (ok) setCorrectCount((n) => n + 1);
    recordResult(ok);
  };

  // Pronunciation exercise handles its own UI/flow.
  const onSpeakResult = (ok) => {
    setScoredTotal((n) => n + 1);
    if (ok) setCorrectCount((n) => n + 1);
    recordResult(ok);
    advance();
  };

  const optionLabel = (o) => (ex.direction === "es_to_native" ? nativeGloss(o.translations, lang) : o.es);

  const promptKey =
    {
      flashcard: "tapToHear",
      listen: "listenPrompt",
      translate: "typePrompt",
      cloze: "clozePrompt",
      speak: "speakPrompt",
    }[ex.type] || (ex.direction === "es_to_native" ? "choosePrompt" : "chooseEsPrompt");

  const clozeParts = ex.type === "cloze" ? ex.template.split("___") : null;

  return (
    <div className="flex min-h-dvh flex-col bg-white">
      <div className="flex items-center gap-2 px-3 py-2.5 sm:px-4 sm:py-3">
        <button
          onClick={finish}
          className="touch-target flex shrink-0 items-center justify-center rounded-full text-xl text-slate-400 active:bg-slate-100"
          aria-label="Close"
        >
          ✕
        </button>
        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100 sm:h-3">
          <div className="h-full rounded-full bg-teal-500 transition-all" style={{ width: `${progressPct}%` }} />
        </div>
        <span className="shrink-0 text-[11px] font-bold tabular-nums text-slate-400 sm:text-xs">
          {idx + 1}/{total}
        </span>
      </div>

      <div className="flex flex-1 flex-col overflow-y-auto px-4 pt-2 sm:px-5 sm:pt-4">
        {(kind === "exam" || kind === "capstone") && (
          <div className="mb-3 rounded-xl bg-amber-100 px-4 py-2 text-center text-sm font-extrabold text-amber-700">
            {kind === "capstone" ? "🎓 " + t("finalExam") : "📝 " + t("examBonus")}
          </div>
        )}
        <p className="mb-4 text-base font-extrabold text-slate-800 sm:mb-6 sm:text-lg">{t(promptKey)}</p>

        {ex.type === "flashcard" && (
          <div className="flex flex-col items-center gap-5 rounded-3xl bg-teal-50 py-8 animate-pop sm:py-10">
            {ex.image_url && <WordImage url={ex.image_url} alt={ex.es} />}
            <SpeakButton text={ex.audio} big />
            <div className="text-4xl font-black text-slate-800">{ex.es}</div>
            <div className="text-lg font-semibold text-teal-700">{nativeGloss(ex.translations, lang)}</div>
          </div>
        )}

        {ex.type === "listen" && (
          <div className="mb-6 flex justify-center">
            <SpeakButton text={ex.audio} big />
          </div>
        )}

        {ex.type === "choice" && ex.direction === "es_to_native" && (
          <div className="mb-6 flex flex-col items-center gap-3 rounded-2xl bg-slate-50 py-6">
            {ex.image_url && <WordImage url={ex.image_url} alt={ex.es} className="max-h-36" />}
            <div className="flex items-center justify-center gap-3">
              <span className="text-3xl font-black text-slate-800">{ex.es}</span>
              <SpeakButton text={ex.audio} />
            </div>
          </div>
        )}

        {ex.type === "choice" && ex.direction === "native_to_es" && (
          <div className="mb-6 flex flex-col items-center gap-3 rounded-2xl bg-slate-50 py-6">
            {ex.image_url && <WordImage url={ex.image_url} alt={ex.es} className="max-h-36" />}
            <span className="text-2xl font-black text-slate-800">{nativeGloss(ex.translations, lang)}</span>
          </div>
        )}

        {(ex.type === "choice" || ex.type === "listen") && (
          <div className="grid grid-cols-1 gap-3">
            {options.map((o) => {
              const isSel = selected === o.es;
              let cls = "border-slate-200 bg-white";
              if (status === "idle" && isSel) cls = "border-teal-500 bg-teal-50";
              if (status !== "idle" && o.es === ex.answer) cls = "border-green-500 bg-green-50";
              else if (status !== "idle" && isSel) cls = "border-red-400 bg-red-50";
              return (
                <button
                  key={o.es}
                  disabled={status !== "idle"}
                  onClick={() => setSelected(o.es)}
                  className={`flex min-h-[52px] items-center justify-between rounded-2xl border-2 px-4 py-3.5 text-left text-base font-bold text-slate-700 transition active:scale-[0.98] sm:px-5 sm:py-4 sm:text-lg ${cls}`}
                >
                  <span>{optionLabel(o)}</span>
                </button>
              );
            })}
          </div>
        )}

        {ex.type === "translate" && (
          <>
            <div className="mb-4 flex items-center justify-center rounded-2xl bg-slate-50 py-6">
              <span className="text-2xl font-black text-slate-800">{nativeGloss(ex.translations, lang)}</span>
            </div>
            <input
              autoFocus
              value={typed}
              disabled={status !== "idle"}
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && status === "idle" && typed.trim() && evaluate()}
              placeholder={t("typeHere")}
              className="w-full rounded-2xl border-2 border-slate-200 px-5 py-4 text-xl font-bold text-slate-800 outline-none focus:border-teal-500"
            />
          </>
        )}

        {ex.type === "cloze" && (
          <>
            <div className="mb-3 flex flex-wrap items-center justify-center gap-x-2 gap-y-3 rounded-2xl bg-slate-50 px-4 py-6 text-2xl font-black text-slate-800">
              <span>{clozeParts[0]}</span>
              <span className="inline-block min-w-[80px] rounded-lg border-b-4 border-teal-400 bg-white px-3 py-1 text-center text-teal-600">
                {status !== "idle" ? ex.answer : typed || "?"}
              </span>
              <span>{clozeParts[1]}</span>
              <SpeakButton text={ex.audio} />
            </div>
            <p className="mb-4 text-center text-sm font-semibold text-slate-500">
              {nativeGloss(ex.translations, lang)}
            </p>
            <input
              autoFocus
              value={typed}
              disabled={status !== "idle"}
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && status === "idle" && typed.trim() && evaluate()}
              placeholder={t("typeHere")}
              className="w-full rounded-2xl border-2 border-slate-200 px-5 py-4 text-xl font-bold text-slate-800 outline-none focus:border-teal-500"
            />
          </>
        )}

        {ex.type === "speak" && <SpeakExercise ex={ex} onResult={onSpeakResult} />}
      </div>

      {/* Feedback + action bar (not for speak, which manages its own buttons) */}
      {ex.type !== "speak" && (
        <div
          className={`sticky bottom-0 shrink-0 px-4 pb-safe pt-3 sm:px-5 sm:pt-4 ${
            status === "correct" ? "bg-green-50" : status === "wrong" ? "bg-red-50" : "bg-white"
          }`}
        >
          {status !== "idle" && (
            <div className="mb-3">
              <p className={`font-extrabold ${status === "correct" ? "text-green-600" : "text-red-500"}`}>
                {status === "correct" ? "✓ " + t("correct") : "✗ " + t("incorrect")}
              </p>
              {status === "wrong" && (
                <p className="text-sm font-semibold text-slate-600">
                  {t("theAnswer")}: <span className="text-slate-900">{ex.answer}</span>
                </p>
              )}
              {status === "correct" && spanishTarget && (
                <div className="mt-3">
                  {!infoOpen ? (
                    <button
                      type="button"
                      onClick={loadInfo}
                      className="w-full rounded-xl border-2 border-teal-200 bg-teal-50 py-2.5 text-sm font-extrabold text-teal-700 active:scale-[0.99]"
                    >
                      ℹ️ {t("information")}
                    </button>
                  ) : (
                    <div className="rounded-xl border border-teal-100 bg-white p-3 text-left shadow-sm">
                      {infoLoading && <p className="text-sm font-semibold text-slate-500">{t("infoLoading")}</p>}
                      {infoError && !infoLoading && (
                        <p className="text-sm font-semibold text-red-500">{t("infoError")}</p>
                      )}
                      {infoData && !infoLoading && (
                        <div className="space-y-2 text-sm text-slate-700">
                          <p>
                            <span className="font-extrabold text-slate-800">{t("infoMeaning")}: </span>
                            {infoData.meaning}
                          </p>
                          <p>
                            <span className="font-extrabold text-slate-800">{t("infoMexicoUsage")}: </span>
                            {infoData.mexico_usage}
                          </p>
                          {infoData.example && (
                            <p className="rounded-lg bg-teal-50 px-3 py-2 italic text-teal-800">
                              “{infoData.example}”
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {ex.type === "flashcard" || status !== "idle" ? (
            <button
              onClick={advance}
              className={`w-full rounded-2xl py-4 font-extrabold text-white shadow-lg active:scale-95 sm:py-3.5 ${
                status === "wrong" ? "bg-red-500" : "bg-teal-600"
              }`}
            >
              {ex.type === "flashcard" ? t("gotIt") : t("continue")}
            </button>
          ) : (
            <button
              onClick={evaluate}
              disabled={ex.type === "translate" || ex.type === "cloze" ? !typed.trim() : selected == null}
              className="w-full rounded-2xl bg-teal-600 py-4 font-extrabold text-white shadow-lg transition active:scale-95 disabled:bg-slate-200 disabled:text-slate-400 sm:py-3.5"
            >
              {t("check")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
