"""Tests for harness_core.distributed."""
from __future__ import annotations

import pytest

from harness_core.distributed import (
    Bus,
    Envelope,
    Subscription,
    topic_matches,
)
from harness_core.provenance import WitnessLattice


# --- topic_matches ---------------------------------------------------


class TestTopicMatches:
    def test_exact_match(self):
        assert topic_matches("agent.alice", "agent.alice")
        assert not topic_matches("agent.alice", "agent.bob")

    def test_single_segment_wildcard(self):
        assert topic_matches("agent.*", "agent.alice")
        assert topic_matches("agent.*", "agent.bob")
        assert not topic_matches("agent.*", "agent.alice.x")
        assert not topic_matches("agent.*", "agent")

    def test_tail_wildcard(self):
        assert topic_matches("agent.>", "agent.alice")
        assert topic_matches("agent.>", "agent.alice.x.y")
        assert not topic_matches("agent.>", "agent")  # > requires at least 1
        assert not topic_matches("agent.>", "other.alice")

    def test_mixed_wildcard(self):
        assert topic_matches("a.*.c", "a.b.c")
        assert not topic_matches("a.*.c", "a.b.d")
        assert not topic_matches("a.*.c", "a.b.c.d")  # length mismatch

    def test_empty_inputs(self):
        assert not topic_matches("", "a.b")
        assert not topic_matches("a.b", "")


# --- Bus pub/sub -----------------------------------------------------


class TestBusBasic:
    def test_publish_to_no_subscribers(self):
        bus = Bus()
        env = bus.publish(topic="agent.alice", payload={"x": 1})
        assert isinstance(env, Envelope)
        assert env.topic == "agent.alice"
        assert env.payload == {"x": 1}
        assert bus.history() == [env]

    def test_subscribe_and_receive(self):
        bus = Bus()
        received: list[Envelope] = []
        sub = bus.subscribe("agent.*", lambda e: received.append(e))
        bus.publish(topic="agent.alice", payload={"hi": True})
        bus.publish(topic="agent.bob", payload={"hi": True})
        bus.publish(topic="other.charlie", payload={"hi": True})
        assert len(received) == 2
        assert received[0].topic == "agent.alice"
        assert received[1].topic == "agent.bob"
        assert isinstance(sub, Subscription)
        assert sub.active

    def test_unsubscribe(self):
        bus = Bus()
        received: list[Envelope] = []
        sub = bus.subscribe("agent.*", lambda e: received.append(e))
        bus.publish(topic="agent.alice", payload={})
        sub.unsubscribe()
        bus.publish(topic="agent.bob", payload={})
        assert len(received) == 1
        assert not sub.active
        assert bus.n_subscriptions() == 0

    def test_multiple_subscribers_all_called(self):
        bus = Bus()
        a, b = [], []
        bus.subscribe("agent.*", lambda e: a.append(e))
        bus.subscribe("agent.*", lambda e: b.append(e))
        bus.publish(topic="agent.alice", payload={})
        assert len(a) == 1 and len(b) == 1

    def test_tail_wildcard_subscriber(self):
        bus = Bus()
        received: list[str] = []
        bus.subscribe("agent.>", lambda e: received.append(e.topic))
        bus.publish(topic="agent.alice", payload={})
        bus.publish(topic="agent.bob.metric", payload={})
        bus.publish(topic="other.charlie", payload={})
        assert received == ["agent.alice", "agent.bob.metric"]

    def test_history_filter(self):
        bus = Bus()
        bus.publish(topic="agent.alice", payload={})
        bus.publish(topic="agent.bob", payload={})
        bus.publish(topic="other.charlie", payload={})
        agents = bus.history(topic_pattern="agent.*")
        assert len(agents) == 2
        all_envs = bus.history()
        assert len(all_envs) == 3

    def test_subscribe_empty_topic_rejected(self):
        with pytest.raises(ValueError):
            Bus().subscribe("", lambda e: None)


# --- Namespace isolation ---------------------------------------------


class TestNamespace:
    def test_namespace_prefix_applied(self):
        bus = Bus(namespace="proj-a")
        env = bus.publish(topic="agent.alice", payload={})
        assert env.topic == "proj-a.agent.alice"

    def test_namespace_preserves_already_prefixed(self):
        bus = Bus(namespace="proj-a")
        env = bus.publish(topic="proj-a.agent.alice", payload={})
        # No double-prefix.
        assert env.topic == "proj-a.agent.alice"

    def test_namespace_subscription_scoped(self):
        bus = Bus(namespace="proj-a")
        received: list[Envelope] = []
        bus.subscribe("agent.*", lambda e: received.append(e))
        bus.publish(topic="agent.alice", payload={})
        assert len(received) == 1
        # The subscription pattern was also namespace-prefixed.
        assert received[0].topic == "proj-a.agent.alice"

    def test_two_buses_with_different_namespaces_isolated(self):
        # Each bus is its own router; namespaces just keep topics tidy
        # within. Two distinct buses don't share state at all.
        bus_a = Bus(namespace="proj-a")
        bus_b = Bus(namespace="proj-b")
        a, b = [], []
        bus_a.subscribe("agent.*", lambda e: a.append(e))
        bus_b.subscribe("agent.*", lambda e: b.append(e))
        bus_a.publish(topic="agent.alice", payload={})
        assert len(a) == 1
        assert len(b) == 0


# --- Request/reply ---------------------------------------------------


class TestRequestReply:
    def test_inline_reply_returns_envelope(self):
        bus = Bus()

        def echo_handler(env: Envelope):
            bus.reply(to=env, payload={"echoed": env.payload}, issued_by="echo")

        bus.subscribe("rpc.echo", echo_handler)
        reply = bus.request(
            topic="rpc.echo",
            payload={"hello": "world"},
            timeout=1.0,
        )
        assert reply is not None
        assert reply.payload["echoed"] == {"hello": "world"}
        assert reply.issued_by == "echo"

    def test_no_reply_returns_none(self):
        bus = Bus()

        def silent_handler(env: Envelope):
            return None  # no reply

        bus.subscribe("rpc.silent", silent_handler)
        # With no inline reply and 0 timeout, request returns None.
        out = bus.request(topic="rpc.silent", payload={}, timeout=0.0)
        assert out is None

    def test_correlation_id_propagates(self):
        bus = Bus()

        def echo_handler(env: Envelope):
            bus.reply(to=env, payload={"x": 1}, issued_by="echo")

        bus.subscribe("rpc.echo", echo_handler)
        reply = bus.request(topic="rpc.echo", payload={}, timeout=1.0)
        assert reply.correlation_id is not None

    def test_inbox_is_unique_per_request(self):
        bus = Bus()
        # No reply path so we can inspect the request envelope's reply_to.
        bus.subscribe("rpc.test", lambda e: None)
        bus.request(topic="rpc.test", payload={}, timeout=0.0)
        bus.request(topic="rpc.test", payload={}, timeout=0.0)
        request_envs = [e for e in bus.history() if e.topic == "rpc.test"]
        assert len({e.reply_to for e in request_envs}) == 2

    def test_inbox_subscription_cleaned_up(self):
        bus = Bus()
        bus.subscribe("rpc.silent", lambda e: None)
        before = bus.n_subscriptions()
        bus.request(topic="rpc.silent", payload={}, timeout=0.0)
        # The temporary inbox subscription is unsubscribed in the finally.
        assert bus.n_subscriptions() == before

    def test_negative_timeout_rejected(self):
        bus = Bus()
        with pytest.raises(ValueError):
            bus.request(topic="x.y", payload={}, timeout=-1.0)


# --- Audit integration ------------------------------------------------


class TestAudit:
    def test_witness_recorded_per_publish(self):
        lattice = WitnessLattice()
        bus = Bus(lattice=lattice)
        bus.publish(topic="agent.alice", payload={"x": 1})
        bus.publish(topic="agent.bob", payload={"y": 2})
        assert lattice.ledger.stats()["total"] == 2

    def test_witness_payload_keys_recorded(self):
        lattice = WitnessLattice()
        bus = Bus(lattice=lattice)
        bus.publish(topic="agent.alice", payload={"x": 1, "y": 2})
        witnesses = lattice.ledger.witnesses_for()
        assert sorted(witnesses[0].content["payload_keys"]) == ["x", "y"]

    def test_no_lattice_no_witnesses(self):
        bus = Bus()
        bus.publish(topic="agent.alice", payload={})
        # Sanity: no exception.


# --- Handler exception isolation -------------------------------------


class TestRobustness:
    def test_unsubscribe_during_dispatch_safe(self):
        bus = Bus()
        received_b = []

        sub_b = bus.subscribe("agent.*", lambda e: received_b.append(e))

        def first_handler(env: Envelope):
            sub_b.unsubscribe()  # detach during dispatch

        bus.subscribe("agent.*", first_handler)
        # Dispatch order is insertion order; first_handler runs first and
        # unsubscribes b. Iteration uses a snapshot, so b's handler may or
        # may not run, but the bus should not crash.
        bus.publish(topic="agent.alice", payload={})
        # Both behaviours are valid; the invariant is no crash and sub_b
        # is now inactive.
        assert not sub_b.active

    def test_dispatch_preserves_topic_routing(self):
        bus = Bus()
        a_received = []
        b_received = []
        bus.subscribe("a.*", lambda e: a_received.append(e))
        bus.subscribe("b.*", lambda e: b_received.append(e))
        bus.publish(topic="a.x", payload={})
        bus.publish(topic="b.y", payload={})
        bus.publish(topic="c.z", payload={})  # nobody
        assert len(a_received) == 1
        assert len(b_received) == 1


# --- Envelope creation -----------------------------------------------


class TestEnvelope:
    def test_basic(self):
        e = Envelope.create(
            topic="x.y", payload={"a": 1}, issued_by="loop",
        )
        assert e.envelope_id != ""
        assert e.topic == "x.y"

    def test_empty_topic_rejected(self):
        with pytest.raises(ValueError):
            Envelope.create(topic="", payload={}, issued_by="x")
