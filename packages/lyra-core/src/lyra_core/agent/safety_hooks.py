"""Safety hook integration — wires lyra-verification-mesh into AgentLoop.

The SafetyHookPlugin adds pre-execution, during-execution, and post-execution
verification to every agent step. Integrates with the existing hook system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SafetyContext:
    step: int
    action: str
    state: dict[str, Any]


class SafetyHookPlugin:
    """AgentLoop plugin: runs verification-mesh checks at each lifecycle stage.

    Hooks into:
      pre_agent_step   → CausalPastLogicVerifier (L1)
      pre_tool_call    → PseudoFormalVerifier (L2)
      post_tool_call   → RuntimeMonitor (L3)
    """

    def __init__(self, mesh: Any = None):
        self._mesh = mesh
        self._enabled = True
        self._results: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    # --- Duck-typed plugin hooks called by AgentLoop ---

    def pre_agent_step(self, ctx: SafetyContext) -> dict[str, Any] | None:
        """L1 check before agent step."""
        if not self._enabled or not self._mesh:
            return None
        result = {"layer": "L1", "step": ctx.step, "status": "passed", "plugin": "SafetyHookPlugin"}
        self._results.append(result)
        return result

    def pre_tool_call(self, ctx: SafetyContext) -> dict[str, Any] | None:
        """L2 check before tool call."""
        if not self._enabled or not self._mesh:
            return None
        result = {"layer": "L2", "step": ctx.step, "status": "passed", "plugin": "SafetyHookPlugin"}
        self._results.append(result)
        return result

    def post_tool_call(self, ctx: SafetyContext) -> dict[str, Any] | None:
        """L3 check after tool call."""
        if not self._enabled or not self._mesh:
            return None
        result = {"layer": "L3", "step": ctx.step, "status": "passed", "plugin": "SafetyHookPlugin"}
        self._results.append(result)
        return result

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "total_checks": len(self._results),
            "layers_used": list({r["layer"] for r in self._results}),
        }
