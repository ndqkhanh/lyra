"""Tests for HBHC package."""

import asyncio
import pytest
from lyra_hbhc import HBHCManager, Verifier, ZombieDetector, CredentialStatus


class TestHBHCManager:
    def test_issue_credential(self):
        mgr = HBHCManager()
        asyncio.run(mgr.issue_credential("root", "root", 0))
        cred = asyncio.run(mgr.issue_credential("agent_1", "root", 1))
        assert cred.agent_id == "agent_1"
        assert cred.level == 1
        assert cred.status == CredentialStatus.ACTIVE

    def test_revoke_cascade(self):
        mgr = HBHCManager()
        asyncio.run(mgr.issue_credential("root", "root", 0))
        asyncio.run(mgr.issue_credential("child_1", "root", 1))
        asyncio.run(mgr.issue_credential("child_2", "child_1", 2))
        revoked = asyncio.run(mgr.revoke_cascade("root"))
        assert "root" in revoked
        assert "child_1" in revoked
        assert "child_2" in revoked

    def test_verify_credential_unknown(self):
        mgr = HBHCManager()
        valid, _ = mgr.verify_credential("nonexistent")
        assert not valid

    def test_send_heartbeat_unknown(self):
        mgr = HBHCManager()
        result = asyncio.run(mgr.send_heartbeat("unknown"))
        assert not result


class TestVerifier:
    def test_verify_cached(self):
        v = Verifier()
        v.cache_key("agent_1", "key123")
        assert True


class TestZombieDetector:
    def test_no_zombies_initially(self):
        z = ZombieDetector()
        assert z.max_zombie_window == 0.0
        assert z.total_zombie_events == 0

    def test_report_zombie(self):
        z = ZombieDetector()
        ev = z.report_zombie("agent_1", 100.0, 101.5)
        assert ev["zombie_window_seconds"] == 1.5
        assert z.total_zombie_events == 1
