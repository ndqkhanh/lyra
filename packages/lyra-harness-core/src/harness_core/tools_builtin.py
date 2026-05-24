"""Generic tools used across multiple projects."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .tools import Tool, ToolError


class EchoTool(Tool):
    name = "echo"
    description = "Echo back the provided text. Useful for tests."
    risk = "low"
    writes = False

    class ArgsModel(BaseModel):
        text: str = Field(..., description="Text to echo")

    def run(self, args: "EchoTool.ArgsModel") -> str:
        return args.text


class CalculatorTool(Tool):
    """Safe arithmetic-only evaluator."""

    name = "calculator"
    description = "Evaluate a simple arithmetic expression (+, -, *, /, parens)."
    risk = "low"
    writes = False

    class ArgsModel(BaseModel):
        expression: str = Field(..., max_length=120)

    _ALLOWED = set("0123456789+-*/(). ")

    def run(self, args: "CalculatorTool.ArgsModel") -> str:
        if not args.expression.strip():
            raise ToolError("empty expression")
        bad = set(args.expression) - self._ALLOWED
        if bad:
            raise ToolError(f"disallowed characters: {sorted(bad)}")
        try:
            # intentionally restricted: only +-*/() and numbers allowed above
            result = eval(args.expression, {"__builtins__": {}}, {})  # noqa: S307
        except Exception as e:  # noqa: BLE001
            raise ToolError(f"evaluation failed: {e}") from e
        return str(result)
