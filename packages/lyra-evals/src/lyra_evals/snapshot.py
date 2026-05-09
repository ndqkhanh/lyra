"""VeRO-style harness snapshots.

Source: *VeRO: An Evaluation Harness for Agents to Optimize Agents*,
arXiv:2602.22480, 2026. VeRO's central claim is that an evaluation is
only reproducible if the harness pins a fingerprint over:

- the code (commit SHA of the harness repo);
- the packages (every installed version that could influence behaviour);
- the policy (the ``.lyra/policy.yaml`` or equivalent — permission
  mode, hooks, feature flags);
- the seed (caller-supplied; zero is a fine value, but it must be pinned).

``HarnessSnapshot.capture()`` is a one-shot collector. ``snapshot_hash``
produces the stable fingerprint that we embed in every ``Report`` so two
eval runs at the same snapshot are either identical or the diff itself
is the bug.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from pathlib import Path


def _git_head_sha(cwd: Path | None = None) -> str:
    """Resolve the HEAD SHA of the repo we're running in.

    Returns ``"unknown"`` if git isn't available or the cwd isn't a
    checkout — tests running from an unpacked tarball must still pass.
    """
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd) if cwd else None,
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8", errors="replace").strip() or "unknown"
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return "unknown"


def _hash_policy(path: Path | None) -> str:
    """SHA-256 of the policy file content, or 64 zeros if absent."""
    if path is None:
        return "0" * 64
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return "0" * 64


def _resolve_packages(names: Iterable[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for name in names:
        try:
            resolved[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            resolved[name] = "unknown"
    return resolved


@dataclass(frozen=True)
class HarnessSnapshot:
    """Immutable, hashable record of the harness at run time."""

    commit_sha: str
    packages: dict[str, str] = field(default_factory=dict)
    policy_hash: str = "0" * 64
    seed: int = 0

    @classmethod
    def capture(
        cls,
        *,
        policy_path: Path | None,
        seed: int,
        packages: Iterable[str] = (),
        repo_root: Path | None = None,
    ) -> HarnessSnapshot:
        return cls(
            commit_sha=_git_head_sha(repo_root),
            packages=_resolve_packages(packages),
            policy_hash=_hash_policy(policy_path),
            seed=seed,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "packages": dict(self.packages),
            "policy_hash": self.policy_hash,
            "seed": self.seed,
        }


def snapshot_hash(snap: HarnessSnapshot) -> str:
    """Stable fingerprint for the snapshot.

    ``json.dumps(..., sort_keys=True)`` gives us order-independence over
    the packages dict; the SHA-256 of the canonical serialisation is the
    fingerprint we print in reports and compare across runs.
    """
    payload = {
        "commit_sha": snap.commit_sha,
        "packages": dict(sorted(snap.packages.items())),
        "policy_hash": snap.policy_hash,
        "seed": snap.seed,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()
