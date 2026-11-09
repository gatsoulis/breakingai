"""Run puzzle tasks through a Copilot model and append raw results to a JSONL file.

No grading happens here: raw replies are stored so graders can be fixed and re-run offline.
Re-running the same command resumes, skipping (task, model, effort, run) rows already saved.

Usage (from the repo root):
    PYTHONPATH=src .venv/bin/python -m puzzles.runner \
        --model gpt-6-luna --effort none --runs 1 --per-cell 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import defaultdict
from pathlib import Path

from copilot import CopilotClient
from copilot.session import PermissionHandler
from copilot.session_events import (
    AssistantUsageData,
    SessionErrorData,
    SkillInvokedData,
    ToolExecutionStartData,
)

from puzzles.generator import DATA_DIR
from puzzles.tools import MCP_TOOLS, TOOLS

SKILLS_DIR = Path(__file__).parent / "skills"
# Tool names the runtime uses to load skill text; adjust after checking a real run.
SKILL_TOOL_NAMES = ["skill"]

DEFAULT_TIMEOUT = 300.0


def load_tasks(path: Path, per_cell: int | None, families: list[str] | None) -> list[dict]:
    tasks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if families:
        tasks = [t for t in tasks if t["family"] in families]
    if per_cell is None:
        return tasks
    taken: dict[tuple, int] = defaultdict(int)
    selected = []
    for t in tasks:
        cell = (t["family"], t["difficulty"])
        if taken[cell] < per_cell:
            taken[cell] += 1
            selected.append(t)
    return selected


def load_done(path: Path) -> set[tuple]:
    if not path.exists():
        return set()
    done = set()
    for line in path.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if not r.get("error"):
                done.add((r["task_id"], r["model"], r["effort"], r.get("tools", ""), r.get("skills", ""), r["run"]))
    return done


async def run_one(
    client: CopilotClient,
    task: dict,
    model: str,
    effort: str,
    tools: str,
    skills: str,
    run: int,
    timeout: float,
) -> dict:
    row = {
        "task_id": task["id"],
        "model": model,
        "effort": effort,
        "tools": tools,
        "skills": skills,
        "run": run,
        "response": None,
        "error": None,
        "latency_s": None,
        "tool_calls": 0,
        "skill_invocations": 0,
        "usage": [],
    }
    usage: list[dict] = []

    def on_event(event):
        data = event.data
        if isinstance(data, ToolExecutionStartData):
            row["tool_calls"] += 1
        elif isinstance(data, SkillInvokedData):
            row["skill_invocations"] += 1
        elif isinstance(data, AssistantUsageData):
            usage.append(
                {
                    "input_tokens": data.input_tokens,
                    "output_tokens": data.output_tokens,
                    "reasoning_tokens": data.reasoning_tokens,
                    "cache_read_tokens": data.cache_read_tokens,
                    "cost": data.cost,
                    "duration_s": data.duration.total_seconds() if data.duration else None,
                    "reasoning_effort": str(data.reasoning_effort) if data.reasoning_effort else None,
                    "model": data.model,
                }
            )
        elif isinstance(data, SessionErrorData):
            row["error"] = f"{data.error_type}: {data.message}"

    start = time.monotonic()
    try:
        kwargs = {"model": model, "available_tools": []}
        if tools:
            names = tools.split(",")
            in_process = [n for n in names if n in TOOLS]
            mcp = [MCP_TOOLS[n] for n in names if n in MCP_TOOLS]
            kwargs["tools"] = [TOOLS[n] for n in in_process]
            kwargs["available_tools"] = in_process + [t for m in mcp for t in m["tool_names"]]
            if mcp:
                kwargs["mcp_servers"] = {m["server_name"]: m["config"] for m in mcp}
                # MCP tools need approval; available_tools limits it to the listed tools.
                kwargs["on_permission_request"] = PermissionHandler.approve_all
        if effort != "default":
            kwargs["reasoning_effort"] = effort
        if skills:
            wanted = skills.split(",")
            kwargs["enable_skills"] = True
            kwargs["skill_directories"] = [str(SKILLS_DIR)]
            kwargs["disabled_skills"] = [
                p.name for p in SKILLS_DIR.iterdir() if p.is_dir() and p.name not in wanted
            ]
            kwargs["available_tools"] = [*kwargs["available_tools"], *SKILL_TOOL_NAMES]
        async with await client.create_session(**kwargs) as session:
            session.on(on_event)
            reply = await session.send_and_wait(task["prompt"], timeout=timeout)
            if reply is None:
                row["error"] = row["error"] or "no assistant message"
            else:
                row["response"] = reply.data.content
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["latency_s"] = round(time.monotonic() - start, 3)
    row["usage"] = usage
    return row


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tasks", type=Path, default=DATA_DIR / "puzzles.jsonl")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "results.jsonl")
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--effort",
        required=True,
        help="reasoning effort (none, low, medium, high, xhigh, max) or 'default' to omit it",
    )
    parser.add_argument("--runs", type=int, default=1, help="repeats per task")
    parser.add_argument("--per-cell", type=int, help="only the first N tasks per (family, difficulty)")
    parser.add_argument("--families", nargs="+", help="only these task families")
    parser.add_argument(
        "--tools", nargs="*", choices=[*TOOLS, *MCP_TOOLS], default=[], help="tools the model may call"
    )
    parser.add_argument(
        "--skills",
        nargs="*",
        choices=sorted(p.name for p in SKILLS_DIR.iterdir() if p.is_dir()),
        default=[],
        help="skills (folders in puzzles/skills) the model may load",
    )
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    tools = ",".join(sorted(args.tools))
    skills = ",".join(sorted(args.skills))
    tasks = load_tasks(args.tasks, args.per_cell, args.families)
    done = load_done(args.out)
    jobs = [
        (t, run)
        for run in range(args.runs)
        for t in tasks
        if (t["id"], args.model, args.effort, tools, skills, run) not in done
    ]
    print(f"{len(jobs)} calls to make ({len(done)} already saved)")

    semaphore = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()
    completed = 0

    async with CopilotClient() as client:
        with args.out.open("a") as out:

            async def worker(task: dict, run: int) -> None:
                nonlocal completed
                async with semaphore:
                    row = await run_one(
                        client, task, args.model, args.effort, tools, skills, run, args.timeout
                    )
                async with write_lock:
                    out.write(json.dumps(row) + "\n")
                    out.flush()
                    completed += 1
                    status = f"ERROR {row['error']}" if row["error"] else f"{row['latency_s']}s"
                    print(f"[{completed}/{len(jobs)}] {task['id']} run {run}: {status}")

            await asyncio.gather(*(worker(t, r) for t, r in jobs))


if __name__ == "__main__":
    asyncio.run(main())
