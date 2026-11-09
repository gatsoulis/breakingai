import unittest
from datetime import date
from decimal import Decimal

from puzzles.generator import (
    FAMILIES,
    DIFFICULTIES,
    add_business_days,
    generate_dataset,
    generate_task,
    grade,
    makespan,
    next_business_day,
    parse_answer,
)


class SolverTests(unittest.TestCase):
    def test_business_days_skip_weekends(self):
        # Friday 2025-01-03 + 1 business day = Monday 2025-01-06
        self.assertEqual(add_business_days(date(2025, 1, 3), 1, set()), date(2025, 1, 6))
        self.assertEqual(add_business_days(date(2025, 1, 6), 5, set()), date(2025, 1, 13))

    def test_business_days_skip_holidays(self):
        holidays = {date(2025, 1, 7)}
        self.assertEqual(add_business_days(date(2025, 1, 6), 1, holidays), date(2025, 1, 8))

    def test_holiday_on_weekend_not_double_counted(self):
        holidays = {date(2025, 1, 4)}  # Saturday
        self.assertEqual(add_business_days(date(2025, 1, 3), 1, holidays), date(2025, 1, 6))

    def test_next_business_day(self):
        self.assertEqual(next_business_day(date(2025, 1, 4), set()), date(2025, 1, 6))
        self.assertEqual(next_business_day(date(2025, 1, 6), set()), date(2025, 1, 6))

    def test_makespan_sequential_parallel_and_limited_workers(self):
        d = {"A": 10, "B": 20, "C": 30}
        deps = {"A": [], "B": [], "C": ["A"]}
        self.assertEqual(makespan(d, deps, ["A", "B", "C"], 1), 60)
        self.assertEqual(makespan(d, deps, ["A", "B", "C"], None), 40)
        # Two workers: A and B start together; C starts at 10 when A frees its worker.
        self.assertEqual(makespan(d, deps, ["A", "B", "C"], 2), 40)
        # A blocked task is skipped: C waits for A, so B and A start together, then C.
        self.assertEqual(makespan(d, deps, ["C", "B", "A"], 2), 40)

    def test_priority_order_changes_makespan(self):
        d = {"A": 10, "B": 20, "C": 30}
        deps = {"A": [], "B": [], "C": []}
        self.assertEqual(makespan(d, deps, ["A", "B", "C"], 2), 40)
        self.assertEqual(makespan(d, deps, ["C", "B", "A"], 2), 30)


class GraderTests(unittest.TestCase):
    def setUp(self):
        self.money = generate_task("table", 2, 0)
        self.integer = generate_task("table", 1, 0)
        self.date = generate_task("dates", 1, 0)

    def test_parse_takes_last_answer_line(self):
        self.assertEqual(parse_answer("ANSWER: 1\nthinking\nANSWER: **2**"), "2")
        self.assertIsNone(parse_answer("no answer here"))

    def test_correct_and_incorrect(self):
        self.assertTrue(grade(self.date, f"reasoning\nANSWER: {self.date.answer}"))
        self.assertFalse(grade(self.date, "ANSWER: 1999-01-01"))
        self.assertFalse(grade(self.date, "no answer line"))
        self.assertTrue(grade(self.integer, f"ANSWER: {self.integer.answer}"))
        self.assertFalse(grade(self.integer, f"ANSWER: {int(self.integer.answer) + 1}"))

    def test_money_tolerance_and_formatting(self):
        value = Decimal(self.money.answer)
        self.assertTrue(grade(self.money, f"ANSWER: ${value + Decimal('0.01'):,}"))
        self.assertFalse(grade(self.money, f"ANSWER: {value + Decimal('0.05')}"))


class DatasetTests(unittest.TestCase):
    def test_deterministic(self):
        a = [t.prompt for t in generate_dataset(3, base_seed=1)]
        b = [t.prompt for t in generate_dataset(3, base_seed=1)]
        c = [t.prompt for t in generate_dataset(3, base_seed=2)]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_shape_and_unique_ids(self):
        tasks = generate_dataset(5)
        self.assertEqual(len(tasks), 5 * len(FAMILIES) * len(DIFFICULTIES))
        self.assertEqual(len({t.id for t in tasks}), len(tasks))

    def test_every_task_grades_its_own_answer(self):
        for t in generate_dataset(30):
            self.assertTrue(grade(t, f"ANSWER: {t.answer}"), t.id)
            self.assertIn("ANSWER:", t.prompt)


if __name__ == "__main__":
    unittest.main()
