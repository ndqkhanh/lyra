"""Integration tests — Phase I modules working together."""

from lyra.memory.admission_control import AdmissionController, ContentType
from lyra.verification.anonymizer import IdentityAnonymizer
from lyra.context.anx_protocol import ANXCompressor, ANXSegment


class TestAdmissionToAnonymizedVerification:
    """A-MAC gates memory → anonymized panel verifies it."""

    def test_full_pipeline(self):
        # 1. Classify and admit a memory
        ctrl = AdmissionController(threshold=0.45)
        score = ctrl.evaluate(
            content="The system architecture uses event-driven microservices",
            content_type=ContentType.FACT,
            confidence=0.90,
        )
        assert score.admit

        # 2. Anonymize the verification debate about this memory
        anon = IdentityAnonymizer()
        debate = anon.anonymize_debate([
            ("Memory Curator", f"Admitted (score={score.combined:.2f}): system uses event-driven microservices"),
            ("Verifier", "Verified against architecture docs: consistent"),
        ])
        assert len(debate.messages) == 2
        assert "Memory Curator" not in debate.to_transcript()

    def test_rejected_memory_not_verified(self):
        """Rejected memories skip verification entirely."""
        ctrl = AdmissionController(threshold=0.95)
        score = ctrl.evaluate(
            content="duplicate duplicate duplicate",
            content_type=ContentType.UNKNOWN,
            confidence=0.30,
        )
        assert not score.admit  # Rejected — no verification needed


class TestAnonymizedVerificationWithANX:
    """Anonymized debate → ANX compression for context efficiency."""

    def test_debate_compression(self):
        # 1. Create an anonymized debate
        anon = IdentityAnonymizer()
        debate = anon.anonymize_debate([
            ("Senior AI Researcher", "The HippoRAG paper shows 10-30x cost reduction for multi-hop retrieval."),
            ("Adversarial Skeptic", "But the evaluation was only on single-hop queries — multi-hop is unproven."),
            ("Senior Software Architect", "We can integrate it as a progressive enhancement behind the vector DB."),
        ])

        # 2. Compress the debate transcript with ANX
        comp = ANXCompressor()
        transcript = debate.to_transcript()

        # Simulate: wrapping the transcript as tool exchange data
        msg = comp.wrap_data_exchange(
            tool_name="verification_panel",
            data=transcript,
            direction="out",
        )

        compact = msg.to_compact()
        assert len(compact) < len(transcript)
        assert msg.segment == ANXSegment.EXCHANGE

    def test_ibc_computation_on_anonymized_votes(self):
        """IBC should be near-zero after anonymization (the whole point)."""
        anon = IdentityAnonymizer()
        debate = anon.anonymize_debate([
            ("Agent A", "Finding: cache hit rate 95%."),
            ("Agent B", "Finding confirmed."),
            ("Agent C", "Finding confirmed."),
        ])

        # Simulate votes where agents evaluate each other's claims
        anon_ids = [m.anonymous_id for m in debate.messages]
        votes = [
            (anon_ids[0], anon_ids[0], True),   # Agent A agrees with self
            (anon_ids[0], anon_ids[1], True),   # Agent A agrees with B
            (anon_ids[1], anon_ids[0], True),   # Agent B agrees with A
        ]

        ibc = anon.compute_ibc(votes)
        # With anonymization, self-bias should be minimal
        assert ibc < 0.5  # Low self-bias after anonymization


class TestANXCompressionPipeline:
    """Full ANX compression: tool call → result → estimation."""

    def test_tool_call_to_result_cycle(self):
        comp = ANXCompressor()

        # Expression: what the agent wants
        expr = comp.wrap_tool_call(
            intent="Search the memory graph for entities related to authentication",
            tool_name="memory_search",
            payload={"query": "authentication", "top_k": 20, "graph_traversal": "pagerank"},
        )
        assert expr.segment == ANXSegment.EXPRESSION

        # Execution: what the tool returned
        exec_msg = comp.wrap_tool_result(
            tool_name="memory_search",
            result={"entities": ["OAuth2", "JWT", "API Key", "Session Token"], "count": 4},
            status="ok",
        )
        assert exec_msg.segment == ANXSegment.EXECUTION

        # Verify savings
        full_json = '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"memory_search","arguments":{"query":"authentication","top_k":20,"graph_traversal":"pagerank"}},"id":1}'
        savings = comp.estimate_savings(full_json, expr.to_compact())
        assert savings["reduction_pct"] > 20
