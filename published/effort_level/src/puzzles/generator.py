"""Seeded generator of multi-step puzzles whose answers are computed by code.

Four families, three difficulty levels (roughly the number of reasoning steps).
Every task carries its own ground-truth answer, so grading is exact-match.

Usage (from the src/ directory):
    python -m puzzles.generator --per-cell 20 --seed 0   # writes gitignored/puzzles.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DATA_DIR = Path(__file__).parent / "gitignored"
DIFFICULTIES = (1, 2, 3)

ANSWER_FORMATS = {
    "date": "a date in YYYY-MM-DD format",
    "money": "a number rounded to 2 decimal places, with no currency symbol or thousands separators",
    "integer": "a whole number with no units or separators",
}

CENT = Decimal("0.01")


@dataclass
class Task:
    id: str
    family: str
    difficulty: int
    seed: str
    prompt: str
    answer: str
    answer_type: str


def _footer(answer_type: str) -> str:
    return (
        "\n\nWork through the problem however you like, but end your reply with a final line "
        f"of the form `ANSWER: <value>`, where <value> is {ANSWER_FORMATS[answer_type]}."
    )


def _money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _fmt_date(d: date) -> str:
    return f"{d.day} {d:%B %Y}"


# ---------------------------------------------------------------- dates


def is_business_day(d: date, holidays: set[date]) -> bool:
    return d.weekday() < 5 and d not in holidays


def add_business_days(start: date, n: int, holidays: set[date]) -> date:
    """Day `start` is day 0; the n-th business day after it is returned."""
    d = start
    while n > 0:
        d += timedelta(days=1)
        if is_business_day(d, holidays):
            n -= 1
    return d


def next_business_day(d: date, holidays: set[date]) -> date:
    while not is_business_day(d, holidays):
        d += timedelta(days=1)
    return d


def _dates_task(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    start = date(2025, 1, 1) + timedelta(days=rng.randrange(0, 730))
    n = rng.randint(5, 15) if difficulty == 1 else rng.randint(10, 25)
    cure = rng.randint(7, 30)

    holidays: set[date] = set()
    if difficulty > 1:
        horizon = int(n * 1.5) + 10 + (cure if difficulty == 3 else 0)
        window = [start + timedelta(days=i) for i in range(1, horizon)]
        holidays = set(rng.sample(window, 3 if difficulty == 2 else 5))

    prompt = (
        f"A notice is served on {_fmt_date(start)} (day 0). It expires after {n} business days. "
        "Business days are Monday to Friday"
    )
    if holidays:
        listed = ", ".join(_fmt_date(h) for h in sorted(holidays))
        prompt += f", excluding these public holidays: {listed}"
    prompt += "."

    expiry = add_business_days(start, n, holidays)
    if difficulty < 3:
        prompt += " On what date does the notice expire?"
        return prompt, expiry.isoformat(), "date"

    deadline = next_business_day(expiry + timedelta(days=cure), holidays)
    prompt += (
        f" Once the notice expires (the expiry date is day 0), the recipient has {cure} calendar "
        "days to cure the breach. If the last day of the cure period is not a business day, the "
        "deadline moves to the next business day. What is the cure deadline?"
    )
    return prompt, deadline.isoformat(), "date"


# ---------------------------------------------------------------- conversion

CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CHF", "CAD", "AUD", "SEK"]


def _conversion_task(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    legs = {1: 1, 2: 2, 3: 4}[difficulty]
    route = rng.sample(CURRENCIES, legs + 1)
    amount = Decimal(rng.randrange(1000, 50000))
    fee = Decimal(rng.choice(["0.5", "1", "1.5", "2"])) if difficulty == 3 else Decimal(0)

    def rate() -> Decimal:
        return Decimal(str(round(rng.uniform(0.4, 2.5), 4)))

    rates = {(a, b): rate() for a, b in zip(route, route[1:])}
    if difficulty > 1:
        # Distractor rates for pairs that are not on the route.
        decoys = 0
        while decoys < 2:
            a, b = rng.sample(CURRENCIES, 2)
            if (a, b) not in rates and (b, a) not in rates:
                rates[(a, b)] = rate()
                decoys += 1

    result = amount
    for a, b in zip(route, route[1:]):
        result = result * rates[(a, b)] * (1 - fee / 100)

    pairs = list(rates.items())
    rng.shuffle(pairs)
    table = "\n".join(f"- 1 {a} = {r} {b}" for (a, b), r in pairs)
    prompt = (
        f"You hold {amount} {route[0]}. Exchange rates:\n{table}\n\n"
        f"Convert along the route {' -> '.join(route)}, in that order."
    )
    if fee:
        prompt += (
            f" Each conversion charges a fee of {fee}% of the converted amount "
            "(deducted after converting)."
        )
    prompt += f" Do not round intermediate values. How much {route[-1]} do you end up with?"
    return prompt, _money(result), "money"


# ---------------------------------------------------------------- scheduling


def makespan(
    durations: dict[str, int],
    deps: dict[str, list[str]],
    priority: list[str],
    workers: int | None,
) -> int:
    """List scheduling: whenever a worker is free, it takes the first task in `priority`
    whose dependencies have all finished. A task finishing at t frees its worker at t."""
    finish: dict[str, int] = {}
    running: list[tuple[int, str]] = []
    pending = list(priority)
    t = 0
    while pending or running:
        for end, task in [r for r in running if r[0] <= t]:
            finish[task] = end
        running = [r for r in running if r[0] > t]
        for task in list(pending):
            if workers is not None and len(running) >= workers:
                break
            if all(d in finish for d in deps[task]):
                pending.remove(task)
                running.append((t + durations[task], task))
        if running:
            t = min(end for end, _ in running)
        elif pending:
            raise ValueError("unsatisfiable dependencies")
    return max(finish.values())


def _scheduling_task(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    n = {1: 4, 2: 6, 3: 8}[difficulty]
    names = [chr(ord("A") + i) for i in range(n)]
    durations = {t: rng.randrange(10, 100, 5) for t in names}

    if difficulty == 1:
        deps = {t: ([names[i - 1]] if i else []) for i, t in enumerate(names)}
    else:
        deps = {t: rng.sample(names[:i], min(i, rng.randint(0, 2))) for i, t in enumerate(names)}
    priority = names[:]
    workers = None
    if difficulty == 3:
        workers = 2
        rng.shuffle(priority)

    lines = []
    for t in names:
        needs = f", needs {', '.join(deps[t])} finished first" if deps[t] else ""
        lines.append(f"- Task {t}: {durations[t]} minutes{needs}")
    prompt = "Tasks (all start at time 0 at the earliest):\n" + "\n".join(lines) + "\n\n"
    if difficulty == 1:
        prompt += "One person does the tasks, one at a time. "
    elif difficulty == 2:
        prompt += "There are enough people to run any number of tasks in parallel. "
    else:
        prompt += (
            "Two people work in parallel. Whenever a person is free, they take the first task "
            f"in this priority list whose prerequisites are all finished: {', '.join(priority)}. "
            "A task that finishes at time t frees its person at time t. "
        )
    prompt += "How many minutes after time 0 is the last task finished?"
    return prompt, str(makespan(durations, deps, priority, workers)), "integer"


# ---------------------------------------------------------------- table

REGIONS = ["North", "South", "East", "West"]
PRODUCTS = ["Widget", "Gadget", "Gizmo", "Doohickey"]


def _table_task(rng: random.Random, difficulty: int) -> tuple[str, str, str]:
    n_rows = {1: 8, 2: 15, 3: 25}[difficulty]
    while True:
        rows = [
            (
                rng.choice(REGIONS),
                rng.choice(PRODUCTS),
                rng.randint(5, 200),
                Decimal(rng.randrange(500, 5000)) / 100,
            )
            for _ in range(n_rows)
        ]
        region, product = rows[0][0], rows[0][1]
        if sum(1 for r in rows if r[0] == region and r[1] == product) >= 2:
            break

    table = "| Region | Product | Units | Unit price |\n|---|---|---|---|\n" + "\n".join(
        f"| {r} | {p} | {u} | {price} |" for r, p, u, price in rows
    )
    if difficulty == 1:
        total = sum(u for r, _, u, _ in rows if r == region)
        question = f"What is the total number of units sold in the {region} region?"
        return f"{table}\n\n{question}", str(total), "integer"
    if difficulty == 2:
        revenue = sum(u * price for r, p, u, price in rows if r == region and p == product)
        question = (
            f"What is the total revenue (units x unit price) from {product} sales in the "
            f"{region} region?"
        )
        return f"{table}\n\n{question}", _money(revenue), "money"

    per_region: dict[str, Decimal] = {}
    for r, _, u, price in rows:
        per_region[r] = per_region.get(r, Decimal(0)) + u * price
    top = sorted(per_region.values(), reverse=True)
    question = (
        "Compute total revenue (units x unit price) for each region. By how much does the "
        "highest-revenue region exceed the second-highest?"
    )
    return f"{table}\n\n{question}", _money(top[0] - top[1]), "money"


# ---------------------------------------------------------------- dataset

FAMILIES = {
    "dates": _dates_task,
    "conversion": _conversion_task,
    "scheduling": _scheduling_task,
    "table": _table_task,
}


def generate_task(family: str, difficulty: int, index: int, base_seed: int = 0) -> Task:
    seed = f"{base_seed}-{family}-{difficulty}-{index}"
    prompt, answer, answer_type = FAMILIES[family](random.Random(seed), difficulty)
    return Task(
        id=f"{family}-d{difficulty}-{index:03d}",
        family=family,
        difficulty=difficulty,
        seed=seed,
        prompt=prompt + _footer(answer_type),
        answer=answer,
        answer_type=answer_type,
    )


def generate_dataset(
    per_cell: int = 20,
    base_seed: int = 0,
    families: list[str] | None = None,
    difficulties: tuple[int, ...] = DIFFICULTIES,
) -> list[Task]:
    return [
        generate_task(f, d, i, base_seed)
        for f in families or list(FAMILIES)
        for d in difficulties
        for i in range(per_cell)
    ]


# ---------------------------------------------------------------- grading

_ANSWER_RE = re.compile(r"ANSWER:\s*(.+)", re.IGNORECASE)


def parse_answer(text: str) -> str | None:
    """Return the value on the last `ANSWER:` line, with light markdown/format cleanup."""
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    return matches[-1].strip().strip("*`_ ").rstrip(".").strip()


def grade(task: Task, response: str) -> bool:
    value = parse_answer(response)
    if value is None:
        return False
    if task.answer_type == "date":
        return value == task.answer
    try:
        number = Decimal(re.sub(r"[,$€£\s]", "", value))
    except Exception:
        return False
    if task.answer_type == "integer":
        return number == Decimal(task.answer)
    return abs(number - Decimal(task.answer)) <= CENT


# ---------------------------------------------------------------- CLI


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-cell", type=int, default=20, help="tasks per (family, difficulty)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--families", nargs="+", choices=list(FAMILIES), default=list(FAMILIES))
    parser.add_argument("--difficulties", nargs="+", type=int, choices=DIFFICULTIES, default=list(DIFFICULTIES))
    parser.add_argument("--out", type=Path, default=DATA_DIR / "puzzles.jsonl")
    args = parser.parse_args()

    tasks = generate_dataset(args.per_cell, args.seed, args.families, tuple(args.difficulties))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(asdict(t)) + "\n" for t in tasks))
    print(f"wrote {len(tasks)} tasks to {args.out}")


if __name__ == "__main__":
    main()
