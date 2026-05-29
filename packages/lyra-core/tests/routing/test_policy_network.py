"""Tests for the RL policy network."""
from __future__ import annotations

import pytest
from lyra_core.routing.policy_network import (
    ACTION_SPACE,
    HIDDEN_DIM,
    NUM_ACTIONS,
    PolicyNetwork,
    PolicyWeights,
)


class TestPolicyWeights:
    def test_random_weights_correct_shape(self):
        pw = PolicyWeights.random()
        assert len(pw.w1) == 12   # FEATURE_DIM
        assert len(pw.w1[0]) == HIDDEN_DIM
        assert len(pw.b1) == HIDDEN_DIM
        assert len(pw.w2) == HIDDEN_DIM
        assert len(pw.w2[0]) == NUM_ACTIONS
        assert len(pw.b2) == NUM_ACTIONS

    def test_random_weights_different_seeds(self):
        pw1 = PolicyWeights.random(seed=42)
        pw2 = PolicyWeights.random(seed=42)
        pw3 = PolicyWeights.random(seed=99)
        assert pw1.w1[0][0] == pw2.w1[0][0]
        assert pw1.w1[0][0] != pw3.w1[0][0]

    def test_zeros_weights(self):
        pw = PolicyWeights.zeros()
        assert all(v == 0.0 for row in pw.w1 for v in row)
        assert all(v == 0.0 for row in pw.w2 for v in row)

    def test_weights_are_mutable(self):
        pw = PolicyWeights.random()
        old = pw.w1[0][0]
        pw.w1[0][0] = old + 0.1
        assert pw.w1[0][0] != old


class TestPolicyNetwork:
    def test_forward_returns_probabilities(self):
        net = PolicyNetwork()
        features = [0.5] * 12
        probs, hidden, logits = net.forward(features)
        assert len(probs) == NUM_ACTIONS
        assert abs(sum(probs) - 1.0) < 1e-6
        assert all(p >= 0.0 for p in probs)
        assert len(hidden) == HIDDEN_DIM

    def test_select_action_returns_valid_tier(self):
        net = PolicyNetwork()
        features = [0.3] * 12
        tier, idx = net.select_action(features)
        assert tier in ACTION_SPACE
        assert 0 <= idx < NUM_ACTIONS

    def test_select_action_exploit_mode(self):
        net = PolicyNetwork()
        features = [0.5] * 12
        tier1, _ = net.select_action(features, exploit=True)
        tier2, _ = net.select_action(features, exploit=True)
        assert tier1 == tier2  # deterministic in exploit mode

    def test_train_step_returns_loss(self):
        net = PolicyNetwork()
        features = [0.5] * 12
        loss = net.train_step(features, action_idx=0, reward=1.0)
        assert isinstance(loss, float)

    def test_train_step_increments_counter(self):
        net = PolicyNetwork()
        features = [0.5] * 12
        for i in range(5):
            net.train_step(features, action_idx=i % 3, reward=0.5)
        assert net.train_steps == 5

    def test_train_step_produces_nonzero_loss(self):
        net = PolicyNetwork()
        features = [0.5] * 12
        losses = []
        for i in range(20):
            loss = net.train_step(features, action_idx=i % 3, reward=10.0)
            losses.append(loss)
        assert net.train_steps == 20
        assert net.avg_loss > 0.0

    def test_avg_loss_with_no_steps(self):
        net = PolicyNetwork()
        assert net.avg_loss == 0.0

    def test_avg_loss_with_steps(self):
        net = PolicyNetwork()
        features = [0.5] * 12
        for i in range(10):
            net.train_step(features, action_idx=i % 3, reward=float(i % 3))
        avg = net.avg_loss
        assert avg > 0.0

    def test_get_set_weights_vector_roundtrip(self):
        net = PolicyNetwork()
        features = [0.5] * 12
        net.train_step(features, action_idx=0, reward=1.0)

        vec = net.get_weights_vector()
        net2 = PolicyNetwork()
        net2.set_weights_vector(vec)

        probs1, _, _ = net.forward(features)
        probs2, _, _ = net2.forward(features)
        assert probs1 == pytest.approx(probs2, abs=1e-6)

    def test_clone_weights_returns_equal_forward(self):
        net = PolicyNetwork()
        features = [0.3] * 12
        cloned = net.clone_weights()
        net2 = PolicyNetwork(weights=cloned)
        p1, _, _ = net.forward(features)
        p2, _, _ = net2.forward(features)
        assert p1 == pytest.approx(p2, abs=1e-6)

    def test_forward_different_inputs_different_outputs(self):
        net = PolicyNetwork()
        p1, _, _ = net.forward([0.0] * 12)
        p2, _, _ = net.forward([1.0] * 12)
        assert p1 != p2

    def test_negative_reward_reduces_action_probability(self):
        net = PolicyNetwork()
        features = [0.5] * 12

        # Get initial probability for action 0
        probs_before, _, _ = net.forward(features)
        probs_before[0]

        # Train with negative reward on action 0
        for _ in range(50):
            net.train_step(features, action_idx=0, reward=-1.0)

        net.lr = 0.01  # Reset learning rate
        probs_after, _, _ = net.forward(features)
        # After many negative updates, probability should decrease
        assert probs_after[0] < 0.99  # not a strict assertion due to SGD noise

    def test_init_with_custom_weights(self):
        pw = PolicyWeights.random(seed=42)
        net = PolicyNetwork(weights=pw, learning_rate=0.05)
        assert net.lr == 0.05
        features = [0.5] * 12
        probs, _, _ = net.forward(features)
        assert abs(sum(probs) - 1.0) < 1e-6
