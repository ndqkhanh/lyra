"""
Identity Anonymizer for the Adversarial Verification Panel.

Implements response anonymization from "When Identity Skews Debate"
(UW-Madison, arXiv 2510.07517). Strips identity markers so verifiers
cannot tell self from peer, eliminating identity-driven sycophancy
and self-bias in multi-agent debate.

References
----------
- When Identity Skews Debate: Identity-Driven Sycophancy in Multi-Agent
  Debate. Choi, Zhu, Li. UW-Madison, arXiv 2510.07517v5
- Actor-Observer Asymmetry in Multi-Agent Role-Play.
  Li et al., arXiv 2604.19548v1
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class AnonymizedMessage:
    """A message with identity markers stripped.

    Attributes:
        anonymous_id: Opaque identifier (e.g. "Agent-7a3f") — verifiers
            can distinguish DIFFERENT speakers but cannot tell WHO.
        content: The message body with all identity markers removed.
        original_agent_name: The real agent name (stored for attribution
            AFTER the verdict, never shown to verifiers).
    """

    anonymous_id: str
    content: str
    original_agent_name: str


@dataclass
class AnonymizedDebate:
    """A complete debate transcript with identities anonymized.

    Attributes:
        messages: Anonymized messages in chronological order.
        id_map: Reverse mapping from anonymous_id → real agent name
            (for post-verdict attribution).
    """

    messages: list[AnonymizedMessage] = field(default_factory=list)
    id_map: dict[str, str] = field(default_factory=dict)

    def to_transcript(self) -> str:
        """Render the anonymized transcript for verifier consumption."""
        lines = []
        for msg in self.messages:
            lines.append(f"[{msg.anonymous_id}]: {msg.content}")
        return "\n\n".join(lines)

    def attribute_verdict(
        self, anonymous_id: str, verdict: str
    ) -> tuple[str, str]:
        """Map an anonymous ID back to the real agent name."""
        real_name = self.id_map.get(anonymous_id, "unknown")
        return real_name, verdict


class IdentityAnonymizer:
    """Strips identity markers from agent messages.

    Identity markers include:
    - Agent names ("Skeptic", "Researcher", "Senior Architect", etc.)
    - Role descriptions ("I am the security reviewer...", "As a senior...")
    - Self-references that reveal the speaker's role
    - Attribution phrases ("From my perspective as...", "Speaking as the...")

    Usage::

        anonymizer = IdentityAnonymizer()
        debate = anonymizer.anonymize_debate([
            ("Skeptic", "As the contrarian, I believe this design is flawed..."),
            ("Architect", "From an architecture perspective, the system..."),
        ])
        transcript = debate.to_transcript()
        # "[Agent-7a3f]: I believe this design is flawed..."
        # "[Agent-b2d1]: The system architecture should..."
    """

    # Patterns that reveal agent identity/role
    _IDENTITY_PATTERNS: list[re.Pattern] = [
        # Role self-descriptions
        re.compile(
            r"(?:as|speaking as|from my perspective as)\s+(?:the\s+)?"
            r"(?:senior\s+)?(?:ai\s+)?"
            r"(?:solutions?\s+)?(?:software\s+)?(?:backend\s+)?"
            r"(?:frontend\s+)?(?:security\s+)?(?:data\s+)?"
            r"(?:ml\s+)?(?:systems?\s+)?"
            r"(?:architect|engineer|researcher|reviewer|scientist|"
            r"designer|manager|writer|specialist|expert|consultant|"
            r"skeptic|contrarian|advisor|analyst|developer)",
            re.IGNORECASE,
        ),
        # "I am the [role]"
        re.compile(
            r"i(?:'m|\s+am)\s+(?:the\s+)?(?:senior\s+)?(?:ai\s+)?"
            r"(?:solutions?\s+)?(?:software\s+)?"
            r"(?:architect|engineer|researcher|reviewer|scientist|"
            r"designer|manager|writer|specialist|expert|consultant|"
            r"skeptic|contrarian)",
            re.IGNORECASE,
        ),
        # "my role is [role]"
        re.compile(
            r"my\s+role\s+(?:is|as)\s+(?:the\s+)?(?:senior\s+)?"
            r"(?:architect|engineer|researcher|reviewer|scientist)",
            re.IGNORECASE,
        ),
        # Domain claims: "in my domain of [X]" / "my expertise in [X]"
        re.compile(
            r"(?:in\s+)?my\s+(?:domain|expertise|specialty|area|field)\s+(?:of|in|is)",
            re.IGNORECASE,
        ),
    ]

    # Agent name patterns to strip from content
    _NAME_PATTERNS: list[str] = [
        "Senior AI Solutions Architect",
        "Senior Software Architect",
        "Senior Backend Engineer",
        "Senior AI Researcher",
        "Senior AI Engineer",
        "Senior SRE",
        "Senior Security Engineer",
        "Senior Distributed-Systems Engineer",
        "Senior Data Engineer",
        "Senior Knowledge Engineer",
        "Senior Product Manager",
        "Senior Product Designer",
        "Senior UX Designer",
        "Senior Technical Writer",
        "Senior ML Evaluation Scientist",
        "Senior Performance Engineer",
        "Senior Cost Engineer",
        "Senior Planning Specialist",
        "Senior Reasoning Specialist",
        "Senior AI Safety Engineer",
        "Senior Alignment Engineer",
        "Senior Voice Engineer",
        "Senior Audio Engineer",
        "Senior Realtime Engineer",
        "Adversarial Red-Team",
        "Adversarial Skeptic",
        "Skeptic",
        "the contrarian",
        "Solutions Architect",
        "Software Architect",
        "Backend Engineer",
        "AI Researcher",
        "LLMOps Engineer",
        "Reliability Engineer",
        "Security Engineer",
        "Distributed Systems Engineer",
        "Data Engineer",
        "Knowledge Engineer",
        "Product Manager",
        "UX Designer",
        "Technical Writer",
        "Evaluation Scientist",
        "Benchmark Scientist",
        "Performance Engineer",
        "Cost Engineer",
        "Planning Specialist",
        "Reasoning Specialist",
        "AI Safety Engineer",
        "Alignment Engineer",
        "Voice Engineer",
        "Audio Engineer",
        "Realtime Engineer",
    ]

    def __init__(self) -> None:
        self._name_lookup: set[str] = {n.lower() for n in self._NAME_PATTERNS}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def anonymize_debate(
        self, messages: list[tuple[str, str]]
    ) -> AnonymizedDebate:
        """Anonymize a full debate transcript.

        Args:
            messages: List of (agent_name, message_content) tuples in
                chronological order.

        Returns:
            AnonymizedDebate with all identity markers removed.
        """
        # Assign anonymous IDs per unique agent name
        name_to_anon: dict[str, str] = {}
        debate = AnonymizedDebate()

        for agent_name, content in messages:
            if agent_name not in name_to_anon:
                name_to_anon[agent_name] = f"Agent-{uuid.uuid4().hex[:4]}"

            anon_id = name_to_anon[agent_name]
            cleaned = self.strip_identity(content, agent_name)

            debate.messages.append(
                AnonymizedMessage(
                    anonymous_id=anon_id,
                    content=cleaned,
                    original_agent_name=agent_name,
                )
            )
            debate.id_map[anon_id] = agent_name

        return debate

    def strip_identity(self, content: str, agent_name: str = "") -> str:
        """Strip identity markers from a single message.

        Args:
            content: The original message text.
            agent_name: The agent's name (used for name-specific stripping).

        Returns:
            Content with identity markers removed or replaced.
        """
        result = content

        # 1. Remove the agent's own name
        if agent_name:
            # Case-insensitive replacement of the full name
            result = re.sub(
                re.escape(agent_name),
                "[speaker]",
                result,
                flags=re.IGNORECASE,
            )

        # 2. Remove any known agent name patterns
        for name in sorted(self._name_lookup, key=len, reverse=True):
            result = re.sub(
                re.escape(name),
                "[speaker]",
                result,
                flags=re.IGNORECASE,
            )

        # 3. Remove role self-description patterns
        for pattern in self._IDENTITY_PATTERNS:
            result = pattern.sub("[speaker]", result)

        # 4. Remove trailing attribution (common in debate formats)
        result = re.sub(r"\s*--\s*\[speaker\]\s*$", "", result)
        result = re.sub(r"\s*\(\s*\[speaker\]\s*\)\s*$", "", result)

        return result.strip()

    def compute_ibc(
        self, votes: list[tuple[str, str, bool]]
    ) -> float:
        """Compute the Identity Bias Coefficient (IBC).

        IBC measures how much identity affects voting. Values near 0 mean
        identity doesn't matter; values near 1 mean identity is the dominant
        factor.

        Reference: Choi et al. §3.2, "Identity Bias Coefficient."

        Args:
            votes: List of (voter_name, target_name, agree?) tuples.

        Returns:
            IBC score (0 = no bias, 1 = extreme bias).
        """
        if not votes:
            return 0.0

        # Group agreements by whether voter and target are the same agent
        self_agreements = []
        other_agreements = []

        for voter, target, agree in votes:
            if voter == target:
                self_agreements.append(1.0 if agree else 0.0)
            else:
                other_agreements.append(1.0 if agree else 0.0)

        if not other_agreements:
            return 0.0

        self_rate = (
            sum(self_agreements) / len(self_agreements)
            if self_agreements
            else 0.0
        )
        other_rate = sum(other_agreements) / len(other_agreements)

        # IBC = difference in agreement rates (self-bias)
        ibc = max(0.0, self_rate - other_rate)
        return round(ibc, 4)
