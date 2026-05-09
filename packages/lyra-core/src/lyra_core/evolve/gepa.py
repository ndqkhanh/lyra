"""GEPA core — Pareto-filtered prompt mutation.

Why "Pareto" rather than scalar fitness? Because prompt-tuning is a
multi-objective problem in practice — you want the highest score for
the smallest number of tokens. Scalar fitness collapses the trade-off
to a single hyperparameter weight; Pareto preserves it as a set of
non-dominated candidates the user can pick from.

The two objectives this module tracks:

* **score↑** — fraction of training examples the prompt passes.
* **length↓** — character count of the prompt (proxy for token cost).

Adding more objectives (latency, refusal rate, safety class) is a
matter of extending :class:`EvolveCandidate` and updating
:func:`pareto_front`. Two objectives is enough to demonstrate the
mechanism and to be honestly useful on its own.
"""
from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "EvolveCandidate",
    "EvolveHistoryEntry",
    "EvolveReport",
    "EvolveTrainExample",
    "Mutator",
    "ScoreFn",
    "evolve",
    "pareto_front",
    "score_candidate",
    "templated_mutator",
]


@dataclass(frozen=True)
class EvolveTrainExample:
    """One ``(input, expected substring)`` training example.

    The check is intentionally a substring match (``expected in
    output``) rather than exact-match — partly because LLM outputs are
    naturally chatty, partly because exact-match would force the
    training set to over-specify the answer shape and inhibit useful
    mutations.
    """

    input: str
    expected: str


@dataclass(frozen=True)
class EvolveCandidate:
    """One prompt with its measured score and bookkeeping metadata.

    ``parents`` is a tuple of parent-prompt fingerprints (the first 12
    chars of the parent prompt, hashed visually so the lineage is
    grep-friendly). Generation 0 candidates have an empty ``parents``
    tuple.
    """

    prompt: str
    score: float
    length: int
    generation: int
    parents: tuple[str, ...] = ()

    def dominates(self, other: "EvolveCandidate") -> bool:
        """Pareto dominance over (score↑, length↓).

        ``self`` dominates ``other`` iff every objective is at-least-as-
        good and at least one objective is strictly better.
        """
        not_worse = self.score >= other.score and self.length <= other.length
        strictly_better = self.score > other.score or self.length < other.length
        return not_worse and strictly_better


@dataclass(frozen=True)
class EvolveHistoryEntry:
    """One generation summary recorded by :func:`evolve`."""

    generation: int
    population: int
    best_score: float
    front_size: int


@dataclass(frozen=True)
class EvolveReport:
    """The output of one :func:`evolve` run."""

    best: EvolveCandidate
    front: tuple[EvolveCandidate, ...]
    history: tuple[EvolveHistoryEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "best": {
                "prompt": self.best.prompt,
                "score": self.best.score,
                "length": self.best.length,
                "generation": self.best.generation,
            },
            "front": [
                {
                    "prompt": c.prompt,
                    "score": c.score,
                    "length": c.length,
                    "generation": c.generation,
                }
                for c in self.front
            ],
            "history": [
                {
                    "generation": h.generation,
                    "population": h.population,
                    "best_score": h.best_score,
                    "front_size": h.front_size,
                }
                for h in self.history
            ],
        }


# ----------------------------- protocols ---------------------------------- #


class Mutator(Protocol):
    """``(prompt, rng) -> mutated_prompt`` — must be deterministic given rng."""

    def __call__(self, prompt: str, rng: random.Random) -> str:  # pragma: no cover
        ...


ScoreFn = Callable[[str, str], str]
"""``(prompt, example_input) -> model_output``.

Wire to your LLM in production; tests use a deterministic stub. The
caller is responsible for any prompt rendering — :func:`score_candidate`
just concatenates ``prompt`` + ``\\n\\n`` + ``input`` if no rendering is
needed.
"""


# ----------------------------- mutators ----------------------------------- #


_TEMPLATED_NUDGES: tuple[str, ...] = (
    "\n\nThink step by step before answering.",
    "\n\nReturn the final answer on its own line, prefixed with 'Answer:'.",
    "\n\nIf the question is ambiguous, ask one clarifying question first.",
    "\n\nBe concise. Three sentences maximum.",
    "\n\nAlways quote the relevant span from the input verbatim.",
    "\n\nFormat the answer as a single JSON object with key 'answer'.",
)


def templated_mutator(prompt: str, rng: random.Random) -> str:
    """Built-in deterministic mutator.

    Picks one of a small handful of canonical reflective rewrites (chain-
    of-thought hint, answer-format pin, clarifying-question prefix,
    concision nudge, citation requirement, JSON wrapper) and appends it
    to the prompt. If the chosen nudge is already present the mutator
    falls through to a no-op so the offspring isn't duplicated. This is
    enough to demonstrate the GEPA mechanism without any LLM.
    """
    pool = [n for n in _TEMPLATED_NUDGES if n.strip() not in prompt]
    if not pool:
        return prompt
    nudge = rng.choice(pool)
    return prompt + nudge


# ----------------------------- scoring ------------------------------------ #


def score_candidate(
    prompt: str,
    examples: Sequence[EvolveTrainExample],
    *,
    model_call: ScoreFn,
) -> float:
    """Run ``model_call`` over each example and return the pass rate.

    Pass rate is ``len({e for e in examples if expected in output}) /
    len(examples)``. Empty training sets return ``1.0`` (vacuously
    correct) so the algorithm degrades gracefully when the user
    forgets to author examples.
    """
    if not examples:
        return 1.0
    passed = 0
    for ex in examples:
        out = model_call(prompt, ex.input)
        if ex.expected in out:
            passed += 1
    return passed / len(examples)


# ----------------------------- pareto ------------------------------------- #


def pareto_front(
    candidates: Sequence[EvolveCandidate],
) -> tuple[EvolveCandidate, ...]:
    """Return the non-dominated subset of ``candidates``.

    Order of the returned tuple is by score descending, length
    ascending, prompt lexicographic — so callers can rely on a
    stable, human-friendly sort without re-sorting themselves.
    """
    if not candidates:
        return ()
    front: list[EvolveCandidate] = []
    for c in candidates:
        dominated = any(other.dominates(c) for other in candidates if other is not c)
        if not dominated:
            front.append(c)
    front.sort(key=lambda c: (-c.score, c.length, c.prompt))
    deduped: list[EvolveCandidate] = []
    seen: set[str] = set()
    for c in front:
        if c.prompt in seen:
            continue
        seen.add(c.prompt)
        deduped.append(c)
    return tuple(deduped)


def _fingerprint(prompt: str) -> str:
    """Short visual lineage fingerprint — first 12 chars, sanitized."""
    head = prompt.strip().splitlines()[0] if prompt.strip() else "(empty)"
    head = "".join(c if c.isprintable() and c != " " else "_" for c in head)
    return head[:12] or "(empty)"


# ----------------------------- driver ------------------------------------- #


def evolve(
    initial_prompts: Sequence[str],
    examples: Sequence[EvolveTrainExample],
    *,
    model_call: ScoreFn,
    generations: int = 3,
    population: int = 4,
    mutator: Mutator = templated_mutator,
    seed: int = 0,
) -> EvolveReport:
    """Run GEPA on ``initial_prompts`` for ``generations`` rounds.

    Args:
        initial_prompts: starting population (typically the human-tuned
            prompt as a single-element list). Empty lists are treated as
            ``[""]``.
        examples: the training set (small — 5-25 is typical).
        model_call: the model wrapper. Tests stub this.
        generations: number of rounds. ``0`` returns the seed
            candidates evaluated once — useful for sanity-checking the
            scoring path without mutation.
        population: target population per generation. Each generation
            mutates the current Pareto front until the population
            reaches this size (capped to 4× ``generations`` to keep
            runtime predictable).
        mutator: ``(prompt, rng) -> prompt`` callable. Defaults to
            :func:`templated_mutator`.
        seed: PRNG seed so test runs are deterministic.

    Returns:
        :class:`EvolveReport` with the best candidate (highest score,
        ties broken by length), the full Pareto front, and a per-
        generation history.
    """
    rng = random.Random(seed)
    seeds = list(initial_prompts) if initial_prompts else [""]
    population = max(1, population)

    pop: list[EvolveCandidate] = []
    for prompt in seeds:
        score = score_candidate(prompt, examples, model_call=model_call)
        pop.append(
            EvolveCandidate(
                prompt=prompt,
                score=score,
                length=len(prompt),
                generation=0,
            )
        )

    history: list[EvolveHistoryEntry] = [
        EvolveHistoryEntry(
            generation=0,
            population=len(pop),
            best_score=max(c.score for c in pop),
            front_size=len(pareto_front(pop)),
        )
    ]

    for g in range(1, generations + 1):
        front = pareto_front(pop)
        offspring: list[EvolveCandidate] = []
        attempts = 0
        max_attempts = population * 4
        existing_prompts = {c.prompt for c in pop}
        while len(offspring) < population and attempts < max_attempts:
            attempts += 1
            parent = rng.choice(front) if front else rng.choice(pop)
            child_prompt = mutator(parent.prompt, rng)
            if child_prompt in existing_prompts:
                continue
            existing_prompts.add(child_prompt)
            child_score = score_candidate(
                child_prompt, examples, model_call=model_call
            )
            offspring.append(
                EvolveCandidate(
                    prompt=child_prompt,
                    score=child_score,
                    length=len(child_prompt),
                    generation=g,
                    parents=(_fingerprint(parent.prompt),),
                )
            )
        pop = list(pareto_front(list(pop) + offspring))
        history.append(
            EvolveHistoryEntry(
                generation=g,
                population=len(pop),
                best_score=max(c.score for c in pop) if pop else 0.0,
                front_size=len(pop),
            )
        )

    front = pareto_front(pop)
    best = max(front, key=lambda c: (c.score, -c.length, -c.generation))
    return EvolveReport(
        best=best,
        front=front,
        history=tuple(history),
    )
