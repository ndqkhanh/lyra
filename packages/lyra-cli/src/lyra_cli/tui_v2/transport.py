"""LyraTransport — bridge harness-tui events to Lyra's real agent loop.

The existing ``lyra tui`` command mounts ``HarnessApp`` against a
:class:`harness_tui.transport.MockTransport`, so the Textual shell only
displays a scripted demo. This transport runs the same ``harness_core``
``AgentLoop`` that ``lyra run`` uses (planner-less for the interactive
case), surfacing real LLM output, tool calls, and token counts to the
TUI.

Concurrency shape:
    submit()      — fast; captures the asyncio loop, spawns a worker
    stream()      — async iterator over the per-transport event queue
    worker thread — sync ``AgentLoop.run(task)``; emits typed events
                    back into the asyncio queue via
                    ``run_coroutine_threadsafe``

Tool-call observability rides on ``harness_core``'s ``HookRegistry``:
a per-turn registry binds ``PRE_TOOL_USE`` / ``POST_TOOL_USE`` to event
emitters, then ``AgentLoop`` is constructed with that registry. The
hooks never block or annotate — they're observation-only — so they
can't change agent behaviour.
"""
from __future__ import annotations

import asyncio
import threading
import time
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Optional

from harness_tui import events
from harness_tui.transport import Transport


# Text-chunk size when re-emitting the final assistant reply as a stream
# of ``TextDelta`` events. Keeps the chat-log render incremental even
# though ``AgentLoop.run`` returns ``final_text`` whole.
_CHUNK_SIZE = 80


def _chunks(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


class LyraTransport(Transport):
    """Drive harness-tui events from a real Lyra agent run."""

    name = "lyra"

    def __init__(
        self,
        *,
        repo_root: Path,
        model: str = "auto",
        max_steps: int = 20,
        provider: Any = None,
        tools: Any = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self._repo_root = Path(repo_root)
        self._model = model
        self._max_steps = max_steps
        self._provider = provider
        self._tools = tools
        self._system_prompt = system_prompt
        self._queue: asyncio.Queue[events.Event] = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="lyra-agent"
        )
        self._seq = 0
        self._cancel_event = threading.Event()

    # -- Lazy wiring (so construction is cheap + tests can inject) ----

    def _ensure_provider(self) -> Any:
        if self._provider is None:
            from ..llm_factory import build_llm  # local import: avoid cycle

            self._provider = build_llm(
                self._model, task_hint="", session_id="tui-v2"
            )
        return self._provider

    def _ensure_tools(self) -> Any:
        if self._tools is None:
            from harness_core.tools import ToolRegistry
            from lyra_core.tools import register_builtin_tools

            registry = ToolRegistry()
            register_builtin_tools(registry, repo_root=self._repo_root)
            self._tools = registry
        return self._tools

    # -- Public Transport contract ------------------------------------

    async def submit(self, user_text: str, *, mode: str = "default") -> str:
        turn_id = f"t_{uuid.uuid4().hex[:8]}"
        # Capture the running asyncio loop so the worker thread can push
        # events back via run_coroutine_threadsafe.
        self._loop = asyncio.get_running_loop()
        self._executor.submit(self._run_turn, turn_id, user_text, mode)
        return turn_id

    async def stream(self) -> AsyncIterator[events.Event]:
        while True:
            event = await self._queue.get()
            yield event

    async def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def cancel(self, call_id: str = "") -> None:
        """Signal the current in-flight turn to stop, then reset for the next."""
        del call_id
        self._cancel_event.set()

    # -- Threadsafe event emission ------------------------------------

    def _emit(self, event: events.Event) -> None:
        """Push an event onto the asyncio queue from any thread."""
        self._seq += 1
        event.seq = self._seq
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._queue.put(event), loop)

    # -- Worker (runs on the executor thread) -------------------------

    def _run_turn(self, turn_id: str, user_text: str, mode: str) -> None:
        # ``mode`` (plan / default / auto) reserved for Phase 2; the
        # interactive run path goes straight through AgentLoop without
        # a planner gate today. Future: when ``mode == "plan"``, route
        # via ``lyra_core.plan.run_planner`` and emit ``PlanProposed``.
        del mode
        # Reset cancel flag at the start of each new turn.
        self._cancel_event.clear()
        self._emit(events.TurnStarted(turn_id=turn_id, user_text=user_text))

        if self._cancel_event.is_set():
            self._emit(events.TurnFinished(turn_id=turn_id, stop_reason="cancelled"))
            return

        try:
            provider = self._ensure_provider()
            tools = self._ensure_tools()
        except Exception as exc:
            self._emit_error(turn_id, f"[provider error] {exc}")
            return

        if self._cancel_event.is_set():
            self._emit(events.TurnFinished(turn_id=turn_id, stop_reason="cancelled"))
            return

        from harness_core.hooks import Hook, HookDecision, HookEvent, HookRegistry
        from harness_core.loop import AgentLoop

        hooks = HookRegistry()
        started_at: dict[str, float] = {}

        def on_pre_tool(call, result) -> HookDecision:
            del result
            call_id = getattr(call, "id", None) or f"c_{uuid.uuid4().hex[:6]}"
            started_at[call_id] = time.monotonic()
            self._emit(
                events.ToolStarted(
                    turn_id=turn_id,
                    call_id=call_id,
                    name=str(getattr(call, "name", "tool")),
                    input=_coerce_mapping(getattr(call, "arguments", None)),
                )
            )
            return HookDecision()

        def on_post_tool(call, result) -> HookDecision:
            call_id = getattr(call, "id", None) or "?"
            duration_ms = int(
                (time.monotonic() - started_at.pop(call_id, time.monotonic())) * 1000
            )
            status = "error" if (result and getattr(result, "is_error", False)) else "ok"
            content = ""
            if result is not None:
                content = str(getattr(result, "content", ""))[:2048]
            self._emit(
                events.ToolFinished(
                    call_id=call_id,
                    status=status,
                    output={"content": content} if content else {},
                    duration_ms=duration_ms,
                )
            )
            return HookDecision()

        hooks.register(
            Hook(
                name="lyra-tui-pre",
                event=HookEvent.PRE_TOOL_USE,
                matcher="*",
                handler=on_pre_tool,
            )
        )
        hooks.register(
            Hook(
                name="lyra-tui-post",
                event=HookEvent.POST_TOOL_USE,
                matcher="*",
                handler=on_post_tool,
            )
        )

        loop_kwargs: dict[str, Any] = {"hooks": hooks, "max_steps": self._max_steps}
        if self._system_prompt:
            loop_kwargs["system_prompt"] = self._system_prompt
        agent = AgentLoop(llm=provider, tools=tools, **loop_kwargs)

        try:
            result = agent.run(user_text)
        except Exception as exc:
            self._emit_error(turn_id, f"[agent error] {exc}")
            return

        if self._cancel_event.is_set():
            self._cancel_event.clear()
            self._emit(events.TurnFinished(turn_id=turn_id, stop_reason="cancelled"))
            return

        final_text = getattr(result, "final_text", "") or ""
        for chunk in _chunks(final_text):
            if self._cancel_event.is_set():
                break
            self._emit(events.TextDelta(turn_id=turn_id, text=chunk))

        tokens_in, tokens_out, cost_usd = _extract_usage(provider)
        stop_reason = _normalise_stop(getattr(result, "stop_reason", "end_turn"))
        self._cancel_event.clear()
        self._emit(
            events.TurnFinished(
                turn_id=turn_id,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                stop_reason=stop_reason,
            )
        )

    def _emit_error(self, turn_id: str, message: str) -> None:
        self._emit(events.TextDelta(turn_id=turn_id, text=message))
        self._emit(events.TurnFinished(turn_id=turn_id, stop_reason="error"))


# ---------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if value is None:
        return {}
    return {"value": value}


def _extract_usage(provider: Any) -> tuple[int, int, float]:
    usage = getattr(provider, "cumulative_usage", None) or {}
    if not isinstance(usage, Mapping):
        return 0, 0, 0.0
    tokens_in = int(usage.get("input_tokens", 0) or 0)
    tokens_out = int(usage.get("output_tokens", 0) or 0)
    cost = float(usage.get("cost_usd", 0.0) or 0.0)
    return tokens_in, tokens_out, cost


def _normalise_stop(reason: Any) -> str:
    if reason is None or reason == "":
        return "end_turn"
    s = str(reason)
    return s.split(".", 1)[1].lower() if s.startswith("StopReason.") else s
