"""Phase D.5 — ``lyra acp`` Typer subcommand.

These tests drive the ACP stdio bridge through the Typer CliRunner.
The ``--once`` flag is the key seam: it consumes a single line from
stdin, dispatches it through :class:`lyra_core.acp.AcpServer`, prints
the response on stdout, and exits. That keeps the test deterministic
without a long-lived subprocess.

We also exercise the live handler bindings:

* ``initialize`` — handshake metadata.
* ``sendUserMessage`` — runs through ``_chat_with_llm`` with a stub
  ``_ensure_llm`` so no network is involved.
* ``cancel`` — best-effort no-op.
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from harness_core.messages import Message
from lyra_cli.__main__ import app


runner = CliRunner()


class _CannedLLM:
    """Pure-Python LLM stub for the ACP send-user-message path."""

    def __init__(self, *, reply: str = "ok") -> None:
        self._reply = reply
        self.last_usage = {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}
        self.model = "stub"
        self.provider_name = "stub"

    def generate(
        self,
        messages: list[Any],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Message:
        return Message.assistant(content=self._reply)


def _make_request(method: str, params: dict[str, Any] | None = None, req_id: int = 1) -> str:
    body: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": req_id}
    if params is not None:
        body["params"] = params
    return json.dumps(body) + "\n"


def test_acp_initialize_returns_handshake() -> None:
    payload = _make_request("initialize", {})
    result = runner.invoke(app, ["acp", "--once"], input=payload)
    assert result.exit_code == 0, result.stdout
    response = json.loads(result.stdout.splitlines()[-1])
    assert response["id"] == 1
    body = response["result"]
    assert body["agent"]["name"] == "lyra"
    assert body["protocol"]["name"] == "acp"
    assert body["capabilities"]["sendUserMessage"] is True


def test_acp_send_user_message_round_trips_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: _CannedLLM(reply="hello back"),
    )

    payload = _make_request(
        "sendUserMessage",
        {"text": "hello there", "system": "test prompt"},
    )
    result = runner.invoke(app, ["acp", "--once", "--model", "stub"], input=payload)

    assert result.exit_code == 0, result.stdout
    response = json.loads(result.stdout.splitlines()[-1])
    assert response["id"] == 1
    body = response["result"]
    assert body["text"] == "hello back"
    assert body["model"] == "stub"
    assert "usage" in body
    assert body["usage"]["tokens"] >= 0


def test_acp_send_user_message_rejects_missing_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: _CannedLLM(),
    )
    payload = _make_request("sendUserMessage", {})
    result = runner.invoke(app, ["acp", "--once"], input=payload)
    assert result.exit_code == 0
    response = json.loads(result.stdout.splitlines()[-1])
    assert response["error"]["code"] == -32602
    assert "text" in response["error"]["message"]


def test_acp_unknown_method_returns_method_not_found() -> None:
    payload = _make_request("totally_made_up", {})
    result = runner.invoke(app, ["acp", "--once"], input=payload)
    assert result.exit_code == 0
    response = json.loads(result.stdout.splitlines()[-1])
    assert response["error"]["code"] == -32601


def test_acp_cancel_returns_ok() -> None:
    payload = _make_request("cancel", {})
    result = runner.invoke(app, ["acp", "--once"], input=payload)
    assert result.exit_code == 0
    response = json.loads(result.stdout.splitlines()[-1])
    assert response["result"] == {"ok": True}
