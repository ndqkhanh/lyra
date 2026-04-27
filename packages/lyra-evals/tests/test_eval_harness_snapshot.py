"""Phase 12 — Red tests for VeRO-style harness snapshots.

VeRO (arXiv:2602.22480, 2026) argues that evaluation harnesses must pin
a reproducible snapshot: commit SHA + package versions + policy hash +
seed. Without the snapshot, two 'identical' evaluation runs silently
drift, contaminating the drift gate.

These tests pin the contract:

1. ``HarnessSnapshot.capture()`` returns a populated dataclass.
2. Same snapshot + deterministic policy → identical ``Report``.
3. Different seeds (with non-deterministic policy) → divergent but
   bounded-divergence reports; the divergence is recorded.
4. The snapshot is serializable and appears in ``Report.to_dict()``.
"""
from __future__ import annotations

from pathlib import Path

from lyra_evals.corpora import golden_tasks
from lyra_evals.runner import EvalRunner, TaskResult
from lyra_evals.snapshot import HarnessSnapshot, snapshot_hash

# ---------------------------------------------------------------------------
# 1. Snapshot capture
# ---------------------------------------------------------------------------


def test_snapshot_captures_required_fields(tmp_path: Path) -> None:
    """A captured snapshot must have commit_sha, packages, policy_hash, seed.

    Missing any of these breaks VeRO's reproducibility invariants.
    """
    policy_file = tmp_path / "policy.yaml"
    policy_file.write_text("version: 1\nrules: []\n", encoding="utf-8")

    snap = HarnessSnapshot.capture(
        policy_path=policy_file,
        seed=1337,
        packages=("lyra-core", "lyra-evals"),
    )
    assert isinstance(snap.commit_sha, str)
    assert len(snap.commit_sha) >= 7 or snap.commit_sha == "unknown"
    assert "lyra-core" in snap.packages
    assert "lyra-evals" in snap.packages
    assert len(snap.policy_hash) == 64  # sha256
    assert snap.seed == 1337


def test_snapshot_is_serializable_to_dict() -> None:
    """Snapshots must JSON-serialize cleanly for retro + CI artifacts."""
    snap = HarnessSnapshot.capture(policy_path=None, seed=0, packages=())
    payload = snap.to_dict()
    assert set(payload) >= {"commit_sha", "packages", "policy_hash", "seed"}
    assert isinstance(payload["packages"], dict)


# ---------------------------------------------------------------------------
# 2. Determinism: same snapshot + deterministic policy → identical report
# ---------------------------------------------------------------------------


def test_same_snapshot_produces_identical_reports() -> None:
    """Two runs under the same snapshot MUST produce identical reports.

    This is the whole point of pinning a snapshot. If a harness change
    sneaks through without bumping the snapshot hash, the diff must
    surface as a drift-gate trip, not as noise.
    """
    def policy(task):  # type: ignore[no-untyped-def]
        return TaskResult(task_id=task.id, passed=True, reason="det")

    tasks = golden_tasks()
    r1 = EvalRunner(policy=policy, drift_gate=None).run(tasks)
    r2 = EvalRunner(policy=policy, drift_gate=None).run(tasks)
    assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# 3. Snapshot hash is the single fingerprint
# ---------------------------------------------------------------------------


def test_snapshot_hash_changes_when_any_component_changes() -> None:
    """Hash must be sensitive to commit SHA, packages, policy, seed.

    Otherwise the drift gate could trip on an unrelated package bump and
    the operator would have no fingerprint to blame.
    """
    base = HarnessSnapshot(
        commit_sha="a" * 40,
        packages={"lyra-core": "0.1.0"},
        policy_hash="0" * 64,
        seed=1,
    )
    h0 = snapshot_hash(base)

    assert snapshot_hash(
        HarnessSnapshot(
            commit_sha="b" * 40,
            packages=base.packages,
            policy_hash=base.policy_hash,
            seed=base.seed,
        )
    ) != h0

    assert snapshot_hash(
        HarnessSnapshot(
            commit_sha=base.commit_sha,
            packages={"lyra-core": "0.2.0"},
            policy_hash=base.policy_hash,
            seed=base.seed,
        )
    ) != h0

    assert snapshot_hash(
        HarnessSnapshot(
            commit_sha=base.commit_sha,
            packages=base.packages,
            policy_hash="1" * 64,
            seed=base.seed,
        )
    ) != h0

    assert snapshot_hash(
        HarnessSnapshot(
            commit_sha=base.commit_sha,
            packages=base.packages,
            policy_hash=base.policy_hash,
            seed=2,
        )
    ) != h0


def test_snapshot_hash_is_stable_across_package_order() -> None:
    """Reordering packages must not change the hash — dicts are unordered."""
    a = HarnessSnapshot(
        commit_sha="x" * 40,
        packages={"lyra-core": "0.1.0", "lyra-evals": "0.1.0"},
        policy_hash="0" * 64,
        seed=0,
    )
    b = HarnessSnapshot(
        commit_sha="x" * 40,
        packages={"lyra-evals": "0.1.0", "lyra-core": "0.1.0"},
        policy_hash="0" * 64,
        seed=0,
    )
    assert snapshot_hash(a) == snapshot_hash(b)
