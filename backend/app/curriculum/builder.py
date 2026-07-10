"""Builds the full 365-day program from authored weeks.

- Each authored WEEK -> 6 daily lessons + 1 weekly exam (7 days).
- Weeks not authored in detail are auto-generated as spiral-review weeks that
  reuse previously learned vocabulary.
- Daily lessons introduce a few new words AND review earlier words (spaced
  repetition), so learned vocabulary keeps coming back.
- A final capstone exam is day 365.
"""

import random
import re
import copy
import unicodedata
from functools import lru_cache
from typing import Dict, List, Optional

from .program import WEEKS, t
from .a1_boost import A1_BOOST
from .a1_boost_extra import A1_BOOST_EXTRA
from .a1_theory_enrichment import enrich_a1_theory
from ..vocab_images import attach_image, image_url_for

AVATARS = ["🦊", "🐱", "🐶", "🐼", "🦉", "🐸", "🦁", "🐨", "🐵", "🦄", "🐷", "🐯"]

TOTAL_WEEKS = 52
DAYS_PER_WEEK = 7           # 6 lessons + 1 exam
LESSONS_PER_WEEK = 6
PESOS_LESSON = 5
PESOS_EXAM = 15
PESOS_CAPSTONE = 38
NEW_WORDS_MIN_PER_DAY = 4
REVIEW_WORDS_PER_DAY = 6
WITHIN_WEEK_REVIEW = 3          # quiz-only review of earlier words this week (from day 3)
QUIZ_REINFORCE_PASS = True      # second quiz round from day 4 when 8+ new words
SPEAK_WORDS_MAX = 3             # pronunciation on key new words
EXAM_QUESTIONS = 30
EXAM_LISTEN_COUNT = 10
# Realistic per-exercise time (includes reading, audio replays, thinking, feedback).
SECONDS_PER_EXERCISE = {"flashcard": 30, "choice": 40, "listen": 45, "translate": 70, "cloze": 75, "speak": 60}
THEORY_READ_SECONDS = 240

SUBJECT_PRONOUNS = {"yo", "tú", "él", "ella", "nosotros", "ustedes", "ellos", "usted"}
PRONOUN_DRILL_TEMPLATES = [
    ("___ soy estudiante.", "yo", "I am a student.", "Я студент."),
    ("___ eres mi amigo.", "tú", "You are my friend.", "Ты мой друг."),
    ("___ es profesor.", "él", "He is a teacher.", "Он учитель."),
    ("___ es doctora.", "ella", "She is a doctor.", "Она врач."),
    ("___ somos de México.", "nosotros", "We are from Mexico.", "Мы из Мексики."),
    ("___ son mis amigos.", "ellos", "They are my friends.", "Они мои друзья."),
    ("¿___ te llamas?", "Cómo", "What's your name?", "Как тебя зовут?"),
    ("Me ___ Ana.", "llamo", "My name is Ana.", "Меня зовут Ана."),
]


@lru_cache(maxsize=1)
def _cloze_gloss_index() -> Dict[tuple, str]:
    """Map (answer, en, ru) -> full Spanish sentence for repairing fragment SRS cards."""
    index: Dict[tuple, str] = {}

    def add(template: str, answer: str, en: str, ru: str):
        filled = template.replace("___", answer)
        index[(_norm(answer), (en or "").strip(), (ru or "").strip())] = filled

    for wk in WEEKS:
        for ch in wk.get("chunks", []):
            add(ch["template"], ch["answer"], ch["en"], ch["ru"])
    for template, answer, en, ru in PRONOUN_DRILL_TEMPLATES:
        add(template, answer, en, ru)
    return index


def normalize_vocab_entry(es: str, en: str = "", ru: str = "") -> dict:
    """Align Spanish text with its gloss (fixes legacy cloze cards that stored only the blank)."""
    es = (es or "").strip()
    en = (en or "").strip()
    ru = (ru or "").strip()
    if not es:
        return {"es": es, "translations": {"en": en, "ru": ru}}

    index = _cloze_gloss_index()
    exact = index.get((_norm(es), en, ru))
    if exact:
        return {"es": exact, "translations": {"en": en, "ru": ru}}

    if " " not in es:
        for (ans, fen, fru), filled in index.items():
            if ans == _norm(es) and (fen == en or fru == ru):
                return {"es": filled, "translations": {"en": fen or en, "ru": fru or ru}}

    return {"es": es, "translations": {"en": en, "ru": ru}}


def repair_card_vocab(es: str, en: str = "", ru: str = "") -> dict:
    """Normalized card fields for SRS (es/en/ru aligned)."""
    n = normalize_vocab_entry(es, en, ru)
    return {
        "es": n["es"],
        "en": n["translations"]["en"],
        "ru": n["translations"]["ru"],
    }


LEVEL_MONTHS = {"A1": 3, "A2": 6, "B1": 12}
LEVEL_MONTH_RANGE = {"A1": (1, 3), "A2": (4, 6), "B1": (7, 12)}
LEVEL_TITLE = {
    "A1": t("A1 — Beginner", "A1 — Начальный", "A1 — Principiante"),
    "A2": t("A2 — Elementary", "A2 — Базовый", "A2 — Elemental"),
    "B1": t("B1 — Intermediate", "B1 — Средний", "B1 — Intermedio"),
}
LEVEL_DESC = {
    "A1": t("Survive your first conversations in Mexican Spanish.",
            "Первые разговоры на мексиканском испанском.",
            "Sobrevive tus primeras conversaciones en español mexicano."),
    "A2": t("Handle everyday situations and talk about your routine.",
            "Повседневные ситуации и рассказ о своём дне.",
            "Maneja situaciones cotidianas y habla de tu rutina."),
    "B1": t("Express opinions, plans and hold real conversations.",
            "Выражай мнения, планы и веди настоящие беседы.",
            "Expresa opiniones, planes y sostén conversaciones reales."),
}

REVIEW_THEORY = {
    "intro": t(
        "Spiral review week: no new grammar — you strengthen everything you've learned so far.",
        "Неделя спирального повторения: без новой грамматики — закрепляем всё пройденное.",
        "Semana de repaso en espiral: sin gramática nueva; refuerzas todo lo aprendido."),
    "grammar": t(
        "Revisit verbs (ser/estar, past & future), agreement and connectors. Mix them freely as you practice.",
        "Повторите глаголы (ser/estar, прошлое и будущее), согласование и связки. Свободно смешивайте их.",
        "Repasa verbos (ser/estar, pasado y futuro), concordancia y conectores; mézclalos al practicar."),
    "examples": [
        {"es": "Ayer fui al mercado y compré fruta.", "en": "Yesterday I went to the market and bought fruit.", "ru": "Вчера я ходил на рынок и купил фрукты."},
        {"es": "Creo que mañana hará buen clima.", "en": "I think the weather will be nice tomorrow.", "ru": "Думаю, завтра будет хорошая погода."},
    ],
    "tip": t("Repetition is the secret to fluency — revisiting words moves them into long-term memory.",
             "Повторение — секрет беглости: возврат к словам переводит их в долговременную память.",
             "La repetición es la clave: reencontrar palabras las fija en la memoria."),
}


def _vi(raw):
    es, en, ru = raw
    return attach_image({"es": es, "translations": {"en": en, "ru": ru}})


def _norm(text: str) -> str:
    """Lowercase and strip accents so 'días' and 'dias' compare equal."""
    text = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _norm_gloss(text: str) -> str:
    t = _norm(text)
    t = re.sub(r"[¿?¡!.,;:\"'()]", " ", t)
    return " ".join(t.split())


def _en_sense(en: str) -> str:
    """Collapse near-synonym English glosses (bye / goodbye) without merging unrelated senses."""
    t = _norm(en)
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"[¿?¡!.,;:\"'/]", " ", t)
    t = " ".join(t.split())
    if t in {"goodbye", "good bye", "bye", "bye bye", "so long"} or t.startswith("bye "):
        return "goodbye"
    return t


def _same_meaning(a: dict, b: dict) -> bool:
    """True when two vocab entries share the same RU gloss and compatible EN sense."""
    ta, tb = a.get("translations") or {}, b.get("translations") or {}
    ru_a, ru_b = _norm_gloss(ta.get("ru", "")), _norm_gloss(tb.get("ru", ""))
    if not ru_a or not ru_b or ru_a != ru_b:
        return False
    en_a, en_b = _en_sense(ta.get("en", "")), _en_sense(tb.get("en", ""))
    if en_a and en_b:
        return en_a == en_b
    return True


@lru_cache
def _all_program_vocab() -> tuple:
    """Every unique vocab item in the program (weeks + A1 boost)."""
    seen, pool = set(), []
    for wk in WEEKS:
        for raw in wk.get("vocab", []):
            v = _vi(raw)
            if v["es"] in seen:
                continue
            seen.add(v["es"])
            pool.append(v)
    for w in range(1, TOTAL_WEEKS + 1):
        if w in A1_BOOST:
            for raw in A1_BOOST[w] + A1_BOOST_EXTRA.get(w, []):
                v = _vi(raw)
                if v["es"] in seen:
                    continue
                seen.add(v["es"])
                pool.append(v)
    return tuple(pool)


@lru_cache(maxsize=1)
def _synonym_index() -> Dict[str, tuple]:
    """Map (ru_gloss, en_sense) → Spanish synonyms. Built once, O(vocab)."""
    by_key: Dict[str, set] = {}
    for item in _all_program_vocab():
        ta = item.get("translations") or {}
        ru = _norm_gloss(ta.get("ru", ""))
        if not ru:
            continue
        en = _en_sense(ta.get("en", "")) or "_"
        key = f"{ru}|{en}"
        by_key.setdefault(key, set()).add(item["es"])
    return {k: tuple(sorted(v)) for k, v in by_key.items()}


def _accepted_es_answers(v: dict) -> List[str]:
    """O(1) synonym lookup via prebuilt gloss index (chao / Adiós → пока)."""
    ta = v.get("translations") or {}
    ru = _norm_gloss(ta.get("ru", ""))
    if not ru:
        return [v["es"]]
    en = _en_sense(ta.get("en", "")) or "_"
    hit = _synonym_index().get(f"{ru}|{en}")
    return list(hit) if hit else [v["es"]]


def _word_tokens(text: str) -> set:
    """Whole-word tokens of a phrase (accent-insensitive)."""
    return set(re.findall(r"[a-z]+", _norm(text)))


def _vocab_tokens(items: List[dict]) -> set:
    tokens = set()
    for v in items:
        tokens |= _word_tokens(v["es"])
    return tokens


def _split_grammar_points(grammar: dict) -> dict:
    """Turn a grammar paragraph into short bullet-friendly points per language."""
    out = {}
    for lang in ("en", "ru", "es"):
        text = (grammar.get(lang) or "").strip()
        if not text:
            out[lang] = []
            continue
        parts = []
        for chunk in re.split(r"(?<=[.!?])\s+", text):
            chunk = chunk.strip()
            if not chunk:
                continue
            if ";" in chunk:
                parts.extend(p.strip() for p in chunk.split(";") if p.strip())
            else:
                parts.append(chunk)
        out[lang] = parts or [text]
    return out


def _listen_examples(week_meta: dict, new_vocab: List[dict], taught_tokens: set, base_examples: List[dict], limit: int = 5) -> List[dict]:
    """Build several listenable phrases for today's theory screen."""
    allowed = set(taught_tokens) | _vocab_tokens(new_vocab)
    new_only = _vocab_tokens(new_vocab)
    seen: set[str] = set()
    out: List[dict] = []

    def add(ex: dict):
        es = (ex.get("es") or "").strip()
        if not es or es in seen:
            return
        seen.add(es)
        out.append({"es": es, "en": ex.get("en", ""), "ru": ex.get("ru", "")})

    for ex in base_examples:
        if _word_tokens(ex["es"]) & new_only:
            add(ex)

    new_answers = {_norm(v["es"]) for v in new_vocab}
    for ch in week_meta.get("chunks", []):
        if _norm(ch.get("answer", "")) in new_answers:
            filled = ch["template"].replace("___", ch["answer"])
            add({"es": filled, "en": ch.get("en", ""), "ru": ch.get("ru", "")})

    for ex in base_examples:
        if _word_tokens(ex["es"]).issubset(allowed):
            add(ex)

    for ch in week_meta.get("chunks", []):
        filled = ch["template"].replace("___", ch["answer"])
        if _word_tokens(filled).issubset(allowed):
            add({"es": filled, "en": ch.get("en", ""), "ru": ch.get("ru", "")})

    if len(out) < limit:
        for ex in base_examples:
            add(ex)
            if len(out) >= limit:
                break

    return out[:limit]


def _est_minutes(exercises: List[dict], has_theory: bool = False) -> int:
    secs = sum(SECONDS_PER_EXERCISE.get(e.get("type"), 30) for e in exercises)
    if has_theory:
        secs += THEORY_READ_SECONDS
    return max(10, round(secs / 60))


def _cloze_exercise(ex_id, chunk):
    """Fill-in-the-blank in a real sentence (contextual active recall)."""
    filled = chunk["template"].replace("___", chunk["answer"])
    out = {
        "id": ex_id, "type": "cloze",
        "template": chunk["template"], "answer": chunk["answer"], "sentence": filled,
        "es": filled,
        "translations": {"en": chunk["en"], "ru": chunk["ru"]},
        "audio": filled,
    }
    url = image_url_for(chunk["answer"])
    if url:
        out["image_url"] = url
    return out


def _speak_exercise(ex_id, v):
    """Pronunciation practice: the learner records and gets a score."""
    out = {
        "id": ex_id, "type": "speak",
        "es": v["es"], "translations": v["translations"], "audio": v["es"],
    }
    if v.get("image_url"):
        out["image_url"] = v["image_url"]
    return out


def _quiz_exercise(rng, ex_id, v, pool, i, force_type=None):
    """Build one quiz exercise (no flashcard), cycling through 4 types."""
    types = ["choice_es_to_native", "listen", "choice_native_to_es", "translate"]
    ex_type = force_type if force_type else types[i % len(types)]
    base = {"id": ex_id, "es": v["es"], "translations": v["translations"], "audio": v["es"]}
    if v.get("image_url"):
        base["image_url"] = v["image_url"]

    def distractors(n=3):
        cands = [c for c in pool if c["es"] != v["es"]]
        rng.shuffle(cands)
        seen, out = set(), []
        for c in cands:
            if c["es"] in seen:
                continue
            seen.add(c["es"])
            out.append(c)
            if len(out) >= n:
                break
        return out

    if ex_type in ("choice_es_to_native", "listen"):
        opts = [v] + distractors()
        rng.shuffle(opts)
        base.update({
            "type": "listen" if ex_type == "listen" else "choice",
            "direction": "es_to_native",
            "options": [{"es": o["es"], "translations": o["translations"]} for o in opts],
            "answer": v["es"],
        })
    elif ex_type == "choice_native_to_es":
        opts = [v] + distractors()
        rng.shuffle(opts)
        base.update({
            "type": "choice", "direction": "native_to_es",
            "options": [{"es": o["es"], "translations": o["translations"]} for o in opts],
            "answer": v["es"],
        })
    else:
        base.update({"type": "translate", "direction": "native_to_es", "answer": v["es"]})
    base["accepted_answers"] = _accepted_es_answers(v)
    return base


def _theory_for_day(week_meta, global_day, day_in_week, taught_tokens, new_vocab):
    """Theory block with day-specific focus; AI tip is injected at request time in the API."""
    base = week_meta.get("theory")
    if not base:
        return None
    th = copy.deepcopy(base)
    th["new_words"] = [
        {
            "es": v["es"],
            "en": v["translations"]["en"],
            "ru": v["translations"]["ru"],
            **({"image_url": v["image_url"]} if v.get("image_url") else {}),
        }
        for v in new_vocab
    ]
    th["grammar_points"] = _split_grammar_points(th.get("grammar", {}))
    th["examples"] = _listen_examples(
        week_meta, new_vocab, taught_tokens, th.get("examples", []), limit=6,
    )

    week_num = week_meta.get("week")
    if week_meta.get("level") == "A1" and week_num:
        enrich_a1_theory(th, week_num, day_in_week, new_vocab, taught_tokens, week_meta, _listen_examples)
    else:
        words = ", ".join(v["es"] for v in new_vocab[:6])
        if len(new_vocab) > 6:
            words += "…"
        th["day_focus"] = t(
            f"Day {day_in_week}/6 — learn {len(new_vocab)} new words today ({words}). "
            f"Read the grammar carefully, listen to every example, then practice.",
            f"День {day_in_week}/6 — сегодня {len(new_vocab)} новых слов ({words}). "
            f"Внимательно прочитайте грамматику, прослушайте примеры и практикуйтесь.",
            f"Día {day_in_week}/6 — hoy {len(new_vocab)} palabras nuevas ({words}). "
            f"Lee la gramática, escucha los ejemplos y practica.",
        )
    return th


def _pronoun_drills(lid, rng, new_vocab, taught_vocab):
    """Extra cloze drills when pronouns or introductions appear."""
    known = {_norm(v["es"]) for v in taught_vocab + new_vocab}
    new_tokens = {_norm(v["es"]) for v in new_vocab}
    has_pronoun = bool(new_tokens & {_norm(p) for p in SUBJECT_PRONOUNS})
    has_intro = any(w in known for w in (_norm("llamo"), _norm("llamas"), _norm("llama")))
    if not has_pronoun and not has_intro:
        return []
    out = []
    for i, (template, answer, en, ru) in enumerate(PRONOUN_DRILL_TEMPLATES):
        if _norm(answer) not in known:
            continue
        out.append(_cloze_exercise(f"{lid}-pd{i}", {
            "template": template, "answer": answer, "en": en, "ru": ru,
        }))
        if len(out) >= 3:
            break
    return out


def _day_lesson(lid, week_meta, day_in_week, global_day, new_vocab, review_pool,
                distractor_pool, chunks, week_so_far_vocab, taught_tokens):
    """A 15-20 min learning day: theory -> preview -> retrieval -> context -> production -> review."""
    rng = random.Random(lid)
    exercises = []

    # 1) Preview new words with flashcards (with audio)
    for i, v in enumerate(new_vocab):
        exercises.append({
            "id": f"{lid}-fc{i}", "type": "flashcard",
            "es": v["es"], "translations": v["translations"], "audio": v["es"],
            **({"image_url": v["image_url"]} if v.get("image_url") else {}),
        })

    # 2) Retrieval practice on the new words (mixed types)
    for i, v in enumerate(new_vocab):
        exercises.append(_quiz_exercise(rng, f"{lid}-q{i}", v, distractor_pool, i))

    # 2b) Second reinforcement pass (from day 4, when 8+ new words)
    if QUIZ_REINFORCE_PASS and len(new_vocab) >= 8 and day_in_week >= 4:
        for i, v in enumerate(new_vocab):
            exercises.append(_quiz_exercise(rng, f"{lid}-q2{i}", v, distractor_pool, i + 2))

    # 3) Within-week review — quiz on words from earlier days (from day 3)
    if week_so_far_vocab and day_in_week >= 3:
        n = min(WITHIN_WEEK_REVIEW, len(week_so_far_vocab))
        picks = rng.sample(week_so_far_vocab, n)
        for i, v in enumerate(picks):
            exercises.append(_quiz_exercise(rng, f"{lid}-wr{i}", v, distractor_pool + week_so_far_vocab, i + 3))

    # 4) Contextual cloze from this week's example sentences
    for i, ch in enumerate(chunks):
        exercises.append(_cloze_exercise(f"{lid}-cz{i}", ch))

    # 4b) Pronoun / introduction grammar drills when relevant
    exercises.extend(_pronoun_drills(lid, rng, new_vocab, distractor_pool))

    # 5) Pronunciation — up to SPEAK_WORDS_MAX key new words
    for i, v in enumerate(new_vocab[:SPEAK_WORDS_MAX]):
        exercises.append(_speak_exercise(f"{lid}-sp{i}", v))

    # 6) Interleaved spaced review of earlier weeks (active recall)
    if review_pool:
        picks = rng.sample(review_pool, min(REVIEW_WORDS_PER_DAY, len(review_pool)))
        for i, v in enumerate(picks):
            exercises.append(_quiz_exercise(rng, f"{lid}-r{i}", v, distractor_pool + review_pool, i + 1))

    th = _theory_for_day(week_meta, global_day, day_in_week, taught_tokens, new_vocab)
    return {
        "id": lid, "kind": "lesson", "week": week_meta["week"], "day_in_week": day_in_week,
        "day": global_day, "level": week_meta["level"], "icon": week_meta["icon"],
        "theme": week_meta["theme"], "title": week_meta["theme"],
        "theory": th,
        "pesos": PESOS_LESSON, "new_vocab_count": len(new_vocab),
        "est_minutes": _est_minutes(exercises, has_theory=th is not None),
        "exercises": exercises,
    }


def _exam_lesson(lid, week_meta, global_day, week_vocab, review_pool, distractor_pool, chunks):
    """Weekly exam: 30 mixed questions — 10 listening + 20 choice/translate."""
    rng = random.Random(lid + "-exam")
    pool: List[dict] = []
    seen: set[str] = set()
    for source in (week_vocab, review_pool or [], distractor_pool or []):
        for v in source:
            if v["es"] in seen:
                continue
            seen.add(v["es"])
            pool.append(v)
    if not pool:
        pool = list(week_vocab) or list(review_pool or []) or list(distractor_pool or [])

    target_questions = EXAM_QUESTIONS if pool else 0
    word_picks: List[dict] = []
    if pool:
        while len(word_picks) < target_questions:
            batch = list(pool)
            rng.shuffle(batch)
            word_picks.extend(batch)
        word_picks = word_picks[:target_questions]

    combined_pool = list({v["es"]: v for v in (distractor_pool or []) + (review_pool or []) + list(week_vocab)}.values())
    if not combined_pool and pool:
        combined_pool = list(pool)

    exercises = []
    if word_picks:
        listen_count = min(EXAM_LISTEN_COUNT, len(word_picks))
        listen_slots = set(rng.sample(range(len(word_picks)), listen_count))
        other_types = ["choice_es_to_native", "choice_native_to_es", "translate"]
        other_i = 0
        for i, v in enumerate(word_picks):
            if i in listen_slots:
                ex = _quiz_exercise(rng, f"{lid}-e{i}", v, combined_pool, i, force_type="listen")
            else:
                ex = _quiz_exercise(
                    rng, f"{lid}-e{i}", v, combined_pool, other_i,
                    force_type=other_types[other_i % len(other_types)],
                )
                other_i += 1
            exercises.append(ex)
        rng.shuffle(exercises)
    return {
        "id": lid, "kind": "exam", "week": week_meta["week"], "day_in_week": DAYS_PER_WEEK,
        "day": global_day, "level": week_meta["level"], "icon": "📝",
        "theme": t("Weekly Exam", "Недельный экзамен", "Examen semanal"),
        "title": t("Weekly Exam — bonus XP!", "Недельный экзамен — бонус XP!", "Examen semanal — ¡XP extra!"),
        "theory": None, "pesos": PESOS_EXAM, "new_vocab_count": 0,
        "est_minutes": _est_minutes(exercises), "exercises": exercises,
    }


def _make_week_meta(w):
    """Return (meta, vocab, is_review, chunks) for authored or spiral-review weeks."""
    for wk in WEEKS:
        if wk["week"] == w:
            vocab = [_vi(v) for v in wk["vocab"]]
            if wk["level"] == "A1" and w in A1_BOOST:
                seen = {v["es"] for v in vocab}
                for raw in A1_BOOST[w] + A1_BOOST_EXTRA.get(w, []):
                    v = _vi(raw)
                    if v["es"] not in seen:
                        vocab.append(v)
                        seen.add(v["es"])
            return wk, vocab, False, list(wk.get("chunks", []))
    # Auto review week
    level = "B1"
    n = w - max(x["week"] for x in WEEKS)
    meta = {
        "week": w, "level": level, "icon": "🔄",
        "theme": t(f"Spiral Review {n}", f"Спиральное повторение {n}", f"Repaso en espiral {n}"),
        "theory": REVIEW_THEORY,
    }
    return meta, None, True, []  # vocab filled later from learned pool


@lru_cache
def _build():
    """Build all 52 weeks (365 days). Returns (weeks_list, lessons_by_id)."""
    weeks_out = []
    lessons_by_id = {}
    learned: List[dict] = []  # cumulative vocab seen so far (for review)

    for w in range(1, TOTAL_WEEKS + 1):
        meta, vocab, is_review, chunks = _make_week_meta(w)
        if is_review:
            # Reuse a rotating sample of everything learned so far.
            rng = random.Random(f"review-{w}")
            if learned:
                k = min(24, len(learned))
                vocab = rng.sample(learned, k)
            else:
                vocab = []

        # Split week vocab across the 6 learning days.
        days = []
        n = len(vocab)
        per = max(NEW_WORDS_MIN_PER_DAY, -(-n // LESSONS_PER_WEEK)) if n else 0
        review_pool_snapshot = list(learned)  # words learned BEFORE this week

        # Cumulative "words the learner already knows" at the END of each day, so
        # we never quiz, offer as a distractor, or cloze a word before it's taught.
        cum_tokens_by_day, cum_vocab_by_day = [], []
        acc_tok, acc_voc = _vocab_tokens(review_pool_snapshot), list(review_pool_snapshot)
        for d in range(1, LESSONS_PER_WEEK + 1):
            day_words = vocab[(d - 1) * per:d * per]
            acc_tok = acc_tok | _vocab_tokens(day_words)
            acc_voc = acc_voc + day_words
            cum_tokens_by_day.append(set(acc_tok))
            cum_vocab_by_day.append(list(acc_voc))

        # Earliest day each cloze becomes answerable (its answer word is taught).
        chunk_unlock = []
        for ch in chunks:
            ans = _norm(ch["answer"])
            unlock = next((d for d in range(1, LESSONS_PER_WEEK + 1)
                           if ans in cum_tokens_by_day[d - 1]), None)
            chunk_unlock.append(unlock)
        unlocked_chunks = [ch for ch, u in zip(chunks, chunk_unlock) if u is not None]

        week_so_far: List[dict] = []
        for d in range(1, LESSONS_PER_WEEK + 1):
            start = (d - 1) * per
            new_vocab = vocab[start:start + per]
            lid = f"w{w:02d}-d{d}"
            gday = (w - 1) * DAYS_PER_WEEK + d
            # Distractors come only from words already taught by today.
            taught_so_far = cum_vocab_by_day[d - 1]
            taught_tokens = cum_tokens_by_day[d - 1]
            distractor_pool = list(taught_so_far)
            if len(distractor_pool) < 4:  # early days: pad from this week's bank
                seen = {v["es"] for v in distractor_pool}
                distractor_pool += [v for v in vocab if v["es"] not in seen]
            # Only cloze sentences whose answer word is already known (1-2/day).
            eligible = [ch for ch, u in zip(chunks, chunk_unlock) if u is not None and u <= d]
            day_chunks = []
            if eligible:
                day_chunks = [eligible[(d - 1) % len(eligible)]]
                if len(eligible) >= 2:
                    second = eligible[(d - 1 + len(eligible) // 2) % len(eligible)]
                    if second is not day_chunks[0]:
                        day_chunks.append(second)
            lesson = _day_lesson(
                lid, meta, d, gday, new_vocab, review_pool_snapshot,
                distractor_pool, day_chunks, week_so_far, taught_tokens,
            )
            days.append(lesson)
            lessons_by_id[lid] = lesson
            week_so_far.extend(new_vocab)

        # Weekly exam (day 7): every word is taught by now, so the full bank is fair.
        exam_id = f"w{w:02d}-exam"
        gday = (w - 1) * DAYS_PER_WEEK + DAYS_PER_WEEK
        exam = _exam_lesson(exam_id, meta, gday, vocab, review_pool_snapshot, list(vocab), unlocked_chunks)
        days.append(exam)
        lessons_by_id[exam_id] = exam

        # After the week, everything in it is "learned".
        learned.extend(vocab)

        weeks_out.append({
            "week": w, "level": meta["level"], "icon": meta["icon"], "theme": meta["theme"],
            "is_review": is_review, "theory": meta["theory"], "days": days,
        })

    # Final capstone (day 365)
    rng = random.Random("capstone")
    cap_vocab = rng.sample(learned, min(15, len(learned))) if learned else []
    cap_ex = [_quiz_exercise(rng, f"capstone-e{i}", v, learned, i) for i, v in enumerate(cap_vocab)]
    capstone = {
        "id": "capstone", "kind": "capstone", "week": TOTAL_WEEKS, "day_in_week": 8, "day": 365,
        "level": "B1", "icon": "🎓",
        "theme": t("Final Graduation", "Финальный экзамен", "Graduación final"),
        "title": t("Graduation Exam 🎓", "Выпускной экзамен 🎓", "Examen de graduación 🎓"),
        "theory": None, "pesos": PESOS_CAPSTONE, "new_vocab_count": 0, "exercises": cap_ex,
    }
    lessons_by_id["capstone"] = capstone
    weeks_out[-1]["days"].append(capstone)

    return weeks_out, lessons_by_id


@lru_cache
def get_weeks() -> List[dict]:
    return _build()[0]


@lru_cache
def get_all_lessons() -> Dict[str, dict]:
    return _build()[1]


def get_lesson(lesson_id: str) -> Optional[dict]:
    return get_all_lessons().get(lesson_id)


@lru_cache
def get_curriculum() -> List[dict]:
    """Group weeks by CEFR level for the dashboard."""
    weeks = get_weeks()
    order = ["A1", "A2", "B1"]
    grouped = {lv: [] for lv in order}
    for wk in weeks:
        grouped.setdefault(wk["level"], []).append(wk)
    levels = []
    for lv in order:
        levels.append({
            "id": lv.lower(), "level": lv, "months": LEVEL_MONTHS[lv],
            "months_from": LEVEL_MONTH_RANGE[lv][0],
            "months_to": LEVEL_MONTH_RANGE[lv][1],
            "title": LEVEL_TITLE[lv], "description": LEVEL_DESC[lv],
            "weeks": grouped[lv],
        })
    return levels


def lesson_ids_for_level(level_id: str) -> List[str]:
    lvl = level_id.upper()
    return [d["id"] for wk in get_weeks() if wk["level"] == lvl for d in wk["days"]]


@lru_cache
def all_vocab_pool() -> List[dict]:
    """Unique vocab items across the whole program (used as distractors)."""
    return list(_all_program_vocab())


def build_quiz(vocab_items: List[dict], pool: List[dict], seed: str, allow_speak: bool = True) -> List[dict]:
    """Public helper: build quiz exercises from vocab dicts (for the review deck)."""
    rng = random.Random(seed)
    combined = pool if len(pool) >= 4 else pool + vocab_items
    out = []
    for i, v in enumerate(vocab_items):
        ex = _quiz_exercise(rng, f"rev-{i}", v, combined, i)
        out.append(ex)
    return out


def total_lessons() -> int:
    return len(get_all_lessons())


__all__ = [
    "get_curriculum", "get_weeks", "get_all_lessons", "get_lesson",
    "lesson_ids_for_level", "total_lessons", "AVATARS", "PESOS_LESSON",
]
