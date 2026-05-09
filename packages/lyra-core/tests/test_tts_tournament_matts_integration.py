"""Test that TournamentTts injects MaTTS prefixes when wired to a bank."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from lyra_core.memory import (
    HeuristicDistiller,
    ReasoningBank,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
)
from lyra_core.tts.tournament import (
    Attempt,
    AttemptGenerator,
    Discriminator,
    TournamentTts,
    TtsBudget,
)


@dataclass
class _RecordingGenerator(AttemptGenerator):
    """Captures every prompt it sees so tests can assert on them."""

    seen_prompts: list[str]

    def generate(self, task_description: str, attempt_index: int) -> Attempt:
        self.seen_prompts.append(task_description)
        return Attempt(id=f"a-{attempt_index}", artefact=f"artefact-{attempt_index}")


class _AlwaysFirst(Discriminator):
    def compare(self, a: Attempt, b: Attempt) -> Attempt:
        return a


def _seed_bank() -> ReasoningBank:
    bank = ReasoningBank(distiller=HeuristicDistiller())
    for i in range(5):
        bank.record(
            Trajectory(
                id=f"t-{i}",
                task_signature="parse-json",
                outcome=TrajectoryOutcome.SUCCESS,
                steps=(
                    TrajectoryStep(index=0, kind="tool_call", payload=f"step-{i}"),
                ),
            )
        )
    return bank


def test_tournament_without_bank_passes_task_description_unchanged() -> None:
    """Default behaviour: no bank => generator sees the raw task description."""
    gen = _RecordingGenerator(seen_prompts=[])
    tts = TournamentTts(
        generator=gen,
        discriminator=_AlwaysFirst(),
        budget=TtsBudget(max_attempts=3, max_wall_clock_s=10, max_total_tokens=10_000),
    )
    tts.run("parse-json")
    assert gen.seen_prompts == ["parse-json", "parse-json", "parse-json"]


def test_tournament_with_bank_injects_matts_prefix() -> None:
    """With a bank wired in, every prompt carries the MaTTS prefix."""
    gen = _RecordingGenerator(seen_prompts=[])
    bank = _seed_bank()
    tts = TournamentTts(
        generator=gen,
        discriminator=_AlwaysFirst(),
        budget=TtsBudget(max_attempts=3, max_wall_clock_s=10, max_total_tokens=10_000),
        reasoning_bank=bank,
    )
    tts.run("parse-json")
    # Each prompt starts with a MaTTS marker and ends with the task block.
    for prompt in gen.seen_prompts:
        assert prompt.startswith("# matts attempt=")
        assert "# task" in prompt
        assert "parse-json" in prompt


def test_tournament_with_bank_diversifies_per_attempt() -> None:
    """The bank must hand out different prefixes per attempt index."""
    gen = _RecordingGenerator(seen_prompts=[])
    bank = _seed_bank()
    tts = TournamentTts(
        generator=gen,
        discriminator=_AlwaysFirst(),
        budget=TtsBudget(max_attempts=4, max_wall_clock_s=10, max_total_tokens=10_000),
        reasoning_bank=bank,
    )
    tts.run("parse-json")
    # At least two distinct prompts across 4 attempts.
    assert len(set(gen.seen_prompts)) >= 2


def test_tournament_falls_through_when_bank_raises() -> None:
    """A misbehaving bank can't break the TTS loop."""

    class BrokenBank:
        def matts_prefix(
            self, task_signature: str, attempt_index: int, *, k: int = 3
        ) -> str:
            raise RuntimeError("FTS5 indexer crashed")

    gen = _RecordingGenerator(seen_prompts=[])
    tts = TournamentTts(
        generator=gen,
        discriminator=_AlwaysFirst(),
        budget=TtsBudget(max_attempts=2, max_wall_clock_s=5, max_total_tokens=5_000),
        reasoning_bank=BrokenBank(),
    )
    tts.run("parse-json")
    # Falls through to the raw task description; loop completes.
    assert gen.seen_prompts == ["parse-json", "parse-json"]


def test_seq_used_to_build_artefacts(tmp_path) -> None:
    """A safety check that the TTS still produces a TtsResult shape."""
    gen = _RecordingGenerator(seen_prompts=[])
    bank = _seed_bank()
    tts = TournamentTts(
        generator=gen,
        discriminator=_AlwaysFirst(),
        budget=TtsBudget(max_attempts=2, max_wall_clock_s=5, max_total_tokens=5_000),
        reasoning_bank=bank,
    )
    result = tts.run("parse-json")
    assert result.winning_attempt is not None
    losers: Sequence[Attempt] = result.losers
    assert len(losers) == 1
