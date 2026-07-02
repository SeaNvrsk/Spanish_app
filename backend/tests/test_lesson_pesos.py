"""Lesson peso awards on first pass and retries."""

from app.gamification import lesson_pesos_delta, lesson_pesos_for_score


def test_lesson_pesos_for_score():
    assert lesson_pesos_for_score(5, 100) == 5
    assert lesson_pesos_for_score(5, 90) == 4  # round(4.5) -> 4
    assert lesson_pesos_for_score(5, 50) == 2


def test_retry_90_to_100_awards_one():
    """Bug fix: delta rounding used to give 0 for 90% -> 100% on a $5 lesson."""
    assert lesson_pesos_delta(5, 100, already_earned=4) == 1


def test_retry_no_double_pay():
    assert lesson_pesos_delta(5, 100, already_earned=5) == 0
    assert lesson_pesos_delta(5, 90, already_earned=4) == 0


def test_retry_big_jump():
    assert lesson_pesos_delta(5, 100, already_earned=2) == 3
