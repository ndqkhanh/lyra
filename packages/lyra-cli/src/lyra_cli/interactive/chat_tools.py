"""Chat-mode tool loop — make Lyra's REPL actually call tools.

Pre-v2.4, ``_chat_with_llm`` (in :mod:`lyra_cli.interactive.session`)
made *one* LLM call per user turn and returned whatever text the model
emitted. Tool calls in the reply were silently dropped: the assistant
might say "I'll read that file for you" and emit a structured
``tool_calls`` block, but Lyra rendered only the prose and never read
the file. Every advert about file-aware chat ("ask Lyra about your
codebase") was a soft lie.

This module ships the missing piece: a real tool-dispatch loop that

1. Builds an Anthropic-style tool spec list from a small, curated chat
   registry (Read, Glob, Grep, Write, Edit; the same five claw-code
   exposes by default). The list is passed to ``provider.generate`` so
   the LLM knows which tools it may call.
2. If the reply has ``tool_calls``, asks
   :class:`ToolApprovalCache` whether each is allowed (yolo skips,
   strict re-prompts), runs the approved ones via the
   :class:`harness_core.tools.ToolRegistry`, builds a tool-result
   ``Message``, and feeds it back into ``provider.generate`` for the
   next hop.
3. Caps the loop at ``max_steps`` (default 8) so a misbehaving model
   can't lock up the REPL with infinite tool calls.
4. Returns the final assistant text, the full transcript (so callers
   can persist it), and a small :class:`ToolLoopReport` with billing
   hints (tool-call count, blocked count) for ``/status``.

The loop is provider-agnostic — anything that implements
``LLMProvider.generate(messages, tools=…)`` works (OpenAI-compat
family, Anthropic via :class:`LyraAnthropicLLM`, Vertex via
:class:`GeminiVertexLLM`, Bedrock, Copilot, Gemini). Streaming is not
yet supported in the tool loop because tool-call SSE arrives as
incremental JSON deltas and Rich can't accumulate a tool card from
half-arguments. The chat handler falls back to non-streaming
``generate`` when tools are enabled and re-engages streaming on the
final hop (no tool calls) so the *answer* still streams.

The renderer is intentionally pluggable: callers pass a ``render``
callback that receives a ``ToolEvent`` and decides how to surface it
(Rich panel, plain-text card, jsonl event, no-op for tests). This
keeps the loop unit-testable without a Rich console.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

# These imports are deliberately late-bound at function call sites to
# avoid pulling all of harness_core into the module just to expose
# types. Top-level imports here are pure typing or zero-cost.

from .tool_approval import ToolApprovalCache


# ---------------------------------------------------------------------------
# Curated chat-mode tool set
# ---------------------------------------------------------------------------
#
# What's *in*: the five canonical filesystem-scoped tools claw-code
# exposes by default. They're enough to power "ask Lyra about your
# codebase" and "fix this typo" without a permission prompt.
#
# What's *out*: Bash / ExecuteCode / Browser / WebFetch — these need
# explicit user opt-in (planned ``/tools enable bash`` in v2.4.x).
# Keeping the chat-mode default to read/write within the repo follows
# claw-code's principle of least surprise: the assistant can show you
# code and propose edits, but it can't run arbitrary commands without
# you turning that on.
_CHAT_TOOL_NAMES: tuple[str, ...] = ("Read", "Glob", "Grep", "Edit", "Write")


def build_chat_tool_registry(repo_root: Path) -> Any:
    """Build a :class:`harness_core.tools.ToolRegistry` for chat mode.

    Lazy-imports :mod:`lyra_core.tools.builtin` so a stripped install
    that doesn't ship lyra-core (rare — almost no one does that) can
    still ``import lyra_cli`` and run plain text turns.

    Args:
        repo_root: The directory the tools are sandboxed to. All
            five tools enforce ``Path.resolve()`` confinement to this
            directory; symlink escapes are rejected with
            ``ToolError``.

    Returns:
        A populated :class:`ToolRegistry`. Each tool's
        ``to_schema()`` already emits the Anthropic-style
        ``{name, description, input_schema}`` shape that Lyra's
        OpenAI-compat ``_tool_to_openai`` translates to OpenAI's
        ``{type: "function", function: …}``.

    Raises:
        ImportError: If ``lyra_core`` is not installed.
    """
    from harness_core.tools import ToolRegistry
    from lyra_core.tools.builtin import register_builtin_tools

    registry = ToolRegistry()
    register_builtin_tools(registry, repo_root=repo_root)
    return registry


def chat_tool_schemas(registry: Any) -> list[dict[str, Any]]:
    """Emit the tool-spec list to pass to ``provider.generate(tools=…)``.

    Filtered to :data:`_CHAT_TOOL_NAMES` so chat mode never accidentally
    advertises a high-risk tool (e.g. a ``Bash`` tool registered for
    a different code path) just because it's in the registry.
    """
    return registry.schemas(allowed=set(_CHAT_TOOL_NAMES))


def collect_mcp_tool_specs(
    session: Any,
    *,
    only_trusted: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Gather chat-loop schemas + dispatch metadata for live MCP servers.

    Returns ``(schemas, dispatchers_by_lyra_name, raw_entries_by_name)``:

    * ``schemas`` — list of Anthropic-style ``{name, description,
      input_schema}`` dicts ready to merge into ``chat_tool_schemas``
      output.
    * ``dispatchers_by_lyra_name`` — map ``"mcp__server__tool"`` →
      :class:`lyra_mcp.client.MCPToolEntry`. The chat loop uses this
      to route tool calls back to the right transport.
    * ``raw_entries_by_name`` — same key, but pointing at the raw
      MCP transport so the loop can call ``transport.call_tool``
      with the original (unprefixed) tool name.

    Tolerant: when lyra-mcp isn't installed or the session has no
    spawned clients, returns three empty containers and the caller
    can proceed with the regular chat tool set unchanged.

    ``only_trusted`` (default False) restricts the schema list to
    servers whose ``trust`` field is ``"first-party"``. Useful for
    very-high-stakes turns where the user wants to disable
    third-party MCP for a single message.
    """
    try:
        from lyra_mcp.client.toolspec import normalise_mcp_tools
    except Exception:
        return [], {}, {}
    clients = getattr(session, "_mcp_clients", {}) or {}
    servers = {s.name: s for s in (getattr(session, "mcp_servers", []) or [])}
    schemas: list[dict[str, Any]] = []
    by_lyra_name: dict[str, Any] = {}
    transports: dict[str, Any] = {}
    for name, transport in clients.items():
        cfg = servers.get(name)
        if only_trusted and cfg is not None and cfg.trust != "first-party":
            continue
        try:
            tools = transport.list_tools()
        except Exception:
            continue
        entries = normalise_mcp_tools(name, tools)
        for entry in entries:
            schemas.append(entry.schema)
            by_lyra_name[entry.lyra_name] = entry
            transports[entry.lyra_name] = transport
    return schemas, by_lyra_name, transports


# ---------------------------------------------------------------------------
# Loop driver
# ---------------------------------------------------------------------------


@dataclass
class ToolEvent:
    """A single rendering checkpoint emitted by the tool loop.

    Callers (the REPL renderer, test fixtures) pattern-match on
    :attr:`kind` and decide how to surface the event.

    Kinds:

    * ``"call"`` — the LLM proposed a tool call. ``call_id`` /
      ``tool_name`` / ``args`` describe it. Renderer should show a
      "running …" card.
    * ``"result"`` — the tool finished. ``output`` carries the
      stringified result (truncated by callers when needed),
      ``is_error`` flags failures.
    * ``"denied"`` — approval was rejected; ``reason`` carries the
      message that was sent back to the model.
    * ``"limit_reached"`` — the loop hit ``max_steps`` and bailed
      out. The final assistant text is whatever was last emitted.
    """

    kind: str
    call_id: str = ""
    tool_name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    is_error: bool = False
    reason: str = ""


@dataclass
class ToolLoopReport:
    """Summary of a finished tool loop, for billing / observability."""

    final_text: str
    tool_calls: int = 0
    blocked_calls: int = 0
    steps: int = 0
    hit_max_steps: bool = False
    transcript: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Approval callback signature (chat mode)
# ---------------------------------------------------------------------------
#
# The chat loop doesn't talk to ``input()`` directly — that would
# couple it to a TTY and make tests that drive the loop hard to
# write. Instead, callers pass an ``approve`` callback receiving the
# pending tool call's ``(name, args)`` and returning ``True`` to run
# / ``False`` to deny. The REPL wires this to Rich Confirm; tests
# pass ``lambda *_: True``.

ApproveFn = Callable[[str, dict[str, Any]], bool]
RenderFn = Callable[[ToolEvent], None]


def _default_approve(_name: str, _args: dict[str, Any]) -> bool:
    """Default approval policy: allow. Used in tests and yolo mode."""
    return True


def _default_render(_event: ToolEvent) -> None:
    """Default renderer: silently drop. Used by tests and headless runs."""
    return None


def run_chat_tool_loop(
    provider: Any,
    messages: list[Any],
    registry: Any,
    *,
    approval_cache: Optional[ToolApprovalCache] = None,
    approve: Optional[ApproveFn] = None,
    render: Optional[RenderFn] = None,
    max_steps: int = 8,
    max_tokens: int = 1024,
    on_usage: Optional[Callable[[Any], None]] = None,
    mcp_schemas: Optional[list[dict[str, Any]]] = None,
    mcp_transports: Optional[dict[str, Any]] = None,
    mcp_call_timeout_s: float = 60.0,
) -> ToolLoopReport:
    """Drive the ``LLMProvider`` think-act-observe loop until it ends.

    This is a strict, deterministic version of
    :class:`harness_core.loop.AgentLoop` tuned for the chat REPL:

    * No tracer / hooks — the chat handler doesn't consume them
      today (Phase D wires hooks into chat).
    * No system-prompt injection — the caller has already built the
      message list with the right system slot.
    * Approval is delegated outward, so the REPL renders prompts
      via Rich while tests can inject ``approve=lambda *_: True``.
    * ``on_usage`` is a billing callback fired *after every*
      ``generate`` so the chat handler's :func:`_bill_turn` runs
      once per LLM hop, not just on the final one.

    Returns a :class:`ToolLoopReport`. ``final_text`` is the assistant
    content from the *last* hop with no tool calls (or the last hop
    period if ``max_steps`` was hit).
    """
    from harness_core.messages import Message  # late-bound

    approve_cb: ApproveFn = approve or _default_approve
    render_cb: RenderFn = render or _default_render
    cache = approval_cache or ToolApprovalCache(mode="normal")

    schemas = list(chat_tool_schemas(registry))
    if mcp_schemas:
        schemas.extend(mcp_schemas)
    mcp_routes: dict[str, Any] = dict(mcp_transports or {})
    transcript: list[Any] = list(messages)
    tool_count = 0
    blocked = 0
    last_text = ""

    for step in range(max_steps):
        try:
            reply: Any = provider.generate(
                transcript,
                tools=schemas,
                max_tokens=max_tokens,
            )
        except Exception:
            # Bubble up — the chat handler converts this into a
            # one-line diagnostic. We do *not* swallow because the
            # transcript is already partially mutated and a silent
            # retry would double-bill.
            raise

        if on_usage is not None:
            try:
                on_usage(provider)
            except Exception:
                # Billing failures must not abort a tool loop —
                # rendering the tool result is more important than
                # ticking the meter.
                pass

        transcript.append(reply)
        last_text = (getattr(reply, "content", "") or "").strip()

        tool_calls = list(getattr(reply, "tool_calls", []) or [])
        if not tool_calls:
            return ToolLoopReport(
                final_text=last_text,
                tool_calls=tool_count,
                blocked_calls=blocked,
                steps=step + 1,
                hit_max_steps=False,
                transcript=transcript,
            )

        # Execute every tool call the model proposed in this hop.
        # Multiple calls per hop happen on stronger models (gpt-4o,
        # Claude Sonnet) when they decide to read several files in
        # parallel before reasoning over the lot.
        results: list[Any] = []
        for call in tool_calls:
            name = getattr(call, "name", "") or ""
            call_id = getattr(call, "id", "") or ""
            args = dict(getattr(call, "args", {}) or {})
            tool_count += 1

            render_cb(
                ToolEvent(
                    kind="call",
                    call_id=call_id,
                    tool_name=name,
                    args=args,
                )
            )

            verdict = cache.inquire(name)
            if verdict == "deny":
                # Cached deny — short-circuit without prompting.
                blocked += 1
                results.append(
                    _tool_result_obj(
                        call_id,
                        f"blocked by cached deny: {name!r}",
                        is_error=True,
                    )
                )
                render_cb(
                    ToolEvent(
                        kind="denied",
                        call_id=call_id,
                        tool_name=name,
                        reason="cached deny",
                    )
                )
                continue
            if verdict == "prompt":
                allowed = approve_cb(name, args)
                if allowed:
                    cache.approve(name)
                else:
                    cache.deny(name)
                    blocked += 1
                    results.append(
                        _tool_result_obj(
                            call_id,
                            f"user denied tool: {name!r}",
                            is_error=True,
                        )
                    )
                    render_cb(
                        ToolEvent(
                            kind="denied",
                            call_id=call_id,
                            tool_name=name,
                            reason="user denied",
                        )
                    )
                    continue

            # Allow path: dispatch via MCP if the name matches the
            # ``mcp__<server>__<tool>`` convention, otherwise via the
            # local chat-tool registry. We try MCP first because the
            # registry never registers names with that prefix, so this
            # is unambiguous.
            mcp_transport = mcp_routes.get(name)
            if mcp_transport is not None:
                output = ""
                is_error = False
                try:
                    from lyra_mcp.client.toolspec import (  # late-bound
                        parse_lyra_mcp_name,
                        render_mcp_result_for_chat,
                    )

                    parsed = parse_lyra_mcp_name(name)
                    if parsed is None:
                        raise ValueError(
                            f"could not parse MCP tool name {name!r}"
                        )
                    _, original = parsed
                    raw_result = mcp_transport.call_tool(
                        original, args, timeout=mcp_call_timeout_s
                    )
                    output = render_mcp_result_for_chat(raw_result)
                    is_error = bool(raw_result.get("isError"))
                except Exception as exc:
                    output = f"[mcp error] {type(exc).__name__}: {exc}"
                    is_error = True
                results.append(
                    _tool_result_obj(call_id, output, is_error=is_error)
                )
                render_cb(
                    ToolEvent(
                        kind="result",
                        call_id=call_id,
                        tool_name=name,
                        args=args,
                        output=output,
                        is_error=is_error,
                    )
                )
                continue

            from harness_core.messages import ToolCall  # late-bound

            wire_call = ToolCall(id=call_id, name=name, args=args)
            result = registry.execute(wire_call)
            output = result.content
            results.append(result)
            render_cb(
                ToolEvent(
                    kind="result",
                    call_id=call_id,
                    tool_name=name,
                    args=args,
                    output=output,
                    is_error=bool(result.is_error),
                )
            )

        transcript.append(Message.tool(results))

    # Loop budget exhausted — surface the last assistant text we have
    # and flag the report so the renderer can show "step budget
    # reached" once. Callers should *not* re-loop from here.
    render_cb(
        ToolEvent(
            kind="limit_reached",
            reason=f"reached max_steps={max_steps}",
        )
    )
    return ToolLoopReport(
        final_text=last_text or "[reached the tool-loop step budget]",
        tool_calls=tool_count,
        blocked_calls=blocked,
        steps=max_steps,
        hit_max_steps=True,
        transcript=transcript,
    )


def _tool_result_obj(call_id: str, content: str, *, is_error: bool) -> Any:
    """Build a :class:`harness_core.messages.ToolResult` dynamically.

    Late import keeps this module's import cost near-zero for code
    paths that never enter the loop (purely text turns, plain-mode
    sessions).
    """
    from harness_core.messages import ToolResult

    return ToolResult(call_id=call_id, content=content, is_error=is_error)


__all__ = [
    "ApproveFn",
    "RenderFn",
    "ToolEvent",
    "ToolLoopReport",
    "build_chat_tool_registry",
    "chat_tool_schemas",
    "collect_mcp_tool_specs",
    "run_chat_tool_loop",
]
