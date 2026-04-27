"""Integration tests: ``settings.json`` -> factory -> preset -> wire.

We tested ProviderRouting marshalling in
``test_openrouter_provider_routing.py`` already. What was missing
(flagged in code review) was an end-to-end check that the factory
actually plumbs ``provider_routing_for`` through to ``_Preset.build``
so a user editing ``~/.lyra/settings.json`` sees the new ``provider``
field on the next request.

These tests use ``LYRA_HOME=tmp_path`` to keep config writes out of
``$HOME`` and a fake ``urlopen`` to capture the outgoing OpenRouter
payload.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


from lyra_cli import llm_factory


class _FakeResp:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _ok_body() -> str:
    return json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ]
        }
    )


def _write_settings(home: Path, payload: dict) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "settings.json").write_text(json.dumps(payload), encoding="utf-8")


def test_openrouter_factory_picks_up_routing_from_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Editing ``settings.json`` flips OpenRouter's wire-level provider routing."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-router-test")
    _write_settings(
        tmp_path,
        {
            "provider_routing": {
                "openrouter": {
                    "sort": "price",
                    "only": ["anthropic", "openai"],
                    "data_collection": "deny",
                }
            }
        },
    )

    captured: dict[str, Any] = {}

    def fake_urlopen(req, timeout: float = 0):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(_ok_body())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    llm = llm_factory.build_llm("openrouter")
    from harness_core.messages import Message

    llm.generate([Message.user("hi")], max_tokens=8)

    provider = captured["body"]["extra_body"]["provider"]
    assert provider == {
        "sort": "price",
        "only": ["anthropic", "openai"],
        "data_collection": "deny",
    }


def test_no_settings_means_no_provider_field(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Default behaviour: no settings.json -> wire payload omits ``provider``."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-router-test")
    # Intentionally no settings.json on disk.

    captured: dict[str, Any] = {}

    def fake_urlopen(req, timeout: float = 0):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(_ok_body())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    llm = llm_factory.build_llm("openrouter")
    from harness_core.messages import Message

    llm.generate([Message.user("hi")], max_tokens=8)

    body = captured["body"]
    extra_body = body.get("extra_body") or {}
    assert "provider" not in extra_body


def test_unknown_field_in_settings_is_silently_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A typo in settings.json must not raise; just drop the unknown key."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-router-test")
    _write_settings(
        tmp_path,
        {
            "provider_routing": {
                "openrouter": {
                    "sort": "price",
                    "made_up_key": "boom",  # typo by user
                }
            }
        },
    )

    captured: dict[str, Any] = {}

    def fake_urlopen(req, timeout: float = 0):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(_ok_body())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    llm = llm_factory.build_llm("openrouter")
    from harness_core.messages import Message

    llm.generate([Message.user("hi")], max_tokens=8)

    provider = captured["body"]["extra_body"]["provider"]
    assert provider == {"sort": "price"}
