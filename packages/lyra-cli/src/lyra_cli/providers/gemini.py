"""Google Gemini adapter.

Gemini is the one cloud LLM in the top tier that does **not** speak
OpenAI's chat-completions format; it has its own
``generativelanguage.googleapis.com/v1beta/models/{model}:generateContent``
endpoint with a distinct message/tool schema. Rather than jam it
into the OpenAI-compatible base we give it its own thin adapter.

Shape of the translation:

*   Our ``system`` messages → Gemini's top-level ``systemInstruction``.
*   Our ``user`` / ``assistant`` messages → Gemini's ``contents``
    array with ``role`` of ``user`` / ``model`` respectively.
*   Our ``tool_calls`` → Gemini ``functionCall`` parts inside a
    ``model`` content.
*   Our ``tool`` (result) messages → Gemini ``functionResponse`` parts
    inside a ``user`` content.
*   Our Anthropic-style tool schemas → Gemini's
    ``tools: [{"functionDeclarations": [...]}]`` with
    ``parameters`` being plain JSON-Schema.

Auth: ``GEMINI_API_KEY`` is preferred; ``GOOGLE_API_KEY`` is accepted
as a fallback because both env vars are documented in Google's own
quickstart and people use them interchangeably.

Stdlib-only. No ``google-generativeai`` dep — the REST API is just
HTTPS with a JSON body like everything else.
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

from .openai_compatible import ProviderHTTPError, ProviderNotConfigured

GEMINI_DEFAULT_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
"""Default Gemini REST root. ``v1beta`` is where all the tool-use
features live in 2026; the stable ``v1`` endpoint is behind on tool
calls and multimodal bits, so we pin v1beta the same way Google's
own SDK does."""

GEMINI_DEFAULT_MODEL: str = "gemini-2.5-pro"
"""Flagship general model. Users can override via
``OPEN_HARNESS_GEMINI_MODEL`` or ``GEMINI_MODEL`` — e.g.
``gemini-2.5-flash`` for cheap/fast or ``gemini-2.5-flash-lite`` for
ultra-cheap."""


class GeminiLLM(LLMProvider):
    """Adapter for the Gemini REST API."""

    def __init__(
        self,
        model: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
            or None
        )
        if not self.api_key:
            raise ProviderNotConfigured(
                "gemini: no API key configured. "
                "Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your shell."
            )
        self.model = (
            model
            or os.environ.get("OPEN_HARNESS_GEMINI_MODEL", "").strip()
            or os.environ.get("GEMINI_MODEL", "").strip()
            or GEMINI_DEFAULT_MODEL
        )
        self.base_url = (base_url or GEMINI_DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        # v2.3.0: token-usage capture parity with the OpenAI-compatible
        # path. Gemini reports counts on the response's
        # ``usageMetadata`` block; we normalise to the same dict shape
        # the rest of the stack expects so ``_bill_turn`` can charge
        # the session without a Gemini-specific code path.
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
        system_text, contents = self._build_contents(messages)
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_text:
            payload["systemInstruction"] = {
                "parts": [{"text": system_text}],
            }
        if tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        self._tool_to_gemini(t) for t in tools
                    ]
                }
            ]

        # Gemini takes the API key as a query param (standard Google
        # REST convention) rather than an Authorization header. Some
        # OpenAI-compat proxies of Gemini exist, but we target the
        # native endpoint so we can use native tool-call features.
        url = (
            f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        )
        data = json.dumps(payload).encode("utf-8")
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
            raise ProviderHTTPError(
                f"gemini HTTP {e.code}: {body.strip()[:500] or e.reason}"
            ) from e
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            raise ProviderHTTPError(
                f"gemini unreachable at {self.base_url}: {e}"
            ) from e

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ProviderHTTPError(
                f"gemini returned non-JSON: {raw[:200]!r}"
            ) from e

        candidates = parsed.get("candidates") or []
        if not candidates:
            # Gemini returns ``promptFeedback.blockReason`` when safety
            # filters reject; surface that instead of a silent empty.
            feedback = parsed.get("promptFeedback") or {}
            reason = feedback.get("blockReason") or parsed.get("error", {}).get(
                "message", "empty response"
            )
            raise ProviderHTTPError(f"gemini: {reason}")
        # Capture usage *before* returning so the caller's billing
        # (``_bill_turn``) sees fresh numbers for this exact turn.
        self._record_usage(parsed.get("usageMetadata"))
        return self._candidate_to_msg(candidates[0])

    def _record_usage(self, usage_metadata: Optional[dict[str, Any]]) -> None:
        """Normalise Gemini's ``usageMetadata`` into the shared shape.

        Gemini emits ``promptTokenCount`` / ``candidatesTokenCount`` /
        ``totalTokenCount``. We translate to ``prompt_tokens`` /
        ``completion_tokens`` / ``total_tokens`` so the cost
        calculator doesn't need a per-provider switch.
        """
        if not isinstance(usage_metadata, dict):
            self.last_usage = {}
            return
        try:
            prompt = int(usage_metadata.get("promptTokenCount") or 0)
            completion = int(usage_metadata.get("candidatesTokenCount") or 0)
            total = int(
                usage_metadata.get("totalTokenCount") or (prompt + completion)
            )
        except (TypeError, ValueError):
            self.last_usage = {}
            return
        if total <= 0:
            self.last_usage = {}
            return
        self.last_usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    # ------------------------------------------------------------------
    # Wire-format translation
    # ------------------------------------------------------------------

    @classmethod
    def _build_contents(
        cls, messages: list[Message]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Split our transcript into Gemini's (systemInstruction, contents).

        Gemini doesn't support ``role=system`` in ``contents``; the
        system prompt goes in a top-level field. Multiple system
        messages are concatenated with newlines because (a) it's rare,
        and (b) Gemini has exactly one ``systemInstruction`` slot.
        """
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                if m.content:
                    system_parts.append(m.content)
                continue
            contents.append(cls._msg_to_gemini(m))
        return "\n\n".join(system_parts), contents

    @staticmethod
    def _msg_to_gemini(m: Message) -> dict[str, Any]:
        """Map one non-system :class:`Message` to a Gemini ``content`` dict."""
        if m.role == "tool":
            parts: list[dict[str, Any]] = []
            for r in m.tool_results:
                # Gemini expects the *response* object to be a JSON-
                # structured dict. We wrap plain-text tool output in
                # ``{"result": "..."}`` so every tool's response is a
                # valid object even if the content was free-form text.
                try:
                    response_obj = json.loads(r.content)
                    if not isinstance(response_obj, dict):
                        response_obj = {"result": response_obj}
                except (json.JSONDecodeError, TypeError):
                    response_obj = {"result": r.content}
                if r.is_error:
                    response_obj["error"] = True
                parts.append(
                    {
                        "functionResponse": {
                            # Gemini uses the *name* not the id to link
                            # responses to calls. We store the call id
                            # in ``call_id`` upstream but have no slot
                            # for it on the wire, so we fall back to
                            # the call id as the function name when
                            # nothing better is available.
                            "name": r.call_id,
                            "response": response_obj,
                        }
                    }
                )
            # Tool results live inside a ``user`` content block in the
            # Gemini transcript model.
            return {"role": "user", "parts": parts}

        parts: list[dict[str, Any]] = []
        if m.content:
            parts.append({"text": m.content})
        for c in m.tool_calls:
            parts.append(
                {
                    "functionCall": {
                        "name": c.name,
                        "args": c.args or {},
                    }
                }
            )
        role = "model" if m.role == "assistant" else "user"
        return {"role": role, "parts": parts or [{"text": ""}]}

    @staticmethod
    def _tool_to_gemini(tool: dict[str, Any]) -> dict[str, Any]:
        """Anthropic-style tool schema → Gemini functionDeclaration.

        Gemini's schema is just JSON-Schema for parameters plus a flat
        ``name`` / ``description``. The translation is essentially a
        relabel.
        """
        if "functionDeclarations" in tool:
            # Already Gemini-shaped; pass through.
            return tool
        return {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema")
            or tool.get("parameters")
            or {"type": "object", "properties": {}},
        }

    @staticmethod
    def _candidate_to_msg(candidate: dict[str, Any]) -> Message:
        """Decode one ``candidates[i]`` entry into a :class:`Message`."""
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        text_chunks: list[str] = []
        tool_calls: list[ToolCall] = []
        for i, p in enumerate(parts):
            if "text" in p and p["text"]:
                text_chunks.append(p["text"])
            fn_call = p.get("functionCall")
            if isinstance(fn_call, dict):
                args = fn_call.get("args") or {}
                tool_calls.append(
                    ToolCall(
                        # Gemini doesn't emit a tool-call id in the
                        # response; synthesise one so the downstream
                        # tool-use loop can track it unambiguously.
                        id=f"gemini_call_{i}",
                        name=fn_call.get("name", ""),
                        args=args if isinstance(args, dict) else {"value": args},
                    )
                )

        # Tool-use detection **overrides** the raw finishReason.
        # Gemini emits ``finishReason: "STOP"`` even when the model
        # produced a functionCall part — the model "stopped" generating
        # because it finished the call, not because the turn ended.
        # The caller (agentic loop) needs to know it must dispatch the
        # tool, so we flip the stop reason when any functionCall was
        # present regardless of what the wire said.
        finish = candidate.get("finishReason") or ""
        if tool_calls:
            stop: StopReason = StopReason.TOOL_USE
        else:
            stop_map = {
                "STOP": StopReason.END_TURN,
                "MAX_TOKENS": StopReason.MAX_TOKENS,
                "SAFETY": StopReason.ERROR,
                "RECITATION": StopReason.ERROR,
            }
            stop = stop_map.get(finish, StopReason.END_TURN)
        return Message.assistant(
            content="".join(text_chunks),
            tool_calls=tool_calls,
            stop_reason=stop,
        )


def gemini_configured() -> bool:
    """Cheap check the factory uses to decide whether to include Gemini.

    We don't probe the endpoint — the key is expensive to acquire
    and a user who set ``GEMINI_API_KEY`` is telling us "try this".
    """
    return bool(
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )


__all__ = [
    "GEMINI_DEFAULT_BASE_URL",
    "GEMINI_DEFAULT_MODEL",
    "GeminiLLM",
    "gemini_configured",
]
