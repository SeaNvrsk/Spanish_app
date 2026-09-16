#!/usr/bin/env python3
"""
Recalculate user balances, lesson progress, daily activity, and prize credits
after removing fake/invalid lesson completions caused by the open-and-exit bug.
"""

import os
import sqlite3

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../espanol.db"))

def run_recalculation():
    print(f"Connecting to DB at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Invalid lesson progress IDs identified from audit logs and speed checks
    invalid_lp_ids = [26, 103, 106, 110, 52, 93]

    print("\n--- Current state before cleanup ---")
    c.execute("SELECT id, name, xp, carryover_pesos FROM users WHERE id IN (4, 5)")
    for row in c.fetchall():
        print(f"User {row[0]} ({row[1]}): xp={row[2]}, carryover={row[3]}")

    # 1. Delete invalid lesson_progress entries
    c.execute("DELETE FROM lesson_progress WHERE id IN (%s)" % ",".join("?" * len(invalid_lp_ids)), invalid_lp_ids)
    print(f"Deleted {c.rowcount} invalid lesson_progress rows.")

    # 2. Update DailyActivity adjustments
    # User 4 adjustments
    # 2026-07-07: subtract 15 xp (w01-exam awarded on 2026-07-07 in DA)
    c.execute("UPDATE daily_activity SET xp = xp - 15 WHERE user_id = 4 AND day = '2026-07-07'")
    # 2026-07-08: subtract 1 lesson completed
    c.execute("UPDATE daily_activity SET lessons_completed = lessons_completed - 1 WHERE user_id = 4 AND day = '2026-07-08'")
    # 2026-08-03: subtract 5 xp, 5 lesson_pesos, 1 lesson_completed (w05-d6)
    c.execute("UPDATE daily_activity SET xp = xp - 5, lesson_pesos = lesson_pesos - 5, lessons_completed = lessons_completed - 1 WHERE user_id = 4 AND day = '2026-08-03'")

    # User 5 adjustments
    # 2026-08-03: subtract 15 xp, 15 lesson_pesos, 1 lesson_completed (w04-exam)
    c.execute("UPDATE daily_activity SET xp = xp - 15, lesson_pesos = lesson_pesos - 15, lessons_completed = lessons_completed - 1 WHERE user_id = 5 AND day = '2026-08-03'")
    # 2026-08-04: subtract 25 xp, 25 lesson_pesos, 3 lessons_completed (w05-exam, w03-d1, w04-d3)
    c.execute("UPDATE daily_activity SET xp = xp - 25, lesson_pesos = lesson_pesos - 25, lessons_completed = lessons_completed - 3 WHERE user_id = 5 AND day = '2026-08-04'")

    # 3. Update User totals
    # User 4: -20 pesos total
    c.execute("UPDATE users SET xp = xp - 20 WHERE id = 4")
    # User 5: -40 pesos total
    c.execute("UPDATE users SET xp = xp - 40 WHERE id = 5")

    # 4. Update MonthPrizeCredit for July 2026 for User 4
    # User 4 July total dropped from 302 to 287 pesos -> 75% share = 215 pesos (was 226)
    c.execute("UPDATE month_prize_credits SET month_pesos = 287, credited = 215 WHERE user_id = 4 AND month = '2026-07'")
    c.execute("UPDATE users SET carryover_pesos = 215 WHERE id = 4")

    conn.commit()

    print("\n--- State after recalculation ---")
    c.execute("SELECT id, name, xp, carryover_pesos FROM users WHERE id IN (4, 5)")
    for row in c.fetchall():
        print(f"User {row[0]} ({row[1]}): xp={row[2]}, carryover={row[3]}")

    c.close()
    conn.close()

if __name__ == "__main__":
    run_recalculation()
