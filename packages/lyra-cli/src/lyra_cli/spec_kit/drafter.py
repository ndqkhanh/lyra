"""LLM-based artifact drafting with streaming."""

from __future__ import annotations
import asyncio
from typing import Any
from pathlib import Path

from .events import SpecDraftChunk


class Drafter:
    """Generates spec artifacts using LLM."""

    def __init__(self, llm_client: Any, event_bus: Any = None):
        self.llm_client = llm_client
        self.event_bus = event_bus
        self.templates_dir = Path(__file__).parent / "templates"

    async def draft_spec(self, prompt: str) -> str:
        """Draft spec.md from user prompt."""
        template = self._load_template("spec_template.md")

        # Placeholder - will implement LLM call
        draft = f"# Feature Spec\n\n{prompt}\n\n{template}"

        # Stream chunks
        if self.event_bus:
            for chunk in self._chunk_text(draft):
                await self._emit_chunk("spec", chunk)
                await asyncio.sleep(0.01)  # Simulate streaming

        return draft

    async def draft_plan(self, spec: str) -> str:
        """Draft plan.md from spec."""
        template = self._load_template("plan_template.md")
        draft = f"# Implementation Plan\n\n{template}"

        if self.event_bus:
            for chunk in self._chunk_text(draft):
                await self._emit_chunk("plan", chunk)
                await asyncio.sleep(0.01)

        return draft

    async def draft_tasks(self, plan: str) -> str:
        """Draft tasks.md from plan."""
        template = self._load_template("tasks_template.md")
        draft = f"# Tasks\n\n{template}"

        if self.event_bus:
            for chunk in self._chunk_text(draft):
                await self._emit_chunk("tasks", chunk)
                await asyncio.sleep(0.01)

        return draft

    def _load_template(self, filename: str) -> str:
        """Load template file."""
        path = self.templates_dir / filename
        if path.exists():
            return path.read_text()
        return ""

    def _chunk_text(self, text: str, chunk_size: int = 50) -> list[str]:
        """Split text into chunks for streaming."""
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    async def _emit_chunk(self, artifact: str, chunk: str) -> None:
        """Emit draft chunk event."""
        if self.event_bus:
            event = SpecDraftChunk(artifact=artifact, chunk=chunk)
            # Would emit to event bus here
