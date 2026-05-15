"""Agent Loop Integration for Lyra TUI.

Connects the TUI to actual LLM providers with streaming output.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator


class TUIAgentIntegration:
    """Integrates AgentLoop with TUI."""

    def __init__(self, model: str, repo_root, budget_cap_usd: float | None = None):
        self.model = model
        self.repo_root = repo_root
        self.budget_cap_usd = budget_cap_usd
        self._agent_loop = None

    async def initialize(self):
        """Initialize agent loop."""
        from lyra_cli.llm_factory import build_llm_auto

        # Build LLM provider
        llm = build_llm_auto(model_hint=self.model)

        # For now, create a simple agent loop without ToolKernel
        # TODO: Integrate with actual lyra_core agent loop when available
        self._agent_loop = {
            "llm": llm,
            "total_tokens": 0,
            "total_cost": 0.0,
            "context_tokens": 0,
        }

    async def run_agent(
        self, user_input: str
    ) -> AsyncIterator[dict]:
        """Run agent with streaming output.

        Yields:
            dict with keys:
                - type: "text" | "tool" | "done"
                - content: str
                - metadata: dict (optional)
        """
        if not self._agent_loop:
            await self.initialize()

        # Simple response for now
        # TODO: Implement actual streaming when lyra_core is ready
        yield {
            "type": "text",
            "content": "Agent integration in progress. ",
        }

        yield {
            "type": "text",
            "content": f"Received: {user_input}\n",
        }

    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        if not self._agent_loop:
            return {
                "total_tokens": 0,
                "total_cost": 0.0,
                "context_tokens": 0,
            }

        return {
            "total_tokens": self._agent_loop.get("total_tokens", 0),
            "total_cost": self._agent_loop.get("total_cost", 0.0),
            "context_tokens": self._agent_loop.get("context_tokens", 0),
        }


        return {
            "total_tokens": self._agent_loop.total_tokens,
            "total_cost": self._agent_loop.total_cost,
            "context_tokens": self._agent_loop.context_tokens,
        }
