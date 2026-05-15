"""OpenAI-compatible chat-completions providers.

Roughly every "serious" LLM backend in 2026 exposes the OpenAI
``/v1/chat/completions`` wire format — OpenAI itself, DeepSeek,
Groq, xAI (Grok), Cerebras, Mistral, OpenRouter, LM Studio, vLLM,
and llama.cpp's ``server`` mode all speak it. Rather than write ten
near-identical adapters we build **one** generic class
(:class:`OpenAICompatibleLLM`) and ten thin presets that just
configure host, default model, API-key env var, and any
provider-specific extra headers.

Why this matters
----------------

Users set ``OPENAI_API_KEY`` / ``DEEPSEEK_API_KEY`` / ``GROQ_API_KEY``
/ etc. in their shell and Lyra just works with zero extra
configuration. The :mod:`lyra_cli.llm_factory` cascade tries
each in priority order and picks the first one available, so a dev
with (say) a free Groq key and no Anthropic budget still gets to run
the agent loop with a real model.

No new Python deps
------------------

Like the Ollama adapter, this module is **stdlib-only** (``urllib``
+ ``json``). Shipping ``openai`` or ``httpx`` as hard deps would
double the CLI install footprint for no technical gain — the chat
endpoint is just HTTP POST with a JSON body.

Tool-call translation
---------------------

The rest of Lyra speaks *Anthropic-style* tool schemas
(``{"name", "description", "input_schema"}``) because that's what
``harness_core`` standardised on. OpenAI's shape is
``{"type": "function", "function": {"name", "description",
"parameters"}}``. We translate on the way out and on the way back
so the rest of the stack stays blissfully unaware that it's
talking to something other than Claude.

Reasoning-model output
----------------------

OpenAI's ``o3`` / ``o4-mini`` and DeepSeek ``R1`` return a separate
``reasoning_content`` field for their hidden chain-of-thought. We
**drop it** at the adapter boundary — leaking model-internal
reasoning into transcripts causes prompt-injection surprises and
bloats logs. If a future feature wants the reasoning text, the
hook goes in :meth:`OpenAICompatibleLLM._choice_to_msg`.
"""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator, Optional

from harness_core.messages import Message, StopReason, ToolCall
from harness_core.models import LLMProvider


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ProviderHTTPError(RuntimeError):
    """Any non-2xx / transport failure from an OpenAI-compatible endpoint.

    Single error type so the factory can fall back with one
    ``except`` clause instead of enumerating ``URLError`` /
    ``HTTPError`` / ``socket.timeout`` / ``OSError``.
    """


class ProviderNotConfigured(RuntimeError):
    """Raised when a caller asks for a provider whose API key is missing.

    Kept separate from :class:`ProviderHTTPError` because "not
    configured" is a caller-fixable setup issue, while HTTP errors
    are transient / deployment problems. The factory uses
    :class:`ProviderNotConfigured` to decide whether to *silently
    skip* in auto-mode or *fail loud* on explicit ``--llm <name>``.
    """


# ---------------------------------------------------------------------------
# Core provider
# ---------------------------------------------------------------------------


@dataclass
class _ReasoningConfig:
    """Per-model reasoning knobs for ``o-series`` style endpoints.

    OpenAI ``o3`` / ``o4-mini`` (and their peers at Groq / DeepSeek)
    accept a ``reasoning_effort`` parameter and reject the legacy
    ``max_tokens`` field in favour of ``max_completion_tokens``. We
    express this as a tiny config object rather than hard-coding it
    in the generate path so presets can opt in by flipping one flag.
    """

    use_max_completion_tokens: bool = False
    supports_reasoning_effort: bool = False
    default_reasoning_effort: Optional[str] = None  # "low" | "medium" | "high"


@dataclass(frozen=True)
class ProviderRouting:
    """OpenRouter provider-routing knobs marshalled into ``extra_body.provider``.

    OpenRouter exposes a ``provider`` field in the request body that
    lets callers control which upstream provider receives the request.
    Without this, the OpenRouter UI is the only place to pin a route
    (price-cheapest, throughput-fastest, only-Anthropic, etc.). We
    surface every documented field and leave them ``None`` by default
    so unconfigured callers keep OpenRouter's default behaviour
    (smart-pick by price + uptime).

    Empty / ``None`` fields are dropped at serialisation time so the
    wire payload stays minimal.
    """

    sort: Optional[str] = None                 # "price" | "throughput" | "latency"
    only: tuple[str, ...] = ()                  # whitelist of upstream provider names
    ignore: tuple[str, ...] = ()                # blacklist
    order: tuple[str, ...] = ()                 # priority order to try
    require_parameters: Optional[bool] = None   # reject providers that drop unknown params
    data_collection: Optional[str] = None       # "allow" | "deny"

    def to_payload(self) -> dict[str, Any]:
        """Return the ``provider`` sub-object for ``extra_body``.

        Empty fields are stripped so a default-constructed instance
        produces ``{}`` and callers can unconditionally call
        ``to_payload()`` without polluting the request body.
        """
        out: dict[str, Any] = {}
        if self.sort:
            out["sort"] = self.sort
        if self.only:
            out["only"] = list(self.only)
        if self.ignore:
            out["ignore"] = list(self.ignore)
        if self.order:
            out["order"] = list(self.order)
        if self.require_parameters is not None:
            out["require_parameters"] = self.require_parameters
        if self.data_collection:
            out["data_collection"] = self.data_collection
        return out


class OpenAICompatibleLLM(LLMProvider):
    """Generic OpenAI-wire-format chat-completions adapter.

    Parameters
    ----------
    api_key:
        Bearer token sent in ``Authorization: Bearer …``. Most
        presets read this from an env var at construction time.
    base_url:
        Endpoint root *without* the trailing ``/chat/completions``.
        E.g. ``https://api.openai.com/v1``.
    model:
        Model slug (``gpt-5``, ``deepseek-chat``, ``kimi-k2-0711``).
    provider_name:
        Short label for error messages and ``describe_selection``.
    extra_headers:
        Additional headers — OpenRouter in particular wants
        ``HTTP-Referer`` / ``X-Title`` for attribution, and some
        Azure deployments want ``api-key`` instead of ``Authorization``.
    auth_scheme:
        ``"bearer"`` (default) puts the key in
        ``Authorization: Bearer …``. ``"api-key"`` puts it in the
        ``api-key`` header (Azure-OpenAI style). ``"none"`` skips the
        auth header entirely (local LM Studio / llama-server, which
        don't need a key).
    timeout:
        Per-request seconds. Default 120 s because reasoning models
        can legitimately sit for a minute+ before first token.
    reasoning:
        See :class:`_ReasoningConfig`.
    api_path:
        Path segment appended to ``base_url``. Defaults to
        ``/chat/completions`` which is where every OpenAI-compatible
        endpoint lives.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str],
        base_url: str,
        model: str,
        provider_name: str,
        extra_headers: Optional[dict[str, str]] = None,
        auth_scheme: str = "bearer",
        timeout: float = 120.0,
        reasoning: Optional[_ReasoningConfig] = None,
        provider_routing: Optional[ProviderRouting] = None,
        _urlopen: Optional[Callable[..., Any]] = None,
        api_path: str = "/chat/completions",
    ) -> None:
        self.api_key = api_key or None
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.provider_name = provider_name
        self.extra_headers = dict(extra_headers or {})
        self.auth_scheme = auth_scheme
        self.timeout = timeout
        self.reasoning = reasoning or _ReasoningConfig()
        self.api_path = api_path if api_path.startswith("/") else "/" + api_path

        self.provider_routing = provider_routing
        # Test seam: callers may inject a fake urlopen to capture the
        # outgoing request without network. When unset, :meth:`generate`
        # calls ``urllib.request.urlopen`` at request time (not cached
        # on the instance) so unit tests can ``patch`` it after
        # construction, matching pre-hook behaviour.
        self._urlopen = _urlopen

        # Token-usage capture (v2.1.3+): each ``generate`` call
        # records the response's ``usage`` block on ``last_usage`` and
        # accumulates totals on ``cumulative_usage`` so the run
        # footer can show "7 in / 4 out · 1.5s" — proof of life that
        # the API actually answered, since mocks never return token
        # counts. Initialised to empty / zero so callers can read
        # safely before the first turn without ``AttributeError``.
        self.last_usage: dict[str, int] = {}
        self.cumulative_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        if auth_scheme != "none" and not self.api_key:
            raise ProviderNotConfigured(
                f"{provider_name}: no API key configured. "
                f"Set the provider's API-key env var and retry."
            )

    def _record_usage(self, usage: Optional[dict[str, Any]]) -> None:
        """Capture per-call usage on ``last_usage`` and add it to ``cumulative_usage``.

        Tolerates partial / missing blocks: providers that omit
        ``usage`` entirely (some local servers, some older Groq
        builds) leave ``last_usage`` empty and don't bump cumulative
        counters. Providers that report only ``total_tokens`` (no
        in/out split) are accepted as-is.
        """
        if not usage:
            self.last_usage = {}
            return
        self.last_usage = dict(usage)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            self.cumulative_usage[key] = (
                self.cumulative_usage.get(key, 0) + int(usage.get(key, 0) or 0)
            )

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
            "messages": [self._msg_to_openai(m) for m in messages],
        }

        # Token limit: reasoning models reject ``max_tokens`` and need
        # ``max_completion_tokens``; classical chat models use the old
        # name. This is the *one* quirk that forced us to split the
        # config rather than pass a single dict.
        if self.reasoning.use_max_completion_tokens:
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens

        # Temperature: reasoning models *ignore* temperature (they
        # always sample with effort=high/medium/low), so we simply
        # omit it when the preset is flagged.
        if not self.reasoning.supports_reasoning_effort:
            payload["temperature"] = temperature
        elif self.reasoning.default_reasoning_effort:
            payload["reasoning_effort"] = self.reasoning.default_reasoning_effort

        if tools:
            payload["tools"] = [self._tool_to_openai(t) for t in tools]

        if self.provider_routing is not None:
            provider_payload = self.provider_routing.to_payload()
            if provider_payload:
                extra_body = payload.setdefault("extra_body", {})
                extra_body["provider"] = provider_payload

        data = json.dumps(payload).encode("utf-8")
        url = self.base_url + self.api_path

        headers = {"Content-Type": "application/json"}
        headers.update(self.extra_headers)
        if self.auth_scheme == "bearer" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.auth_scheme == "api-key" and self.api_key:
            headers["api-key"] = self.api_key

        req = urllib.request.Request(
            url, data=data, method="POST", headers=headers
        )
        opener = self._urlopen if self._urlopen is not None else urllib.request.urlopen
        try:
            with opener(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover — defensive
                pass
            raise ProviderHTTPError(
                f"{self.provider_name} HTTP {e.code}: "
                f"{body.strip()[:500] or e.reason}"
            ) from e
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            raise ProviderHTTPError(
                f"{self.provider_name} unreachable at {self.base_url}: {e}"
            ) from e

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ProviderHTTPError(
                f"{self.provider_name} returned non-JSON: {raw[:200]!r}"
            ) from e

        choices = parsed.get("choices") or []
        if not choices:
            err_msg = (
                (parsed.get("error") or {}).get("message")
                or parsed.get("message")
                or "empty response"
            )
            raise ProviderHTTPError(f"{self.provider_name}: {err_msg}")

        # Capture token usage for proof-of-life display in the run
        # footer. Done *before* returning so a caller iterating
        # generate() sees accumulated totals immediately.
        self._record_usage(parsed.get("usage"))

        return self._choice_to_msg(choices[0])

    # ------------------------------------------------------------------
    # Streaming (v2.2.4)
    # ------------------------------------------------------------------
    #
    # ``stream`` is the streaming peer of :meth:`generate`. It posts to
    # the same ``/chat/completions`` endpoint with ``stream=true`` plus
    # ``stream_options.include_usage=true`` (OpenAI's opt-in for usage
    # telemetry on streamed responses; DeepSeek, Groq, Cerebras,
    # Mistral, OpenRouter and xAI all honour it). Yields per-chunk
    # text deltas as :class:`str`; the final ``usage`` block is parked
    # on :attr:`last_usage` so callers can immediately bill the turn
    # via :func:`lyra_cli.interactive.session._bill_turn`.
    #
    # Keep this minimal: we yield *text only*. Tool-call streaming is
    # a different shape (incremental JSON arguments) and Lyra's chat
    # mode doesn't take tools yet. ``lyra run --plan`` still drives
    # tool loops through :meth:`generate`, which is the deliberate
    # spend-tokens-AND-touch-the-repo surface.
    #
    # Mid-stream errors fall through to the caller as
    # :class:`ProviderHTTPError`; the chat handler catches that and
    # surfaces a friendly error renderable while keeping whatever
    # text has already streamed onto the screen.

    def stream(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        """Yield text deltas from a streaming chat completion.

        Mirrors the parameter contract of :meth:`generate`. After the
        iterator is fully consumed, :attr:`last_usage` and
        :attr:`cumulative_usage` are updated from the final
        ``usage`` event.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._msg_to_openai(m) for m in messages],
            "stream": True,
            # Most major providers honour this; harmless to send to
            # those that don't (they simply omit the usage chunk).
            "stream_options": {"include_usage": True},
        }

        if self.reasoning.use_max_completion_tokens:
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens

        if not self.reasoning.supports_reasoning_effort:
            payload["temperature"] = temperature
        elif self.reasoning.default_reasoning_effort:
            payload["reasoning_effort"] = self.reasoning.default_reasoning_effort

        if tools:
            payload["tools"] = [self._tool_to_openai(t) for t in tools]

        if self.provider_routing is not None:
            provider_payload = self.provider_routing.to_payload()
            if provider_payload:
                extra_body = payload.setdefault("extra_body", {})
                extra_body["provider"] = provider_payload

        data = json.dumps(payload).encode("utf-8")
        url = self.base_url + self.api_path

        headers = {
            "Content-Type": "application/json",
            # Per the OpenAI streaming docs — some CDNs collapse the
            # response if Accept doesn't explicitly opt into SSE.
            "Accept": "text/event-stream",
        }
        headers.update(self.extra_headers)
        if self.auth_scheme == "bearer" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.auth_scheme == "api-key" and self.api_key:
            headers["api-key"] = self.api_key

        req = urllib.request.Request(
            url, data=data, method="POST", headers=headers
        )
        opener = self._urlopen if self._urlopen is not None else urllib.request.urlopen

        try:
            resp = opener(req, timeout=self.timeout)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover — defensive
                pass
            raise ProviderHTTPError(
                f"{self.provider_name} HTTP {e.code}: "
                f"{body.strip()[:500] or e.reason}"
            ) from e
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            raise ProviderHTTPError(
                f"{self.provider_name} unreachable at {self.base_url}: {e}"
            ) from e

        # Reset before consuming so a caller that re-runs the stream
        # sees a clean ``last_usage`` until the new final-chunk lands.
        self.last_usage = {}

        # Track streamed text and prompt size for a usage *backstop*
        # when the provider's SSE feed never emits a final ``usage``
        # event. Some self-hosted gateways (older vLLM, custom proxy
        # builds, the LM Studio "/v1" surface in some versions) honour
        # ``stream_options.include_usage`` only on the final
        # ``[DONE]`` boundary in newer builds and silently drop it in
        # older ones. Without this backstop those calls would bill
        # $0 (because ``last_usage`` stayed empty), making the spend
        # meter lie. The estimator is intentionally conservative —
        # we'd rather slightly under-report than fabricate large
        # numbers — and uses a 4-chars-per-token heuristic that tracks
        # OpenAI's tiktoken to ±15% on natural-language English. Tool
        # JSON, code, and CJK text are tokenised denser, so this
        # under-counts those — acceptable for a fallback that's only
        # active when the provider is misbehaving.
        streamed_chars = 0
        prompt_chars = sum(
            len(m.content or "")
            + sum(len(str(arg)) for c in (m.tool_calls or []) for arg in (c.args or {}).values())
            for m in messages
        )

        try:
            for raw_line in self._iter_sse_data_lines(resp):
                if raw_line == "[DONE]":
                    break
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    # Provider sent a malformed chunk; skip rather
                    # than aborting the whole stream — the user can
                    # always /retry.
                    continue

                # Final usage chunk arrives with an empty ``choices``
                # list and a populated ``usage`` block. We capture it
                # here so the chat handler's _bill_turn() reads it
                # back the moment the iterator finishes.
                usage = event.get("usage")
                if usage:
                    self._record_usage(usage)

                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0] or {}).get("delta") or {}
                text = delta.get("content")
                if text:
                    streamed_chars += len(text)
                    yield text
        finally:
            try:
                resp.close()
            except Exception:
                pass

        # Backstop: provider never emitted a ``usage`` event, but we
        # *did* receive content. Estimate so the meter at least moves
        # off $0. Skip when nothing streamed (caller saw an empty
        # response anyway and will surface that as an error).
        if not self.last_usage and streamed_chars > 0:
            est_prompt = max(1, prompt_chars // 4)
            est_completion = max(1, streamed_chars // 4)
            self._record_usage(
                {
                    "prompt_tokens": est_prompt,
                    "completion_tokens": est_completion,
                    "total_tokens": est_prompt + est_completion,
                    # Marker so observability tooling can label these
                    # as estimates if it wants to ("est." chip in the
                    # status bar). The cost calculator ignores unknown
                    # keys, so this is purely informational.
                    "estimated": True,
                }
            )

    @staticmethod
    def _iter_sse_data_lines(resp: Any) -> Iterator[str]:
        """Yield ``data:`` payloads from an SSE response, line by line.

        SSE frames are delimited by blank lines and the payload lives
        on a ``data: <json>`` line. We're tolerant of CRLF / LF, of
        ``data:<json>`` without the space, and of multi-line ``data:``
        continuations (RFC-correct: concatenate with newlines).

        Operates on the raw ``urlopen`` response object (which exposes
        ``readline``) rather than buffering the whole body — that
        defeats the point of streaming.
        """
        pending: list[str] = []
        while True:
            try:
                raw = resp.readline()
            except Exception:
                break
            if not raw:
                break
            if isinstance(raw, bytes):
                line = raw.decode("utf-8", errors="replace")
            else:
                line = raw
            line = line.rstrip("\r\n")

            if not line:
                if pending:
                    yield "\n".join(pending)
                    pending = []
                continue

            if line.startswith(":"):
                # SSE comment / heartbeat (e.g. OpenRouter keepalive).
                continue

            if line.startswith("data:"):
                pending.append(line[5:].lstrip())
            # Other SSE field types (event:, id:, retry:) are
            # ignored — we only care about ``data``.

        if pending:
            yield "\n".join(pending)

    # ------------------------------------------------------------------
    # Message <-> OpenAI wire format
    # ------------------------------------------------------------------

    @staticmethod
    def _msg_to_openai(m: Message) -> dict[str, Any]:
        """Map a single :class:`Message` to an OpenAI chat-message dict."""
        if m.role == "tool":
            if not m.tool_results:
                return {"role": "tool", "content": "", "tool_call_id": ""}
            # OpenAI wants one message per tool_call_id. Callers may
            # produce multiple results in a single tool-message; we
            # emit the *first* result's id (matching the behaviour of
            # the Ollama adapter) and concatenate all contents. A
            # future refactor could return a list here, but the chat
            # wire format only accepts a flat message sequence, so
            # emitting multiple dicts would need a calling-convention
            # change upstream.
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
                    "type": "function",
                    "function": {
                        "name": c.name,
                        # OpenAI *requires* arguments as a JSON-encoded
                        # string on the wire, even though its own SDK
                        # surfaces it as a dict. Serialise here so the
                        # adapter works against literally the published
                        # API reference.
                        "arguments": json.dumps(c.args or {}),
                    },
                }
                for c in m.tool_calls
            ]
        return out

    @staticmethod
    def _tool_to_openai(tool: dict[str, Any]) -> dict[str, Any]:
        """Anthropic-style tool schema → OpenAI function-tool schema.

        Pass-through if the caller already built the OpenAI shape —
        lets advanced callers bypass translation.
        """
        if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
            return tool
        return {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema")
                or tool.get("parameters")
                or {"type": "object", "properties": {}},
            },
        }

    @staticmethod
    def _choice_to_msg(choice: dict[str, Any]) -> Message:
        """Decode one ``choices[i]`` entry into a :class:`Message`."""
        msg = choice.get("message") or {}
        text = msg.get("content")
        # Reasoning models may emit ``content: null`` with the real
        # reply only present as ``reasoning_content`` / ``reasoning``.
        # We deliberately do **not** surface the reasoning text as the
        # assistant message — see the module docstring for why.
        if text is None:
            text = ""

        raw_calls = msg.get("tool_calls") or []
        tool_calls: list[ToolCall] = []
        for i, c in enumerate(raw_calls):
            fn = c.get("function") or {}
            name = fn.get("name") or c.get("name") or ""
            args: Any = fn.get("arguments")
            if args is None:
                args = c.get("arguments") or {}
            if isinstance(args, str):
                # OpenAI serialises arguments as a JSON string; some
                # providers already deserialise it (Groq, DeepSeek).
                # Accept both.
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

        finish_raw = choice.get("finish_reason") or (
            "tool_calls" if tool_calls else "stop"
        )
        stop_map = {
            "stop": StopReason.END_TURN,
            "end_turn": StopReason.END_TURN,
            "length": StopReason.MAX_TOKENS,
            "max_tokens": StopReason.MAX_TOKENS,
            "tool_calls": StopReason.TOOL_USE,
            "tool_use": StopReason.TOOL_USE,
            "function_call": StopReason.TOOL_USE,
            "content_filter": StopReason.ERROR,
        }
        stop = stop_map.get(finish_raw, StopReason.END_TURN)
        return Message.assistant(
            content=text or "",
            tool_calls=tool_calls,
            stop_reason=stop,
        )


# ---------------------------------------------------------------------------
# Preset registry
# ---------------------------------------------------------------------------
#
# Each preset is a factory that constructs an ``OpenAICompatibleLLM``
# with the right host / default model / env var wired up. Splitting
# this into a registry of dataclasses means the factory's auto-cascade
# can iterate over a single list instead of enumerating a dozen
# ``if`` branches, *and* we can reuse the same metadata for the
# ``--llm`` flag's help text.


@dataclass(frozen=True)
class _Preset:
    """Static metadata + factory for one OpenAI-compatible preset."""

    name: str                       # slug used by --llm <name>
    label: str                      # human label for describe_selection
    base_url: str
    env_keys: tuple[str, ...]       # env vars to check, first non-empty wins
    default_model: str
    model_env_keys: tuple[str, ...] = ()   # optional model overrides
    extra_headers: tuple[tuple[str, str], ...] = ()   # frozen items
    auth_scheme: str = "bearer"
    reasoning: Optional[_ReasoningConfig] = None
    # If True, the factory *also* tries this preset when no env var is
    # set — useful for local servers that don't need a key.
    probe_reachable: bool = False
    reachable_path: str = "/models"   # used only when probe_reachable

    def read_api_key(self) -> Optional[str]:
        for k in self.env_keys:
            v = os.environ.get(k, "").strip()
            if v:
                return v
        return None

    def read_model(self, explicit: Optional[str] = None) -> str:
        if explicit:
            return explicit
        for k in self.model_env_keys:
            v = os.environ.get(k, "").strip()
            if v:
                return v
        return self.default_model

    def build(
        self,
        model: Optional[str] = None,
        *,
        provider_routing: "Optional[ProviderRouting]" = None,
    ) -> OpenAICompatibleLLM:
        api_key = self.read_api_key()
        if not api_key and self.auth_scheme != "none":
            raise ProviderNotConfigured(
                f"{self.name}: missing API key. "
                f"Set one of {', '.join(self.env_keys)} in your shell."
            )
        return OpenAICompatibleLLM(
            api_key=api_key,
            base_url=self.base_url,
            model=self.read_model(model),
            provider_name=self.name,
            extra_headers=dict(self.extra_headers),
            auth_scheme=self.auth_scheme,
            reasoning=self.reasoning,
            provider_routing=provider_routing,
        )

    def configured(self) -> bool:
        """True if this preset can be activated without further setup.

        * Cloud presets → True iff *any* of ``env_keys`` is set.
        * Local presets → True iff ``probe_reachable`` is True *and*
          the endpoint responds to GET ``<base_url><reachable_path>``.
        """
        if self.auth_scheme == "none" and self.probe_reachable:
            return _endpoint_reachable(self.base_url + self.reachable_path)
        return self.read_api_key() is not None


def _endpoint_reachable(url: str, timeout: float = 0.8) -> bool:
    """Cheap GET probe for local OpenAI-compatible servers.

    Used by LM Studio and llama.cpp's ``server`` mode which both
    expose ``/v1/models`` on ``127.0.0.1:<port>`` by default. Same
    short timeout as the Ollama probe so auto-mode startup stays
    snappy even when every local port is closed.
    """
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500   # even 401/404 means *something* listened
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError):
        return False


# ---------------------------------------------------------------------------
# The actual presets
# ---------------------------------------------------------------------------
#
# Ordering here is the *default* auto-cascade order (first match wins).
# When you add a new preset, think hard about where it fits: "best
# capability with the user's keys" goes first, "cheapest decent
# coder" next, local fallbacks last.


PRESETS: tuple[_Preset, ...] = (
    _Preset(
        name="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        env_keys=("OPENAI_API_KEY",),
        model_env_keys=("OPEN_HARNESS_OPENAI_MODEL", "OPENAI_MODEL"),
        # gpt-4o is universally available across OpenAI account tiers;
        # gpt-5 is the flagship but not all keys can call it (returns
        # HTTP 404 from the API). Users who have gpt-5 access can opt
        # in via OPENAI_MODEL=gpt-5 or `/model openai:gpt-5`.
        default_model="gpt-4o",
    ),
    _Preset(
        name="openai-reasoning",
        label="OpenAI · reasoning",
        base_url="https://api.openai.com/v1",
        env_keys=("OPENAI_API_KEY",),
        model_env_keys=("OPEN_HARNESS_OPENAI_REASONING_MODEL",),
        default_model="o3-mini",
        reasoning=_ReasoningConfig(
            use_max_completion_tokens=True,
            supports_reasoning_effort=True,
            default_reasoning_effort="medium",
        ),
    ),
    _Preset(
        name="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        env_keys=("DEEPSEEK_API_KEY",),
        model_env_keys=("OPEN_HARNESS_DEEPSEEK_MODEL", "DEEPSEEK_MODEL"),
        # deepseek-chat is the general model; deepseek-coder /
        # deepseek-reasoner are siblings. V3 is served under
        # ``deepseek-chat`` by default (per DeepSeek's own docs).
        default_model="deepseek-chat",
    ),
    _Preset(
        name="xai",
        label="xAI · Grok",
        base_url="https://api.x.ai/v1",
        env_keys=("XAI_API_KEY", "GROK_API_KEY"),
        model_env_keys=("OPEN_HARNESS_XAI_MODEL", "XAI_MODEL"),
        # Grok-4 is the current flagship; ``grok-code-fast-1`` is the
        # coding-tuned sibling. Users point at whichever via env var.
        default_model="grok-4",
    ),
    _Preset(
        name="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        env_keys=("GROQ_API_KEY",),
        model_env_keys=("OPEN_HARNESS_GROQ_MODEL", "GROQ_MODEL"),
        # Groq hosts many models; their current recommended "best for
        # agents" is Kimi-K2 (Moonshot 1T MoE). Llama-3.3-70B is the
        # classic fallback and we expose it as the default because
        # it's universally available on the free tier.
        default_model="llama-3.3-70b-versatile",
    ),
    _Preset(
        name="cerebras",
        label="Cerebras",
        base_url="https://api.cerebras.ai/v1",
        env_keys=("CEREBRAS_API_KEY",),
        model_env_keys=("OPEN_HARNESS_CEREBRAS_MODEL", "CEREBRAS_MODEL"),
        # Cerebras is the fastest inference provider (~2000 t/s on
        # Llama 3.3 70B). They also host Qwen-3-Coder.
        default_model="llama-3.3-70b",
    ),
    _Preset(
        name="mistral",
        label="Mistral",
        base_url="https://api.mistral.ai/v1",
        env_keys=("MISTRAL_API_KEY",),
        model_env_keys=("OPEN_HARNESS_MISTRAL_MODEL", "MISTRAL_MODEL"),
        # Codestral is the coding-tuned flagship; mistral-large-latest
        # is the general model.
        default_model="codestral-latest",
    ),
    _Preset(
        name="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        env_keys=("OPENROUTER_API_KEY",),
        model_env_keys=("OPEN_HARNESS_OPENROUTER_MODEL", "OPENROUTER_MODEL"),
        # OpenRouter is a meta-provider — one key, hundreds of models.
        # We default to a solid open-weight general model so free
        # credits work out of the box; users pick a specific slug via
        # env var.
        default_model="meta-llama/llama-3.3-70b-instruct",
        extra_headers=(
            ("HTTP-Referer", "https://github.com/harness-engineering/lyra"),
            ("X-Title", "Lyra"),
        ),
    ),
    _Preset(
        name="lmstudio",
        label="LM Studio (local)",
        base_url="http://127.0.0.1:1234/v1",
        env_keys=(),   # no key needed for local
        model_env_keys=("OPEN_HARNESS_LMSTUDIO_MODEL",),
        # LM Studio accepts any loaded model regardless of slug;
        # leaving this empty makes the server pick whatever is
        # currently loaded, which is usually what the user wants.
        default_model="local-model",
        auth_scheme="none",
        probe_reachable=True,
    ),
    _Preset(
        name="qwen",
        label="Qwen (Alibaba DashScope)",
        # Same endpoint as ``dashscope`` — Phase 2 promotes ``qwen``
        # from a build-time string alias to a first-class peer so the
        # user-facing slug matches the model brand they're typing.
        # The legacy ``dashscope`` preset stays below for back-compat
        # with anyone scripting the old name; both read the same env
        # vars in the same priority order, but the canonical home is
        # here.
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        # Both env names work; ``QWEN_API_KEY`` matches the brand,
        # ``DASHSCOPE_API_KEY`` matches Alibaba's docs. Whichever the
        # user pasted first wins.
        env_keys=("QWEN_API_KEY", "DASHSCOPE_API_KEY"),
        model_env_keys=(
            "OPEN_HARNESS_QWEN_MODEL",
            "QWEN_MODEL",
            "OPEN_HARNESS_DASHSCOPE_MODEL",
            "DASHSCOPE_MODEL",
        ),
        # qwen-plus is the mid-tier general model. Users routing to
        # ``qwen3-coder`` / ``qwen-max`` set the env var or pass
        # ``--model``.
        default_model="qwen-plus",
    ),
    _Preset(
        name="dashscope",
        label="Alibaba DashScope (legacy alias for qwen)",
        # Kept for back-compat: anyone scripting ``--llm dashscope``
        # or relying on the v2.0 preset name still works. The qwen
        # preset above is the new canonical name and shows up first
        # in the auto cascade.
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        env_keys=("DASHSCOPE_API_KEY", "QWEN_API_KEY"),
        model_env_keys=("OPEN_HARNESS_DASHSCOPE_MODEL", "DASHSCOPE_MODEL"),
        default_model="qwen-plus",
    ),
    _Preset(
        name="vllm",
        label="vLLM (local)",
        base_url="http://127.0.0.1:8000/v1",
        env_keys=(),
        model_env_keys=("OPEN_HARNESS_VLLM_MODEL", "VLLM_MODEL"),
        # vLLM requires the model name on every request; users set the
        # right slug via env var or pass --model. Empty default keeps
        # us from shipping a model assumption that may not match the
        # user's deployment.
        default_model="",
        auth_scheme="none",
        probe_reachable=True,
    ),
    _Preset(
        name="llama-server",
        label="llama.cpp server (local)",
        # llama.cpp's HTTP server defaults to :8080.
        base_url="http://127.0.0.1:8080/v1",
        env_keys=(),
        model_env_keys=("OPEN_HARNESS_LLAMA_SERVER_MODEL",),
        default_model="local-model",
        auth_scheme="none",
        probe_reachable=True,
    ),
    _Preset(
        name="tgi",
        label="HuggingFace TGI (local)",
        # HuggingFace Text Generation Inference exposes the OpenAI
        # chat shape on /v1/chat/completions when started with
        # --port 8081 (we pick this port to keep it distinct from
        # llama.cpp at 8080).
        base_url="http://127.0.0.1:8081/v1",
        env_keys=(),
        model_env_keys=("OPEN_HARNESS_TGI_MODEL", "TGI_MODEL"),
        default_model="tgi",
        auth_scheme="none",
        probe_reachable=True,
    ),
    _Preset(
        name="llamafile",
        label="Llamafile (Mozilla, local)",
        # Llamafile starts on :8082 by default in our docs (each local
        # backend gets a unique default port to ease running multiple
        # at once).
        base_url="http://127.0.0.1:8082/v1",
        env_keys=(),
        model_env_keys=("OPEN_HARNESS_LLAMAFILE_MODEL",),
        default_model="llamafile",
        auth_scheme="none",
        probe_reachable=True,
    ),
    _Preset(
        name="mlx",
        label="MLX-LM (Apple Silicon, local)",
        # MLX-LM's OpenAI-compatible server uses :8083 in our docs to
        # stay distinct from the other local backends. Users who run
        # MLX with a different port set OPEN_HARNESS_MLX_BASE_URL via
        # the factory's base-url override.
        base_url="http://127.0.0.1:8083/v1",
        env_keys=(),
        model_env_keys=("OPEN_HARNESS_MLX_MODEL", "MLX_MODEL"),
        default_model="mlx-community/Llama-3.2-3B-Instruct-4bit",
        auth_scheme="none",
        probe_reachable=True,
    ),
)


def preset_by_name(name: str) -> Optional[_Preset]:
    """Return the preset whose ``name`` matches (case-insensitive)."""
    norm = name.lower().strip()
    for p in PRESETS:
        if p.name == norm:
            return p
    return None


def configured_presets() -> Iterable[_Preset]:
    """Yield presets that are ready to use in the current environment.

    Order is the declaration order in :data:`PRESETS`, i.e. the
    default cascade order. The factory's ``auto`` path iterates this.
    """
    for p in PRESETS:
        if p.configured():
            yield p


def iter_presets() -> Iterable[_Preset]:
    """Yield every preset (configured or not) for help text generation."""
    return iter(PRESETS)


__all__ = [
    "OpenAICompatibleLLM",
    "PRESETS",
    "ProviderHTTPError",
    "ProviderNotConfigured",
    "ProviderRouting",
    "configured_presets",
    "iter_presets",
    "preset_by_name",
]
