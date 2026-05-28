"""Compound Agent — 5-slot compound architecture for multi-perspective reasoning.

Implements a compound agent pattern where 5 specialized sub-agent "slots"
collaborate on a single task, each providing a unique cognitive perspective.
The orchestrator fuses slot outputs into a unified response.

Based on compound architecture research (arXiv 2026) and Claude Code's
subagent-as-teammate pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SlotRole(StrEnum):
    ANALYST = "analyst"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


@dataclass(frozen=True)
class SlotOutput:
    role: SlotRole
    content: str
    confidence: float
    key_insight: str


@dataclass(frozen=True)
class CompoundResult:
    task: str
    slot_outputs: tuple[SlotOutput, SlotOutput, SlotOutput, SlotOutput, SlotOutput]
    fused_response: str
    consensus_level: float
    dissent_notes: str


@dataclass
class SlotConfig:
    role: SlotRole
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class CompoundConfig:
    slots: dict[SlotRole, SlotConfig] = field(default_factory=dict)
    consensus_threshold: float = 0.6
    fusion_strategy: str = "weighted_vote"


class CompoundAgent:
    """5-slot compound agent for multi-perspective task execution.

    Slots:
    1. ANALYST — breaks down the problem, identifies key components
    2. CRITIC — challenges assumptions, finds edge cases, spots risks
    3. SYNTHESIZER — combines perspectives, finds patterns across views
    4. EXECUTOR — proposes concrete implementation plan
    5. VERIFIER — validates the fused output against requirements

    The orchestrator fuses all 5 perspectives into a coherent response.
    """

    def __init__(self, config: CompoundConfig | None = None) -> None:
        self.config = config or CompoundConfig()
        self._execution_count: int = 0

    async def execute(
        self,
        task: str,
        slot_fns: dict[SlotRole, object],  # async fn(str) -> str per slot
    ) -> CompoundResult:
        """Execute a task through all 5 compound slots in parallel.

        Args:
            task: The task description.
            slot_fns: Mapping of SlotRole to async callable(task) -> response.
        """
        self._execution_count += 1
        import asyncio

        roles = [
            SlotRole.ANALYST, SlotRole.CRITIC, SlotRole.SYNTHESIZER,
            SlotRole.EXECUTOR, SlotRole.VERIFIER,
        ]

        outputs: dict[SlotRole, SlotOutput] = {}

        async def _run_slot(role: SlotRole) -> None:
            fn = slot_fns.get(role)
            if fn is None:
                outputs[role] = SlotOutput(
                    role=role,
                    content=f"[{role.value} slot not configured]",
                    confidence=0.0,
                    key_insight="",
                )
                return
            content = await fn(task)
            outputs[role] = SlotOutput(
                role=role,
                content=content,
                confidence=0.8,
                key_insight=content[:120] if content else "",
            )

        await asyncio.gather(*[_run_slot(r) for r in roles])

        fused = self._fuse(outputs)
        consensus = self._compute_consensus(outputs)
        dissent = self._extract_dissent(outputs)

        return CompoundResult(
            task=task,
            slot_outputs=(
                outputs[SlotRole.ANALYST],
                outputs[SlotRole.CRITIC],
                outputs[SlotRole.SYNTHESIZER],
                outputs[SlotRole.EXECUTOR],
                outputs[SlotRole.VERIFIER],
            ),
            fused_response=fused,
            consensus_level=round(consensus, 4),
            dissent_notes=dissent,
        )

    def execute_sync(self, task: str, slot_outputs: dict[SlotRole, str]) -> CompoundResult:
        """Synchronous execution with pre-computed slot outputs."""
        self._execution_count += 1
        outputs: dict[SlotRole, SlotOutput] = {}

        for role in SlotRole:
            content = slot_outputs.get(role, "")
            outputs[role] = SlotOutput(
                role=role,
                content=content,
                confidence=0.8 if content else 0.0,
                key_insight=content[:120] if content else "",
            )

        fused = self._fuse(outputs)
        consensus = self._compute_consensus(outputs)
        dissent = self._extract_dissent(outputs)

        return CompoundResult(
            task=task,
            slot_outputs=(
                outputs[SlotRole.ANALYST], outputs[SlotRole.CRITIC],
                outputs[SlotRole.SYNTHESIZER], outputs[SlotRole.EXECUTOR],
                outputs[SlotRole.VERIFIER],
            ),
            fused_response=fused,
            consensus_level=round(consensus, 4),
            dissent_notes=dissent,
        )

    def _fuse(self, outputs: dict[SlotRole, SlotOutput]) -> str:
        """Fuse 5 slot outputs into a single coherent response."""
        sections: list[str] = []

        analyst = outputs.get(SlotRole.ANALYST)
        if analyst and analyst.content:
            sections.append(f"[Analysis] {analyst.content[:300]}")

        critic = outputs.get(SlotRole.CRITIC)
        if critic and critic.content:
            sections.append(f"[Risks & Concerns] {critic.content[:200]}")

        executor = outputs.get(SlotRole.EXECUTOR)
        if executor and executor.content:
            sections.append(f"[Plan] {executor.content[:400]}")

        verifier = outputs.get(SlotRole.VERIFIER)
        if verifier and verifier.content:
            sections.append(f"[Validation] {verifier.content[:200]}")

        synthesizer = outputs.get(SlotRole.SYNTHESIZER)
        synth_text = synthesizer.content if synthesizer else ""
        sections.append(f"[Synthesis] {synth_text[:300]}")

        return "\n\n".join(sections)

    def _compute_consensus(self, outputs: dict[SlotRole, SlotOutput]) -> float:
        """Compute consensus level across all 5 slots."""
        confidences = [o.confidence for o in outputs.values()]
        if not confidences:
            return 0.0
        mean = sum(confidences) / len(confidences)
        variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
        return max(0.0, 1.0 - variance)

    def _extract_dissent(self, outputs: dict[SlotRole, SlotOutput]) -> str:
        """Extract dissenting opinions from the critic and verifier slots."""
        notes: list[str] = []
        critic = outputs.get(SlotRole.CRITIC)
        verifier = outputs.get(SlotRole.VERIFIER)

        if critic and critic.confidence < 0.5:
            notes.append(f"Critic low confidence: {critic.key_insight}")
        if verifier and verifier.confidence < 0.5:
            notes.append(f"Verifier low confidence: {verifier.key_insight}")

        return "; ".join(notes) if notes else ""

    @property
    def execution_count(self) -> int:
        return self._execution_count
