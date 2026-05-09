"""GitHub Copilot as a chat backend.

Copilot's internal chat API accepts OpenAI-style chat completions but
requires a short-lived session token derived from a long-lived GitHub
OAuth token. The flow is:

1. User OAuths Lyra as a Copilot-eligible GitHub app -> long-lived
   ``gho_*`` token.
2. On first call, we exchange the gho_* for a 30-min ``ghs_*`` session
   token via ``GET /copilot_internal/v2/token``.
3. Session token goes in ``Authorization: Bearer ghs_...`` on chat
   calls.
4. On 401, we refresh the session token and retry once.

Token persistence is pluggable - the default store writes to
``~/.lyra/auth.json`` with ``chmod 600``.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional, Tuple

from harness_core.messages import Message, StopReason, ToolCall
from harness_core.models import LLMProvider


COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
COPILOT_CHAT_URL = "https://api.githubcopilot.com/chat/completions"


class CopilotUnavailable(RuntimeError):
    """Raised when no GitHub token is configured or refresh fails."""


class CopilotTokenStore:
    """JSON-file token store. ``chmod 600`` on save."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or (Path.home() / ".lyra" / "auth.json")

    def save(self, provider: str, token: str, *, expires_at: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                data = {}
        data[provider] = {"token": token, "expires_at": int(expires_at)}
        self.path.write_text(json.dumps(data, indent=2))
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def load(self, provider: str) -> Optional[Tuple[str, int]]:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return None
        rec = data.get(provider)
        if not isinstance(rec, dict):
            return None
        tok = rec.get("token")
        exp = rec.get("expires_at")
        if isinstance(tok, str) and isinstance(exp, int):
            return tok, exp
        return None

    def clear(self, provider: str) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return
        data.pop(provider, None)
        self.path.write_text(json.dumps(data, indent=2))


def _refresh_copilot_token(
    *,
    github_token: str,
    http: Any,
) -> Tuple[str, int]:
    """Exchange a gho_* token for a ghs_* session token."""
    resp = http.request(
        "GET",
        COPILOT_TOKEN_URL,
        headers={
            "authorization": f"token {github_token}",
            "editor-version": "Lyra/1.7.4",
            "user-agent": "Lyra",
        },
        timeout=10.0,
    )
    if resp.status_code != 200:
        raise CopilotUnavailable(
            f"copilot token refresh failed: HTTP {resp.status_code}: {resp.text}"
        )
    payload = resp.json()
    tok = payload.get("token")
    exp = int(payload.get("expires_at", time.time() + 1500))
    if not isinstance(tok, str):
        raise CopilotUnavailable("copilot token refresh returned no token field")
    return tok, exp


class CopilotLLM(LLMProvider):
    """Chat completions via GitHub Copilot's internal endpoint."""

    def __init__(
        self,
        *,
        github_token: Optional[str],
        http: Any,
        model: str = "gpt-4o",
        token_store: Optional[CopilotTokenStore] = None,
    ) -> None:
        if not github_token:
            raise CopilotUnavailable(
                "no GitHub token configured - run `lyra /auth copilot`"
            )
        self.github_token = github_token
        self.http = http
        self.model = model
        self.token_store = token_store or CopilotTokenStore()
        self.provider_name = "copilot"
        # v2.3.0: token-usage capture so ``_bill_turn`` can attribute
        # cost correctly. Copilot's chat endpoint speaks OpenAI shape
        # (``{"usage": {"prompt_tokens", "completion_tokens",
        # "total_tokens"}}``) so we read it verbatim.
        self.last_usage: dict[str, int] = {}

    def _session_token(self) -> str:
        cached = self.token_store.load("copilot")
        if cached and cached[1] > time.time() + 60:
            return cached[0]
        tok, exp = _refresh_copilot_token(
            github_token=self.github_token, http=self.http
        )
        self.token_store.save("copilot", tok, expires_at=exp)
        return tok

    def generate(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Message:
        payload = {
            "model": self.model,
            "messages": [_msg_to_openai(m) for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = [_tool_to_openai(t) for t in tools]
        resp = self._chat_call(payload)
        if resp.status_code == 401:
            self.token_store.clear("copilot")
            resp = self._chat_call(payload)
        if resp.status_code >= 400:
            raise CopilotUnavailable(
                f"copilot chat failed: HTTP {resp.status_code}: {resp.text}"
            )
        body = resp.json()
        self._record_usage(body)
        return _choice_to_msg(body["choices"][0])

    def _record_usage(self, body: dict[str, Any]) -> None:
        """Capture OpenAI-style ``usage`` from the response body.

        Tolerates Copilot's occasional habit of omitting the field on
        very short turns; an empty ``last_usage`` tells ``_bill_turn``
        to skip the round (we'd rather under-bill than guess).
        """
        usage = (body or {}).get("usage") if isinstance(body, dict) else None
        if not isinstance(usage, dict):
            self.last_usage = {}
            return
        try:
            prompt = int(usage.get("prompt_tokens") or 0)
            completion = int(usage.get("completion_tokens") or 0)
            total = int(usage.get("total_tokens") or (prompt + completion))
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

    def _chat_call(self, payload: dict[str, Any]) -> Any:
        return self.http.request(
            "POST",
            COPILOT_CHAT_URL,
            headers={
                "authorization": f"Bearer {self._session_token()}",
                "content-type": "application/json",
                "editor-version": "Lyra/1.7.4",
                "user-agent": "Lyra",
            },
            json=payload,
            timeout=120.0,
        )


def _msg_to_openai(m: Message) -> dict[str, Any]:
    if m.role == "tool":
        if not m.tool_results:
            return {"role": "tool", "content": "", "tool_call_id": ""}
        first = m.tool_results[0]
        return {
            "role": "tool",
            "content": "\n\n".join(r.content for r in m.tool_results),
            "tool_call_id": first.call_id,
        }
    out: dict[str, Any] = {"role": m.role, "content": m.content or ""}
    if m.role == "assistant" and m.tool_calls:
        out["tool_calls"] = [
            {"id": c.id, "type": "function",
             "function": {"name": c.name, "arguments": json.dumps(c.args or {})}}
            for c in m.tool_calls
        ]
    return out


def _tool_to_openai(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema") or tool.get("parameters")
                          or {"type": "object", "properties": {}},
        },
    }


def _choice_to_msg(choice: dict[str, Any]) -> Message:
    msg = choice.get("message") or {}
    text = msg.get("content") or ""
    tool_calls: list[ToolCall] = []
    for i, c in enumerate(msg.get("tool_calls") or []):
        fn = c.get("function") or {}
        args_raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except json.JSONDecodeError:
            args = {"_raw": args_raw}
        tool_calls.append(ToolCall(
            id=str(c.get("id") or f"call_{i}"),
            name=fn.get("name", ""),
            args=args if isinstance(args, dict) else {"value": args},
        ))
    fin = choice.get("finish_reason") or ("tool_calls" if tool_calls else "stop")
    stop_map = {"stop": StopReason.END_TURN, "length": StopReason.MAX_TOKENS,
                "tool_calls": StopReason.TOOL_USE,
                "content_filter": StopReason.ERROR}
    return Message.assistant(
        content=text,
        tool_calls=tool_calls,
        stop_reason=stop_map.get(fin, StopReason.END_TURN),
    )


__all__ = [
    "CopilotLLM",
    "CopilotTokenStore",
    "CopilotUnavailable",
    "_refresh_copilot_token",
    "COPILOT_TOKEN_URL",
    "COPILOT_CHAT_URL",
]
