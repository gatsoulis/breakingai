"""Grade a results file and print accuracy by family and difficulty.

Usage (from the repo root):
    PYTHONPATH=src .venv/bin/python -m puzzles.report
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from puzzles.generator import DATA_DIR, Task, grade, parse_answer


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarize(tasks: dict[str, Task], results: list[dict]) -> str:
    def setting(r: dict) -> tuple:
        return (r["model"], r["effort"], r.get("tools", ""), r.get("skills", ""))

    settings = sorted({setting(r) for r in results})
    out = []
    for model, effort, tools, skills in settings:
        rows = [r for r in results if setting(r) == (model, effort, tools, skills)]
        graded = []  # (task, row, outcome) where outcome is correct / wrong / no_answer / error
        for r in rows:
            task = tasks.get(r["task_id"])
            if task is None:
                continue
            if r.get("error") or r.get("response") is None:
                outcome = "error"
            elif parse_answer(r["response"]) is None:
                outcome = "no_answer"
            else:
                outcome = "correct" if grade(task, r["response"]) else "wrong"
            graded.append((task, r, outcome))

        out.append(
            f"\n=== {model} @ effort={effort}, tools={tools or 'none'}, "
            f"skills={skills or 'none'}: {len(graded)} calls ==="
        )
        n = len(graded)
        for outcome in ("correct", "wrong", "no_answer", "error"):
            count = sum(1 for _, _, o in graded if o == outcome)
            out.append(f"  {outcome:<10} {count:>5}  ({count / n:.0%})")

        out.append("\naccuracy by family x difficulty (correct / calls)")
        cells: dict[tuple, list[bool]] = defaultdict(list)
        for task, _, outcome in graded:
            cells[(task.family, task.difficulty)].append(outcome == "correct")
        difficulties = sorted({d for _, d in cells})
        out.append(f"  {'family':<12}" + "".join(f"{'d' + str(d):>14}" for d in difficulties))
        for family in sorted({f for f, _ in cells}):
            line = f"  {family:<12}"
            for d in difficulties:
                v = cells.get((family, d), [])
                line += f"{f'{sum(v)}/{len(v)} ({sum(v) / len(v):.0%})' if v else '-':>14}"
            out.append(line)

        by_task: dict[str, list[bool]] = defaultdict(list)
        for task, _, outcome in graded:
            by_task[task.id].append(outcome == "correct")
        multi = {k: v for k, v in by_task.items() if len(v) > 1}
        if multi:
            always = sum(all(v) for v in multi.values())
            never = sum(not any(v) for v in multi.values())
            out.append(
                f"\nconsistency over {len(multi)} tasks with repeats: "
                f"always right {always}, always wrong {never}, mixed {len(multi) - always - never}"
            )

        latencies = [r["latency_s"] for _, r, _ in graded if r.get("latency_s") is not None]
        usage = [u for _, r, _ in graded for u in r.get("usage", [])]

        def avg(key: str) -> float | None:
            values = [u[key] for u in usage if u.get(key) is not None]
            return mean(values) if values else None

        parts = []
        if latencies:
            parts.append(f"latency {mean(latencies):.1f}s")
        if tools or skills:
            parts.append(f"tool_calls {mean(r.get('tool_calls', 0) for _, r, _ in graded):.1f}")
        if skills:
            parts.append(f"skill_loads {mean(r.get('skill_invocations', 0) for _, r, _ in graded):.1f}")
        for key in ("input_tokens", "output_tokens", "reasoning_tokens", "cost"):
            value = avg(key)
            if value is not None:
                parts.append(f"{key} {value:.1f}")
        total_cost = sum(u["cost"] for u in usage if u.get("cost") is not None)
        correct = sum(1 for _, _, o in graded if o == "correct")
        out.append("\nmeans per call: " + (", ".join(parts) or "no usage data"))
        if usage and correct:
            out.append(f"total cost {total_cost:.2f}; cost per correct answer {total_cost / correct:.3f}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tasks", type=Path, default=DATA_DIR / "puzzles.jsonl")
    parser.add_argument("--results", type=Path, default=DATA_DIR / "results.jsonl")
    args = parser.parse_args()

    tasks = {t["id"]: Task(**t) for t in load_jsonl(args.tasks)}
    print(summarize(tasks, load_jsonl(args.results)))


if __name__ == "__main__":
    main()
