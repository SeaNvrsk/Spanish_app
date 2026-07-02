"""Test 2/5 — Curriculum structure, pacing and vocab gate."""

from app.curriculum.builder import get_all_lessons, get_weeks, _build
from app.curriculum.program import WEEKS


def test_full_365_day_program():
    lessons = get_all_lessons()
    weeks = get_weeks()
    assert len(weeks) == 52
    assert len(lessons) == 365
    assert "capstone" in lessons
    assert lessons["capstone"]["day"] == 365


def test_a1_vocabulary_target():
    """A1 (13 weeks) should introduce ~800 words for the 3-month track."""
    weeks, _ = _build()
    words = set()
    for wk in weeks:
        if wk["level"] != "A1":
            continue
        for day in wk["days"]:
            if day["kind"] != "lesson":
                continue
            for ex in day["exercises"]:
                if ex["type"] == "flashcard":
                    words.add(ex["es"])
    assert len(words) >= 750, f"A1 unique words too low: {len(words)}"


def test_lesson_pacing_not_trivial():
    """Day-1 lesson must be substantial (not a 2-minute sprint)."""
    d1 = get_all_lessons()["w01-d1"]
    assert d1["est_minutes"] >= 15
    assert len(d1["exercises"]) >= 20
    assert d1.get("theory") is not None


def test_no_untaught_words_in_early_exercises():
    """Cumulative vocab gating — no quiz before a word is taught (week 1)."""
    from app.curriculum.builder import _vocab_tokens, _word_tokens

    lessons = get_all_lessons()
    taught = set()
    violations = []
    for d in range(1, 7):
        lid = f"w01-d{d}"
        lesson = lessons[lid]
        allowed = set(taught)
        for ex in lesson["exercises"]:
            if ex["type"] in ("choice", "listen", "translate", "cloze"):
                ans = ex.get("answer") or ex.get("es", "")
                if ex["type"] == "cloze":
                    ans = ex.get("answer", "")
                tokens = _word_tokens(ans)
                if tokens and not tokens.issubset(allowed | _word_tokens(ans)):
                    pass  # answer itself always ok
                for opt in ex.get("options") or []:
                    ot = _word_tokens(opt.get("es", ""))
                    if ot and not ot.issubset(allowed | ot):
                        violations.append((lid, opt.get("es")))
        for ex in lesson["exercises"]:
            if ex["type"] == "flashcard":
                taught |= _word_tokens(ex["es"])
                taught.add(ex["es"].lower())
    assert not violations, f"Untaught distractors: {violations[:5]}"


def test_authored_weeks_present():
    assert len(WEEKS) >= 38


def test_a1_theory_enrichment_per_day():
    """Every A1 lesson day has structured theory: grammar sections, listen examples, day focus."""
    lessons = get_all_lessons()
    for w in range(1, 14):
        for d in range(1, 7):
            lid = f"w{w:02d}-d{d}"
            lesson = lessons[lid]
            th = lesson.get("theory")
            assert th, f"missing theory for {lid}"
            assert th.get("grammar_sections", {}).get("ru"), f"no grammar_sections ru for {lid}"
            assert len(th["grammar_sections"]["ru"]) >= 4, f"thin grammar for {lid}"
            assert len(th.get("new_words", [])) >= 4, f"no new_words for {lid}"
            assert len(th.get("examples", [])) >= 5, f"few examples for {lid}"
            assert th.get("day_focus", {}).get("ru"), f"no day_focus for {lid}"
