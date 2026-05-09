"""Remote-control bridge tests (v3.7 L37-1)."""
from __future__ import annotations

import pytest

from lyra_core.acp.remote_control import (
    AttachToken,
    RelayHub,
    RemoteAuthError,
    RemoteScopeError,
    RemoteSession,
    issue_token,
    verify_token,
)


SECRET = b"test-secret-32-bytes-________"


def _session(session_id: str = "sess-1") -> RemoteSession:
    return RemoteSession(
        session_id=session_id, secret=SECRET,
        pre_approved_kinds=frozenset({"read", "lint"}),
    )


# --- Token round-trip ------------------------------------------------------


def test_issue_and_verify_token_round_trip() -> None:
    token = issue_token(session_id="sess-1", secret=SECRET)
    verify_token(token, secret=SECRET)        # no exception


def test_verify_rejects_bad_signature() -> None:
    token = issue_token(session_id="sess-1", secret=SECRET)
    tampered = AttachToken(
        session_id=token.session_id, nonce=token.nonce,
        issued_ts=token.issued_ts, ttl_s=token.ttl_s,
        signature="0" * 64,
    )
    with pytest.raises(RemoteAuthError, match="LBL-RC-AUTH.*HMAC"):
        verify_token(tampered, secret=SECRET)


def test_verify_rejects_expired_token() -> None:
    token = issue_token(
        session_id="sess-1", secret=SECRET, ttl_s=10.0, now_ts=1000.0,
    )
    with pytest.raises(RemoteAuthError, match="LBL-RC-AUTH.*expired"):
        verify_token(token, secret=SECRET, now_ts=2000.0)


# --- Attach / detach / scope -----------------------------------------------


def test_attach_with_valid_token_returns_channel() -> None:
    sess = _session()
    token = sess.issue_attach_token()
    ch = sess.attach(token)
    assert ch.open
    assert ch.session_id == "sess-1"


def test_attach_rejects_replay() -> None:
    sess = _session()
    token = sess.issue_attach_token()
    sess.attach(token)
    with pytest.raises(RemoteAuthError, match="replay refused"):
        sess.attach(token)


def test_attach_rejects_session_id_mismatch() -> None:
    sess = _session("sess-1")
    other_token = issue_token(session_id="sess-2", secret=SECRET)
    with pytest.raises(RemoteAuthError, match="session_id mismatch"):
        sess.attach(other_token)


def test_relay_admits_pre_approved_action_kind() -> None:
    sess = _session()
    ch = sess.attach(sess.issue_attach_token())
    sess.relay(ch.channel_id, action_kind="read", message={"path": "x"})
    assert len(ch.history) == 1
    assert ch.history[0]["action_kind"] == "read"


def test_relay_refuses_action_kind_outside_scope() -> None:
    sess = _session()
    ch = sess.attach(sess.issue_attach_token())
    with pytest.raises(RemoteScopeError, match="LBL-RC-SCOPE"):
        sess.relay(ch.channel_id, action_kind="bash", message={"cmd": "rm"})


def test_relay_refuses_after_detach() -> None:
    sess = _session()
    ch = sess.attach(sess.issue_attach_token())
    sess.detach(ch.channel_id)
    with pytest.raises(RemoteScopeError):
        sess.relay(ch.channel_id, action_kind="read", message={})


# --- RelayHub --------------------------------------------------------------


def test_relay_hub_register_and_lookup() -> None:
    hub = RelayHub()
    sess = _session("sess-a")
    hub.register(sess)
    assert hub.get("sess-a") is sess
    assert "sess-a" in hub.all_session_ids()


def test_relay_hub_duplicate_register_raises() -> None:
    hub = RelayHub()
    hub.register(_session("sess-a"))
    with pytest.raises(ValueError):
        hub.register(_session("sess-a"))
