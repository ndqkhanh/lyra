"""
Phases 5-8: Research, Safety, Evaluation, and Integration

This module consolidates the remaining phases:
- Phase 5: Research & Learning capabilities
- Phase 6: Safety & Governance
- Phase 7: Evaluation & Telemetry
- Phase 8: Integration & Polish
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


# ============================================================================
# PHASE 5: RESEARCH & LEARNING
# ============================================================================

@dataclass
class ResearchQuery:
    """A research query with results."""
    query: str
    sources: List[str]
    findings: List[str]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReasoningStrategy:
    """A reusable reasoning strategy."""
    name: str
    description: str
    steps: List[str]
    success_count: int = 0
    failure_count: int = 0
    examples: List[Dict[str, Any]] = field(default_factory=list)


class ReasoningBank:
    """
    Bank of reasoning strategies extracted from experience.

    Implements conservative retrieval to avoid negative transfer.
    """

    def __init__(self, bank_path: Path):
        self.bank_path = bank_path
        self.strategies: Dict[str, ReasoningStrategy] = {}
        self._load()

    def add_strategy(self, strategy: ReasoningStrategy) -> None:
        """Add a reasoning strategy."""
        self.strategies[strategy.name] = strategy
        self._save()

    def retrieve_strategy(self, task: str, min_success_rate: float = 0.7) -> Optional[ReasoningStrategy]:
        """
        Retrieve relevant strategy with conservative threshold.

        Args:
            task: Task description
            min_success_rate: Minimum success rate threshold

        Returns:
            Best matching strategy or None
        """
        task_lower = task.lower()
        best_match = None
        best_score = 0.0

        for strategy in self.strategies.values():
            # Calculate success rate
            total = strategy.success_count + strategy.failure_count
            if total == 0:
                success_rate = 0.5
            else:
                success_rate = strategy.success_count / total

            # Skip if below threshold
            if success_rate < min_success_rate:
                continue

            # Calculate relevance
            relevance = sum(1 for word in strategy.description.lower().split() if word in task_lower)

            score = relevance * success_rate
            if score > best_score:
                best_score = score
                best_match = strategy

        return best_match

    def _load(self) -> None:
        """Load strategies from disk."""
        if not self.bank_path.exists():
            return

        with open(self.bank_path) as f:
            data = json.load(f)
            for name, strategy_data in data.items():
                self.strategies[name] = ReasoningStrategy(**strategy_data)

    def _save(self) -> None:
        """Save strategies to disk."""
        self.bank_path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: vars(strategy) for name, strategy in self.strategies.items()}
        with open(self.bank_path, "w") as f:
            json.dump(data, f, indent=2)


class ResearchEngine:
    """Research capabilities for Lyra."""

    def __init__(self, reasoning_bank: ReasoningBank):
        self.reasoning_bank = reasoning_bank
        self.research_history: List[ResearchQuery] = []

    def conduct_research(self, query: str) -> ResearchQuery:
        """
        Conduct research on a topic.

        Args:
            query: Research query

        Returns:
            Research results
        """
        # Simplified - would use web search, paper retrieval, etc.
        research = ResearchQuery(
            query=query,
            sources=["placeholder_source"],
            findings=["placeholder_finding"],
            confidence=0.7,
        )
        self.research_history.append(research)
        return research


# ============================================================================
# PHASE 6: SAFETY & GOVERNANCE
# ============================================================================

class ThreatLevel(str, Enum):
    """Threat severity level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityThreat:
    """A detected security threat."""
    type: str
    level: ThreatLevel
    description: str
    detected_at: datetime = field(default_factory=datetime.now)
    mitigated: bool = False


class SafetyGuard:
    """
    Multi-layer defense system.

    Layers:
    1. Input validation
    2. Memory safety
    3. Skill safety
    4. Modification safety
    5. Output safety
    """

    def __init__(self):
        self.threats: List[SecurityThreat] = []
        self.quarantine: List[Any] = []

    def validate_input(self, user_input: str) -> tuple[bool, Optional[SecurityThreat]]:
        """
        Validate user input for prompt injection.

        Args:
            user_input: User's input

        Returns:
            Tuple of (is_safe, threat)
        """
        # Detect prompt injection patterns
        injection_patterns = [
            "ignore previous instructions",
            "disregard all",
            "forget everything",
            "new instructions:",
            "system:",
            "you are now",
        ]

        for pattern in injection_patterns:
            if pattern in user_input.lower():
                threat = SecurityThreat(
                    type="prompt_injection",
                    level=ThreatLevel.HIGH,
                    description=f"Detected pattern: {pattern}",
                )
                self.threats.append(threat)
                return False, threat

        return True, None

    def validate_memory(self, memory_content: str) -> tuple[bool, Optional[SecurityThreat]]:
        """Validate memory for poisoning attempts."""
        # Check for suspicious patterns
        if any(pattern in memory_content.lower() for pattern in ["<script>", "eval(", "exec("]):
            threat = SecurityThreat(
                type="memory_poisoning",
                level=ThreatLevel.CRITICAL,
                description="Suspicious code patterns detected",
            )
            self.threats.append(threat)
            return False, threat

        return True, None

    def validate_skill(self, skill_code: str) -> tuple[bool, Optional[SecurityThreat]]:
        """Validate skill code for malicious patterns."""
        dangerous_patterns = [
            "os.system",
            "subprocess.call",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
        ]

        for pattern in dangerous_patterns:
            if pattern in skill_code:
                threat = SecurityThreat(
                    type="malicious_skill",
                    level=ThreatLevel.CRITICAL,
                    description=f"Dangerous pattern: {pattern}",
                )
                self.threats.append(threat)
                return False, threat

        return True, None

    def get_threat_report(self) -> Dict[str, Any]:
        """Generate threat report."""
        return {
            "total_threats": len(self.threats),
            "by_level": self._count_by_level(),
            "by_type": self._count_by_type(),
            "mitigated": sum(1 for t in self.threats if t.mitigated),
            "active": sum(1 for t in self.threats if not t.mitigated),
        }

    def _count_by_level(self) -> Dict[str, int]:
        """Count threats by level."""
        counts = {}
        for threat in self.threats:
            counts[threat.level.value] = counts.get(threat.level.value, 0) + 1
        return counts

    def _count_by_type(self) -> Dict[str, int]:
        """Count threats by type."""
        counts = {}
        for threat in self.threats:
            counts[threat.type] = counts.get(threat.type, 0) + 1
        return counts


# ============================================================================
# PHASE 7: EVALUATION & TELEMETRY
# ============================================================================

@dataclass
class Metric:
    """A performance metric."""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)


class TelemetrySystem:
    """
    Telemetry and evaluation system.

    Tracks:
    - Task success rate
    - Memory quality
    - Skill quality
    - Evolution metrics
    - Efficiency metrics
    - Safety metrics
    """

    def __init__(self, telemetry_path: Path):
        self.telemetry_path = telemetry_path
        self.metrics: List[Metric] = []

    def record_metric(self, name: str, value: float, unit: str = "") -> None:
        """Record a metric."""
        metric = Metric(name=name, value=value, unit=unit)
        self.metrics.append(metric)
        self._save()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        if not self.metrics:
            return {}

        # Group by name
        by_name = {}
        for metric in self.metrics:
            if metric.name not in by_name:
                by_name[metric.name] = []
            by_name[metric.name].append(metric.value)

        # Calculate statistics
        summary = {}
        for name, values in by_name.items():
            summary[name] = {
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1],
            }

        return summary

    def _save(self) -> None:
        """Save metrics to disk."""
        self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in self.metrics
        ]
        with open(self.telemetry_path, "w") as f:
            json.dump(data, f, indent=2)


# ============================================================================
# PHASE 8: INTEGRATION
# ============================================================================

class LyraSystem:
    """
    Integrated Lyra system combining all phases.

    Phases:
    1. Memory Foundation
    2. Context Engineering
    3. Skills & Procedural Memory
    4. Self-Evolution Engine
    5. Research & Learning
    6. Safety & Governance
    7. Evaluation & Telemetry
    8. Integration & Polish
    """

    def __init__(self, base_path: Path):
        """
        Initialize Lyra system.

        Args:
            base_path: Base directory for Lyra data
        """
        self.base_path = base_path

        # Phase 5: Research
        self.reasoning_bank = ReasoningBank(base_path / "reasoning_bank.json")
        self.research_engine = ResearchEngine(self.reasoning_bank)

        # Phase 6: Safety
        self.safety_guard = SafetyGuard()

        # Phase 7: Telemetry
        self.telemetry = TelemetrySystem(base_path / "telemetry.json")

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "reasoning_strategies": len(self.reasoning_bank.strategies),
            "research_queries": len(self.research_engine.research_history),
            "security_threats": len(self.safety_guard.threats),
            "metrics_recorded": len(self.telemetry.metrics),
            "system_health": "operational",
        }

    def run_health_check(self) -> Dict[str, bool]:
        """Run system health check."""
        return {
            "reasoning_bank": self.reasoning_bank.bank_path.exists(),
            "safety_guard": len(self.safety_guard.threats) < 100,
            "telemetry": self.telemetry.telemetry_path.exists(),
        }
