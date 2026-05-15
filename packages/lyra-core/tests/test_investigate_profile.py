"""Tests for the investigate-mode permissions profile presets.

Cite: arXiv:2605.05242 §3; DCI-Agent-Lite README "--cwd <corpus_root>".

The profile is a value object — these tests pin the contract only.
The downstream integration with the host's permissions grammar lives
in a follow-up bundle.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.investigate import (
    READ_ONLY,
    InvestigateProfile,
    read_write,
)


class TestReadOnlyDefault:
    def test_name(self) -> None:
        assert READ_ONLY.name == "investigate-readonly"

    def test_is_read_only(self) -> None:
        assert READ_ONLY.read_only is True
        assert READ_ONLY.write_root is None

    def test_network_denied(self) -> None:
        assert READ_ONLY.allow_network is False

    def test_dci_workhorse_binaries_in_allowlist(self) -> None:
        """The seven RQ6 workhorse binaries must be in the default allowlist."""
        for binary in ("rg", "find", "sed", "head", "tail", "cat", "wc"):
            assert binary in READ_ONLY.allowed_set

    def test_dangerous_binaries_not_in_allowlist(self) -> None:
        for binary in ("sh", "bash", "python", "curl", "wget", "rm"):
            assert binary not in READ_ONLY.allowed_set

    def test_allowed_set_is_frozen(self) -> None:
        s = READ_ONLY.allowed_set
        assert isinstance(s, frozenset)


class TestReadWriteFactory:
    def test_builds_writable_profile(self, tmp_path: Path) -> None:
        p = read_write(tmp_path)
        assert p.read_only is False
        assert p.write_root == tmp_path
        assert p.name == "investigate-rw"

    def test_same_allowlist_as_readonly(self, tmp_path: Path) -> None:
        p = read_write(tmp_path)
        assert p.allowed_set == READ_ONLY.allowed_set

    def test_network_still_denied(self, tmp_path: Path) -> None:
        assert read_write(tmp_path).allow_network is False


class TestProfileValidation:
    def test_rejects_read_only_with_write_root(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="write_root must be None"):
            InvestigateProfile(
                name="bogus", read_only=True, write_root=tmp_path,
            )

    def test_rejects_writable_without_write_root(self) -> None:
        with pytest.raises(ValueError, match="write_root must be set"):
            InvestigateProfile(
                name="bogus", read_only=False, write_root=None,
            )

    def test_frozen_dataclass(self) -> None:
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            READ_ONLY.name = "x"   # type: ignore[misc]
