"""Domain knowledge storage: fact storage with provenance, rule storage, ontology alignment, versioning."""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .belief_system import BeliefSource, BeliefSystem

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class RuleType(Enum):
    """Types of rules in the knowledge base."""

    IF_THEN = auto()        # Simple conditional
    DEFAULT = auto()        # Defeasible default rule
    STRICT = auto()         # Must-always-hold rule
    PRAGMATIC = auto()      # Heuristic/rule of thumb
    ONTOLOGICAL = auto()    # Domain ontology constraint


@dataclass
class Rule:
    """A rule in the knowledge base.

    Attributes:
        rule_id: Unique identifier.
        name: Human-readable name.
        rule_type: Type of rule.
        antecedent: The 'if' part (condition).
        consequent: The 'then' part (result).
        confidence: Confidence in this rule (0-1).
        domain: Knowledge domain.
        exceptions: Known exceptions to this rule.
        source: Where the rule came from.
        timestamp: When created.
        version: Rule version number.
    """

    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    rule_type: RuleType = RuleType.IF_THEN
    antecedent: str = ""
    consequent: str = ""
    confidence: float = 0.7
    domain: str = "general"
    exceptions: list[str] = field(default_factory=list)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    version: int = 1


@dataclass
class Fact:
    """A fact in the knowledge base with provenance tracking.

    Attributes:
        fact_id: Unique identifier.
        statement: The fact statement.
        domain: Knowledge domain.
        truth_value: 1.0 = true, 0.0 = false, in between = uncertain.
        provenance: Where this fact came from.
        source_document: Reference document.
        extraction_method: How the fact was extracted.
        timestamp: When added.
        verified: Whether the fact has been verified.
        version: Fact version for versioning support.
    """

    fact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    statement: str = ""
    domain: str = "general"
    truth_value: float = 1.0
    provenance: str = ""
    source_document: str = ""
    extraction_method: str = ""
    timestamp: float = field(default_factory=time.time)
    verified: bool = False
    version: int = 1


@dataclass
class OntologyConcept:
    """A concept in the domain ontology.

    Attributes:
        concept_id: Unique identifier.
        name: Concept name.
        parent: Parent concept (broader term).
        children: Child concepts (narrower terms).
        synonyms: Alternative names.
        domain: Knowledge domain.
        description: Human-readable description.
    """

    concept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    domain: str = "general"
    description: str = ""


@dataclass
class KnowledgeVersion:
    """A versioned snapshot of the knowledge base.

    Attributes:
        version_id: Unique version identifier.
        version_number: Sequential version number.
        timestamp: When created.
        description: What changed.
        fact_ids: Fact IDs at this version.
        rule_ids: Rule IDs at this version.
    """

    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version_number: int = 1
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    fact_ids: list[str] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)


# ── Knowledge Base ──────────────────────────────────────────────────────


class KnowledgeBase:
    """Domain knowledge storage with provenance tracking and versioning.

    Stores facts, rules, and ontology concepts, tracks their provenance,
    supports versioned snapshots, and provides ontology alignment utilities.
    """

    def __init__(self, belief_system: BeliefSystem | None = None) -> None:
        self.belief_system = belief_system or BeliefSystem()

        self._facts: dict[str, Fact] = {}
        self._rules: dict[str, Rule] = {}
        self._concepts: dict[str, OntologyConcept] = {}
        self._concept_index: dict[str, str] = {}  # synonym -> concept_id
        self._versions: deque[KnowledgeVersion] = deque(maxlen=100)
        self._current_version: int = 1

    # ── Fact management ────────────────────────────────────────────────

    def add_fact(self, fact: Fact) -> Fact:
        """Add a fact with provenance tracking.

        Automatically creates a corresponding belief.

        Args:
            fact: The fact to add.

        Returns:
            The added fact.
        """
        self._facts[fact.fact_id] = fact
        fact.version = self._current_version

        # Create corresponding belief
        if not self.belief_system._beliefs.get(f"fact_{fact.fact_id}"):
            self.belief_system.create_belief(
                domain=fact.domain,
                statement=fact.statement,
                confidence=fact.truth_value,
                source=BeliefSource.IMPORTED,
                evidence=[fact.provenance] if fact.provenance else [],
                source_reliability=1.0 if fact.verified else 0.5,
            )

        logger.debug("Fact added: %s [%s]", fact.fact_id[:8], fact.domain)
        return fact

    def create_fact(
        self,
        domain: str,
        statement: str,
        provenance: str = "",
        truth_value: float = 1.0,
    ) -> Fact:
        """Create and add a fact (convenience method)."""
        fact = Fact(
            domain=domain,
            statement=statement,
            truth_value=truth_value,
            provenance=provenance,
        )
        return self.add_fact(fact)

    def get_fact(self, fact_id: str) -> Fact | None:
        """Get a fact by ID."""
        return self._facts.get(fact_id)

    def get_facts_by_domain(self, domain: str) -> list[Fact]:
        """Get all facts in a domain."""
        return [f for f in self._facts.values() if f.domain == domain]

    def get_verified_facts(self) -> list[Fact]:
        """Get all verified facts."""
        return [f for f in self._facts.values() if f.verified]

    def verify_fact(self, fact_id: str, verified: bool = True) -> bool:
        """Mark a fact as verified or unverified.

        Returns:
            True if the fact was found and updated.
        """
        fact = self._facts.get(fact_id)
        if fact is None:
            return False
        fact.verified = verified
        return True

    # ── Rule management ────────────────────────────────────────────────

    def add_rule(self, rule: Rule) -> Rule:
        """Add a rule to the knowledge base.

        Args:
            rule: The rule to add.

        Returns:
            The added rule.
        """
        self._rules[rule.rule_id] = rule
        rule.version = self._current_version

        # Register conditional probability
        self.belief_system.set_conditional(
            rule.antecedent, rule.consequent, rule.confidence
        )

        logger.debug("Rule added: %s (%s -> %s)", rule.rule_id[:8],
                    rule.antecedent[:30], rule.consequent[:30])
        return rule

    def create_rule(
        self,
        antecedent: str,
        consequent: str,
        confidence: float = 0.7,
        rule_type: RuleType = RuleType.IF_THEN,
        domain: str = "general",
    ) -> Rule:
        """Create and add a rule (convenience method)."""
        rule = Rule(
            antecedent=antecedent,
            consequent=consequent,
            confidence=confidence,
            rule_type=rule_type,
            domain=domain,
        )
        return self.add_rule(rule)

    def get_rule(self, rule_id: str) -> Rule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def get_rules_by_domain(self, domain: str) -> list[Rule]:
        """Get all rules in a domain."""
        return [r for r in self._rules.values() if r.domain == domain]

    def get_rules_applicable_to(self, condition: str) -> list[Rule]:
        """Find rules whose antecedent matches a condition.

        Uses keyword matching to identify applicable rules.

        Args:
            condition: The condition to match against antecedents.

        Returns:
            List of applicable rules, sorted by confidence.
        """
        condition_lower = condition.lower()
        condition_words = set(condition_lower.split())

        scored: list[tuple[float, Rule]] = []
        for rule in self._rules.values():
            antecedent_words = set(rule.antecedent.lower().split())
            overlap = condition_words & antecedent_words
            if overlap:
                score = len(overlap) / max(len(antecedent_words), 1)
                score *= rule.confidence
                scored.append((score, rule))

        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored]

    # ── Ontology management ────────────────────────────────────────────

    def add_concept(self, concept: OntologyConcept) -> OntologyConcept:
        """Add an ontology concept.

        Args:
            concept: The concept to add.

        Returns:
            The added concept.
        """
        self._concepts[concept.concept_id] = concept
        for synonym in concept.synonyms:
            self._concept_index[synonym.lower()] = concept.concept_id
        self._concept_index[concept.name.lower()] = concept.concept_id

        logger.debug("Concept added: %s [%s]", concept.name, concept.domain)
        return concept

    def get_concept(self, name_or_synonym: str) -> OntologyConcept | None:
        """Look up a concept by name or synonym."""
        concept_id = self._concept_index.get(name_or_synonym.lower())
        if concept_id:
            return self._concepts.get(concept_id)
        return None

    def get_concept_hierarchy(self, concept_id: str) -> dict[str, Any]:
        """Get the full concept hierarchy (ancestors and descendants).

        Args:
            concept_id: The root concept.

        Returns:
            Dict with parent, children, and depth.
        """
        concept = self._concepts.get(concept_id)
        if not concept:
            return {}

        def _get_ancestors(cid: str) -> list[str]:
            c = self._concepts.get(cid)
            if not c or not c.parent:
                return []
            return [c.parent] + _get_ancestors(c.parent)

        def _get_descendants(cid: str) -> list[str]:
            c = self._concepts.get(cid)
            if not c:
                return []
            result = list(c.children)
            for child in c.children:
                result.extend(_get_descendants(child))
            return result

        return {
            "concept": concept.name,
            "parent": concept.parent,
            "ancestors": _get_ancestors(concept_id),
            "children": concept.children,
            "descendants": _get_descendants(concept_id),
            "synonyms": concept.synonyms,
        }

    def align_concepts(self, source_name: str, target_name: str) -> bool:
        """Align two concepts as synonyms (ontology alignment).

        After alignment, both names refer to the same concept.

        Args:
            source_name: The source concept name.
            target_name: The target concept name.

        Returns:
            True if alignment was successful.
        """
        source = self.get_concept(source_name)
        target = self.get_concept(target_name)

        if not source or not target:
            return False

        if target_name.lower() not in source.synonyms:
            source.synonyms.append(target_name.lower())
            self._concept_index[target_name.lower()] = source.concept_id

        logger.info("Aligned concept '%s' -> '%s'", source_name, target_name)
        return True

    # ── Versioning ─────────────────────────────────────────────────────

    def create_version(self, description: str = "") -> KnowledgeVersion:
        """Create a versioned snapshot of the current knowledge state.

        Args:
            description: Description of changes in this version.

        Returns:
            The created version snapshot.
        """
        self._current_version += 1

        version = KnowledgeVersion(
            version_number=self._current_version,
            description=description,
            fact_ids=list(self._facts.keys()),
            rule_ids=list(self._rules.keys()),
        )
        self._versions.append(version)

        logger.info("Knowledge version %d created: %s", self._current_version, description)
        return version

    def get_version(self, version_number: int) -> KnowledgeVersion | None:
        """Get a specific version."""
        for v in self._versions:
            if v.version_number == version_number:
                return v
        return None

    def get_latest_version(self) -> KnowledgeVersion | None:
        """Get the most recent version."""
        return self._versions[-1] if self._versions else None

    # ── Statistics ─────────────────────────────────────────────────────

    @property
    def fact_count(self) -> int:
        """Number of facts."""
        return len(self._facts)

    @property
    def rule_count(self) -> int:
        """Number of rules."""
        return len(self._rules)

    @property
    def concept_count(self) -> int:
        """Number of ontology concepts."""
        return len(self._concepts)

    @property
    def summary(self) -> dict[str, Any]:
        """Get knowledge base summary."""
        by_domain: dict[str, dict[str, int]] = {}
        for f in self._facts.values():
            if f.domain not in by_domain:
                by_domain[f.domain] = {"facts": 0, "rules": 0}
            by_domain[f.domain]["facts"] += 1
        for r in self._rules.values():
            if r.domain not in by_domain:
                by_domain[r.domain] = {"facts": 0, "rules": 0}
            by_domain[r.domain]["rules"] += 1

        return {
            "facts": self.fact_count,
            "verified_facts": len(self.get_verified_facts()),
            "rules": self.rule_count,
            "concepts": self.concept_count,
            "versions": len(self._versions),
            "current_version": self._current_version,
            "by_domain": by_domain,
        }
