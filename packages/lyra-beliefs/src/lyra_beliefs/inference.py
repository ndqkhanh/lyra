"""Belief-based inference: deductive, inductive, abductive, default reasoning, confidence propagation."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

import numpy as np

from .belief_system import Belief, BeliefSource, BeliefSystem
from .knowledge_base import KnowledgeBase, Rule, RuleType
from .exceptions import InferenceError

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class InferenceType(Enum):
    """Types of logical inference."""

    DEDUCTION = auto()      # From general to specific
    INDUCTION = auto()      # From specific to general
    ABDUCTION = auto()      # Best explanation
    DEFAULT = auto()        # Defeasible (default) reasoning
    ANALOGICAL = auto()     # Reasoning by analogy


@dataclass
class InferenceResult:
    """Result of an inference operation.

    Attributes:
        inferred_beliefs: New beliefs produced.
        inference_type: How they were inferred.
        premises_used: Premise belief IDs.
        rules_used: Rule IDs applied.
        confidence: Confidence in the inferred result.
        explanation: Human-readable chain of reasoning.
        timestamp: When inferred.
    """

    inferred_beliefs: list[Belief] = field(default_factory=list)
    inference_type: InferenceType = InferenceType.DEDUCTION
    premises_used: list[str] = field(default_factory=list)
    rules_used: list[str] = field(default_factory=list)
    confidence: float = 0.0
    explanation: str = ""
    timestamp: float = field(default_factory=time.time)


# ── Inference Engine ────────────────────────────────────────────────────


class InferenceEngine:
    """Multi-strategy inference engine operating over beliefs and rules.

    Supports deduction, induction, abduction, and default reasoning
    with confidence propagation through the inference chain.
    """

    def __init__(
        self,
        belief_system: BeliefSystem,
        knowledge_base: Optional[KnowledgeBase] = None,
    ) -> None:
        self.belief_system = belief_system
        self.knowledge_base = knowledge_base
        self._inference_history: list[InferenceResult] = []

    # ── Deductive inference ────────────────────────────────────────────

    def deduce(
        self,
        premises: list[str],  # belief_ids
        max_steps: int = 10,
    ) -> InferenceResult:
        """Perform deductive inference from premises.

        Forward-chaining: starting from known premises, apply rules
        to derive new conclusions.

        Args:
            premises: Starting belief IDs.
            max_steps: Maximum inference steps.

        Returns:
            InferenceResult with deduced beliefs.
        """
        known: set[str] = set(premises)
        new_beliefs: list[Belief] = []
        rules_applied: list[str] = []
        explanation_parts: list[str] = []

        for step in range(max_steps):
            new_found = False

            for rule_id, rule in self.knowledge_base._rules.items() if self.knowledge_base else []:
                if rule_id in rules_applied:
                    continue

                # Check if antecedent matches known beliefs
                antecedent_words = set(rule.antecedent.lower().split())
                matched_beliefs = []

                for belief_id in known:
                    belief = self.belief_system.get(belief_id) if belief_id in self.belief_system._beliefs else None
                    if belief is None:
                        continue
                    belief_words = set(belief.statement.lower().split())
                    if antecedent_words & belief_words:
                        matched_beliefs.append(belief)

                if matched_beliefs:
                    # Derive consequent
                    best_match = max(matched_beliefs, key=lambda b: b.confidence)
                    inferred_confidence = (
                        best_match.confidence * rule.confidence
                        * 0.8  # Penalty for inference uncertainty
                    )

                    # Create new belief from consequent
                    new_belief = self.belief_system.create_belief(
                        domain=rule.domain,
                        statement=rule.consequent,
                        confidence=inferred_confidence,
                        source=BeliefSource.INFERRED,
                        evidence=[f"Deduced from: {best_match.statement}"],
                        source_reliability=rule.confidence,
                    )

                    new_beliefs.append(new_belief)
                    known.add(new_belief.belief_id)
                    rules_applied.append(rule_id)
                    explanation_parts.append(
                        f"{rule.name}: {rule.antecedent} -> {rule.consequent}"
                    )
                    new_found = True

            if not new_found:
                break

        confidence = (
            np.mean([b.confidence for b in new_beliefs]) if new_beliefs else 0.0
        )

        result = InferenceResult(
            inferred_beliefs=new_beliefs,
            inference_type=InferenceType.DEDUCTION,
            premises_used=premises,
            rules_used=rules_applied,
            confidence=float(confidence),
            explanation="; ".join(explanation_parts),
        )
        self._inference_history.append(result)
        return result

    # ── Inductive inference ────────────────────────────────────────────

    def induce(
        self,
        observations: list[str],  # belief_ids of observations
        domain: str = "general",
    ) -> InferenceResult:
        """Perform inductive inference from specific observations.

        Generalizes from multiple specific observations to form
        a broader rule or belief.

        Args:
            observations: Observed belief IDs.
            domain: Domain for the generalization.

        Returns:
            InferenceResult with induced generalization.
        """
        obs_beliefs = []
        for oid in observations:
            try:
                obs_beliefs.append(self.belief_system.get(oid))
            except Exception:
                continue

        if len(obs_beliefs) < 2:
            return InferenceResult(
                inference_type=InferenceType.INDUCTION,
                confidence=0.0,
                explanation="Need at least 2 observations for induction",
            )

        # Extract common words/patterns across observations
        common_words: set[str] = set()
        first = True
        for b in obs_beliefs:
            words = set(b.statement.lower().split())
            if first:
                common_words = words
                first = False
            else:
                common_words &= words

        if not common_words or len(common_words) < 3:
            return InferenceResult(
                inference_type=InferenceType.INDUCTION,
                confidence=0.0,
                explanation="Insufficient commonality for induction",
            )

        # Build generalization
        generalization = f"Generally: {' and '.join(sorted(common_words)[:5])} are correlated"
        avg_confidence = float(np.mean([b.confidence for b in obs_beliefs]))

        # Confidence increases with number of observations (diminishing returns)
        induction_confidence = avg_confidence * (1.0 - 1.0 / (len(obs_beliefs) + 1))

        new_belief = self.belief_system.create_belief(
            domain=domain,
            statement=generalization,
            confidence=induction_confidence,
            source=BeliefSource.INFERRED,
            evidence=[b.statement for b in obs_beliefs[:5]],
            source_reliability=0.6,  # Inductive inference is inherently less certain
        )

        result = InferenceResult(
            inferred_beliefs=[new_belief],
            inference_type=InferenceType.INDUCTION,
            premises_used=observations,
            confidence=induction_confidence,
            explanation=f"Induced from {len(obs_beliefs)} observations: {generalization}",
        )
        self._inference_history.append(result)
        return result

    # ── Abductive inference ────────────────────────────────────────────

    def abduce(
        self,
        observation: str,  # belief_id
        candidate_explanations: Optional[list[str]] = None,  # belief_ids
        max_explanations: int = 5,
    ) -> InferenceResult:
        """Perform abductive reasoning: find the best explanation.

        Given an observation, finds the most plausible explanation
        among candidate hypotheses.

        Args:
            observation: Observed belief ID.
            candidate_explanations: Candidate explanatory belief IDs.
            max_explanations: Maximum explanations to return.

        Returns:
            InferenceResult with best explanation(s).
        """
        obs_belief = self.belief_system.get(observation) if observation in self.belief_system._beliefs else None
        if obs_belief is None:
            return InferenceResult(
                inference_type=InferenceType.ABDUCTION,
                confidence=0.0,
                explanation="Observation not found",
            )

        # Build candidate explanations
        candidates: list[Belief] = []
        if candidate_explanations:
            for cid in candidate_explanations:
                try:
                    candidates.append(self.belief_system.get(cid))
                except Exception:
                    continue
        else:
            # Search knowledge base for rules whose consequent matches the observation
            if self.knowledge_base:
                for rule in self.knowledge_base.get_rules_applicable_to(obs_belief.statement):
                    # The rule's antecedent is a candidate explanation
                    for bid, belief in self.belief_system._beliefs.items():
                        if rule.antecedent.lower() in belief.statement.lower():
                            candidates.append(belief)
                            break

        if not candidates:
            return InferenceResult(
                inference_type=InferenceType.ABDUCTION,
                confidence=0.0,
                explanation="No candidate explanations found",
            )

        # Score candidates:
        # 1. How well does the candidate explain the observation?
        # 2. How confident is the candidate?
        # 3. Is there a known rule linking them?
        scored: list[tuple[float, Belief, str]] = []

        for candidate in candidates:
            score = candidate.confidence * 0.4

            # Check if there is a rule linking candidate -> observation
            if self.knowledge_base:
                applicable_rules = self.knowledge_base.get_rules_applicable_to(candidate.statement)
                for rule in applicable_rules:
                    if obs_belief.statement.lower() in rule.consequent.lower():
                        score += rule.confidence * 0.4
                        break

            # Keyword overlap
            cand_words = set(candidate.statement.lower().split())
            obs_words = set(obs_belief.statement.lower().split())
            overlap = cand_words & obs_words
            score += min(0.2, len(overlap) * 0.02)

            explanation = f"{candidate.statement} -> {obs_belief.statement}"
            scored.append((score, candidate, explanation))

        scored.sort(key=lambda x: -x[0])
        top = scored[:max_explanations]

        new_beliefs = [
            self.belief_system.create_belief(
                domain=obs_belief.domain,
                statement=f"Best explanation: {candidate.statement}",
                confidence=score,
                source=BeliefSource.INFERRED,
                evidence=[obs_belief.statement, candidate.statement],
            )
            for score, candidate, _ in top
        ]

        result = InferenceResult(
            inferred_beliefs=new_beliefs,
            inference_type=InferenceType.ABDUCTION,
            premises_used=[observation],
            confidence=float(np.mean([b.confidence for b in new_beliefs])) if new_beliefs else 0.0,
            explanation="; ".join(exp for _, _, exp in top),
        )
        self._inference_history.append(result)
        return result

    # ── Default reasoning ──────────────────────────────────────────────

    def default_reason(
        self,
        query: str,
        domain: str = "general",
    ) -> InferenceResult:
        """Perform default (defeasible) reasoning.

        Uses default rules to reach conclusions that can be retracted
        when contradictory evidence appears.

        Args:
            query: The statement to reason about.
            domain: Domain for context.

        Returns:
            InferenceResult with default conclusion.
        """
        if not self.knowledge_base:
            return InferenceResult(
                inference_type=InferenceType.DEFAULT,
                confidence=0.0,
                explanation="No knowledge base for default rules",
            )

        # Find applicable default rules
        default_rules = [
            r for r in self.knowledge_base._rules.values()
            if r.rule_type == RuleType.DEFAULT and r.domain == domain
        ]

        if not default_rules:
            return InferenceResult(
                inference_type=InferenceType.DEFAULT,
                confidence=0.0,
                explanation="No default rules found",
            )

        # Match query against default rule antecedents
        query_words = set(query.lower().split())
        matched_rules: list[tuple[float, Rule]] = []

        for rule in default_rules:
            ant_words = set(rule.antecedent.lower().split())
            overlap = query_words & ant_words
            if overlap:
                score = len(overlap) / max(len(ant_words), 1) * rule.confidence
                matched_rules.append((score, rule))

        if not matched_rules:
            return InferenceResult(
                inference_type=InferenceType.DEFAULT,
                confidence=0.0,
                explanation="No applicable default rules",
            )

        matched_rules.sort(key=lambda x: -x[0])
        best_score, best_rule = matched_rules[0]

        # Check for exceptions
        has_exception = any(
            exc.lower() in query.lower() for exc in best_rule.exceptions
        )

        if has_exception:
            new_belief = self.belief_system.create_belief(
                domain=domain,
                statement=f"Exception to default: {best_rule.consequent} does NOT apply",
                confidence=0.8,
                source=BeliefSource.INFERRED,
                evidence=[f"Exception matched: {best_rule.exceptions}"],
            )
            confidence = 0.2
        else:
            new_belief = self.belief_system.create_belief(
                domain=domain,
                statement=best_rule.consequent,
                confidence=best_score * 0.7,  # Default reasoning penalty
                source=BeliefSource.INFERRED,
                evidence=[f"Default rule: {best_rule.antecedent} -> {best_rule.consequent}"],
            )
            confidence = best_score * 0.7

        result = InferenceResult(
            inferred_beliefs=[new_belief],
            inference_type=InferenceType.DEFAULT,
            rules_used=[best_rule.rule_id],
            confidence=float(confidence),
            explanation=f"Default: {best_rule.antecedent} -> {best_rule.consequent}",
        )
        self._inference_history.append(result)
        return result

    # ── Confidence propagation ─────────────────────────────────────────

    def propagate_confidence(
        self, source_belief_id: str, max_depth: int = 3
    ) -> dict[str, float]:
        """Propagate confidence changes through the belief network.

        When a belief's confidence changes, this propagates the change
        through conditional relationships to connected beliefs.

        Args:
            source_belief_id: The belief whose confidence changed.
            max_depth: Maximum propagation depth.

        Returns:
            Dict of belief_id -> new_confidence.
        """
        source = self.belief_system.get(source_belief_id) if source_belief_id in self.belief_system._beliefs else None
        if source is None:
            return {}

        changes: dict[str, float] = {}
        visited: set[str] = {source_belief_id}
        queue: list[tuple[str, int]] = [(source_belief_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            current = self.belief_system.get(current_id) if current_id in self.belief_system._beliefs else None
            if current is None:
                continue

            for bid, belief in self.belief_system._beliefs.items():
                if bid in visited:
                    continue
                if belief.status.value != 1:  # Skip retracted
                    continue

                # Check conditional relationship
                prob = self.belief_system.get_conditional(current_id, bid)
                if prob > 0.5:  # Only propagate if there's a positive relationship
                    influence = (prob - 0.5) * 2.0  # Normalize to [0, 1]
                    new_conf = belief.confidence + (
                        (current.confidence - 0.5) * influence * 0.3
                    )
                    new_conf = max(0.0, min(1.0, new_conf))

                    if abs(new_conf - belief.confidence) > 0.01:
                        changes[bid] = new_conf
                        visited.add(bid)
                        queue.append((bid, depth + 1))

        # Apply changes
        for bid, new_conf in changes.items():
            self.belief_system._beliefs[bid].confidence = new_conf
            self.belief_system._beliefs[bid].last_updated = time.time()

        return changes

    # ── History ────────────────────────────────────────────────────────

    @property
    def inference_history(self) -> list[InferenceResult]:
        """Get all inference history."""
        return list(self._inference_history)

    @property
    def recent_inferences(self, n: int = 10) -> list[InferenceResult]:
        """Get the n most recent inferences."""
        return list(self._inference_history[-n:])

    @property
    def summary(self) -> dict[str, Any]:
        """Get inference engine summary."""
        by_type: dict[str, int] = {}
        for inf in self._inference_history:
            by_type[inf.inference_type.name] = by_type.get(inf.inference_type.name, 0) + 1

        total_beliefs_inferred = sum(
            len(inf.inferred_beliefs) for inf in self._inference_history
        )

        return {
            "total_inferences": len(self._inference_history),
            "by_type": by_type,
            "total_beliefs_inferred": total_beliefs_inferred,
            "avg_confidence": float(np.mean(
                [inf.confidence for inf in self._inference_history]
            )) if self._inference_history else 0.0,
        }
