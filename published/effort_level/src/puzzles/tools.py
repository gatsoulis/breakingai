"""Tools the model can call. Add new tools here and register them in TOOLS."""

from __future__ import annotations

import ast
import operator
import sys
from pathlib import Path

from copilot import define_tool
from pydantic import BaseModel, Field

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def safe_eval(node: ast.AST) -> float:
    """Evaluate only numbers and + - * / ** and parentheses; never arbitrary code."""
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](safe_eval(node.left), safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](safe_eval(node.operand))
    raise ValueError("only numbers and + - * / ** ( ) are allowed")


def calculate(expression: str) -> str:
    """Shared by the in-process tool and the MCP server."""
    try:
        return str(safe_eval(ast.parse(expression, mode="eval")))
    except Exception as exc:
        # Errors go back to the model as text so it can fix its input.
        return f"error: {exc}"


# 1. The parameter schema: the model sees these names and descriptions.
class CalculatorParams(BaseModel):
    expression: str = Field(description="Arithmetic expression, e.g. '17620 * 1.539 * 0.985'")


CALCULATOR_DESCRIPTION = (
    "Exact arithmetic. Use for any multiplication, division or other calculation "
    "instead of computing in your head. Supports + - * / ** and parentheses."
)


# 2. The tool: the description is what the model reads to decide when to call it.
@define_tool(
    description=CALCULATOR_DESCRIPTION,
    skip_permission=True,  # pure math with no side effects, so no approval prompt
)
def calculator(params: CalculatorParams) -> str:
    return calculate(params.expression)


TOOLS = {"calculator": calculator}

# Tools served by an MCP server subprocess. The runtime starts the command and talks MCP over stdio.
MCP_TOOLS = {
    "calculator-mcp": {
        "server_name": "calculator",
        "config": {
            "type": "stdio",
            "command": sys.executable,
            "args": ["-m", "puzzles.mcp_calculator"],
            "env": {"PYTHONPATH": str(Path(__file__).parent.parent)},
            "tools": ["*"],
        },
        "tool_names": ["calculator-calculate"],  # "<server>-<tool>" as the model sees it
    }
}
