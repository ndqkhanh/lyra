"""Google Vertex AI provider — Gemini via google-cloud-aiplatform.

google-cloud-aiplatform is an *optional* dependency
(``pip install 'lyra[vertex]'``) because it pulls in protobuf, grpc,
and the entire AI Platform client surface (~80 MB) which most users
who hit Gemini do via the public ``generativelanguage`` endpoint or
OpenRouter instead.

This adapter wraps a ``GenerativeModel`` instance from
``vertexai.generative_models`` and translates between harness-core
``Message``s and Vertex's ``Content`` / ``Part`` shape. As of v2.3.0
the adapter:

* **Forwards ``tools`` to the wire** — earlier revisions accepted the
  argument in the signature but dropped it before
  ``generate_content`` was called, so any agentic loop pointed at
  Vertex got a tool-less response no matter what schema was passed.
* **Records token usage on ``last_usage``** so
  :func:`lyra_cli.interactive.session._bill_turn` can roll Vertex
  cost into ``session.cost_usd`` instead of silently leaving the
  meter at $0.
* **Surfaces ``functionCall`` / ``functionResponse`` parts** as
  proper :class:`ToolCall` objects, mirroring the public-Gemini
  adapter so the same agent loop drives both endpoints.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional

from harness_core.messages import Message, StopReason, ToolCall
from harness_core.models import LLMProvider


class VertexUnavailable(RuntimeError):
    """Raised when google-cloud-aiplatform isn't installed and no client given."""


def _try_import_vertex() -> Optional[Any]:
    try:
        import vertexai  # type: ignore  # noqa: F401
        from vertexai.generative_models import GenerativeModel  # type: ignore
    except ImportError:
        return None
    return GenerativeModel


def vertex_available() -> bool:
    """True when google-cloud-aiplatform is importable."""
    return _try_import_vertex() is not None


class GeminiVertexLLM(LLMProvider):
    """Gemini routed through Google Vertex AI."""

    def __init__(
        self,
        *,
        model: str,
        project: str,
        location: str = "us-central1",
        client: Optional[Any] = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            GenerativeModel = _try_import_vertex()
            if GenerativeModel is None:
                raise VertexUnavailable(
                    "google-cloud-aiplatform is not installed; "
                    "install with `pip install 'lyra[vertex]'`"
                )
            import vertexai  # type: ignore
            vertexai.init(project=project, location=location)
            self._client = GenerativeModel(model)
        self.model = model
        self.project = project
        self.location = location
        self.provider_name = "vertex"
        # v2.3.0: token-usage capture parity with the OpenAI-compatible
        # path. ``_bill_turn`` reads this dict; an empty dict means
        # "no usage reported by the provider" and silently no-ops the
        # billing — better than under-counting.
        self.last_usage: dict[str, int] = {}

    @staticmethod
    def _msg_to_vertex(m: Message) -> dict:
        """Map harness Message to Vertex content shape.

        Tool messages are wrapped as ``functionResponse`` parts inside
        a ``user`` content (Vertex routes tool results through the
        user channel, same as the public-Gemini API). Assistant
        ``tool_calls`` become ``functionCall`` parts inside a
        ``model`` content. Plain text and "no parts" turns degrade
        gracefully — Vertex rejects empty parts arrays, so we always
        emit at least one ``{"text": ""}``.
        """
        if m.role == "tool":
            parts: list[dict[str, Any]] = []
            for r in (m.tool_results or []):
                try:
                    response_obj: Any = json.loads(r.content)
                    if not isinstance(response_obj, dict):
                        response_obj = {"result": response_obj}
                except (json.JSONDecodeError, TypeError):
                    response_obj = {"result": r.content}
                if r.is_error:
                    response_obj["error"] = True
                parts.append(
                    {
                        "functionResponse": {
                            "name": r.call_id,
                            "response": response_obj,
                        }
                    }
                )
            return {"role": "user", "parts": parts or [{"text": ""}]}

        parts: list[dict[str, Any]] = []
        if m.content:
            parts.append({"text": m.content})
        for c in (m.tool_calls or []):
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
    def _tool_to_vertex(tool: dict[str, Any]) -> dict[str, Any]:
        """Anthropic-style tool schema → Vertex ``functionDeclaration``.

        Pass-through when the caller already speaks Vertex shape so
        custom integrations (e.g. user-provided ``tools`` block)
        survive untouched.
        """
        if "functionDeclarations" in tool:
            return tool
        return {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema")
            or tool.get("parameters")
            or {"type": "object", "properties": {}},
        }

    def generate(
        self,
        messages: List[Message],
        tools: Optional[List[dict]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        contents = [self._msg_to_vertex(m) for m in messages]
        gen_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        kwargs: dict[str, Any] = {
            "contents": contents,
            "generation_config": gen_config,
        }
        # v2.3.0: forward tools to the wire. Earlier revisions silently
        # dropped this so any agent loop pointed at Vertex received a
        # tool-less response. The wrapper expects Vertex's
        # ``[{"function_declarations": [...]}]`` shape; we adapt from
        # Anthropic-style schemas the rest of the stack uses.
        if tools:
            kwargs["tools"] = [
                {
                    "function_declarations": [
                        self._tool_to_vertex(t) for t in tools
                    ]
                }
            ]

        resp = self._client.generate_content(**kwargs)
        self._record_usage(resp)
        return self._response_to_msg(resp)

    def _record_usage(self, resp: Any) -> None:
        """Capture token usage onto ``last_usage`` (best effort).

        Vertex returns counts on ``response.usage_metadata`` with
        attributes ``prompt_token_count`` / ``candidates_token_count``
        / ``total_token_count``. The structure is the same in both
        the SDK's protobuf wrapper and the dict mode some test fakes
        return — we read both shapes and silently no-op when neither
        exists rather than crash a real call.
        """
        meta = getattr(resp, "usage_metadata", None)
        if meta is None and isinstance(resp, dict):
            meta = resp.get("usage_metadata") or resp.get("usageMetadata")
        if meta is None:
            self.last_usage = {}
            return
        prompt = (
            getattr(meta, "prompt_token_count", None)
            if not isinstance(meta, dict)
            else meta.get("prompt_token_count") or meta.get("promptTokenCount")
        )
        completion = (
            getattr(meta, "candidates_token_count", None)
            if not isinstance(meta, dict)
            else meta.get("candidates_token_count")
            or meta.get("candidatesTokenCount")
        )
        total = (
            getattr(meta, "total_token_count", None)
            if not isinstance(meta, dict)
            else meta.get("total_token_count") or meta.get("totalTokenCount")
        )
        try:
            prompt_i = int(prompt or 0)
            completion_i = int(completion or 0)
            total_i = int(total or (prompt_i + completion_i))
        except (TypeError, ValueError):
            self.last_usage = {}
            return
        if total_i <= 0:
            self.last_usage = {}
            return
        self.last_usage = {
            "prompt_tokens": prompt_i,
            "completion_tokens": completion_i,
            "total_tokens": total_i,
        }

    @staticmethod
    def _response_to_msg(resp: Any) -> Message:
        """Decode a Vertex response into our :class:`Message`.

        Handles two shapes:

        * SDK ``GenerationResponse`` with ``.candidates[0].content.parts``
          where each part has ``.text`` or ``.function_call`` / ``.functionCall``.
        * Dict mode (used by test fakes) with the same nested keys.

        ``finish_reason == STOP`` overrides to ``TOOL_USE`` whenever a
        ``functionCall`` appeared, matching the public-Gemini adapter
        (Vertex emits ``STOP`` even when the model stopped to call a
        tool; the agent loop has to see ``TOOL_USE`` so it dispatches).
        """
        candidates = (
            getattr(resp, "candidates", None)
            if not isinstance(resp, dict)
            else resp.get("candidates")
        )
        if not candidates:
            text = getattr(resp, "text", None) or ""
            return Message.assistant(content=text, stop_reason=StopReason.END_TURN)

        candidate = candidates[0]
        content = (
            getattr(candidate, "content", None)
            if not isinstance(candidate, dict)
            else candidate.get("content")
        )
        parts = (
            (getattr(content, "parts", None) if not isinstance(content, dict) else content.get("parts"))
            or []
        )
        text_chunks: list[str] = []
        tool_calls: list[ToolCall] = []
        for i, p in enumerate(parts):
            t = (
                getattr(p, "text", None)
                if not isinstance(p, dict)
                else p.get("text")
            )
            if isinstance(t, str) and t:
                text_chunks.append(t)
            fc = (
                getattr(p, "function_call", None)
                if not isinstance(p, dict)
                else (p.get("functionCall") or p.get("function_call"))
            )
            if fc is not None:
                name = (
                    getattr(fc, "name", None)
                    if not isinstance(fc, dict)
                    else fc.get("name")
                ) or ""
                args = (
                    getattr(fc, "args", None)
                    if not isinstance(fc, dict)
                    else fc.get("args")
                ) or {}
                # SDK args are a Struct/MapComposite; coerce to plain
                # dict so the agent loop and JSON-encoders can work
                # with them.
                if not isinstance(args, dict):
                    try:
                        args = dict(args)
                    except (TypeError, ValueError):
                        args = {"_raw": str(args)}
                tool_calls.append(
                    ToolCall(
                        id=f"vertex_call_{i}",
                        name=name,
                        args=args,
                    )
                )

        finish = (
            getattr(candidate, "finish_reason", None)
            if not isinstance(candidate, dict)
            else (candidate.get("finish_reason") or candidate.get("finishReason"))
        )
        if tool_calls:
            stop = StopReason.TOOL_USE
        else:
            finish_str = str(finish or "STOP").upper()
            stop_map = {
                "STOP": StopReason.END_TURN,
                "MAX_TOKENS": StopReason.MAX_TOKENS,
                "SAFETY": StopReason.ERROR,
                "RECITATION": StopReason.ERROR,
            }
            stop = stop_map.get(finish_str, StopReason.END_TURN)
        return Message.assistant(
            content="".join(text_chunks),
            tool_calls=tool_calls,
            stop_reason=stop,
        )


__all__ = [
    "GeminiVertexLLM",
    "VertexUnavailable",
    "vertex_available",
]
