"""Minimal demo: give the model a calculator tool and watch it call it.

Usage (from the repo root):
    PYTHONPATH=src .venv/bin/python -m puzzles.calculator_demo --task-id conversion-d1-000
    PYTHONPATH=src .venv/bin/python -m puzzles.calculator_demo --no-tool   # same task, no tool
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from copilot import CopilotClient
from copilot.session import PermissionHandler
from copilot.session_events import (
    AssistantUsageData,
    ToolExecutionCompleteData,
    ToolExecutionStartData,
)

from puzzles.generator import DATA_DIR, Task, grade
from puzzles.tools import calculator

# Tool anatomy (schema, function, description) lives in puzzles/tools.py.
# Registration is below: tools=[calculator] plus available_tools=["calculator"].


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--task-id", default="conversion-d1-000")
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--effort", default="none")
    parser.add_argument("--no-tool", action="store_true")
    parser.add_argument("--mcp", action="store_true", help="use the calculator MCP server instead")
    parser.add_argument("--tasks", default=str(DATA_DIR / "puzzles.jsonl"))
    args = parser.parse_args()

    task = next(
        Task(**t)
        for t in map(json.loads, open(args.tasks))
        if t["id"] == args.task_id
    )

    def on_event(event):
        data = event.data
        if isinstance(data, ToolExecutionStartData):
            print(f"  -> model calls {data.tool_name}({data.arguments})")
        elif isinstance(data, ToolExecutionCompleteData):
            print(f"  <- tool result: {data.result.content if data.result else data.error}")
        elif isinstance(data, AssistantUsageData):
            print(f"  [model call: {data.output_tokens} output tokens]")

    async with CopilotClient() as client:
        # 3. Registering the tool: pass it in `tools`, and allow it by name.
        session_kwargs = {"tools": [calculator], "available_tools": ["calculator"]}
        if args.no_tool:
            session_kwargs = {"available_tools": []}
        elif args.mcp:
            # The runtime launches this command as a subprocess and talks MCP over stdio.
            session_kwargs = {
                "mcp_servers": {
                    "calculator": {
                        "type": "stdio",
                        "command": sys.executable,
                        "args": ["-m", "puzzles.mcp_calculator"],
                        "env": {"PYTHONPATH": str(Path(__file__).parent.parent)},
                        "tools": ["*"],
                    }
                },
                "available_tools": ["calculator-calculate"],
                "on_permission_request": PermissionHandler.approve_all,
            }
        async with await client.create_session(
            model=args.model,
            reasoning_effort=args.effort,
            **session_kwargs,
        ) as session:
            session.on(on_event)
            print(task.prompt, "\n")
            reply = await session.send_and_wait(task.prompt, timeout=300)

    print("\nmodel reply:", reply.data.content if reply else None)
    print("expected:   ", task.answer)
    print("correct:    ", bool(reply) and grade(task, reply.data.content))


if __name__ == "__main__":
    asyncio.run(main())
