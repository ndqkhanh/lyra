"""Tests for Zero-Trust Federation — cross-agent identity and authorization."""

import time

import pytest

from lyra_agent_swarm.zero_trust_federation import (
    AuthDecision,
    AuthStatus,
    Capability,
    FederationConfig,
    FederationIdentity,
    FederationLevel,
    FederationRegistry,
    ZeroTrustFederation,
)


class TestFederationLevel:
    def test_level_values(self):
        assert FederationLevel.ISOLATED.value == "isolated"
        assert FederationLevel.RESTRICTED.value == "restricted"
        assert FederationLevel.STANDARD.value == "standard"
        assert FederationLevel.ELEVATED.value == "elevated"

    def test_four_levels(self):
        assert len(FederationLevel) == 4


class TestAuthStatus:
    def test_status_values(self):
        assert AuthStatus.ALLOWED.value == "allowed"
        assert AuthStatus.DENIED.value == "denied"
        assert AuthStatus.EXPIRED.value == "expired"
        assert AuthStatus.REVOKED.value == "revoked"


class TestFederationIdentity:
    def test_identity_creation(self):
        identity = FederationIdentity(
            agent_id="agent-007",
            public_key_hash="abc123def456",
            federation_level=FederationLevel.STANDARD,
            registered_at=time.time(),
            last_seen=time.time(),
        )
        assert identity.agent_id == "agent-007"
        assert identity.federation_level == FederationLevel.STANDARD

    def test_identity_elevated(self):
        identity = FederationIdentity(
            agent_id="admin-agent",
            public_key_hash="admin_hash",
            federation_level=FederationLevel.ELEVATED,
            registered_at=time.time(),
            last_seen=time.time(),
        )
        assert identity.federation_level == FederationLevel.ELEVATED

    def test_identity_immutable(self):
        i = FederationIdentity("a1", "hash", FederationLevel.STANDARD, 0.0, 0.0)
        with pytest.raises(Exception):
            i.federation_level = FederationLevel.ELEVATED


class TestCapability:
    def test_capability_creation(self):
        cap = Capability(
            capability_id="cap-001",
            issuer="orchestrator",
            holder="worker-1",
            action="deploy",
            resource="production",
            issued_at=time.time(),
            expires_at=time.time() + 3600,
            max_uses=3,
            use_count=0,
            signature="sig123",
        )
        assert cap.capability_id == "cap-001"
        assert cap.issuer == "orchestrator"
        assert cap.action == "deploy"
        assert cap.max_uses == 3

    def test_capability_single_use(self):
        cap = Capability(
            capability_id="cap-once",
            issuer="admin",
            holder="agent",
            action="read_config",
            resource="config",
            issued_at=time.time(),
            expires_at=time.time() + 600,
            max_uses=1,
            use_count=0,
            signature="s1",
        )
        assert cap.max_uses == 1

    def test_capability_immutable(self):
        c = Capability("c1", "issuer", "holder", "read", "*", 0.0, 3600.0, 1, 0, "sig")
        with pytest.raises(Exception):
            c.use_count = 5


class TestAuthDecision:
    def test_allowed_decision(self):
        decision = AuthDecision(
            allowed=True,
            reason="Authorized for read_metrics",
            agent_id="agent-1",
            action="read_metrics",
            status=AuthStatus.ALLOWED,
        )
        assert decision.allowed is True
        assert decision.status == AuthStatus.ALLOWED

    def test_denied_decision(self):
        decision = AuthDecision(
            allowed=False,
            reason="Insufficient federation level",
            agent_id="agent-2",
            action="deploy",
            status=AuthStatus.DENIED,
        )
        assert decision.allowed is False
        assert decision.status == AuthStatus.DENIED

    def test_decision_immutable(self):
        d = AuthDecision(True, "ok", "a1", "read", AuthStatus.ALLOWED)
        with pytest.raises(Exception):
            d.allowed = False


class TestFederationConfig:
    def test_default_config(self):
        config = FederationConfig()
        assert config.session_timeout_sec == 3600.0
        assert config.max_capability_depth == 3
        assert config.require_mtls is False

    def test_custom_config(self):
        config = FederationConfig(session_timeout_sec=600.0, require_mtls=True)
        assert config.session_timeout_sec == 600.0
        assert config.require_mtls is True


class TestFederationRegistry:
    def test_register_agent(self):
        registry = FederationRegistry()
        identity = registry.register("agent-1", "pubkey123")
        assert identity.agent_id == "agent-1"
        assert registry.agent_count == 1

    def test_register_multiple_agents(self):
        registry = FederationRegistry()
        registry.register("a1", "pk1")
        registry.register("a2", "pk2")
        registry.register("a3", "pk3")
        assert registry.agent_count == 3

    def test_get_identity_exists(self):
        registry = FederationRegistry()
        registry.register("agent-x", "pubkey-x")
        identity = registry.get_identity("agent-x")
        assert identity is not None
        assert identity.agent_id == "agent-x"

    def test_get_identity_missing(self):
        registry = FederationRegistry()
        identity = registry.get_identity("nonexistent")
        assert identity is None

    def test_revoke_agent(self):
        registry = FederationRegistry()
        registry.register("agent-r", "pk-r")
        registry.revoke("agent-r")
        identity = registry.get_identity("agent-r")
        assert identity is None

    def test_heartbeat_updates_last_seen(self):
        registry = FederationRegistry()
        identity = registry.register("agent-hb", "pk-hb")
        old_seen = identity.last_seen
        time.sleep(0.01)
        registry.heartbeat("agent-hb")
        updated = registry.get_identity("agent-hb")
        assert updated is not None
        assert updated.last_seen >= old_seen

    def test_heartbeat_unknown_agent(self):
        registry = FederationRegistry()
        registry.heartbeat("no-such-agent")

    def test_register_with_level(self):
        registry = FederationRegistry()
        identity = registry.register("elevated-agent", "pk-e", level=FederationLevel.ELEVATED)
        assert identity.federation_level == FederationLevel.ELEVATED


class TestZeroTrustFederation:
    def test_authorize_registered_agent(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("worker-1", "pk1", level=FederationLevel.STANDARD)
        decision = ztf.authorize("worker-1", "read_metrics")
        assert decision.allowed is True

    def test_authorize_unregistered_agent(self):
        ztf = ZeroTrustFederation()
        decision = ztf.authorize("unknown-agent", "read_metrics")
        assert decision.allowed is False
        assert decision.status == AuthStatus.DENIED

    def test_authorize_revoked_agent(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("traitor", "pk-bad")
        ztf.registry.revoke("traitor")
        decision = ztf.authorize("traitor", "read_metrics")
        assert decision.allowed is False
        assert decision.status in (AuthStatus.DENIED, AuthStatus.REVOKED)

    def test_authorize_elevated_action_requires_elevated_level(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("basic-agent", "pk-basic", level=FederationLevel.STANDARD)
        decision = ztf.authorize("basic-agent", "deploy")
        assert decision.allowed is False

    def test_authorize_elevated_action_with_elevated_level(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("admin-agent", "pk-admin", level=FederationLevel.ELEVATED)
        decision = ztf.authorize("admin-agent", "deploy")
        assert decision.allowed is True

    def test_session_timeout(self):
        config = FederationConfig(session_timeout_sec=0.0)
        ztf = ZeroTrustFederation(config=config)
        ztf.registry.register("timed-out", "pk-to", level=FederationLevel.STANDARD)
        decision = ztf.authorize("timed-out", "read_metrics")
        assert decision.status == AuthStatus.EXPIRED

    def test_issue_capability(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("issuer", "pk-iss", level=FederationLevel.ELEVATED)
        ztf.registry.register("holder", "pk-hold")
        cap = ztf.issue_capability("issuer", "holder", "read_metrics", "*")
        assert isinstance(cap, Capability)
        assert cap.issuer == "issuer"
        assert cap.holder == "holder"

    def test_verify_valid_capability(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("issuer", "pk-i", level=FederationLevel.ELEVATED)
        ztf.registry.register("holder", "pk-h")
        cap = ztf.issue_capability("issuer", "holder", "read_metrics", "*", max_uses=5)
        decision = ztf.verify_capability(cap.capability_id)
        assert decision.allowed is True

    def test_verify_unknown_capability(self):
        ztf = ZeroTrustFederation()
        decision = ztf.verify_capability("bogus-cap-id")
        assert decision.allowed is False

    def test_verify_expired_capability(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("issuer", "pk-i", level=FederationLevel.ELEVATED)
        ztf.registry.register("holder", "pk-h")
        cap = ztf.issue_capability("issuer", "holder", "read", "*", ttl_sec=-1)
        decision = ztf.verify_capability(cap.capability_id)
        assert decision.allowed is False

    def test_capability_use_count_exhausted(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("issuer", "pk-i", level=FederationLevel.ELEVATED)
        ztf.registry.register("holder", "pk-h")
        cap = ztf.issue_capability("issuer", "holder", "read", "*", max_uses=1)
        first = ztf.verify_capability(cap.capability_id)
        assert first.allowed is True
        second = ztf.verify_capability(cap.capability_id)
        assert second.allowed is False

    def test_stats(self):
        ztf = ZeroTrustFederation()
        ztf.registry.register("agent", "pk", level=FederationLevel.STANDARD)
        ztf.authorize("agent", "read_metrics")
        stats = ztf.stats()
        assert "agents" in stats
        assert "allowed" in stats
        assert "denied" in stats
        assert "capabilities_issued" in stats
