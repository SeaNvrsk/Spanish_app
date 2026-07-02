import { useI18n, localized } from "../i18n";
import { appPath } from "../appBase";
import { SpeakButton } from "./ExercisePlayer";

function SectionTitle({ icon, children }) {
  return (
    <h3 className="mb-3 flex items-center gap-2 text-sm font-extrabold uppercase tracking-wide text-teal-600">
      <span className="text-base">{icon}</span>
      {children}
    </h3>
  );
}

export default function TheoryScreen({ lesson, onStart, onClose }) {
  const { t, lang } = useI18n();
  const th = lesson.theory;
  const grammarSections = th.grammar_sections?.[lang] || th.grammar_sections?.en || [];
  const grammarPoints = th.grammar_points?.[lang] || th.grammar_points?.en || [];
  const newWords = th.new_words || [];
  const examples = th.examples || [];

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-white">
      <div className="flex shrink-0 items-center gap-2 border-b border-slate-100 px-3 py-2.5 sm:px-4 sm:py-3">
        <button
          onClick={onClose}
          className="touch-target flex shrink-0 items-center justify-center rounded-full text-xl text-slate-400 active:bg-slate-100"
          aria-label="Close"
        >
          ✕
        </button>
        <span className="truncate font-extrabold text-slate-700">{localized(lesson.theme, lang)}</span>
        {lesson.day_in_week && (
          <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
            {t("day")} {lesson.day_in_week}/6
          </span>
        )}
        {lesson.est_minutes && (
          <span className="ml-auto rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-600">
            ~{lesson.est_minutes} {t("minAbbr")}
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 pb-4 sm:px-5 sm:pb-6">
        {th.day_focus && (
          <div className="mt-3 rounded-2xl border-2 border-teal-200 bg-gradient-to-br from-teal-50 to-emerald-50/80 p-4 shadow-sm">
            <p className="text-[15px] font-bold leading-relaxed text-teal-900">{localized(th.day_focus, lang)}</p>
          </div>
        )}

        {th.intro && (
          <div className="mt-5 rounded-2xl bg-slate-50 p-4">
            <p className="text-[15px] leading-relaxed font-semibold text-slate-700">{localized(th.intro, lang)}</p>
          </div>
        )}

        {newWords.length > 0 && (
          <section className="mt-6">
            <SectionTitle icon="📚">
              {t("theoryWordsTitle")}
              <span className="ml-1 rounded-full bg-teal-100 px-2 py-0.5 text-[11px] font-black text-teal-700">
                {newWords.length}
              </span>
            </SectionTitle>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {newWords.map((w) => (
                <div
                  key={w.es}
                  className="flex items-center gap-3 rounded-xl border border-slate-100 bg-white p-3 shadow-sm"
                >
                  {w.image_url ? (
                    <img
                      src={w.image_url.startsWith("http") ? w.image_url : appPath(w.image_url)}
                      alt={w.es}
                      loading="lazy"
                      className="h-12 w-12 shrink-0 rounded-lg object-cover shadow-sm"
                    />
                  ) : (
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-lg">
                      🇲🇽
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-base font-black text-slate-800">{w.es}</p>
                    <p className="truncate text-sm text-slate-500">{lang === "ru" ? w.ru : w.en}</p>
                  </div>
                  <SpeakButton text={w.es} />
                </div>
              ))}
            </div>
          </section>
        )}

        {(grammarSections.length > 0 || grammarPoints.length > 0) && (
          <section className="mt-6">
            <SectionTitle icon="📘">{t("grammarTitle")}</SectionTitle>
            <div className="space-y-2.5">
              {grammarSections.length > 0
                ? grammarSections.map((section, i) => (
                    <div
                      key={i}
                      className="overflow-hidden rounded-xl border border-slate-100 bg-white shadow-sm"
                    >
                      <div className="border-b border-teal-100 bg-teal-50/60 px-3.5 py-2">
                        <p className="text-sm font-extrabold text-teal-800">{section.title}</p>
                      </div>
                      <p className="px-3.5 py-3 text-[15px] leading-relaxed text-slate-700">{section.text}</p>
                    </div>
                  ))
                : grammarPoints.map((point, i) => (
                    <div
                      key={i}
                      className="flex gap-3 rounded-xl border border-slate-100 bg-white p-3.5 shadow-sm"
                    >
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-teal-100 text-xs font-black text-teal-700">
                        {i + 1}
                      </span>
                      <p className="text-[15px] leading-relaxed text-slate-700">{point}</p>
                    </div>
                  ))}
            </div>
          </section>
        )}

        {examples.length > 0 && (
          <section className="mt-6">
            <SectionTitle icon="🔊">{t("listenTitle")}</SectionTitle>
            <div className="space-y-2.5">
              {examples.map((exm, i) => (
                <div
                  key={`${exm.es}-${i}`}
                  className="flex items-center gap-3 rounded-xl border border-teal-100 bg-gradient-to-r from-white to-teal-50/40 p-3.5 shadow-sm"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-500 text-sm font-black text-white">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-base font-bold text-slate-800">{exm.es}</p>
                    <p className="text-sm text-slate-500">{lang === "ru" ? exm.ru : exm.en}</p>
                  </div>
                  <SpeakButton text={exm.es} />
                </div>
              ))}
            </div>
          </section>
        )}

        {th.tip && (
          <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <h3 className="mb-2 flex items-center gap-2 text-sm font-extrabold uppercase tracking-wide text-amber-600">
              <span>🌵</span> {t("tipTitle")}
            </h3>
            <p className="text-[15px] font-semibold leading-relaxed text-amber-900">{localized(th.tip, lang)}</p>
          </div>
        )}
      </div>

      <div className="shrink-0 border-t border-slate-100 bg-white px-4 pb-safe pt-3 sm:px-5">
        <button
          onClick={onStart}
          className="w-full rounded-2xl bg-teal-600 py-4 font-extrabold text-white shadow-lg active:scale-95 sm:py-3.5"
        >
          {t("startExercises")} →
        </button>
      </div>
    </div>
  );
}
