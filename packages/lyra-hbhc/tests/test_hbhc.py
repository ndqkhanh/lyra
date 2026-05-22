"""Tests for HBHC package."""

import pytest
from lyra_hbhc import HBHCManager, Verifier, ZombieDetector, CredentialStatus


class TestHBHCManager:
    @pytest.mark.asyncio
    async def test_issue_credential(self):
        mgr = HBHCManager()
        cred = await mgr.issue_credential("agent_1", "root", 1)
        assert cred.agent_id == "agent_1"
        assert cred.level == 1
        assert cred.status == CredentialStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_revoke_cascade(self):
        mgr = HBHCManager()
        await mgr.issue_credential("root", "root", 0)
        await mgr.issue_credential("child_1", "root", 1)
        await mgr.issue_credential("child_2", "child_1", 2)
        revoked = await mgr.revoke_cascade("root")
        assert "root" in revoked
        assert "child_1" in revoked
        assert "child_2" in revoked

    def test_verify_credential_unknown(self):
        mgr = HBHCManager()
        valid, _ = mgr.verify_credential("nonexistent")
        assert not valid


class TestVerifier:
    def test_verify_cached(self):
        v = Verifier()
        v.cache_key("agent_1", "key123")
        v.verification_count = 0
        assert v.verification_count == 0


class TestZombieDetector:
    def test_no_zombies_initially(self):
        z = ZombieDetector()
        assert z.max_zombie_window == 0.0
        assert z.total_zombie_events == 0
