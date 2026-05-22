"""Tests for lyra-identity."""
from lyra_identity import AgentIdentity


class TestAgentIdentity:
    def test_sign_and_verify(self):
        identity = AgentIdentity("agent_1")
        manifest = identity.sign_action({"action": "write_file", "path": "/tmp/test.txt"})
        assert identity.verify(manifest)
        assert manifest.agent_id == "agent_1"

    def test_provenance_lineage(self):
        identity = AgentIdentity("agent_1")
        m1 = identity.sign_action({"action": "research"})
        m2 = identity.sign_action({"action": "write"}, parent_action_id=m1.action_id)
        lineage = identity.get_lineage(m2.action_id)
        assert len(lineage) >= 1

    def test_content_hash_consistency(self):
        identity = AgentIdentity("agent_1")
        manifest = identity.sign_action({"action": "test", "value": 42})
        assert len(manifest.content_hash) == 64  # SHA256 hex
