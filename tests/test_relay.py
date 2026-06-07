"""Tests for Lyra relay server."""

import time
from lyra.server.relay import RelayServer, RelayCredential, SessionStatus


class TestRelayCredential:
    """Credential lifecycle tests."""

    def test_not_expired(self):
        cred = RelayCredential(
            token="test-token",
            purpose="register",
            session_id=None,
            expires_at=time.time() + 3600,
        )
        assert not cred.is_expired

    def test_expired(self):
        cred = RelayCredential(
            token="test-token",
            purpose="register",
            session_id=None,
            expires_at=time.time() - 1,
        )
        assert cred.is_expired


class TestRelayServer:
    """Relay server tests."""

    def test_register_session(self):
        relay = RelayServer(secret_key="test-key")
        reg_cred = relay.issue_registration_credential()
        session_id, attach_cred = relay.register_session(
            name="Test Session",
            credential=reg_cred,
        )
        assert session_id.startswith("lyra-")
        assert len(attach_cred) > 0

    def test_get_session(self):
        relay = RelayServer(secret_key="test-key")
        reg_cred = relay.issue_registration_credential()
        session_id, _ = relay.register_session("Test", reg_cred)

        session = relay.get_session(session_id)
        assert session is not None
        assert session.name == "Test"
        assert session.status == SessionStatus.ONLINE

    def test_list_sessions(self):
        relay = RelayServer(secret_key="test-key")
        cred1 = relay.issue_registration_credential()
        relay.register_session("Session A", cred1)
        cred2 = relay.issue_registration_credential()
        relay.register_session("Session B", cred2)

        sessions = relay.list_sessions()
        assert len(sessions) == 2
        names = {s["name"] for s in sessions}
        assert names == {"Session A", "Session B"}

    def test_invalid_credential_raises(self):
        relay = RelayServer(secret_key="test-key")
        try:
            relay.register_session("Test", "invalid-credential")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_expired_credential_raises(self):
        relay = RelayServer(secret_key="test-key")
        cred = RelayCredential(
            token="expired",
            purpose="register",
            session_id=None,
            expires_at=time.time() - 1,
        )
        relay._credentials["expired"] = cred
        try:
            relay.register_session("Test", "expired")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_heartbeat(self):
        relay = RelayServer(secret_key="test-key")
        reg_cred = relay.issue_registration_credential()
        session_id, _ = relay.register_session("Test", reg_cred)

        session = relay.get_session(session_id)
        old_heartbeat = session.last_heartbeat

        time.sleep(0.01)
        relay.heartbeat(session_id)

        assert relay.get_session(session_id).last_heartbeat > old_heartbeat

    def test_heartbeat_unknown_session(self):
        relay = RelayServer(secret_key="test-key")
        relay.heartbeat("nonexistent")  # Should not raise

    def test_cleanup_timeouts(self):
        relay = RelayServer(secret_key="test-key")
        reg_cred = relay.issue_registration_credential()
        session_id, _ = relay.register_session("Test", reg_cred)

        # Artificially age the session
        session = relay.get_session(session_id)
        session.last_heartbeat = time.time() - 3600  # 1 hour ago

        import asyncio
        timed_out = asyncio.get_event_loop().run_until_complete(
            relay.cleanup_timeouts()
        )
        assert session_id in timed_out
        assert relay.get_session(session_id).status == SessionStatus.TIMEOUT

    def test_remove_session(self):
        relay = RelayServer(secret_key="test-key")
        admin_cred = relay.issue_admin_credential()
        reg_cred = relay.issue_registration_credential()
        session_id, _ = relay.register_session("Test", reg_cred)

        relay.remove_session(session_id, admin_cred)
        assert relay.get_session(session_id) is None

    def test_verify_attach(self):
        relay = RelayServer(secret_key="test-key")
        reg_cred = relay.issue_registration_credential()
        session_id, attach_cred = relay.register_session("Test", reg_cred)

        assert relay.verify_attach(session_id, attach_cred)
        assert not relay.verify_attach(session_id, "wrong-credential")
        assert not relay.verify_attach("wrong-session", attach_cred)

    def test_generate_session_url(self):
        url = RelayServer.generate_session_url(
            "lyra.example.com", "session-123", "cred-abc"
        )
        assert "lyra.example.com" in url
        assert "session-123" in url
        assert "cred-abc" in url

    def test_unique_session_ids(self):
        relay = RelayServer(secret_key="test-key")
        ids = set()
        for _ in range(10):
            cred = relay.issue_registration_credential()
            sid, _ = relay.register_session(f"Test-{_}", cred)
            ids.add(sid)
        assert len(ids) == 10  # All unique
