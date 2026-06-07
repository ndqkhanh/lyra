"""
Tests for the Agent Mesh Protocol module (protocol.py).

Covers:
  - MeshProtocol: connection lifecycle, heartbeat, peer management
  - AgentDiscovery: discovery, gossip, capability queries
  - MeshRouter: route table, routing strategies, broadcast
  - MeshEncryption: key management, encrypt/decrypt, sign/verify
  - MeshSecurity: token auth, challenge-response, access control
"""

from __future__ import annotations

import time

import pytest

from lyra.agents_mesh.protocol import (
    AccessLevel,
    AccessRule,
    AgentDiscovery,
    AuthMethod,
    DiscoveryMethod,
    EncryptionScheme,
    MeshEncryption,
    MeshEnvelope,
    MeshIdentity,
    MeshProtocol,
    MeshProtocolState,
    MeshRouter,
    MeshSecurity,
    RouteEntry,
    RoutingStrategy,
)


# ======================================================================
# MeshProtocol
# ======================================================================


class TestMeshProtocol:
    def test_initial_state(self) -> None:
        proto = MeshProtocol("test-node")
        assert proto.node_id == "test-node"
        assert proto.state == MeshProtocolState.DISCONNECTED
        assert proto.peer_count() == 0

    def test_connect(self) -> None:
        proto = MeshProtocol("test-node")
        assert proto.connect() is True
        assert proto.state == MeshProtocolState.CONNECTED
        assert proto.is_connected() is True

    def test_double_connect(self) -> None:
        proto = MeshProtocol("test-node")
        proto.connect()
        assert proto.connect() is True  # idempotent

    def test_disconnect(self) -> None:
        proto = MeshProtocol("test-node")
        proto.connect()
        assert proto.disconnect() is True
        assert proto.state == MeshProtocolState.DISCONNECTED

    def test_peer_management(self) -> None:
        proto = MeshProtocol("test-node")
        proto.register_peer("peer-a")
        proto.register_peer("peer-b")
        assert proto.peer_count() == 2
        assert "peer-a" in proto.get_peers()

        assert proto.unregister_peer("peer-a") is True
        assert proto.peer_count() == 1
        assert proto.unregister_peer("ghost") is False

    def test_heartbeat(self) -> None:
        proto = MeshProtocol("test-node")
        proto.connect()
        hb = proto.send_heartbeat()
        assert hb["type"] == "heartbeat"
        assert hb["node_id"] == "test-node"

        proto.receive_heartbeat("peer-a")
        proto.receive_heartbeat("peer-b")
        assert proto.peer_count() == 2

    def test_heartbeat_timing(self) -> None:
        proto = MeshProtocol("test-node", heartbeat_interval=0.1)
        assert proto.should_send_heartbeat() is True
        proto.send_heartbeat()
        assert proto.should_send_heartbeat() is False

    def test_stale_peers(self) -> None:
        proto = MeshProtocol("test-node", node_timeout=-1)
        proto.register_peer("peer-a")
        assert len(proto.get_stale_peers()) == 1

    def test_send_receive_message(self) -> None:
        proto = MeshProtocol("test-node")
        msg_id = proto.send_message("target-a", {"data": 42}, "test_msg")
        assert len(msg_id) > 0

        msgs = proto.receive_messages()
        assert len(msgs) == 1
        assert msgs[0]["target"] == "target-a"

    def test_receive_filtered(self) -> None:
        proto = MeshProtocol("test-node")
        proto.send_message("t1", {"x": 1}, "type_a")
        proto.send_message("t2", {"x": 2}, "type_b")
        assert len(proto.receive_messages(msg_type="type_a")) == 1

    def test_register_handler(self) -> None:
        proto = MeshProtocol("test-node")
        called = False

        def handler(msg: dict) -> None:
            nonlocal called
            called = True

        proto.register_handler("custom", handler)
        assert "custom" in proto._handlers

    def get_statistics(self, proto: MeshProtocol) -> None:
        proto.connect()
        stats = proto.get_statistics()
        assert stats["node_id"] == "test-node"
        assert stats["state"] == "connected"


# ======================================================================
# AgentDiscovery
# ======================================================================


class TestAgentDiscovery:
    def test_initial_state(self) -> None:
        discovery = AgentDiscovery("agent-a")
        assert discovery.local_agent_id == "agent-a"
        assert discovery.agent_count() == 0

    def test_announce(self) -> None:
        discovery = AgentDiscovery("agent-a")
        ann = discovery.announce()
        assert ann["type"] == "discovery_announce"
        assert ann["agent_id"] == "agent-a"

    def test_discover_new_agent(self) -> None:
        discovery = AgentDiscovery("agent-a")
        identity = MeshIdentity(
            agent_id="agent-b",
            capabilities=["planning", "execution"],
        )
        assert discovery.discover("agent-b", identity) is True
        assert discovery.agent_count() == 1

    def test_discover_duplicate(self) -> None:
        discovery = AgentDiscovery("agent-a")
        discovery.discover("agent-b")
        assert discovery.discover("agent-b") is False  # not new

    def test_forget_agent(self) -> None:
        discovery = AgentDiscovery("agent-a")
        discovery.discover("agent-b")
        assert discovery.forget("agent-b") is True
        assert discovery.forget("ghost") is False

    def test_find_by_capability(self) -> None:
        discovery = AgentDiscovery("agent-a")
        discovery.discover("b", MeshIdentity(agent_id="b", capabilities=["research"]))
        discovery.discover("c", MeshIdentity(agent_id="c", capabilities=["planning"]))
        assert "b" in discovery.find_by_capability("research")
        assert "c" not in discovery.find_by_capability("research")

    def test_find_by_name(self) -> None:
        discovery = AgentDiscovery("agent-a")
        discovery.discover("agent-b1")
        discovery.discover("helper-c")
        assert len(discovery.find_by_name("agent-")) == 1

    def test_gossip_messages(self) -> None:
        discovery = AgentDiscovery("agent-a", gossip_fanout=2)
        discovery.discover("b", MeshIdentity(agent_id="b", capabilities=["x"]))
        discovery.discover("c", MeshIdentity(agent_id="c", capabilities=["y"]))
        gossip_msgs = discovery.gossip()
        assert len(gossip_msgs) > 0
        assert gossip_msgs[0]["type"] == "gossip"

    def test_receive_gossip(self) -> None:
        discovery = AgentDiscovery("agent-a")
        msg = {"about": "new-agent", "capabilities": ["test"]}
        assert discovery.receive_gossip(msg) is True
        assert discovery.agent_count() == 1

    def test_get_active_agents(self) -> None:
        discovery = AgentDiscovery("agent-a", node_timeout=3600)
        discovery.discover("b")
        assert len(discovery.get_active_agents()) == 1

    def test_on_discovery_listener(self) -> None:
        discovery = AgentDiscovery("agent-a")
        discovered: list[str] = []

        def listener(aid: str, _identity: MeshIdentity) -> None:
            discovered.append(aid)

        discovery.on_discovery(listener)
        discovery.discover("new-agent")
        assert "new-agent" in discovered

    def test_get_statistics(self) -> None:
        discovery = AgentDiscovery("agent-a")
        discovery.discover("b")
        stats = discovery.get_statistics()
        assert stats["discovered"] == 1
        assert stats["local_agent"] == "agent-a"


# ======================================================================
# MeshRouter
# ======================================================================


class TestMeshRouter:
    def test_initial_state(self) -> None:
        router = MeshRouter("node-a")
        assert router.route_count() == 0
        assert router.local_node_id == "node-a"

    def test_add_route(self) -> None:
        router = MeshRouter("node-a")
        assert router.add_route("target-b", "next-hop-c", cost=1.5) is True
        assert router.route_count() == 1

    def test_get_route(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("target-b", "next-hop-c", cost=1.5)
        entry = router.get_route("target-b")
        assert entry is not None
        assert entry.next_hop == "next-hop-c"
        assert entry.cost == 1.5

    def test_get_expired_route(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("target-b", "next-hop-c", ttl=0.001)
        time.sleep(0.002)
        assert router.get_route("target-b") is None

    def test_remove_route(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("target-b", "next-hop-c")
        assert router.remove_route("target-b") is True
        assert router.remove_route("ghost") is False

    def test_route_direct(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("target-b", "target-b", cost=1.0)
        result = router.route("target-b", {"msg": "hello"})
        assert result["target"] == "target-b"
        assert result["source"] == "node-a"

    def test_route_broadcast(self) -> None:
        router = MeshRouter("node-a")
        result = router.route("*", {"msg": "broadcast"}, strategy=RoutingStrategy.BROADCAST)
        assert result["target"] == "*"
        assert result["strategy"] == "broadcast"

    def test_route_unreachable_raises(self) -> None:
        router = MeshRouter("node-a")
        with pytest.raises(ValueError, match="unreachable"):
            router.route("ghost", {"msg": "x"})

    def test_prune_expired(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("a", "hop-a", ttl=0.001)
        router.add_route("b", "hop-b", ttl=300)
        time.sleep(0.002)
        pruned = router.prune_expired()
        assert pruned == 1
        assert router.route_count() == 1

    def test_clear_routes(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("a", "hop-a")
        router.add_route("b", "hop-b")
        router.clear_routes()
        assert router.route_count() == 0

    def test_route_history(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("b", "b")
        router.route("b", {"msg": "hello"})
        assert len(router.get_history()) == 1

    def test_get_statistics(self) -> None:
        router = MeshRouter("node-a")
        router.add_route("b", "b")
        stats = router.get_statistics()
        assert stats["local_node"] == "node-a"
        assert stats["routes"] >= 1


# ======================================================================
# MeshEncryption
# ======================================================================


class TestMeshEncryption:
    def test_key_generation(self) -> None:
        enc = MeshEncryption("agent-a")
        key = enc.generate_key(16)
        assert len(key) == 16

    def test_store_and_get_key(self) -> None:
        enc = MeshEncryption("agent-a")
        key = enc.generate_key()
        enc.store_key("test-key", key)
        assert enc.get_key("test-key") == key
        assert enc.get_key("nonexistent") is None

    def test_derive_key(self) -> None:
        enc = MeshEncryption("agent-a")
        key = enc.derive_key("passphrase")
        assert len(key) == 32  # DEFAULT_KEY_SIZE_BYTES

    def test_encrypt_decrypt_roundtrip(self) -> None:
        enc = MeshEncryption("agent-a")
        key = enc.generate_key()
        enc.store_key("k1", key)
        env = enc.encrypt("Hello, mesh!", key_id="k1")
        assert env.sender_id == "agent-a"
        assert env.scheme == EncryptionScheme.AES_GCM

        plain = enc.decrypt(env, key_id="k1")
        assert plain == "Hello, mesh!"

    def test_encrypt_no_encryption(self) -> None:
        enc = MeshEncryption("agent-a")
        env = enc.encrypt("plaintext", scheme=EncryptionScheme.NONE)
        assert env.scheme == EncryptionScheme.NONE
        assert enc.decrypt(env) == "plaintext"

    def test_encrypt_missing_key_raises(self) -> None:
        enc = MeshEncryption("agent-a")
        with pytest.raises(ValueError, match="not found"):
            enc.encrypt("data", key_id="missing")

    def test_decrypt_wrong_key_raises(self) -> None:
        enc = MeshEncryption("agent-a")
        k1 = enc.generate_key()
        enc.store_key("k1", k1)
        env = enc.encrypt("secret", key_id="k1")
        with pytest.raises(ValueError, match="not found"):
            enc.decrypt(env, key_id="wrong-key")

    def test_sign_verify(self) -> None:
        enc = MeshEncryption("agent-a")
        key = enc.generate_key()
        enc.store_key("k1", key)
        sig = enc.sign("payload-data", "k1")
        assert enc.verify("payload-data", sig, "k1") is True
        assert enc.verify("tampered", sig, "k1") is False

    def test_get_statistics(self) -> None:
        enc = MeshEncryption("agent-a")
        enc.generate_key()
        stats = enc.get_statistics()
        assert stats["local_agent"] == "agent-a"
        assert stats["default_scheme"] == "aes_gcm"


# ======================================================================
# MeshSecurity
# ======================================================================


class TestMeshSecurity:
    def test_issue_and_validate_token(self) -> None:
        sec = MeshSecurity("hub")
        token = sec.issue_token("agent-b")
        assert sec.validate_token("agent-b", token) is True
        assert sec.validate_token("agent-b", "wrong-token") is False

    def test_revoke_token(self) -> None:
        sec = MeshSecurity("hub")
        sec.issue_token("agent-b")
        assert sec.revoke_token("agent-b") is True
        assert sec.validate_token("agent-b", "any-token") is False

    def test_authenticate_with_token(self) -> None:
        sec = MeshSecurity("hub")
        token = sec.issue_token("agent-b")
        assert sec.authenticate("agent-b", token) is True
        assert sec.is_authenticated("agent-b") is True

    def test_authenticate_failure(self) -> None:
        sec = MeshSecurity("hub")
        assert sec.authenticate("agent-b", "bad-token") is False
        assert sec.is_authenticated("agent-b") is False

    def test_authenticate_rate_limiting(self) -> None:
        sec = MeshSecurity("hub")
        sec.set_max_auth_attempts(3)
        for _ in range(3):
            sec.authenticate("attacker", "bad")
        assert sec.authenticate("attacker", "bad") is False  # rate limited

    def test_deauthenticate(self) -> None:
        sec = MeshSecurity("hub")
        token = sec.issue_token("agent-b")
        sec.authenticate("agent-b", token)
        assert sec.deauthenticate("agent-b") is True
        assert sec.is_authenticated("agent-b") is False

    def test_access_levels(self) -> None:
        sec = MeshSecurity("hub")
        token = sec.issue_token("agent-b")
        sec.authenticate("agent-b", token)
        assert sec.get_access_level("agent-b") == AccessLevel.READ

        sec.set_access_level("agent-b", AccessLevel.ADMIN)
        assert sec.get_access_level("agent-b") == AccessLevel.ADMIN

    def test_check_access(self) -> None:
        sec = MeshSecurity("hub")
        token = sec.issue_token("agent-b")
        sec.authenticate("agent-b", token)
        sec.set_access_level("agent-b", AccessLevel.WRITE)
        assert sec.check_access("agent-b", AccessLevel.READ) is True
        assert sec.check_access("agent-b", AccessLevel.ADMIN) is False

    def test_set_access_level_unauthenticated_raises(self) -> None:
        sec = MeshSecurity("hub")
        with pytest.raises(ValueError, match="unauthenticated"):
            sec.set_access_level("ghost", AccessLevel.ADMIN)

    def test_access_rules(self) -> None:
        sec = MeshSecurity("hub")
        rule = AccessRule(
            rule_id="r1",
            agent_pattern="agent-*",
            operation="send_message",
            allowed=True,
            priority=10,
        )
        sec.add_access_rule(rule)
        matching = sec.evaluate_rules("agent-b", "send_message")
        assert len(matching) == 1
        assert matching[0].rule_id == "r1"

    def test_access_rule_matches(self) -> None:
        rule = AccessRule(rule_id="r1", agent_pattern="*", operation="*")
        assert rule.matches("any-agent", "any-op") is True
        assert rule.matches("any-agent", "any-op", "resource-x") is True

    def test_access_rule_no_match(self) -> None:
        rule = AccessRule(rule_id="r1", agent_pattern="specific-*", operation="read")
        assert rule.matches("other-agent", "read") is False
        assert rule.matches("specific-1", "write") is False

    def test_get_statistics(self) -> None:
        sec = MeshSecurity("hub")
        token = sec.issue_token("agent-b")
        sec.authenticate("agent-b", token)
        stats = sec.get_statistics()
        assert stats["authenticated_agents"] == 1
        assert stats["active_tokens"] == 1
