"""Score learner pronunciation against a target Spanish phrase."""

from __future__ import annotations

import difflib
import re
from collections import Counter
from typing import NamedTuple


class PronunciationResult(NamedTuple):
    score: int
    passed: bool
    asr_corrected: bool  # Whisper mis-transcribed but pronunciation accepted


def normalize(s: str) -> str:
    s = s.lower().strip()
    for src, dst in (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ü", "u"),
        ("ñ", "n"),
    ):
        s = s.replace(src, dst)
    s = re.sub(r"[¿?¡!.,;:\"']", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _char_overlap_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    shared = sum((Counter(a) & Counter(b)).values())
    return shared / max(len(a), len(b))


def _short_word_heuristic(expected: str, heard: str) -> float | None:
    """Whisper often mis-hears short Spanish words ("ella" → "ey ya")."""
    if len(expected) > 6:
        return None
    collapsed = heard.replace(" ", "")
    if len(collapsed) < 2:
        return None
    if expected[0] != collapsed[0] or expected[-1] != collapsed[-1]:
        return None
    if abs(len(expected) - len(collapsed)) > 2:
        return None
    overlap = _char_overlap_ratio(expected, collapsed)
    if overlap >= 0.45:
        return max(0.85, overlap)
    return None


def _match_ratio(expected: str, heard: str) -> float:
    candidates: list[float] = [
        difflib.SequenceMatcher(None, expected, heard).ratio(),
    ]
    collapsed = heard.replace(" ", "")
    candidates.append(difflib.SequenceMatcher(None, expected, collapsed).ratio())
    candidates.append(_char_overlap_ratio(expected, collapsed))

    heard_words = heard.split()
    if heard_words:
        candidates.append(max(difflib.SequenceMatcher(None, expected, w).ratio() for w in heard_words))
        if expected in heard_words:
            candidates.append(0.98)

    expected_words = expected.split()
    if len(expected_words) > 1 and all(w in heard_words for w in expected_words):
        candidates.append(0.95)

    short = _short_word_heuristic(expected, heard)
    if short is not None:
        candidates.append(short)

    return max(candidates)


def score_pronunciation(target: str, transcript: str) -> PronunciationResult:
    """
    Return score, pass/fail, and whether Whisper's text was corrected.

    If the learner passed, score is always 100 — a low score should not punish
    ASR mistakes when our matcher accepted the attempt.
    """
    expected = normalize(target)
    heard = normalize(transcript)
    if not expected or not heard:
        return PronunciationResult(0, False, False)

    if expected == heard:
        return PronunciationResult(100, True, False)

    ratio = _match_ratio(expected, heard)
    threshold = 65 if len(expected) <= 5 else 70
    passed = ratio >= threshold or (len(expected) <= 5 and ratio >= 0.72)

    if not passed:
        return PronunciationResult(round(ratio * 100), False, False)

    asr_corrected = heard != expected
    return PronunciationResult(100, True, asr_corrected)
