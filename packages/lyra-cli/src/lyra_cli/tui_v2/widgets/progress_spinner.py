"""Real-time progress spinners — enhanced with multi-agent awareness.

Expands on the original single-spinner design to support parallel agent
visualizations, phase tracking, and ECC-style emoji status indicators.
"""
from __future__ import annotations

import time
from typing import Optional


# ── Spinner frames ──────────────────────────────────────────────────────

SPINNER_FRAMES = ["⏺", "✶", "✻", "✳", "✽", "✶"]
NYAN_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
HARP_FRAMES = ["♪", "♫", "♬", "♩"]  # Lyra constellation motif

SPINNER_VERBS = [
    "Thinking", "Analyzing", "Processing", "Computing",
    "Researching", "Implementing", "Verifying", "Optimizing",
    "Blanching", "Roosting", "Galloping", "Puttering", "Pollinating",
    "Composing", "Crafting", "Reasoning", "Investigating",
]


class ProgressSpinner:
    """Animated spinner with verb rotation and multi-agent awareness.

    Example output:
      ⏺ Thinking… (2s · ↓ 1.2k tokens)
      ✶ Analyzing… (5s · ↓ 3.4k tokens · 2 agents running)

    Supports per-agent subtracking:
      ♪ main: Roosting… (2m 53s · ↓ 2.6k tokens · thought for 28s)
      ♫ sub-agent-1: Analyzing… (10s · ↓ 1.1k tokens)
    """

    def __init__(self, style: str = "default"):
        self.frame_index = 0
        self.verb_index = 0
        self.start_time: Optional[float] = None
        self.tokens_used = 0
        self._agent_labels: dict[str, float] = {}  # agent_id → started_at
        self._agent_tokens: dict[str, int] = {}
        self._frame_set = (
            HARP_FRAMES if style == "harp"
            else NYAN_FRAMES if style == "nyan"
            else SPINNER_FRAMES
        )

    # ── Lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        self.start_time = time.time()
        self.frame_index = 0
        self.verb_index = 0

    def stop(self) -> None:
        self.start_time = None

    # ── Agent tracking ──────────────────────────────────────────────────

    def register_agent(self, agent_id: str) -> None:
        self._agent_labels[agent_id] = time.time()
        self._agent_tokens[agent_id] = 0

    def update_agent_tokens(self, agent_id: str, tokens: int) -> None:
        if agent_id in self._agent_tokens:
            self._agent_tokens[agent_id] = tokens

    def unregister_agent(self, agent_id: str) -> None:
        self._agent_labels.pop(agent_id, None)
        self._agent_tokens.pop(agent_id, None)

    @property
    def agent_count(self) -> int:
        return len(self._agent_labels)

    # ── Frame rendering ─────────────────────────────────────────────────

    def next_frame(
        self,
        tokens: int = 0,
        agent_id: Optional[str] = None,
        thought_time: Optional[float] = None,
    ) -> str:
        """Get next spinner frame.

        Args:
            tokens: Total tokens used so far
            agent_id: If provided, render per-agent frame
            thought_time: Extended thinking duration in seconds

        Returns:
            Formatted spinner string
        """
        frame = self._frame_set[self.frame_index % len(self._frame_set)]
        verb = SPINNER_VERBS[self.verb_index % len(SPINNER_VERBS)]
        self.frame_index += 1

        if self.frame_index % len(self._frame_set) == 0:
            self.verb_index += 1

        # ── Per-agent mode ──────────────────────────────────────────────
        if agent_id:
            if self.start_time:
                elapsed = time.time() - self.start_time
                dur = self._format_duration(elapsed)
            else:
                dur = ""

            tok_str = f"↓ {tokens / 1000:.1f}k tokens" if tokens > 0 else ""
            parts = [p for p in [dur, tok_str] if p]
            metrics = f" ({' · '.join(parts)})" if parts else ""

            return f"{frame} {agent_id}: {verb}…{metrics}"

        # ── Aggregate mode ──────────────────────────────────────────────
        status = f"{frame} {verb}…"

        parts = []
        if self.start_time:
            elapsed = time.time() - self.start_time
            parts.append(self._format_duration(elapsed))

        if tokens > 0:
            parts.append(f"↓ {tokens / 1000:.1f}k tokens")

        if self.agent_count > 1:
            parts.append(f"{self.agent_count} agents")

        if thought_time:
            parts.append(f"thought {self._format_duration(thought_time)}")

        if parts:
            status += f" ({' · '.join(parts)})"

        return status

    # ── Helpers ─────────────────────────────────────────────────────────

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
