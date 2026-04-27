"""Hermes-style :class:`AgentLoop` for lyra.

The loop is deliberately minimal — it is a *driver* that owns the
LLM/tool/store interaction shape, not the semantics of any specific
model, tool, or persistence layer. Plugins observe deterministic seams
and may short-circuit the loop via :class:`KeyboardInterrupt`.

Contract (see ``tests/test_agent_loop_contract.py``):

- Construction:
  ``AgentLoop(llm=..., tools=..., store=..., plugins=[...], budget=IterationBudget(max=N))``
- ``run_conversation(user_text, *, session_id) -> TurnResult``
- Plugin hooks (duck-typed, all optional):
    * ``on_session_start(ctx)`` — once, before the first LLM call
    * ``pre_llm_call(ctx)``    — before each LLM call
    * ``pre_tool_call(ctx)``   — before each tool dispatch; may raise
      ``KeyboardInterrupt`` to terminate the turn
    * ``post_tool_call(ctx)``  — after each tool dispatch returns,
      including when the dispatch synthesised an error dict. Paired
      1:1 with ``pre_tool_call`` (hermes-agent parity).
    * ``on_session_end(ctx)``  — always, once, at the tail
- Stop reasons surfaced on :class:`TurnResult`:
    * ``end_turn``    — LLM returned without further tool calls
    * ``budget``      — :class:`IterationBudget` exhausted
    * ``interrupt``   — plugin raised KeyboardInterrupt (or ^C)

The loop is inspired by NousResearch/hermes-agent's
``run_conversation`` and opencode's tool-dispatch shape, rewritten in
Python with explicit hook seams so the REPL, test-driver and task-tool
subagent fork all share one implementation.
"""

from __future__ import annotations

from concurrent.futures import Executor
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, MutableMapping, Optional

_SKILL_MANAGE_TOOL = "skill_manage"
_DEFAULT_SKILL_NUDGE_INTERVAL = 8


@dataclass
class IterationBudget:
    """Hard cap on LLM calls within a single ``run_conversation``.

    The budget counts *LLM invocations* (not tool dispatches). Reaching
    ``max`` stops the loop with ``stopped_by="budget"``. ``grace`` is a
    soft nudge used by higher-level callers (e.g. post-turn skill
    review); it does not affect the hard cap here.
    """

    max: int = 25
    grace: int = 0


@dataclass
class TurnResult:
    """Structured outcome of a single turn."""

    final_text: str = ""
    iterations: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    stopped_by: str = "end_turn"


# --- Plugin context helpers ----------------------------------------- #


@dataclass
class SessionCtx:
    """Context passed to ``on_session_start`` / ``on_session_end``."""

    session_id: str
    user_text: str = ""


@dataclass
class LLMCtx:
    """Context passed to ``pre_llm_call``."""

    session_id: str
    iteration: int
    messages: list[dict]


@dataclass
class ToolCtx:
    """Context passed to ``pre_tool_call``."""

    session_id: str
    tool_name: str
    arguments: Mapping[str, Any]
    call_id: str | None = None


@dataclass
class ToolResultCtx:
    """Context passed to ``post_tool_call``.

    Mirrors :class:`ToolCtx` plus the dispatch outcome. When the tool
    body raised, ``result`` is the ``{"error": ..., "type": ...}`` dict
    the loop synthesised — this keeps the post-hook contract total,
    which is what hermes-agent plugins (audit / budget / safety) rely
    on to observe every outcome regardless of failure mode.
    """

    session_id: str
    tool_name: str
    arguments: Mapping[str, Any]
    result: Any
    call_id: str | None = None


def _fire(plugins: list, hook: str, ctx: Any) -> None:
    """Invoke ``hook`` on each plugin that declares it.

    Hooks are duck-typed: a plugin contributes a hook simply by defining
    a method with that name. Exceptions propagate — KeyboardInterrupt in
    particular is how a plugin (or the user via ^C) can stop the loop.
    Non-interrupt errors are *not* swallowed here; the loop's own
    try/except handles termination semantics.
    """
    for plugin in plugins:
        fn = getattr(plugin, hook, None)
        if callable(fn):
            fn(ctx)


# --- The loop -------------------------------------------------------- #


@dataclass
class AgentLoop:
    """Drive one agentic conversation turn.

    The loop repeatedly asks the ``llm`` for a message, and if the
    response includes tool calls, dispatches them via ``tools`` before
    re-asking. Each LLM call counts against ``budget``. Plugin hooks
    observe the seams; ``store`` receives user/assistant messages for
    persistence.

    Skill self-creation loop (hermes pattern, plan Phase 3):

    - ``_iters_since_skill`` counts tool-loop iterations where the
      ``skill_manage`` tool is present in ``tools``. A direct
      ``skill_manage`` dispatch resets the counter to 0.
    - After each turn, if ``skill_manage`` is available AND the counter
      exceeds ``skill_nudge_interval``, the loop submits a background
      skill review job to ``review_executor``. The job runs a forked
      ``AgentLoop`` that may call ``skill_manage`` itself — this happens
      off the user's critical path.
    """

    llm: Any
    tools: Mapping[str, Callable[..., Any]]
    store: Any
    plugins: list = field(default_factory=list)
    budget: IterationBudget = field(default_factory=IterationBudget)
    skill_nudge_interval: int = _DEFAULT_SKILL_NUDGE_INTERVAL
    review_executor: Optional[Executor] = None
    _iters_since_skill: int = 0

    # ---- public API ------------------------------------------------- #

    def run_conversation(self, user_text: str, *, session_id: str) -> TurnResult:
        """Run a single turn. Always returns a :class:`TurnResult`."""
        self._start_session(session_id=session_id, user_text=user_text)

        messages: list[dict] = [{"role": "user", "content": user_text}]
        tool_calls_record: list[dict] = []
        result = TurnResult()

        try:
            while result.iterations < self.budget.max:
                _fire(
                    self.plugins,
                    "pre_llm_call",
                    LLMCtx(
                        session_id=session_id,
                        iteration=result.iterations,
                        messages=list(messages),
                    ),
                )

                response = self._invoke_llm(messages)
                result.iterations += 1

                content = str(response.get("content", "") or "")
                tool_calls = list(response.get("tool_calls") or [])
                stop_reason = response.get("stop_reason", "end_turn")

                self._record_assistant(session_id, content, tool_calls)
                messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                    }
                )

                if not tool_calls:
                    # No tool use → conversation turn ends here.
                    result.final_text = content
                    result.stopped_by = (
                        "end_turn" if stop_reason in ("end_turn", "stop", "complete") else stop_reason
                    )
                    break

                # Tool-loop iteration with skill_manage available — tick the
                # skills self-creation counter (plan Phase 3).
                if _SKILL_MANAGE_TOOL in (self.tools or {}):
                    self._iters_since_skill += 1

                # Dispatch every tool call; a plugin may KeyboardInterrupt
                # out of ``pre_tool_call`` to terminate the turn.
                for call in tool_calls:
                    tool_name = str(call.get("name", ""))
                    args = call.get("arguments") or {}
                    _fire(
                        self.plugins,
                        "pre_tool_call",
                        ToolCtx(
                            session_id=session_id,
                            tool_name=tool_name,
                            arguments=args,
                            call_id=call.get("id"),
                        ),
                    )
                    tool_result = self._dispatch_tool(tool_name, args)
                    _fire(
                        self.plugins,
                        "post_tool_call",
                        ToolResultCtx(
                            session_id=session_id,
                            tool_name=tool_name,
                            arguments=args,
                            result=tool_result,
                            call_id=call.get("id"),
                        ),
                    )
                    tool_calls_record.append(
                        {
                            "id": call.get("id"),
                            "name": tool_name,
                            "arguments": dict(args) if isinstance(args, Mapping) else args,
                            "result": tool_result,
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "content": _stringify(tool_result),
                        }
                    )
                    if tool_name == _SKILL_MANAGE_TOOL:
                        # The model just tended the skill garden — reset
                        # the nudge counter so we don't over-schedule
                        # background reviews (hermes pattern).
                        self._iters_since_skill = 0
            else:
                # ``while`` exited without break → budget exhausted.
                result.stopped_by = "budget"
        except KeyboardInterrupt:
            result.stopped_by = "interrupt"

        result.tool_calls = tool_calls_record
        self._maybe_schedule_skill_review(session_id=session_id)
        _fire(
            self.plugins,
            "on_session_end",
            SessionCtx(session_id=session_id, user_text=user_text),
        )
        return result

    # ---- skill self-creation -------------------------------------- #

    def _maybe_schedule_skill_review(self, *, session_id: str) -> None:
        """Submit a background skill review when the nudge threshold is crossed.

        Mirrors hermes-agent's ``_iters_since_skill`` nudge: if the
        parent turn has gone long without a ``skill_manage`` call and the
        tool is actually wired in, fork a review on the
        ``review_executor`` so the user's next turn is not blocked.
        """
        if _SKILL_MANAGE_TOOL not in (self.tools or {}):
            return
        if self.review_executor is None:
            return
        if self._iters_since_skill <= self.skill_nudge_interval:
            return
        try:
            from lyra_skills.review.background import spawn_skill_review
        except Exception:
            return

        try:
            self.review_executor.submit(
                spawn_skill_review, self, session_id=session_id
            )
        except Exception:
            # Never let the critical path fail on a review submission.
            return
        # Avoid re-submitting every turn until the skill garden was tended.
        self._iters_since_skill = 0

    # ---- seams (override-friendly) ---------------------------------- #

    def _start_session(self, *, session_id: str, user_text: str) -> None:
        """Persist the user turn and fire ``on_session_start``."""
        start = getattr(self.store, "start_session", None)
        if callable(start):
            start(session_id=session_id)
        append = getattr(self.store, "append_message", None)
        if callable(append):
            append(session_id=session_id, role="user", content=user_text)
        _fire(
            self.plugins,
            "on_session_start",
            SessionCtx(session_id=session_id, user_text=user_text),
        )

    def _record_assistant(
        self, session_id: str, content: str, tool_calls: list[dict]
    ) -> None:
        append = getattr(self.store, "append_message", None)
        if callable(append):
            append(
                session_id=session_id,
                role="assistant",
                content=content,
                tool_calls=tool_calls,
            )

    def _invoke_llm(self, messages: list[dict]) -> MutableMapping[str, Any]:
        tool_defs = self._tool_defs()
        call = getattr(self.llm, "generate", None)
        if call is None and callable(self.llm):
            call = self.llm
        if call is None:
            raise RuntimeError("AgentLoop.llm must expose .generate(...) or be callable")
        response = call(messages=messages, tools=tool_defs)
        if not isinstance(response, Mapping):
            raise TypeError(f"LLM returned {type(response).__name__}, expected mapping")
        return dict(response)

    def _tool_defs(self) -> list[dict]:
        defs: list[dict] = []
        for name, fn in (self.tools or {}).items():
            if hasattr(fn, "__tool_schema__"):
                schema = fn.__tool_schema__  # type: ignore[attr-defined]
                if isinstance(schema, Mapping):
                    defs.append(dict(schema))
                    continue
            defs.append({"name": name, "description": (fn.__doc__ or "").strip()})
        return defs

    def _dispatch_tool(self, name: str, arguments: Any) -> Any:
        fn = (self.tools or {}).get(name)
        if fn is None:
            return {"error": f"unknown tool {name!r}"}
        try:
            if isinstance(arguments, Mapping):
                return fn(**arguments)
            if arguments in (None, {}, []):
                return fn()
            return fn(arguments)
        except KeyboardInterrupt:
            # Propagate to outer handler — treated as user interrupt.
            raise
        except Exception as exc:  # pragma: no cover - defensive
            return {"error": str(exc), "type": type(exc).__name__}


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        import json

        return json.dumps(value, default=str)
    except Exception:  # pragma: no cover - defensive
        return str(value)
