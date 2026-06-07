"""Tests for identity anonymizer in verification panel."""

from lyra.verification.anonymizer import IdentityAnonymizer


class TestIdentityAnonymizer:
    """Identity stripping tests."""

    def test_strip_role_self_description(self):
        anon = IdentityAnonymizer()
        msg = "As the senior architect, I believe this design is flawed."
        cleaned = anon.strip_identity(msg, "Senior Software Architect")
        assert "senior architect" not in cleaned.lower()
        assert "Senior Software Architect" not in cleaned

    def test_strip_i_am_role(self):
        anon = IdentityAnonymizer()
        msg = "I am the security engineer, and this has vulnerabilities."
        cleaned = anon.strip_identity(msg, "Senior Security Engineer")
        assert "security engineer" not in cleaned.lower()

    def test_strip_my_role(self):
        anon = IdentityAnonymizer()
        msg = "My role as the backend engineer is to ensure API stability."
        cleaned = anon.strip_identity(msg, "Senior Backend Engineer")
        assert "backend engineer" not in cleaned.lower()

    def test_preserve_technical_content(self):
        """Technical content should survive anonymization."""
        anon = IdentityAnonymizer()
        msg = "The SQL query has an N+1 problem in the user loop."
        cleaned = anon.strip_identity(msg, "Senior Backend Engineer")
        assert "SQL query" in cleaned
        assert "N+1 problem" in cleaned
        assert "user loop" in cleaned

    def test_anonymize_debate_multiple_speakers(self):
        """Multiple speakers get different anonymous IDs."""
        anon = IdentityAnonymizer()
        debate = anon.anonymize_debate([
            ("Senior AI Researcher", "The paper shows 67.3% accuracy."),
            ("Adversarial Skeptic", "But the ablation study had N=10."),
            ("Senior Software Architect", "The system can handle this load."),
        ])
        assert len(debate.messages) == 3

        # Different agents get different anonymous IDs
        ids = {msg.anonymous_id for msg in debate.messages}
        assert len(ids) == 3

        # Same agent gets same ID
        debate2 = anon.anonymize_debate([
            ("Alice", "First message."),
            ("Alice", "Second message."),
        ])
        ids2 = {msg.anonymous_id for msg in debate2.messages}
        assert len(ids2) == 1  # Same agent = same ID

    def test_transcript_rendering(self):
        """Transcript should be verifier-readable."""
        anon = IdentityAnonymizer()
        debate = anon.anonymize_debate([
            ("Researcher", "Finding: the cache hit rate is 95%."),
            ("Skeptic", "But what about cold starts?"),
        ])
        transcript = debate.to_transcript()
        assert "[Agent-" in transcript
        assert "Researcher" not in transcript
        assert "Skeptic" not in transcript
        assert "cache hit rate is 95%" in transcript

    def test_attribute_verdict(self):
        """Post-verdict attribution should recover real names."""
        anon = IdentityAnonymizer()
        debate = anon.anonymize_debate([
            ("Alice", "Claim A."),
            ("Bob", "Claim B."),
        ])
        anon_id = debate.messages[0].anonymous_id
        real_name, _ = debate.attribute_verdict(anon_id, "confirmed")
        assert real_name == "Alice"

    def test_ibc_zero_when_no_self_votes(self):
        """IBC should be 0 when no agent votes on their own work."""
        anon = IdentityAnonymizer()
        votes = [
            ("Alice", "Bob", True),
            ("Alice", "Charlie", False),
            ("Bob", "Charlie", True),
        ]
        ibc = anon.compute_ibc(votes)
        assert ibc == 0.0

    def test_ibc_positive_when_self_bias(self):
        """IBC should be positive when agents favor their own work."""
        anon = IdentityAnonymizer()
        votes = [
            ("Alice", "Alice", True),   # Self-agreement
            ("Alice", "Bob", False),    # Disagree with others
            ("Bob", "Bob", True),       # Self-agreement
            ("Bob", "Alice", False),    # Disagree with others
        ]
        ibc = anon.compute_ibc(votes)
        assert ibc > 0.0  # Positive self-bias
