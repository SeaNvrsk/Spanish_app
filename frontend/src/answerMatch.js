/** Accent-insensitive Spanish answer matching for cloze and translate. */

const OPTIONAL_FILLERS = new Set([
  "yo",
  "tu",
  "el",
  "ella",
  "usted",
  "ustedes",
  "nosotros",
  "nosotras",
  "ellos",
  "ellas",
  "me",
  "te",
  "se",
  "mi",
  "un",
  "una",
  "unos",
  "unas",
  "los",
  "las",
  "lo",
  "la",
  "de",
  "a",
  "en",
  "y",
  "que",
]);

export function normalize(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[¿?¡!.,;:"'`´«»“”…—–()]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function tokens(s) {
  return normalize(s).split(" ").filter(Boolean);
}

function containsConsecutive(haystack, needle) {
  if (!needle.length || needle.length > haystack.length) return false;
  for (let i = 0; i <= haystack.length - needle.length; i += 1) {
    if (needle.every((tok, j) => haystack[i + j] === tok)) return true;
  }
  return false;
}

/**
 * Accept the target itself, or the target plus extra words that already
 * belong to the same Spanish phrase (so "estudié mucho" counts for "estudié").
 */
export function typedMatchesSpanish(typed, target, extraContext = "") {
  const typedTok = tokens(typed);
  const answerTok = tokens(target);
  if (!typedTok.length || !answerTok.length) return false;
  if (typedTok.length === answerTok.length && typedTok.every((tok, i) => tok === answerTok[i])) {
    return true;
  }
  if (!containsConsecutive(typedTok, answerTok)) return false;
  const allowed = new Set([...tokens(extraContext), ...answerTok, ...OPTIONAL_FILLERS]);
  return typedTok.every((tok) => allowed.has(tok));
}

export function isTranslateCorrect(ex, typed) {
  const targets = [ex.answer, ...(ex.accepted_answers || [])].filter(Boolean);
  const extra = [ex.es, ex.sentence, ex.audio].filter(Boolean).join(" ");
  return targets.some((target) => typedMatchesSpanish(typed, target, extra));
}

export function isClozeCorrect(ex, typed) {
  const template = String(ex.template || "");
  const parts = template.split("___");
  const pre = parts[0] || "";
  const post = parts.slice(1).join("___") || "";
  const filled = `${pre}${ex.answer || ""}${post}`;
  const sentence = ex.sentence || ex.es || filled;
  const targets = [ex.answer, ...(ex.accepted_answers || [])].filter(Boolean);
  return targets.some((target) => typedMatchesSpanish(typed, target, sentence));
}
