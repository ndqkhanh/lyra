"""Lyra LLM Agent — wraps the Anthropic SDK for use by the TUI gateway."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable, cast

import anthropic
from anthropic.types import MessageParam

logger = logging.getLogger(__name__)

StreamCallback = Callable[[str], None]


def _load_claude_settings_env() -> None:
    """Load ANTHROPIC_* env vars from ~/.claude/settings.json if not already set."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return
    try:
        with open(settings_path) as f:
            cfg = json.load(f)
    except Exception:
        return
    env = cfg.get("env", {})
    if not isinstance(env, dict):
        return
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL", "ANTHROPIC_AUTH_TOKEN"):
        if key not in os.environ and key in env:
            os.environ[key] = str(env[key])
    if "ANTHROPIC_AUTH_TOKEN" in env and "ANTHROPIC_API_KEY" not in os.environ:
        os.environ["ANTHROPIC_API_KEY"] = str(env["ANTHROPIC_AUTH_TOKEN"])


def _api_key() -> str:
    _load_claude_settings_env()
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return key


class LyraAgent:
    """LLM agent wrapping the Anthropic Messages API.

    Implements the interface expected by ``tui_gateway.server``:
    ``run_conversation()``, ``interrupt()``, ``_compress_context()``,
    ``model``, and per-session token counters.
    """

    def __init__(self, session_id: str, session_key: str, model: str | None = None) -> None:
        self._sid = session_id
        self._key = session_key
        self.model = model or os.environ.get("LYRA_MODEL", "") or os.environ.get("ANTHROPIC_MODEL", "") or "claude-sonnet-4-6"
        self._client = anthropic.Anthropic(api_key=_api_key())
        self._interrupt = threading.Event()

        # usage counters
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        self.session_cache_read_tokens = 0
        self.session_cache_write_tokens = 0
        self.session_reasoning_tokens = 0
        self.session_total_tokens = 0
        self.session_api_calls = 0

    # ── public API ──────────────────────────────────────────────────

    def interrupt(self) -> None:
        """Signal the current ``run_conversation`` to stop at the next safe point."""
        self._interrupt.set()

    def run_conversation(
        self,
        text: str,
        *,
        conversation_history: list[dict] | None = None,
        stream_callback: StreamCallback | None = None,
    ) -> dict:
        """Run a single turn of conversation.

        Returns a dict with keys: ``messages`` (full message list), ``final_response`` (str),
        and optionally ``interrupted`` or ``error``.
        """
        self._interrupt.clear()

        messages: list[dict[str, Any]] = list(conversation_history or [])
        messages.append({"role": "user", "content": text})

        try:
            final = ""
            with self._client.messages.stream(
                model=self.model,
                max_tokens=8192,
                messages=cast(list[MessageParam], messages),
            ) as stream:
                for event in stream:
                    if self._interrupt.is_set():
                        stream.close()
                        messages.append({"role": "assistant", "content": final})
                        return {
                            "messages": messages,
                            "final_response": final,
                            "interrupted": True,
                        }

                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        delta = event.delta.text
                        final += delta
                        if stream_callback:
                            stream_callback(delta)

                    elif event.type == "message_delta":
                        self._record_usage(event.usage)

        except anthropic.APIError as exc:
            logger.error("Anthropic API error: %s", exc)
            return {"messages": messages, "final_response": "", "error": str(exc)}
        except Exception as exc:
            logger.error("Unexpected error in run_conversation: %s", exc)
            return {"messages": messages, "final_response": "", "error": str(exc)}

        messages.append({"role": "assistant", "content": final})
        self.session_api_calls += 1

        return {"messages": messages, "final_response": final}

    def _compress_context(self, history: list[dict], _keep_last: int | None = None) -> tuple[list[dict], dict]:
        """Basic context compression: keep system message + last N messages."""
        keep = _keep_last or 20
        system_msgs = [m for m in history if m.get("role") == "system"]
        rest = [m for m in history if m.get("role") != "system"]

        if len(rest) <= keep:
            return history, {"compressed": False, "original": len(history), "final": len(history)}

        compressed = system_msgs + rest[-keep:]
        return compressed, {"compressed": True, "original": len(history), "final": len(compressed)}

    # ── internals ───────────────────────────────────────────────────

    def _record_usage(self, usage: Any) -> None:
        if usage is None:
            return
        self.session_input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.session_output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.session_cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.session_cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.session_total_tokens = (
            self.session_input_tokens + self.session_output_tokens
        )
