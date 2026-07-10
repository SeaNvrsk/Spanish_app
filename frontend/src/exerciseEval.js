import { nativeGloss } from "./i18n";

export function normalize(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[¿?¡!.,;:"'()]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function glossKey(translations, lang) {
  return normalize(nativeGloss(translations, lang));
}

/** Same word sense when RU or EN gloss matches (e.g. chao / Adiós → «пока»). */
export function sameMeaning(transA, transB) {
  const ruA = glossKey(transA, "ru");
  const ruB = glossKey(transB, "ru");
  if (ruA && ruB && ruA === ruB) return true;
  const enA = glossKey(transA, "en");
  const enB = glossKey(transB, "en");
  return Boolean(enA && enB && enA === enB);
}

/** Accept answers that share the same translation (e.g. chao / Adiós → «пока»). */
export function isChoiceCorrect(ex, selectedEs, options, lang) {
  if (selectedEs == null || selectedEs === "") return false;
  if (selectedEs === ex.answer) return true;
  if (ex.direction !== "es_to_native" && ex.direction !== "native_to_es") return false;
  const answerOpt = options.find((o) => o.es === ex.answer);
  const selectedOpt = options.find((o) => o.es === selectedEs);
  if (!answerOpt || !selectedOpt) return false;
  return sameMeaning(answerOpt.translations, selectedOpt.translations);
}

export function isTranslateCorrect(ex, typed) {
  const t = normalize(typed);
  if (!t) return false;
  if (t === normalize(ex.answer)) return true;
  return (ex.accepted_answers || []).some((a) => normalize(a) === t);
}

export function isSynonymOption(ex, option, options, lang) {
  if (option.es === ex.answer) return true;
  const answerOpt = options.find((o) => o.es === ex.answer);
  if (!answerOpt) return false;
  return sameMeaning(answerOpt.translations, option.translations);
}
