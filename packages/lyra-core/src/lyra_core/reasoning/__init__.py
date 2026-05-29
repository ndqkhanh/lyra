"""
Multi-Hop Reasoning System

Tracks reasoning chains across multiple context layers.

Features:
- Reasoning chain tracking
- Multi-step inference
- Evidence linking
- Provenance tracking
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import time


class ReasoningType(Enum):
    """Types of reasoning steps"""
    RETRIEVAL = "retrieval"
    INFERENCE = "inference"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"
    CONTRADICTION = "contradiction"


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain"""
    id: str
    type: ReasoningType
    content: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    def add_evidence(self, evidence_id: str):
        """Add evidence to this step"""
        if evidence_id not in self.evidence:
            self.evidence.append(evidence_id)


@dataclass
class ReasoningChain:
    """A chain of reasoning steps"""
    id: str
    steps: List[ReasoningStep] = field(default_factory=list)
    conclusion: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)

    def add_step(self, step: ReasoningStep):
        """Add a step to the chain"""
        self.steps.append(step)
        # Update chain confidence (minimum of all steps)
        if self.steps:
            self.confidence = min(s.confidence for s in self.steps)

    def get_evidence_chain(self) -> List[str]:
        """Get all evidence IDs in the chain"""
        evidence = []
        for step in self.steps:
            evidence.extend(step.evidence)
        return evidence

    def get_step_count(self) -> int:
        """Get number of steps in chain"""
        return len(self.steps)


class MultiHopReasoner:
    """
    Multi-hop reasoning system

    Tracks reasoning chains across multiple steps and layers,
    maintaining provenance and evidence links.
    """

    def __init__(self):
        self.chains: Dict[str, ReasoningChain] = {}
        self.steps: Dict[str, ReasoningStep] = {}
        self._step_counter = 0
        self._chain_counter = 0

    def create_chain(self, metadata: Optional[Dict] = None) -> ReasoningChain:
        """Create a new reasoning chain"""
        chain_id = f"chain_{self._chain_counter}"
        self._chain_counter += 1

        chain = ReasoningChain(
            id=chain_id,
            metadata=metadata or {}
        )
        self.chains[chain_id] = chain
        return chain

    def add_step(
        self,
        chain_id: str,
        type: ReasoningType,
        content: str,
        evidence: Optional[List[str]] = None,
        confidence: float = 1.0
    ) -> ReasoningStep:
        """Add a reasoning step to a chain"""
        if chain_id not in self.chains:
            raise ValueError(f"Chain {chain_id} not found")

        step_id = f"step_{self._step_counter}"
        self._step_counter += 1

        step = ReasoningStep(
            id=step_id,
            type=type,
            content=content,
            evidence=evidence or [],
            confidence=confidence
        )

        self.steps[step_id] = step
        self.chains[chain_id].add_step(step)

        return step

    def link_evidence(self, step_id: str, evidence_id: str):
        """Link evidence to a reasoning step"""
        if step_id not in self.steps:
            raise ValueError(f"Step {step_id} not found")

        self.steps[step_id].add_evidence(evidence_id)

    def conclude_chain(self, chain_id: str, conclusion: str):
        """Set conclusion for a reasoning chain"""
        if chain_id not in self.chains:
            raise ValueError(f"Chain {chain_id} not found")

        self.chains[chain_id].conclusion = conclusion

    def get_chain(self, chain_id: str) -> Optional[ReasoningChain]:
        """Get a reasoning chain by ID"""
        return self.chains.get(chain_id)

    def find_chains_with_evidence(self, evidence_id: str) -> List[ReasoningChain]:
        """Find all chains that use specific evidence"""
        matching_chains = []

        for chain in self.chains.values():
            if evidence_id in chain.get_evidence_chain():
                matching_chains.append(chain)

        return matching_chains

    def find_contradictions(self) -> List[tuple]:
        """Find contradictory reasoning chains"""
        contradictions = []

        # Look for chains with contradiction steps
        for chain in self.chains.values():
            for step in chain.steps:
                if step.type == ReasoningType.CONTRADICTION:
                    contradictions.append((chain.id, step.id))

        return contradictions

    def get_reasoning_path(self, chain_id: str) -> List[str]:
        """Get the reasoning path as a list of step contents"""
        chain = self.chains.get(chain_id)
        if not chain:
            return []

        path = [step.content for step in chain.steps]
        if chain.conclusion:
            path.append(f"Conclusion: {chain.conclusion}")

        return path

    def get_stats(self) -> Dict:
        """Get reasoning statistics"""
        if not self.chains:
            return {
                'total_chains': 0,
                'total_steps': 0,
                'avg_chain_length': 0.0
            }

        total_steps = sum(len(chain.steps) for chain in self.chains.values())
        avg_length = total_steps / len(self.chains)

        # Count by reasoning type
        type_counts = {}
        for step in self.steps.values():
            type_name = step.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            'total_chains': len(self.chains),
            'total_steps': total_steps,
            'avg_chain_length': avg_length,
            'avg_confidence': sum(c.confidence for c in self.chains.values()) / len(self.chains),
            'by_type': type_counts,
            'contradictions': len(self.find_contradictions())
        }

    def visualize_chain(self, chain_id: str) -> str:
        """Create a text visualization of a reasoning chain"""
        chain = self.chains.get(chain_id)
        if not chain:
            return f"Chain {chain_id} not found"

        lines = [f"Reasoning Chain: {chain_id}"]
        lines.append(f"Confidence: {chain.confidence:.2f}")
        lines.append("")

        for i, step in enumerate(chain.steps, 1):
            lines.append(f"{i}. [{step.type.value}] {step.content}")
            if step.evidence:
                lines.append(f"   Evidence: {', '.join(step.evidence)}")
            lines.append(f"   Confidence: {step.confidence:.2f}")
            lines.append("")

        if chain.conclusion:
            lines.append(f"Conclusion: {chain.conclusion}")

        return "\n".join(lines)
