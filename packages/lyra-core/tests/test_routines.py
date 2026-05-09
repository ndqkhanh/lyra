"""Routines tests (v3.7 L37-8)."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from lyra_core.cron.routines import (
    CronTrigger,
    GitHubWebhookTrigger,
    HttpApiTrigger,
    Routine,
    RoutineAuthError,
    RoutineRegistry,
    TriggerKind,
    verify_api_signature,
    verify_github_signature,
)


SECRET = b"test-routine-secret-32-bytes____"


def _sign_github(body: bytes, *, secret: bytes = SECRET) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def _sign_api(body: bytes, *, secret: bytes = SECRET) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _registry() -> RoutineRegistry:
    reg = RoutineRegistry()
    fired: list[tuple[str, dict]] = []

    def workflow(name, payload):
        fired.append((name, payload))

    reg.register_workflow("scan-issues", workflow)
    reg.fired = fired      # type: ignore[attr-defined]
    return reg


# --- HMAC verification -----------------------------------------------------


def test_verify_github_signature_round_trip() -> None:
    body = b'{"action":"opened"}'
    sig = _sign_github(body)
    verify_github_signature(secret=SECRET, body=body, received_signature=sig)


def test_verify_github_signature_rejects_bad_prefix() -> None:
    with pytest.raises(RoutineAuthError, match="LBL-ROUTINE-AUTH.*sha256"):
        verify_github_signature(
            secret=SECRET, body=b"x", received_signature="md5=abc",
        )


def test_verify_github_signature_rejects_bad_hmac() -> None:
    body = b'{"x":1}'
    with pytest.raises(RoutineAuthError, match="LBL-ROUTINE-AUTH.*mismatch"):
        verify_github_signature(
            secret=SECRET, body=body, received_signature="sha256=" + "0" * 64,
        )


def test_verify_api_signature_round_trip() -> None:
    body = b'{"action":"fire"}'
    verify_api_signature(secret=SECRET, body=body, received_signature=_sign_api(body))


def test_verify_api_signature_rejects_mismatch() -> None:
    with pytest.raises(RoutineAuthError, match="LBL-ROUTINE-AUTH.*mismatch"):
        verify_api_signature(
            secret=SECRET, body=b"x", received_signature="0" * 64,
        )


# --- Registry registration -------------------------------------------------


def test_register_workflow_duplicate_raises() -> None:
    reg = RoutineRegistry()
    reg.register_workflow("w1", lambda n, p: None)
    with pytest.raises(ValueError, match="already registered"):
        reg.register_workflow("w1", lambda n, p: None)


def test_register_routine_with_unknown_workflow_raises() -> None:
    reg = RoutineRegistry()
    with pytest.raises(ValueError, match="unknown workflow"):
        reg.register_routine(Routine(
            name="r1", trigger=CronTrigger(), workflow="missing",
        ))


# --- Cron firing -----------------------------------------------------------


def test_fire_cron_invokes_workflow() -> None:
    reg = _registry()
    reg.register_routine(Routine(
        name="daily-scan", trigger=CronTrigger(expression="0 17 * * *"),
        workflow="scan-issues",
    ))
    inv = reg.fire_cron("daily-scan", payload={"window": "today"})
    assert inv.trigger_kind is TriggerKind.CRON
    assert not inv.deferred
    assert reg.fired == [("daily-scan", {"window": "today"})]


def test_fire_cron_on_non_cron_routine_raises() -> None:
    reg = _registry()
    reg.register_routine(Routine(
        name="webhook-r", trigger=GitHubWebhookTrigger(repo="me/r", events=("push",)),
        workflow="scan-issues", secret=SECRET,
    ))
    with pytest.raises(ValueError, match="not cron-triggered"):
        reg.fire_cron("webhook-r")


# --- GitHub webhook firing -------------------------------------------------


def test_fire_github_webhook_admits_signed_request() -> None:
    reg = _registry()
    reg.register_routine(Routine(
        name="on-push", trigger=GitHubWebhookTrigger(repo="me/repo", events=("push",)),
        workflow="scan-issues", secret=SECRET,
    ))
    body = json.dumps({"action": "push"}).encode()
    inv = reg.fire_github_webhook(
        "on-push", body=body, signature=_sign_github(body),
        repo="me/repo", event="push",
    )
    assert inv.trigger_kind is TriggerKind.GITHUB_WEBHOOK
    assert reg.fired and reg.fired[0][1]["_event"] == "push"


def test_fire_github_webhook_refuses_bad_signature() -> None:
    reg = _registry()
    reg.register_routine(Routine(
        name="on-push", trigger=GitHubWebhookTrigger(repo="me/repo", events=("push",)),
        workflow="scan-issues", secret=SECRET,
    ))
    body = b'{"x":1}'
    with pytest.raises(RoutineAuthError):
        reg.fire_github_webhook(
            "on-push", body=body, signature="sha256=" + "0" * 64,
            repo="me/repo", event="push",
        )


def test_fire_github_webhook_refuses_unsubscribed_event() -> None:
    reg = _registry()
    reg.register_routine(Routine(
        name="on-push", trigger=GitHubWebhookTrigger(repo="me/repo", events=("push",)),
        workflow="scan-issues", secret=SECRET,
    ))
    body = b"{}"
    with pytest.raises(ValueError, match="does not subscribe"):
        reg.fire_github_webhook(
            "on-push", body=body, signature=_sign_github(body),
            repo="me/repo", event="issue_opened",
        )


# --- HTTP API firing -------------------------------------------------------


def test_fire_http_api_admits_signed_request() -> None:
    reg = _registry()
    reg.register_routine(Routine(
        name="api-fire", trigger=HttpApiTrigger(path="/routines/fire"),
        workflow="scan-issues", secret=SECRET,
    ))
    body = json.dumps({"hello": "world"}).encode()
    inv = reg.fire_http_api(
        "api-fire", body=body, signature=_sign_api(body),
    )
    assert inv.trigger_kind is TriggerKind.HTTP_API
    assert reg.fired == [("api-fire", {"hello": "world"})]


def test_fire_http_api_refuses_unsigned() -> None:
    reg = _registry()
    reg.register_routine(Routine(
        name="api-fire", trigger=HttpApiTrigger(),
        workflow="scan-issues", secret=SECRET,
    ))
    with pytest.raises(RoutineAuthError):
        reg.fire_http_api("api-fire", body=b"x", signature="0" * 64)


# --- LBL-ROUTINE-COST ------------------------------------------------------


def test_LBL_ROUTINE_COST_defers_over_envelope() -> None:
    reg = _registry()
    reg.cost_envelope = 1.5
    reg.register_routine(Routine(
        name="pricey", trigger=CronTrigger(),
        workflow="scan-issues", cost_per_firing=1.0,
    ))
    first = reg.fire_cron("pricey")
    assert not first.deferred
    second = reg.fire_cron("pricey")
    assert second.deferred
    assert second.bright_line == "LBL-ROUTINE-COST"
    assert reg.deferred_queue and reg.deferred_queue[0].routine_name == "pricey"
    # Workflow only fired once (the deferred firing did NOT execute).
    assert len(reg.fired) == 1


def test_replay_deferred_runs_when_envelope_has_headroom() -> None:
    reg = _registry()
    reg.cost_envelope = 1.5
    reg.register_routine(Routine(
        name="pricey", trigger=CronTrigger(),
        workflow="scan-issues", cost_per_firing=1.0,
    ))
    reg.fire_cron("pricey")        # cost 1.0
    reg.fire_cron("pricey")        # would push to 2.0, deferred
    assert len(reg.deferred_queue) == 1
    # Lift the envelope and replay.
    reg.cost_envelope = 10.0
    replayed = reg.replay_deferred()
    assert len(replayed) == 1
    assert not replayed[0].deferred
    assert reg.deferred_queue == []
    assert len(reg.fired) == 2


def test_unknown_routine_raises() -> None:
    reg = RoutineRegistry()
    with pytest.raises(KeyError):
        reg.fire_cron("ghost")
