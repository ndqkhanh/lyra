"""Integration tests for evolution framework."""
import pytest
import time


def test_evolution_round_with_harness_and_cost_tracking(mock_harness, mock_cost_meter):
    """Test complete evolution round with harness and cost tracking."""
    meter, budget = mock_cost_meter

    # 1. Write candidate
    success = mock_harness.workspace_write("candidate.py", "def solve(): return 42")
    assert success is True

    # Track cost
    meter.add_tokens(100, cost_per_token=0.001)

    # 2. Read candidate
    content = mock_harness.workspace_read("candidate.py")
    assert content is not None

    # Track cost
    meter.add_tokens(50, cost_per_token=0.001)

    # 3. Submit score
    success = mock_harness.submit("candidate_001")
    assert success is True

    # Track cost
    meter.add_tokens(20, cost_per_token=0.001)

    # 4. Check budget
    assert meter.check_budget(budget) is True

    # 5. Verify total costs
    stats = meter.get_stats()
    assert stats["tokens_used"] == 170
    assert stats["dollars_spent"] == pytest.approx(0.17, rel=0.01)


def test_reward_hacking_attempt_blocked(mock_harness, mock_cost_meter):
    """Test that reward hacking attempts are blocked."""
    meter, budget = mock_cost_meter

    # Simulate agent trying to hack rewards
    # 1. Try to read evaluator test cases
    with pytest.raises(PermissionError):
        mock_harness.workspace_read("../evaluator/test_cases.py")

    # Cost is still tracked even for failed operations
    meter.add_tokens(50, cost_per_token=0.001)

    # 2. Try to write fake scores
    with pytest.raises(PermissionError):
        mock_harness.workspace_write("../archive/scores/fake.json", '{"score": 100}')

    # Cost is still tracked
    meter.add_tokens(50, cost_per_token=0.001)

    # 3. Verify costs were tracked despite failures
    stats = meter.get_stats()
    assert stats["tokens_used"] == 100
    assert stats["dollars_spent"] == pytest.approx(0.1, rel=0.01)

    # 4. Budget check still works
    assert meter.check_budget(budget) is True


def test_legitimate_evolution_workflow(mock_harness, mock_cost_meter):
    """Test complete legitimate evolution workflow."""
    meter, budget = mock_cost_meter

    # Round 1: Initial candidate
    mock_harness.workspace_write("candidate_v1.py", "def solve(x): return x * 2")
    meter.add_tokens(100, cost_per_token=0.001)

    # Evaluate
    candidate_path = mock_harness.archive_dir / "candidates" / "candidate_001.json"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text('{"code": "def solve(x): return x * 2"}')

    result = mock_harness.evaluate("candidate_001")
    assert "score" in result
    meter.add_tokens(200, cost_per_token=0.001)

    # Round 2: Improved candidate
    mock_harness.workspace_write("candidate_v2.py", "def solve(x): return x * 2 + 1")
    meter.add_tokens(100, cost_per_token=0.001)

    # Check budget before continuing
    assert meter.check_budget(budget) is True

    # Evaluate improved candidate
    candidate_path2 = mock_harness.archive_dir / "candidates" / "candidate_002.json"
    candidate_path2.write_text('{"code": "def solve(x): return x * 2 + 1"}')

    result2 = mock_harness.evaluate("candidate_002")
    assert "score" in result2
    meter.add_tokens(200, cost_per_token=0.001)

    # Final stats
    stats = meter.get_stats()
    assert stats["tokens_used"] == 600
    assert stats["dollars_spent"] == pytest.approx(0.6, rel=0.01)

    # Still under budget
    assert meter.check_budget(budget) is True
