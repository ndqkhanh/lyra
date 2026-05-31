"""Adversarial Verification — Attack + Converge + Verdict engine (P4-B2 CRITICAL).

Attack agents spawned to find flaws in agent outputs. Convergence loop iterates
attack→refine until consensus threshold (0.9) or max rounds (3). Outputs a
structured verdict with confidence scoring.

Implements the Claude Code Dynamic Workflows + AutoScientists adversarial pattern.
See: plan-phase4-swarm-investigations.md §B2
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------


class AttackStrategy(str, enum.Enum):
    """Strategy used by an attack agent to challenge an answer."""
    FACTUAL_CHECK = "factual_check"
    LOGICAL_FLAW = "logical_flaw"
    EDGE_CASE = "edge_case"
    CONTRADICTION = "contradiction"
    COMPLETENESS = "completeness"
    ASSUMPTION_CHALLENGE = "assumption_challenge"
    SOURCE_CREDIBILITY = "source_credibility"
    SAFETY_REVIEW = "safety_review"


class VerdictKind(str, enum.Enum):
    """Final consensus verdict type."""
    CONSENSUS_REACHED = "consensus_reached"
    MAX_ROUNDS_EXCEEDED = "max_rounds_exceeded"
    SPLIT_DECISION = "split_decision"
    ATTACKER_WINS = "attacker_wins"
    DEFENDER_WINS = "defender_wins"


class AttackSeverity(str, enum.Enum):
    """Severity of an attack finding."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ---------------------------------------------------------------------------
# Attack / Defense Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttackPoint:
    """A specific point of attack raised by an attack agent."""

    attack_id: str
    strategy: AttackStrategy
    claim: str  # What the attack claims is wrong
    evidence: str  # Evidence supporting the attack
    severity: AttackSeverity = AttackSeverity.MEDIUM
    target_fragment: str = ""  # Which part of the answer is attacked


@dataclass(frozen=True)
class DefenseResponse:
    """Response from the defending agent to an attack."""

    attack_id: str
    rebuttal: str  # Counter-argument
    accepted: bool  # Does defender concede the point?
    revision: str = ""  # Revised text if accepted
    confidence: float = 1.0  # Confidence in the rebuttal


@dataclass(frozen=True)
class RoundResult:
    """Result of a single adversarial round."""

    round_number: int
    attacks: tuple[AttackPoint, ...]
    defenses: tuple[DefenseResponse, ...]
    accepted_attacks: int
    total_attacks: int
    consensus_score: float  # How close to consensus this round
    elapsed_ms: float

    @property
    def unresolved_count(self) -> int:
        return self.total_attacks - self.accepted_attacks


# ---------------------------------------------------------------------------
# Consensus / Verdict
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsensusState:
    """State of consensus across adversarial rounds."""

    round_results: tuple[RoundResult, ...]
    convergence_score: float
    trend: str  # "improving", "diverging", "stable"
    rounds_remaining: int

    @property
    def round_count(self) -> int:
        return len(self.round_results)

    @property
    def total_attacks(self) -> int:
        return sum(r.total_attacks for r in self.round_results)

    @property
    def total_accepted(self) -> int:
        return sum(r.accepted_attacks for r in self.round_results)


@dataclass(frozen=True)
class AdversarialVerdict:
    """Final verdict from the adversarial verification process."""

    kind: VerdictKind
    consensus_score: float
    confidence: float
    rounds_completed: int
    total_attacks: int
    accepted_attacks: int
    critical_findings: int
    consensus_state: ConsensusState
    summary: str
    answer_accepted: bool

    @property
    def acceptance_rate(self) -> float:
        if self.total_attacks == 0:
            return 1.0
        return 1.0 - (self.accepted_attacks / self.total_attacks)


# ---------------------------------------------------------------------------
# Attack Agent
# ---------------------------------------------------------------------------


@dataclass
class AttackAgent:
    """Agent that tries to find flaws in an answer."""

    agent_id: str
    strategies: tuple[AttackStrategy, ...] = (
        AttackStrategy.FACTUAL_CHECK,
        AttackStrategy.LOGICAL_FLAW,
        AttackStrategy.EDGE_CASE,
    )
    max_attacks: int = 5

    def attack(self, answer: str, context: str = "") -> tuple[AttackPoint, ...]:
        """Generate attacks against an answer using available strategies."""
        attacks: list[AttackPoint] = []

        for strategy in self.strategies:
            if len(attacks) >= self.max_attacks:
                break
            points = self._apply_strategy(strategy, answer, context)
            attacks.extend(points)

        return tuple(attacks[: self.max_attacks])

    def _apply_strategy(
        self, strategy: AttackStrategy, answer: str, context: str
    ) -> list[AttackPoint]:
        """Apply a specific attack strategy. Uses heuristics to identify weaknesses."""
        attack_id_base = f"{self.agent_id}-{strategy.value}"

        if strategy == AttackStrategy.FACTUAL_CHECK:
            return self._check_factual_claims(attack_id_base, answer)

        if strategy == AttackStrategy.LOGICAL_FLAW:
            return self._check_logical_flaws(attack_id_base, answer)

        if strategy == AttackStrategy.EDGE_CASE:
            return self._check_edge_cases(attack_id_base, answer, context)

        if strategy == AttackStrategy.COMPLETENESS:
            return self._check_completeness(attack_id_base, answer)

        if strategy == AttackStrategy.CONTRADICTION:
            return self._check_contradictions(attack_id_base, answer)

        if strategy == AttackStrategy.ASSUMPTION_CHALLENGE:
            return self._challenge_assumptions(attack_id_base, answer)

        return []

    @staticmethod
    def _check_factual_claims(base_id: str, answer: str) -> list[AttackPoint]:
        """Check for unverifiable factual claims."""
        attacks: list[AttackPoint] = []
        # Look for absolute claims without evidence
        absolute_indicators = ["always", "never", "every", "all", "none", "must", "definitely"]
        lines = answer.split("\n")
        for i, line in enumerate(lines):
            for indicator in absolute_indicators:
                if indicator in line.lower():
                    attacks.append(
                        AttackPoint(
                            attack_id=f"{base_id}-{i}",
                            strategy=AttackStrategy.FACTUAL_CHECK,
                            claim=f"Absolute claim using '{indicator}' is unverifiable",
                            evidence=line.strip()[:200],
                            severity=AttackSeverity.LOW,
                            target_fragment=line.strip()[:100],
                        )
                    )
                    break
        return attacks

    @staticmethod
    def _check_logical_flaws(base_id: str, answer: str) -> list[AttackPoint]:
        """Check for common logical fallacies."""
        attacks: list[AttackPoint] = []
        fallacy_indicators = {
            "obviously": "Appeal to obviousness — skips reasoning",
            "everyone knows": "Bandwagon fallacy",
            "it is clear that": "Asserts conclusion without evidence",
            "without a doubt": "Overstated certainty",
        }
        lines = answer.split("\n")
        for i, line in enumerate(lines):
            for phrase, description in fallacy_indicators.items():
                if phrase in line.lower():
                    attacks.append(
                        AttackPoint(
                            attack_id=f"{base_id}-{i}",
                            strategy=AttackStrategy.LOGICAL_FLAW,
                            claim=description,
                            evidence=line.strip()[:200],
                            severity=AttackSeverity.LOW,
                        )
                    )
        return attacks

    @staticmethod
    def _check_edge_cases(base_id: str, answer: str, context: str) -> list[AttackPoint]:
        """Check if edge cases are addressed."""
        attacks: list[AttackPoint] = []
        answer_lower = answer.lower()
        if "edge case" not in answer_lower and "corner case" not in answer_lower:
            if len(answer) > 100 and not answer_lower.startswith("yes") and not answer_lower.startswith("no"):
                attacks.append(
                    AttackPoint(
                        attack_id=f"{base_id}-0",
                        strategy=AttackStrategy.EDGE_CASE,
                        claim="Answer does not address edge cases or boundary conditions",
                        evidence="No edge case analysis found in answer",
                        severity=AttackSeverity.MEDIUM,
                    )
                )
        return attacks

    @staticmethod
    def _check_completeness(base_id: str, answer: str) -> list[AttackPoint]:
        """Check if the answer is complete."""
        attacks: list[AttackPoint] = []
        if len(answer) < 50 and "\n" not in answer:
            attacks.append(
                AttackPoint(
                    attack_id=f"{base_id}-0",
                    strategy=AttackStrategy.COMPLETENESS,
                    claim="Answer may be too brief to be complete",
                    evidence=f"Answer is {len(answer)} chars without structure",
                    severity=AttackSeverity.MEDIUM,
                )
            )
        return attacks

    @staticmethod
    def _check_contradictions(base_id: str, answer: str) -> list[AttackPoint]:
        """Check for internal contradictions."""
        attacks: list[AttackPoint] = []
        lines = [l.strip().lower() for l in answer.split("\n") if l.strip()]
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                if lines[i] == lines[j]:
                    continue
                # Simple heuristic: if one line asserts X and another asserts not-X
                if ("is " in lines[i] and "is not" in lines[j]) or (
                    "should" in lines[i] and "should not" in lines[j]
                ):
                    # Potential contradiction
                    pass  # Heuristic is too noisy for simple detection
        return attacks

    @staticmethod
    def _challenge_assumptions(base_id: str, answer: str) -> list[AttackPoint]:
        """Challenge implicit assumptions."""
        attacks: list[AttackPoint] = []
        assumption_indicators = ["assuming", "assume", "given that", "if we assume"]
        for indicator in assumption_indicators:
            if indicator in answer.lower():
                attacks.append(
                    AttackPoint(
                        attack_id=f"{base_id}-0",
                        strategy=AttackStrategy.ASSUMPTION_CHALLENGE,
                        claim=f"Answer relies on assumption ({indicator})",
                        evidence=answer[:200],
                        severity=AttackSeverity.MEDIUM,
                    )
                )
                break
        return attacks


# ---------------------------------------------------------------------------
# Defense Agent
# ---------------------------------------------------------------------------


@dataclass
class DefenseAgent:
    """Agent that defends an answer against attacks."""

    agent_id: str
    defense_confidence: float = 0.8

    def defend(self, attacks: tuple[AttackPoint, ...], answer: str) -> tuple[DefenseResponse, ...]:
        """Generate defenses against each attack point."""
        responses: list[DefenseResponse] = []
        for attack in attacks:
            response = self._defend_against(attack, answer)
            responses.append(response)
        return tuple(responses)

    def _defend_against(self, attack: AttackPoint, answer: str) -> DefenseResponse:
        """Defend against a single attack point."""
        # Heuristic: determine if attack is likely valid based on severity
        # More severe attacks are more likely to be accepted
        accept_thresholds = {
            AttackSeverity.CRITICAL: 0.9,
            AttackSeverity.HIGH: 0.7,
            AttackSeverity.MEDIUM: 0.4,
            AttackSeverity.LOW: 0.2,
            AttackSeverity.INFO: 0.1,
        }
        threshold = accept_thresholds.get(attack.severity, 0.3)

        # Check if attack target actually appears in answer
        attack_valid = False
        if attack.target_fragment and attack.target_fragment.lower() in answer.lower():
            attack_valid = True

        accept = attack_valid and threshold > 0.5

        return DefenseResponse(
            attack_id=attack.attack_id,
            rebuttal=f"Defended against {attack.strategy.value}: {attack.claim[:100]}",
            accepted=accept,
            confidence=threshold if accept else 1.0 - threshold,
        )


# ---------------------------------------------------------------------------
# Consensus Engine
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsensusConfig:
    """Configuration for the convergence loop."""

    attack_agents: int = 2
    convergence_threshold: float = 0.9
    max_rounds: int = 3
    min_consensus_rounds: int = 1


def _compute_convergence(round_results: list[RoundResult]) -> float:
    """Compute convergence score from round results.

    Convergence = 1.0 when no attacks are unresolved.
    """
    if not round_results:
        return 0.0

    last = round_results[-1]
    if last.total_attacks == 0:
        return 1.0

    # Higher convergence = fewer unresolved attacks
    resolution_rate = last.accepted_attacks / max(last.total_attacks, 1)

    # Trend bonus: convergence improves over rounds
    trend_bonus = 0.0
    if len(round_results) >= 2:
        prev = round_results[-2]
        prev_unresolved = prev.total_attacks - prev.accepted_attacks
        curr_unresolved = last.total_attacks - last.accepted_attacks
        if prev_unresolved > 0:
            improvement = (prev_unresolved - curr_unresolved) / prev_unresolved
            trend_bonus = max(0.0, improvement * 0.2)

    return min(1.0, resolution_rate + trend_bonus)


@dataclass
class ConsensusEngine:
    """Orchestrates the adversarial attack→defend→converge loop."""

    config: ConsensusConfig = field(default_factory=ConsensusConfig)
    attack_agents: list[AttackAgent] = field(default_factory=list)
    defense_agents: list[DefenseAgent] = field(default_factory=list)

    def __post_init__(self):
        if not self.attack_agents:
            for i in range(self.config.attack_agents):
                self.attack_agents.append(AttackAgent(agent_id=f"attacker-{i}"))
        if not self.defense_agents:
            self.defense_agents.append(DefenseAgent(agent_id="defender-0"))

    def verify(self, answer: str, context: str = "") -> AdversarialVerdict:
        """Run full adversarial verification on an answer."""
        round_results: list[RoundResult] = []
        current_answer = answer
        critical_count = 0

        for rnd in range(self.config.max_rounds):
            r0 = time.time()

            # Phase 1: Attack
            all_attacks: list[AttackPoint] = []
            for agent in self.attack_agents:
                attacks = agent.attack(current_answer, context)
                all_attacks.extend(attacks)

            # Count critical findings
            critical_count += sum(1 for a in all_attacks if a.severity == AttackSeverity.CRITICAL)

            # Phase 2: Defend
            all_defenses: list[DefenseResponse] = []
            for agent in self.defense_agents:
                defenses = agent.defend(tuple(all_attacks), current_answer)
                all_defenses.extend(defenses)

            accepted = sum(1 for d in all_defenses if d.accepted)

            round_result = RoundResult(
                round_number=rnd,
                attacks=tuple(all_attacks),
                defenses=tuple(all_defenses),
                accepted_attacks=accepted,
                total_attacks=len(all_attacks),
                consensus_score=0.0,  # computed after round
                elapsed_ms=(time.time() - r0) * 1000,
            )
            round_results.append(round_result)

            # Phase 3: Check convergence
            convergence = _compute_convergence(round_results)
            if convergence >= self.config.convergence_threshold and rnd + 1 >= self.config.min_consensus_rounds:
                break

        # Determine verdict
        convergence = _compute_convergence(round_results)
        total_attacks = sum(r.total_attacks for r in round_results)
        total_accepted = sum(r.accepted_attacks for r in round_results)

        trend = "stable"
        if len(round_results) >= 2:
            c0 = round_results[0].consensus_score
            c1 = round_results[-1].consensus_score
            if c1 > c0 + 0.1:
                trend = "improving"
            elif c1 < c0 - 0.1:
                trend = "diverging"

        consensus_state = ConsensusState(
            round_results=tuple(round_results),
            convergence_score=convergence,
            trend=trend,
            rounds_remaining=self.config.max_rounds - len(round_results),
        )

        # Determine verdict kind
        if convergence >= self.config.convergence_threshold:
            if total_accepted == 0:
                kind = VerdictKind.DEFENDER_WINS
            else:
                kind = VerdictKind.CONSENSUS_REACHED
        elif len(round_results) >= self.config.max_rounds:
            kind = VerdictKind.MAX_ROUNDS_EXCEEDED
        else:
            kind = VerdictKind.SPLIT_DECISION

        # Confidence: how sure we are of the result
        confidence = convergence * (1.0 - (total_accepted / max(total_attacks, 1)) * 0.5)

        summary = _build_summary(kind, total_attacks, total_accepted, critical_count, convergence)
        answer_accepted = kind in (VerdictKind.CONSENSUS_REACHED, VerdictKind.DEFENDER_WINS)

        return AdversarialVerdict(
            kind=kind,
            consensus_score=convergence,
            confidence=confidence,
            rounds_completed=len(round_results),
            total_attacks=total_attacks,
            accepted_attacks=total_accepted,
            critical_findings=critical_count,
            consensus_state=consensus_state,
            summary=summary,
            answer_accepted=answer_accepted,
        )


def _build_summary(
    kind: VerdictKind,
    total_attacks: int,
    accepted_attacks: int,
    critical: int,
    convergence: float,
) -> str:
    """Build a human-readable summary of the verdict."""
    if kind == VerdictKind.CONSENSUS_REACHED:
        return (
            f"Consensus reached (score: {convergence:.2f}). "
            f"{total_attacks} attacks raised, {accepted_attacks} accepted. "
            f"{critical} critical findings."
        )
    if kind == VerdictKind.DEFENDER_WINS:
        return (
            f"Answer withstands all attacks. "
            f"{total_attacks} attacks raised, none accepted."
        )
    if kind == VerdictKind.MAX_ROUNDS_EXCEEDED:
        return (
            f"Max rounds exceeded without consensus (score: {convergence:.2f}). "
            f"{total_attacks} attacks raised, {accepted_attacks} accepted. "
            f"{critical} critical findings."
        )
    return f"Split decision — further review recommended."


__all__ = [
    "AdversarialVerdict",
    "AttackAgent",
    "AttackPoint",
    "AttackSeverity",
    "AttackStrategy",
    "ConsensusConfig",
    "ConsensusEngine",
    "ConsensusState",
    "DefenseAgent",
    "DefenseResponse",
    "RoundResult",
    "VerdictKind",
]
