"""A calculator exposed as an MCP server over stdio.

The Copilot runtime starts this file as a subprocess, asks it which tools it offers
(name, description, schema) and sends it tool calls as JSON-RPC messages.

Run by hand to check it starts (it waits for MCP messages on stdin):
    PYTHONPATH=src .venv/bin/python -m puzzles.mcp_calculator
"""

from mcp.server.mcpserver import MCPServer

from puzzles.tools import CALCULATOR_DESCRIPTION, calculate

server = MCPServer("calculator")


@server.tool(name="calculate", description=CALCULATOR_DESCRIPTION)
def calculate_tool(expression: str) -> str:
    """expression: Arithmetic expression, e.g. '17620 * 1.539 * 0.985'"""
    return calculate(expression)


if __name__ == "__main__":
    server.run(transport="stdio")
