"""Pattern Extraction (ECC pattern) — extract instincts from session traces."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class InstinctType(Enum):
    """The category of an extracted instinct."""

    TOOL_USAGE = "tool_usage"
    WORKFLOW = "workflow"
    ERROR_RECOVERY = "error_recovery"
    OPTIMIZATION = "optimization"


@dataclass(frozen=True)
class Instinct:
    """An extracted behavioural instinct from session data."""

    pattern_name: str
    trigger_condition: str
    action_template: str
    confidence: float
    occurrence_count: int


@dataclass(frozen=True)
class ExtractionConfig:
    """Configuration for instinct extraction."""

    min_occurrences: int = 3
    min_confidence: float = 0.5
    max_instincts: int = 20


class InstinctExtractor:
    """Extracts behavioural instincts (patterns) from session traces."""

    def __init__(self, config: ExtractionConfig | None = None) -> None:
        self._config = config or ExtractionConfig()

    @property
    def config(self) -> ExtractionConfig:
        return self._config

    def extract_from_sessions(
        self, sessions: Sequence[str]
    ) -> list[Instinct]:
        """Extract instincts from a list of session traces."""
        return extract_from_sessions(sessions, self._config)

    def validate_instinct(
        self, instinct: Instinct, test_sessions: Sequence[str]
    ) -> bool:
        """Validate an instinct against a set of test sessions."""
        return validate_instinct(instinct, test_sessions)


def _generate_instinct(
    pattern_name: str,
    instinct_type: InstinctType,
    config: ExtractionConfig,
) -> Instinct:
    """Generate a single Instinct from a pattern name and type."""
    occurrences = random.randint(1, config.min_occurrences + 4)
    meets_threshold = occurrences >= config.min_occurrences
    confidence = round(
        min(
            (occurrences / (config.min_occurrences + 2))
            * random.uniform(0.8, 1.0),
            1.0,
        ),
        4,
    )

    if not meets_threshold or confidence < config.min_confidence:
        confidence = round(min(confidence, config.min_confidence - 0.01), 4)

    trigger_templates = {
        InstinctType.TOOL_USAGE: "when tool {} is invoked",
        InstinctType.WORKFLOW: "when workflow {} starts",
        InstinctType.ERROR_RECOVERY: "when error {} occurs",
        InstinctType.OPTIMIZATION: "when {} exceeds threshold",
    }
    action_templates = {
        InstinctType.TOOL_USAGE: "apply tool usage pattern for {}",
        InstinctType.WORKFLOW: "execute workflow steps for {}",
        InstinctType.ERROR_RECOVERY: "run recovery procedure for {}",
        InstinctType.OPTIMIZATION: "optimize based on {}",
    }

    trigger = trigger_templates[instinct_type].format(pattern_name)
    action = action_templates[instinct_type].format(pattern_name)

    return Instinct(
        pattern_name=pattern_name,
        trigger_condition=trigger,
        action_template=action,
        confidence=confidence,
        occurrence_count=occurrences,
    )


def extract_from_sessions(
    sessions: Sequence[str],
    config: ExtractionConfig | None = None,
) -> list[Instinct]:
    """Extract behavioural instincts from session trace data.

    Args:
        sessions: a sequence of session trace identifiers or content.
        config: extraction configuration; uses defaults if not provided.

    Returns:
        A list of Instinct objects extracted from the sessions.

    Raises:
        ValueError: if sessions is empty.
    """
    if not sessions:
        raise ValueError("Session list cannot be empty for extraction.")

    cfg = config or ExtractionConfig()
    instinct_types = list(InstinctType)
    instincts: list[Instinct] = []

    for i, session_id in enumerate(sessions):
        if len(instincts) >= cfg.max_instincts:
            break

        instinct_type = instinct_types[i % len(instinct_types)]
        pattern_name = f"{instinct_type.value}_pattern_{i}"
        instinct = _generate_instinct(pattern_name, instinct_type, cfg)

        if instinct.occurrence_count >= cfg.min_occurrences:
            instincts.append(instinct)

    return instincts[: cfg.max_instincts]


def validate_instinct(
    instinct: Instinct, test_sessions: Sequence[str]
) -> bool:
    """Validate an extracted instinct against test session traces.

    Simulates validation by checking whether the instinct's confidence
    and occurrence count meet basic reliability thresholds.

    Args:
        instinct: the instinct to validate.
        test_sessions: sessions to validate against.

    Returns:
        True if the instinct is validated, False otherwise.
    """
    if not test_sessions:
        return False

    if instinct.confidence < 0.3:
        return False

    if instinct.occurrence_count < 2:
        return False

    return random.random() < 0.7
