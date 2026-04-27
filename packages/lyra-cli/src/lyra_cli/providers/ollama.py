"""Ollama adapter — local LLMs via the Ollama daemon.

`Ollama <https://ollama.com>`_ is the most widely installed local
LLM runtime on developer machines in 2025: a single daemon on
``:11434`` that serves any GGUF model via an OpenAI-ish HTTP API.
This adapter lets Lyra talk to it with *zero* new Python
dependencies — we use ``urllib`` from the stdlib on purpose so
``pip install lyra`` stays lean for users who only want
Anthropic / Mock.

Why Ollama and not llama-cpp-python, MLX, or Candle?

* **Ubiquity.** If a dev has any local LLM at all in 2025, it's
  Ollama. The install is ``brew install ollama`` or the one-click
  Mac app; models pull with ``ollama pull``.
* **Zero install friction from our side.** No wheel, no native
  compile, no model-file management inside our repo.
* **Tool-call compatible.** Ollama's ``/api/chat`` endpoint has
  supported OpenAI-style ``tools`` since 0.3.x (mid-2024), so we can
  drive the same agentic loop the Anthropic path uses.
* **Cloud-free escape hatch.** Works fully offline once a model is
  pulled — important for air-gapped labs, CI runners without a key,
  and users who just want to try Lyra without giving a
  credit-card to anyone.

Default model: ``qwen2.5-coder:1.5b`` — ~1 GB, runs CPU-only on a
laptop at usable speed, Apache-2.0, tuned for code. Users can
override via ``OPEN_HARNESS_LOCAL_MODEL`` (CLI-specific) or the more
familiar ``OLLAMA_MODEL``.

Default host: ``http://127.0.0.1:11434``. Override via
``OLLAMA_HOST`` (matches Ollama's own convention).

Error handling
--------------

* :class:`OllamaConnectionError` — daemon isn't running / reachable.
  The factory catches this and falls back to Mock with a friendly
  message so the CLI still boots.
* HTTP 404 from Ollama means the model isn't pulled yet — the error
  message includes the ``ollama pull <model>`` hint.
* ``urllib.error.HTTPError`` / ``urllib.error.URLError`` bubble up
  as :class:`OllamaConnectionError` so callers only have one class
  to catch.

This module is intentionally small (one class + one reachability
probe + one factory helper). Heavier concerns (retry budgets, token
accounting, streaming) live in higher layers.
"""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Optional

from harness_core.messages import Message, StopReason, ToolCall
from harness_core.models import LLMProvider


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

OLLAMA_DEFAULT_HOST: str = "http://127.0.0.1:11434"
"""Default Ollama daemon URL. Matches Ollama's own default."""

OLLAMA_DEFAULT_MODEL: str = "qwen2.5-coder:1.5b"
"""Default model tag.

Chosen because it's (1) small enough to run on a CPU-only laptop
(~1 GB, 1.5 B params), (2) coding-specialised (Qwen2.5-Coder), and
(3) Apache-2.0 licensed so it's safe to recommend. Users can swap
via env vars without touching code.
"""

_OLLAMA_REACHABILITY_TIMEOUT_SEC: float = 0.8
"""Snappy timeout for the ``/api/tags`` probe.

The reachability check runs on *every* ``lyra`` invocation in
auto-mode, so we can't afford a 5-second hang when Ollama is off.
0.8 s is the sweet spot: long enough for a busy daemon to respond,
short enough to feel instant on a cold start.
"""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class OllamaConnectionError(RuntimeError):
    """Raised when the Ollama daemon isn't reachable / usable.

    This is a single catch-all surface so callers (mainly
    :mod:`lyra_cli.llm_factory`) can fall back to Mock with one
    ``except`` clause instead of enumerating every stdlib networking
    exception type.
    """


# ---------------------------------------------------------------------------
# Host resolution helpers
# ---------------------------------------------------------------------------


def _resolve_host() -> str:
    """Read ``OLLAMA_HOST`` with Ollama's own parsing quirks applied.

    Ollama accepts ``OLLAMA_HOST`` in three shapes — full URL
    (``http://host:port``), ``host:port``, or just ``host`` (in
    which case port defaults to 11434). We replicate that so users
    with an existing ``OLLAMA_HOST`` env get the same behaviour they
    already expect from the ``ollama`` CLI.
    """
    raw = os.environ.get("OLLAMA_HOST", "").strip()
    if not raw:
        return OLLAMA_DEFAULT_HOST
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw.rstrip("/")
    # ``host:port`` or bare ``host`` — assume http:// (Ollama does).
    return f"http://{raw.rstrip('/')}" if ":" in raw else f"http://{raw}:11434"


def _resolve_model(explicit: Optional[str]) -> str:
    """Pick a model tag.

    Order: explicit > ``OPEN_HARNESS_LOCAL_MODEL`` > ``OLLAMA_MODEL``
    > :data:`OLLAMA_DEFAULT_MODEL`. ``OPEN_HARNESS_LOCAL_MODEL`` wins
    because it's the CLI's namespaced override; ``OLLAMA_MODEL`` is
    still honoured to match community muscle-memory.
    """
    if explicit:
        return explicit
    env = os.environ.get("OPEN_HARNESS_LOCAL_MODEL", "").strip() or os.environ.get(
        "OLLAMA_MODEL", ""
    ).strip()
    return env or OLLAMA_DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Reachability probe
# ---------------------------------------------------------------------------


def ollama_reachable(host: Optional[str] = None, *, timeout: Optional[float] = None) -> bool:
    """Return True iff an Ollama daemon responds to ``/api/tags`` on *host*.

    Used by :func:`lyra_cli.llm_factory.build_llm` to decide
    whether the auto-cascade should pick Ollama. We hit ``/api/tags``
    specifically because it's cheap (no model load, just enumerates
    pulled models) and served even on a fresh daemon with zero
    models pulled.

    The timeout is deliberately short (see
    :data:`_OLLAMA_REACHABILITY_TIMEOUT_SEC`) — the reachability
    check runs on every auto-mode invocation and must not dominate
    startup latency. Any transport error is caught and returned as
    ``False``; callers get a boolean, not a stack trace.
    """
    url = (host or _resolve_host()) + "/api/tags"
    t = timeout if timeout is not None else _OLLAMA_REACHABILITY_TIMEOUT_SEC
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=t) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError):
        return False


def list_pulled_models(host: Optional[str] = None) -> list[str]:
    """Return the list of model tags currently pulled on the daemon.

    Returns an empty list (not an error) when the daemon is unreachable
    or the payload is unexpected — callers just need "what's available",
    not a full reachability audit.
    """
    url = (host or _resolve_host()) + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=_OLLAMA_REACHABILITY_TIMEOUT_SEC) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError, json.JSONDecodeError):
        return []
    models = data.get("models") or []
    tags: list[str] = []
    for m in models:
        tag = m.get("name") or m.get("model")
        if isinstance(tag, str):
            tags.append(tag)
    return tags


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class OllamaLLM(LLMProvider):
    """Local LLM provider backed by an Ollama daemon.

    Parameters
    ----------
    model:
        Ollama model tag (e.g. ``"qwen2.5-coder:1.5b"``,
        ``"llama3.2:3b"``). Defaults to :data:`OLLAMA_DEFAULT_MODEL`
        / env-var overrides — see :func:`_resolve_model`.
    host:
        Daemon URL. Defaults to :func:`_resolve_host` which honours
        ``OLLAMA_HOST``.
    timeout:
        Per-request HTTP timeout in seconds. Generation can legitimately
        take ~30 s on CPU for larger prompts, so we default to 120.

    The adapter is stateless — a single ``OllamaLLM()`` instance is
    safe to share across turns and threads; we allocate a fresh
    ``urllib`` request for every ``generate`` call.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        *,
        host: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = _resolve_model(model)
        self.host = (host or _resolve_host()).rstrip("/")
        self.timeout = timeout
        # v2.3.0: token-usage capture parity. Ollama reports
        # ``prompt_eval_count`` (tokens evaluated for the prompt) and
        # ``eval_count`` (tokens generated). For locally-served models
        # the dollar conversion is typically $0/token, but the meter
        # still uses these to track *throughput* so users can see e.g.
        # "23,000 tokens / session" even on free runs.
        self.last_usage: dict[str, int] = {}

    # ------------------------------------------------------------------
    # LLMProvider API
    # ------------------------------------------------------------------

    def generate(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._msg_to_ollama(m) for m in messages],
            # Streaming is the default for Ollama; we turn it off so the
            # agentic loop gets one coherent message per turn — same
            # ergonomic shape as the Anthropic path. Streaming will be
            # added as a separate code path when the REPL UI is ready
            # for chunk callbacks (TODO: phase-14 streaming).
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if tools:
            payload["tools"] = [self._tool_to_ollama(t) for t in tools]

        data = json.dumps(payload).encode("utf-8")
        url = self.host + "/api/chat"
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover — defensive
                pass
            # 404 from /api/chat almost always means the model tag isn't
            # pulled yet — give the user the exact command to fix it.
            if e.code == 404:
                raise OllamaConnectionError(
                    f"ollama: model '{self.model}' not pulled. "
                    f"Run `ollama pull {self.model}` and retry."
                ) from e
            raise OllamaConnectionError(
                f"ollama HTTP {e.code} from {url}: {body.strip() or e.reason}"
            ) from e
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            raise OllamaConnectionError(
                f"ollama unreachable at {self.host}: {e}. "
                f"Is the daemon running? (`ollama serve` or the Ollama app)"
            ) from e

        try:
            data_out = json.loads(raw)
        except json.JSONDecodeError as e:
            raise OllamaConnectionError(
                f"ollama returned non-JSON ({e}): {raw[:200]!r}"
            ) from e

        self._record_usage(data_out)
        return self._ollama_to_msg(data_out)

    def _record_usage(self, body: dict[str, Any]) -> None:
        """Capture Ollama's token counts onto ``last_usage``.

        Ollama reports tokens in two top-level fields rather than an
        OpenAI-style ``usage`` block:

        * ``prompt_eval_count`` — tokens evaluated for the prompt.
        * ``eval_count`` — tokens generated by the model.

        Older builds (pre-0.3.0) only emit one or the other; we
        tolerate that and silently no-op when neither is present.
        """
        if not isinstance(body, dict):
            self.last_usage = {}
            return
        try:
            prompt = int(body.get("prompt_eval_count") or 0)
            completion = int(body.get("eval_count") or 0)
        except (TypeError, ValueError):
            self.last_usage = {}
            return
        total = prompt + completion
        if total <= 0:
            self.last_usage = {}
            return
        self.last_usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    # ------------------------------------------------------------------
    # Message <-> Ollama wire format
    # ------------------------------------------------------------------

    @staticmethod
    def _msg_to_ollama(m: Message) -> dict[str, Any]:
        """Encode one :class:`Message` as an Ollama chat message.

        Ollama expects roles ``system`` / ``user`` / ``assistant`` /
        ``tool``. Tool messages use ``role="tool"`` with the result
        text in ``content`` and a ``tool_call_id`` linking back to the
        assistant's earlier call — we flatten our ``tool_results``
        list into one ``tool`` message per result for clean mapping.
        """
        if m.role == "tool":
            # Flatten: emit one dict; the chat API only reads a single
            # tool_call_id + content at a time. If there are multiple
            # results, just concatenate — callers rarely produce more
            # than one per turn and we'd only lose diagnostic detail.
            if not m.tool_results:
                return {"role": "tool", "content": ""}
            first = m.tool_results[0]
            combined = "\n\n".join(
                f"[{r.call_id}{' error' if r.is_error else ''}]\n{r.content}"
                for r in m.tool_results
            )
            return {
                "role": "tool",
                "content": combined,
                "tool_call_id": first.call_id,
            }

        out: dict[str, Any] = {"role": m.role, "content": m.content or ""}
        if m.role == "assistant" and m.tool_calls:
            out["tool_calls"] = [
                {
                    "id": c.id,
                    "function": {
                        "name": c.name,
                        # Ollama accepts either ``arguments`` as JSON
                        # string (OpenAI-style) or a dict; the dict
                        # shape is simpler and the docs confirm it.
                        "arguments": c.args or {},
                    },
                }
                for c in m.tool_calls
            ]
        return out

    @staticmethod
    def _tool_to_ollama(tool: dict[str, Any]) -> dict[str, Any]:
        """Translate one tool schema into Ollama / OpenAI shape.

        The rest of the Lyra stack uses Anthropic-style tool
        schemas: ``{"name", "description", "input_schema"}``. Ollama
        (like OpenAI) expects ``{"type": "function", "function":
        {"name", "description", "parameters"}}``. We do the conversion
        here so the caller's schema dicts can stay unchanged and all
        providers plug in as drop-ins.

        Pass-through is the fallback for callers already building the
        OpenAI shape — we detect it and leave it alone.
        """
        if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
            return tool
        return {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema") or tool.get("parameters") or {
                    "type": "object",
                    "properties": {},
                },
            },
        }

    @staticmethod
    def _ollama_to_msg(resp: dict[str, Any]) -> Message:
        """Decode one ``/api/chat`` response into our :class:`Message`.

        Ollama's response shape is::

            {
              "model": "...",
              "message": {"role": "assistant", "content": "...",
                          "tool_calls": [{"function": {"name": "...",
                                                       "arguments": {...}}}]},
              "done_reason": "stop" | "length" | "tool_calls",
              ...
            }

        The ``done_reason`` field was added in Ollama 0.3.x; older
        daemons only emit ``done: true`` without a reason. We treat
        an absent reason as :data:`StopReason.END_TURN`.
        """
        msg = resp.get("message") or {}
        text = msg.get("content", "") or ""
        raw_calls = msg.get("tool_calls") or []

        tool_calls: list[ToolCall] = []
        for i, c in enumerate(raw_calls):
            fn = c.get("function") or {}
            name = fn.get("name") or c.get("name") or ""
            args = fn.get("arguments") or c.get("arguments") or {}
            # Some Ollama builds serialise arguments as a JSON string
            # (OpenAI's legacy wire format). Accept both.
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args else {}
                except json.JSONDecodeError:
                    args = {"_raw": args}
            tool_calls.append(
                ToolCall(
                    id=str(c.get("id") or f"call_{i}"),
                    name=name,
                    args=args if isinstance(args, dict) else {"value": args},
                )
            )

        stop_raw = resp.get("done_reason") or ("tool_use" if tool_calls else "end_turn")
        stop_map = {
            "stop": StopReason.END_TURN,
            "end_turn": StopReason.END_TURN,
            "length": StopReason.MAX_TOKENS,
            "tool_calls": StopReason.TOOL_USE,
            "tool_use": StopReason.TOOL_USE,
        }
        stop = stop_map.get(stop_raw, StopReason.END_TURN)
        return Message.assistant(
            content=text,
            tool_calls=tool_calls,
            stop_reason=stop,
        )


__all__ = [
    "OLLAMA_DEFAULT_HOST",
    "OLLAMA_DEFAULT_MODEL",
    "OllamaConnectionError",
    "OllamaLLM",
    "list_pulled_models",
    "ollama_reachable",
]
