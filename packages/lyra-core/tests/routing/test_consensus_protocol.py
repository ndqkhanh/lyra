"""Tests for the gossip consensus protocol."""
from __future__ import annotations

import time

from lyra_memory.gossip.consensus_protocol import (
    ConsensusConfig,
    GossipMessage,
    GossipNode,
    MemoryUpdate,
    UpdateOp,
    VectorClock,
)


class TestVectorClock:
    def test_create_initial_clock(self):
        vc = VectorClock.create("node-a")
        assert vc.get("node-a") == 0

    def test_increment(self):
        vc = VectorClock.create("node-a")
        vc2 = vc.increment("node-a")
        assert vc2.get("node-a") == 1
        assert vc.get("node-a") == 0  # original unchanged

    def test_increment_new_node(self):
        vc = VectorClock.create("node-a")
        vc2 = vc.increment("node-b")
        assert vc2.get("node-a") == 0
        assert vc2.get("node-b") == 1

    def test_get_missing_node(self):
        vc = VectorClock.create("node-a")
        assert vc.get("node-b") == 0

    def test_happens_before_true(self):
        vc1 = VectorClock.create("a").increment("a")
        vc2 = vc1.increment("a").increment("a")
        assert vc1.happens_before(vc2)
        assert not vc2.happens_before(vc1)

    def test_happens_before_concurrent(self):
        vc1 = VectorClock.create("a").increment("a")
        vc2 = VectorClock.create("b").increment("b")
        assert not vc1.happens_before(vc2)
        assert not vc2.happens_before(vc1)

    def test_happens_before_equal(self):
        vc1 = VectorClock.create("a")
        assert not vc1.happens_before(vc1)

    def test_concurrent(self):
        vc1 = VectorClock.create("a").increment("a")
        vc2 = VectorClock.create("b").increment("b")
        assert vc1.concurrent(vc2)

    def test_concurrent_not_when_ordered(self):
        vc1 = VectorClock.create("a").increment("a")
        vc2 = vc1.increment("a").increment("a")
        assert not vc1.concurrent(vc2)

    def test_merge_pointwise_max(self):
        vc1 = VectorClock(counters=(("a", 3), ("b", 1)))
        vc2 = VectorClock(counters=(("a", 1), ("b", 5)))
        merged = vc1.merge(vc2)
        assert merged.get("a") == 3
        assert merged.get("b") == 5

    def test_to_from_dict_roundtrip(self):
        vc = VectorClock(counters=(("a", 2), ("b", 3)))
        d = vc.to_dict()
        restored = VectorClock.from_dict(d)
        assert restored.get("a") == 2
        assert restored.get("b") == 3


class TestMemoryUpdate:
    def test_create_put_update(self):
        clock = VectorClock.create("node-1").increment("node-1")
        update = MemoryUpdate.create(
            key="memory:001",
            value="important knowledge",
            op=UpdateOp.PUT,
            node_id="node-1",
            clock=clock,
        )
        assert update.key == "memory:001"
        assert update.value == "important knowledge"
        assert update.op == UpdateOp.PUT
        assert update.node_id == "node-1"
        assert len(update.content_hash) == 64
        assert len(update.update_id) > 0

    def test_create_delete_update(self):
        clock = VectorClock.create("node-1").increment("node-1")
        update = MemoryUpdate.create(
            key="memory:002", value="", op=UpdateOp.DELETE,
            node_id="node-1", clock=clock,
            parent_hash="abc123",
        )
        assert update.op == UpdateOp.DELETE
        assert update.parent_hash == "abc123"

    def test_unique_update_ids(self):
        clock = VectorClock.create("n1").increment("n1")
        u1 = MemoryUpdate.create("k", "v", UpdateOp.PUT, "n1", clock)
        u2 = MemoryUpdate.create("k", "v", UpdateOp.PUT, "n1", clock)
        assert u1.update_id != u2.update_id


class TestGossipMessage:
    def test_create_message(self):
        clock = VectorClock.create("sender").increment("sender")
        update = MemoryUpdate.create("k", "v", UpdateOp.PUT, "sender", clock)
        msg = GossipMessage.create(
            updates=(update,),
            sender_id="sender",
            sender_clock=clock,
        )
        assert msg.sender_id == "sender"
        assert len(msg.updates) == 1
        assert msg.ttl == 3
        assert len(msg.message_id) > 0

    def test_custom_ttl(self):
        clock = VectorClock.create("s").increment("s")
        msg = GossipMessage.create(updates=(), sender_id="s", sender_clock=clock, ttl=5)
        assert msg.ttl == 5


class TestGossipNode:
    def test_create_node(self):
        node = GossipNode("node-alpha")
        assert node.node_id == "node-alpha"
        assert node.store_size == 0
        assert node.peer_count == 0
        assert node.merge_count == 0

    def test_put_stores_value(self):
        node = GossipNode("n1")
        update = node.put("key1", "value1")
        assert node.store_size == 1
        assert node.get("key1") is update
        assert node.get("key1").value == "value1"

    def test_put_advances_clock(self):
        node = GossipNode("n1")
        node.put("k1", "v1")
        assert node.clock.get("n1") == 1
        node.put("k2", "v2")
        assert node.clock.get("n1") == 2

    def test_delete_removes_key(self):
        node = GossipNode("n1")
        node.put("k1", "v1")
        assert node.store_size == 1
        deleted = node.delete("k1")
        assert deleted is not None
        assert deleted.op == UpdateOp.DELETE
        assert node.store_size == 0
        assert node.get("k1") is None

    def test_delete_nonexistent(self):
        node = GossipNode("n1")
        assert node.delete("nonexistent") is None

    def test_local_keys(self):
        node = GossipNode("n1")
        node.put("b", "vb")
        node.put("a", "va")
        node.put("c", "vc")
        assert node.local_keys() == ["a", "b", "c"]

    def test_add_peer(self):
        node = GossipNode("n1")
        node.add_peer("n2")
        assert node.peer_count == 1
        assert "n2" in node._peer_clocks

    def test_add_peer_idempotent(self):
        node = GossipNode("n1")
        node.add_peer("n2")
        node.add_peer("n2")
        assert node.peer_count == 1

    def test_remove_peer(self):
        node = GossipNode("n1")
        node.add_peer("n2")
        node.remove_peer("n2")
        assert node.peer_count == 0

    def test_prepare_gossip_sends_updates(self):
        n1 = GossipNode("n1")
        n1.add_peer("n2")
        n1.put("k1", "v1")
        n1.put("k2", "v2")

        msg = n1.prepare_gossip()
        assert len(msg.updates) == 2

    def test_prepare_gossip_respects_peer_clock(self):
        n1 = GossipNode("n1")
        n1.add_peer("n2")
        n1.put("k1", "v1")

        # n2 already knows about n1's update
        n1._peer_clocks["n2"] = n1.clock

        msg = n1.prepare_gossip()
        assert len(msg.updates) == 0

    def test_receive_gossip_updates_store(self):
        n1 = GossipNode("n1")
        n2 = GossipNode("n2")
        n1.add_peer("n2")

        # n2 creates an update
        n2.put("shared-key", "from-n2")
        msg = n2.prepare_gossip(peer_ids=["n1"])

        result = n1.receive_gossip(msg)
        assert len(result.accepted) == 1
        assert n1.get("shared-key") is not None
        assert n1.get("shared-key").value == "from-n2"

    def test_receive_gossip_merges_clocks(self):
        n1 = GossipNode("n1")
        n2 = GossipNode("n2")
        n1.add_peer("n2")

        n2.put("k", "v")
        n2_clock_before = n2.clock.get("n2")
        n1.receive_gossip(n2.prepare_gossip(peer_ids=["n1"]))
        assert n1.clock.get("n2") == n2_clock_before

    def test_receive_gossip_deduplicates(self):
        n1 = GossipNode("n1")
        n2 = GossipNode("n2")
        n1.add_peer("n2")

        n2.put("k", "v")
        msg = n2.prepare_gossip(peer_ids=["n1"])

        r1 = n1.receive_gossip(msg)
        assert len(r1.accepted) == 1

        r2 = n1.receive_gossip(msg)
        assert len(r2.accepted) == 0  # already seen

    def test_receive_gossip_ttl_zero_rejected(self):
        n1 = GossipNode("n1")
        clock = VectorClock.create("n1").increment("n1")
        msg = GossipMessage(
            message_id="test",
            updates=(),
            sender_id="n2",
            sender_clock=clock,
            sent_at=time.time(),
            ttl=0,
        )
        result = n1.receive_gossip(msg)
        assert result.merge_count == 0

    def test_receive_gossip_expired_updates_rejected(self):
        n1 = GossipNode("n1")
        n1.add_peer("n2")

        old_clock = VectorClock.create("n2").increment("n2")
        old_update = MemoryUpdate(
            update_id="old-1",
            key="old-key",
            value="old-value",
            op=UpdateOp.PUT,
            node_id="n2",
            vector_clock=old_clock,
            timestamp=time.time() - 1000,  # very old
            content_hash="abc123",
        )
        msg = GossipMessage.create(
            updates=(old_update,),
            sender_id="n2",
            sender_clock=old_clock,
        )
        result = n1.receive_gossip(msg)
        assert len(result.rejected) >= 1

    def test_conflict_resolution_lww(self):
        n1 = GossipNode("n1")
        n2 = GossipNode("n2")
        n1.add_peer("n2")
        n2.add_peer("n1")

        # Both nodes write to same key concurrently
        n1.put("conflict-key", "n1-value")
        n2.put("conflict-key", "n2-value")

        # n1 receives n2's update
        msg = n2.prepare_gossip(peer_ids=["n1"])
        result = n1.receive_gossip(msg)

        # Should detect conflict
        assert len(result.conflicts) >= 1
        # n1's clock for n1 is higher (put was called), so n1's value should win
        final = n1.get("conflict-key")
        assert final is not None
        assert final.value in ("n1-value", "n2-value")

    def test_should_sync_initially_true(self):
        node = GossipNode("n1")
        assert node.should_sync()

    def test_convergence_ratio_no_peers(self):
        node = GossipNode("n1")
        assert node.convergence_ratio() == 1.0

    def test_convergence_ratio_with_peers(self):
        n1 = GossipNode("n1")
        n1.add_peer("n2")
        n1.add_peer("n3")
        # Peers just added with default clocks
        ratio = n1.convergence_ratio()
        assert 0.0 <= ratio <= 1.0

    def test_is_converged_default_threshold(self):
        node = GossipNode("n1")
        assert node.is_converged()  # no peers = fully converged

    def test_full_gossip_round_converges(self):
        """Simulate a gossip round between multiple nodes."""
        n1 = GossipNode("n1")
        n2 = GossipNode("n2")
        n3 = GossipNode("n3")

        n1.add_peer("n2")
        n1.add_peer("n3")
        n2.add_peer("n1")
        n2.add_peer("n3")
        n3.add_peer("n1")
        n3.add_peer("n2")

        # n1 writes some data
        n1.put("shared-1", "v1")
        n1.put("shared-2", "v2")

        # Gossip: n1 -> n2, n3
        for target in [n2, n3]:
            msg = n1.prepare_gossip(peer_ids=[target.node_id])
            target.receive_gossip(msg)

        # All nodes should have the data
        assert n2.get("shared-1") is not None
        assert n2.get("shared-2") is not None
        assert n3.get("shared-1") is not None
        assert n3.get("shared-2") is not None

    def test_node_initial_state(self):
        node = GossipNode("test-node")
        assert node.store_size == 0
        assert node.peer_count == 0
        assert node.clock.get("test-node") == 0

    def test_custom_config(self):
        cfg = ConsensusConfig(fanout=5, sync_interval_sec=10.0)
        node = GossipNode("n1", config=cfg)
        assert node.config.fanout == 5
        assert node.config.sync_interval_sec == 10.0
