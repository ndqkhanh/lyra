"""DSPy-style multi-hop program — Signature + Demonstration buffer.

The program is a thin wrapper around :class:`MultiHopPipeline`. It adds:

    - A :class:`Signature` declaring inputs + output + instruction.
    - A tuple of :class:`Demonstration` examples prepended to the prompt.
    - Immutable :meth:`with_demonstrations` for compilation.

The program is *deterministic given the same pipeline + demonstrations*:
calling it twice with the same inputs and the same pipeline state returns
the same answer. This composes with :class:`PureFunctionAgent` semantics —
compiled programs are replayable.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Optional

from ..pipeline import MultiHopPipeline, PipelineResult


@dataclass(frozen=True)
class Signature:
    """Typed I/O schema for a program.

    >>> sig = Signature(
    ...     instruction="Answer the multi-hop question precisely.",
    ...     inputs=("question",),
    ...     output="answer",
    ... )
    >>> "question" in sig.inputs
    True
    """

    instruction: str
    inputs: tuple[str, ...] = ("question",)
    output: str = "answer"

    def __post_init__(self) -> None:
        if not self.instruction:
            raise ValueError("instruction must be non-empty")
        if not self.inputs:
            raise ValueError("inputs must be non-empty")
        if not self.output:
            raise ValueError("output must be non-empty")
        # Output field must not collide with an input.
        if self.output in self.inputs:
            raise ValueError(
                f"output {self.output!r} cannot also be an input field"
            )

    def render(self, *, demonstrations: Iterable["Demonstration"] = ()) -> str:
        """Render the prompt header (instruction + demonstrations)."""
        lines = [self.instruction.rstrip(), ""]
        demos = tuple(demonstrations)
        if demos:
            lines.append("Examples:")
            for i, demo in enumerate(demos, 1):
                ex = demo.example
                input_block = "; ".join(
                    f"{k}={ex.inputs.get(k)!r}" for k in self.inputs
                )
                lines.append(f"  {i}. {input_block} → {self.output}={ex.output!r}")
            lines.append("")
        return "\n".join(lines)


@dataclass(frozen=True)
class Example:
    """One labelled (inputs, output) example for training/compilation."""

    inputs: dict[str, Any]
    output: Any

    def __post_init__(self) -> None:
        if not self.inputs:
            raise ValueError("inputs dict must be non-empty")


@dataclass(frozen=True)
class Demonstration:
    """A bootstrapped demonstration — example + agent trace + score."""

    example: Example
    trace: tuple[str, ...]
    score: float
    operator_used: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")


@dataclass(frozen=True)
class ProgramOutput:
    """The output of a program call."""

    inputs: dict[str, Any]
    output: Any
    pipeline_result: PipelineResult
    demonstrations_used: int = 0

    @property
    def completed(self) -> bool:
        return self.pipeline_result.completed


@dataclass
class MultiHopProgram:
    """A compilable multi-hop program over a :class:`MultiHopPipeline`.

    Calling the program runs the pipeline on the rendered prompt; the
    demonstration buffer is used to *prefix* the question with worked
    examples (DSPy-style few-shot).

    >>> from harness_core.routing import BELLERouter
    >>> from harness_core.multi_hop import (
    ...     SelfAskOperator, IRCoTOperator, StubLLM, StubRetriever,
    ... )
    >>> from harness_core.pipeline import MultiHopPipeline
    >>> llm = StubLLM(responses=[
    ...     "Are follow up questions needed here? No\\nSo the final answer is: 42\\n"
    ... ])
    >>> pipeline = MultiHopPipeline(
    ...     router=BELLERouter(),
    ...     self_ask=SelfAskOperator(llm=llm, retriever=StubRetriever(), max_hops=1),
    ...     ircot=IRCoTOperator(llm=StubLLM(responses=[]), retriever=StubRetriever()),
    ... )
    >>> sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
    >>> program = MultiHopProgram(pipeline=pipeline, signature=sig)
    >>> out = program(question="ultimate?")
    >>> out.output
    '42'
    """

    pipeline: MultiHopPipeline
    signature: Signature
    demonstrations: tuple[Demonstration, ...] = ()

    def __call__(self, **inputs: Any) -> ProgramOutput:
        """Run the program on the given inputs.

        The first input field's value is used as the multi-hop query;
        additional inputs are recorded in the result but not threaded into
        the pipeline (production wires them through the prompt).
        """
        missing = [name for name in self.signature.inputs if name not in inputs]
        if missing:
            raise ValueError(
                f"missing required inputs: {missing}; signature requires {self.signature.inputs}"
            )

        # The first input is the canonical query; production templates render
        # the full prompt header + demonstrations + question.
        primary_field = self.signature.inputs[0]
        primary_value = str(inputs[primary_field])

        rendered_query = self._compose_query(primary_value)
        result = self.pipeline.answer(rendered_query)
        return ProgramOutput(
            inputs=dict(inputs),
            output=result.answer,
            pipeline_result=result,
            demonstrations_used=len(self.demonstrations),
        )

    def with_demonstrations(
        self,
        demonstrations: Iterable[Demonstration],
    ) -> "MultiHopProgram":
        """Return a new program with the given demonstrations attached.

        Immutable update — the original program is unchanged.
        """
        return replace(self, demonstrations=tuple(demonstrations))

    def with_signature(self, signature: Signature) -> "MultiHopProgram":
        """Return a new program with a different signature."""
        return replace(self, signature=signature)

    def _compose_query(self, primary_value: str) -> str:
        """Compose the rendered prompt header + question.

        The pipeline's underlying operators see the full rendered text
        (including demonstrations + instruction). For the rule-based router,
        the query type classifies on the *whole rendered string*, so the
        primary value should appear last for clean classification.
        """
        header = self.signature.render(demonstrations=self.demonstrations)
        if header.strip():
            return f"{header}\nQuestion: {primary_value}"
        return primary_value


def evaluate(
    *,
    program: MultiHopProgram,
    examples: Iterable[Example],
    eval_fn: Callable[[Example, ProgramOutput], float],
) -> float:
    """Mean score of a program over an evaluation set.

    ``eval_fn(example, output) -> float`` returns a score in [0, 1] for one
    (example, output) pair. The average across the eval set is returned.
    """
    examples = list(examples)
    if not examples:
        raise ValueError("examples must be non-empty")
    total = 0.0
    n = 0
    for ex in examples:
        out = program(**ex.inputs)
        score = eval_fn(ex, out)
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"eval_fn returned out-of-range score: {score}")
        total += score
        n += 1
    return total / n


__all__ = [
    "Demonstration",
    "Example",
    "MultiHopProgram",
    "ProgramOutput",
    "Signature",
    "evaluate",
]
