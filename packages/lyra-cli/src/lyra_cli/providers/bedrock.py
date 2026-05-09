"""AWS Bedrock provider — Anthropic Claude via Bedrock Converse API.

Bedrock hosts Anthropic's models with the same input shape as the
Anthropic SDK but routed through AWS SigV4-signed HTTPS. We use
``boto3`` (an *optional* dependency, install via ``lyra[bedrock]``)
because writing SigV4 by hand is hostile to anyone reading this
file later.

Why optional:

* ``boto3`` ships ~50 MB of generated client code. Forcing it on
  every Lyra install would balloon the CLI footprint for the
  majority of users who run on Anthropic's own API.
* Ops teams running on AWS already have ``boto3`` available and
  install it with one ``pip install 'lyra[bedrock]'``.

Tool calls round-trip through Bedrock's Converse API shape
(``toolUse`` / ``toolResult`` blocks); we map those to harness-core's
:class:`ToolCall`.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional

from harness_core.messages import Message, StopReason, ToolCall
from harness_core.models import LLMProvider


class BedrockUnavailable(RuntimeError):
    """Raised when boto3 isn't installed and no client was injected."""


def _try_import_boto3() -> Optional[Any]:
    try:
        import boto3  # type: ignore
    except ImportError:
        return None
    return boto3


def bedrock_available() -> bool:
    """True when boto3 is importable in the current process."""
    return _try_import_boto3() is not None


class AnthropicBedrockLLM(LLMProvider):
    """Anthropic Claude served via AWS Bedrock Converse.

    Parameters
    ----------
    model:
        Bedrock model ID, e.g. ``anthropic.claude-opus-4-5-v2:0``.
    region:
        AWS region. Defaults to the boto3 session default
        (``AWS_REGION`` env var).
    client:
        Optional pre-built bedrock-runtime client. If ``None`` we
        build one from boto3; this kwarg exists primarily for tests
        which inject a fake.
    """

    def __init__(
        self,
        *,
        model: str,
        region: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            boto3 = _try_import_boto3()
            if boto3 is None:
                raise BedrockUnavailable(
                    "boto3 is not installed; install with `pip install 'lyra[bedrock]'`"
                )
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=region,
            )
        self.model = model
        self.provider_name = "bedrock"
        # v2.3.0: token-usage capture so ``_bill_turn`` can charge the
        # session correctly. Bedrock returns counts on ``resp["usage"]``
        # with ``inputTokens`` / ``outputTokens`` / ``totalTokens``.
        self.last_usage: dict[str, int] = {}

    @staticmethod
    def _msg_to_bedrock(m: Message) -> dict:
        """Map harness Message to Bedrock Converse content blocks."""
        if m.role == "tool":
            blocks = []
            for r in (m.tool_results or []):
                blocks.append({
                    "toolResult": {
                        "toolUseId": r.call_id,
                        "content": [{"text": str(r.content)}],
                        "status": "error" if r.is_error else "success",
                    }
                })
            return {"role": "user", "content": blocks}

        content_blocks: list[dict] = []
        if m.content:
            content_blocks.append({"text": m.content})
        if m.role == "assistant" and m.tool_calls:
            for tc in m.tool_calls:
                content_blocks.append({
                    "toolUse": {
                        "toolUseId": tc.id,
                        "name": tc.name,
                        "input": tc.args or {},
                    }
                })
        return {"role": m.role, "content": content_blocks}

    def generate(
        self,
        messages: List[Message],
        tools: Optional[List[dict]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        kwargs: dict[str, Any] = {
            "modelId": self.model,
            "messages": [self._msg_to_bedrock(m) for m in messages],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if tools:
            kwargs["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": t.get("name", ""),
                            "description": t.get("description", ""),
                            "inputSchema": {
                                "json": t.get("input_schema") or t.get("parameters")
                                or {"type": "object", "properties": {}}
                            },
                        }
                    }
                    for t in tools
                ]
            }
        resp = self._client.converse(**kwargs)
        self._record_usage(resp)
        return self._parse_response(resp)

    def _record_usage(self, resp: Any) -> None:
        """Capture Bedrock Converse ``usage`` onto ``last_usage``.

        Bedrock returns ``{"usage": {"inputTokens": int,
        "outputTokens": int, "totalTokens": int}}``. We normalise to
        the ``prompt_tokens`` / ``completion_tokens`` / ``total_tokens``
        keys :func:`_bill_turn` reads, so cost calc looks identical
        across every provider.
        """
        usage = None
        if isinstance(resp, dict):
            usage = resp.get("usage")
        else:
            usage = getattr(resp, "usage", None)
        if not usage:
            self.last_usage = {}
            return
        try:
            if isinstance(usage, dict):
                prompt = int(usage.get("inputTokens") or 0)
                completion = int(usage.get("outputTokens") or 0)
                total = int(usage.get("totalTokens") or (prompt + completion))
            else:
                prompt = int(getattr(usage, "inputTokens", 0) or 0)
                completion = int(getattr(usage, "outputTokens", 0) or 0)
                total = int(
                    getattr(usage, "totalTokens", 0) or (prompt + completion)
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

    @staticmethod
    def _parse_response(resp: dict) -> Message:
        msg = (resp.get("output") or {}).get("message") or {}
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in msg.get("content", []):
            if "text" in block and block["text"]:
                text_parts.append(block["text"])
            elif "toolUse" in block:
                tu = block["toolUse"]
                args = tu.get("input") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"_raw": args}
                tool_calls.append(
                    ToolCall(
                        id=tu.get("toolUseId", ""),
                        name=tu.get("name", ""),
                        args=args if isinstance(args, dict) else {"value": args},
                    )
                )
        stop_raw = resp.get("stopReason") or ("tool_use" if tool_calls else "end_turn")
        stop_map = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.END_TURN,
            "content_filtered": StopReason.ERROR,
        }
        return Message.assistant(
            content="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=stop_map.get(stop_raw, StopReason.END_TURN),
        )


__all__ = [
    "AnthropicBedrockLLM",
    "BedrockUnavailable",
    "bedrock_available",
]
