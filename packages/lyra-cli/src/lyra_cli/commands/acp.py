"""``lyra acp`` — host Lyra as an Agent Client Protocol subprocess.

The Agent Client Protocol (ACP) is the same JSON-RPC 2.0 stdio surface
opencode and Zed's agent ecosystem speak. Editors and IDEs spawn
``lyra acp``, send line-delimited JSON over stdin, and receive
responses on stdout — the agent itself stays alive for the editor's
lifetime.

This subcommand wires the protocol's three core methods to live Lyra
state:

* ``initialize`` — returns the version, capabilities, and the
  packages installed in the host's Python environment so the
  client can verify the bridge before sending real turns.
* ``sendUserMessage`` — runs one chat turn through the same
  :func:`session._chat_with_llm` path the REPL uses, applying the
  caller's chosen ``model`` (default ``auto``). The response includes
  the assistant's text, the per-turn token usage, and the cost in
  USD so the editor can render its own status badge.
* ``cancel`` — best-effort cancellation hook (no-op until the
  underlying ``LLMProvider`` exposes a real cancellation surface).

Reference: https://agentclientprotocol.com
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer

acp_app = typer.Typer(
    name="acp",
    help=(
        "Host Lyra as an ACP (Agent Client Protocol) subprocess. "
        "Reads JSON-RPC 2.0 requests from stdin and writes responses "
        "to stdout."
    ),
)


@acp_app.callback(invoke_without_command=True)
def acp_serve(
    ctx: typer.Context,
    repo_root: Path = typer.Option(
        Path.cwd,
        "--repo-root",
        "-C",
        help="Repository root the agent should treat as cwd (default: current dir).",
    ),
    model: str = typer.Option(
        "auto",
        "--model",
        "--llm",
        help=(
            "LLM to bind to. ``auto`` (default) picks the first "
            "configured backend in the cascade. Pass an explicit name "
            "(``deepseek``, ``anthropic``, ``openai``, ``gemini``, "
            "``ollama``, ``mock`` …) to pin one."
        ),
    ),
    mode: str = typer.Option(
        "agent",
        "--mode",
        help="Initial mode (agent | plan | debug | ask).",
    ),
    once: bool = typer.Option(
        False,
        "--once",
        help=(
            "Process exactly one request from stdin and exit. Useful "
            "for tests and CI smoke checks; the default is to stream."
        ),
    ),
) -> None:
    """Run the ACP stdio bridge — sub-callable so ``lyra acp`` Just Works."""
    if ctx.invoked_subcommand is not None:
        return

    from lyra_core.acp import AcpServer

    from .. import __version__
    from ..interactive.session import (
        InteractiveSession,
        _chat_with_llm,
        _ensure_lifecycle_bus,
    )

    session = InteractiveSession(repo_root=repo_root.resolve(), model=model, mode=mode)
    # Make sure the lifecycle bus is materialised so plugins, tests,
    # and the editor's status badge can subscribe symmetrically with
    # the REPL path.
    _ensure_lifecycle_bus(session)

    server = AcpServer()
    server.register("initialize", lambda params: _handle_initialize(params, version=__version__))
    server.register(
        "sendUserMessage",
        lambda params: _handle_send_user_message(session, params),
    )
    server.register("cancel", lambda _params: {"ok": True})

    if once:
        line = sys.stdin.readline()
        if not line.strip():
            raise typer.Exit(0)
        out = server.handle_request(line)
        if out is not None:
            sys.stdout.write(out + "\n")
            sys.stdout.flush()
        raise typer.Exit(0)

    for response in server.serve(sys.stdin):
        sys.stdout.write(response + "\n")
        sys.stdout.flush()


def _handle_initialize(params: dict[str, Any], *, version: str) -> dict[str, Any]:
    """Implement ``initialize`` — handshake with the ACP client.

    Returns version + capability bits the client uses to decide which
    methods are safe to call. ``params`` is unused for now but kept in
    the signature so future protocol-version negotiation lands here.
    """
    _ = params
    return {
        "agent": {"name": "lyra", "version": version},
        "protocol": {"name": "acp", "version": "1.0"},
        "capabilities": {
            "sendUserMessage": True,
            "cancel": False,
            "streaming": False,
            "tools": True,
        },
    }


def _handle_send_user_message(session: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Implement ``sendUserMessage`` — single chat turn through Lyra.

    Expected ``params`` shape (extensions are ignored for now)::

        {
            "text": "<user message>",
            "system": "<optional system prompt>"
        }
    """
    from lyra_core.acp import AcpError
    from ..interactive.session import _chat_with_llm

    text = (params.get("text") or "").strip()
    if not text:
        raise AcpError(-32602, "missing required field: text")
    system = params.get("system") or "You are Lyra, a CLI-native coding agent."

    pre_cost = session.cost_usd
    pre_tokens = session.tokens_used

    ok, reply = _chat_with_llm(session, text, system_prompt=system)

    if not ok:
        raise AcpError(-32000, reply or "agent turn failed")

    return {
        "text": reply,
        "model": session.model,
        "usage": {
            "tokens": max(0, session.tokens_used - pre_tokens),
            "cost_usd": round(max(0.0, session.cost_usd - pre_cost), 6),
        },
    }


__all__ = ["acp_app", "acp_serve"]
