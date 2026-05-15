"""Tests for harness_core.programs — DSPy-style compilable programs."""
from __future__ import annotations

import pytest

from harness_core.multi_hop import (
    IRCoTOperator,
    SelfAskOperator,
    StubLLM,
    StubRetriever,
)
from harness_core.pipeline import MultiHopPipeline
from harness_core.programs import (
    BootstrapFewShot,
    Demonstration,
    Example,
    MultiHopProgram,
    ProgramOutput,
    Signature,
    evaluate,
)
from harness_core.routing import BELLERouter


def _build_immediate_answer_pipeline(answer: str = "42") -> MultiHopPipeline:
    llm = StubLLM(responses=[
        f"Are follow up questions needed here? No\nSo the final answer is: {answer}\n",
    ])
    return MultiHopPipeline(
        router=BELLERouter(),
        self_ask=SelfAskOperator(llm=llm, retriever=StubRetriever(), max_hops=1),
        ircot=IRCoTOperator(llm=StubLLM(responses=[]), retriever=StubRetriever()),
    )


# --- Signature ----------------------------------------------------------


class TestSignature:
    def test_valid(self):
        sig = Signature(instruction="answer", inputs=("question",), output="answer_field")
        assert sig.inputs == ("question",)

    def test_empty_instruction_rejected(self):
        with pytest.raises(ValueError):
            Signature(instruction="", inputs=("q",), output="a")

    def test_empty_inputs_rejected(self):
        with pytest.raises(ValueError):
            Signature(instruction="x", inputs=(), output="a")

    def test_output_in_inputs_rejected(self):
        with pytest.raises(ValueError):
            Signature(instruction="x", inputs=("a",), output="a")

    def test_render_no_demos(self):
        sig = Signature(instruction="Answer precisely.", inputs=("question",), output="answer")
        rendered = sig.render()
        assert "Answer precisely." in rendered
        assert "Examples:" not in rendered

    def test_render_with_demos(self):
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        demos = [
            Demonstration(
                example=Example(inputs={"question": "what is 2+2?"}, output="4"),
                trace=("compute",),
                score=1.0,
            ),
        ]
        rendered = sig.render(demonstrations=demos)
        assert "Examples:" in rendered
        assert "what is 2+2?" in rendered
        assert "answer='4'" in rendered


# --- Example / Demonstration -------------------------------------------


class TestExample:
    def test_valid(self):
        e = Example(inputs={"q": "x"}, output="y")
        assert e.inputs == {"q": "x"}

    def test_empty_inputs_rejected(self):
        with pytest.raises(ValueError):
            Example(inputs={}, output="y")


class TestDemonstration:
    def test_valid(self):
        d = Demonstration(
            example=Example(inputs={"q": "x"}, output="y"),
            trace=("step1", "step2"),
            score=0.8,
        )
        assert d.score == 0.8

    def test_score_out_of_range(self):
        ex = Example(inputs={"q": "x"}, output="y")
        with pytest.raises(ValueError):
            Demonstration(example=ex, trace=(), score=1.5)


# --- MultiHopProgram ---------------------------------------------------


class TestMultiHopProgram:
    def test_call_returns_program_output(self):
        pipeline = _build_immediate_answer_pipeline("42")
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        out = program(question="what is everything")
        assert isinstance(out, ProgramOutput)
        assert out.output == "42"
        assert out.completed is True
        assert out.demonstrations_used == 0

    def test_missing_input_raises(self):
        pipeline = _build_immediate_answer_pipeline()
        sig = Signature(instruction="Answer.", inputs=("question", "context"), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        with pytest.raises(ValueError) as exc:
            program(question="x")  # missing 'context'
        assert "context" in str(exc.value)

    def test_with_demonstrations_immutable(self):
        pipeline = _build_immediate_answer_pipeline()
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        demo = Demonstration(
            example=Example(inputs={"question": "q"}, output="a"),
            trace=(),
            score=1.0,
        )
        program2 = program.with_demonstrations([demo])
        assert program is not program2
        assert program.demonstrations == ()
        assert len(program2.demonstrations) == 1

    def test_with_signature_immutable(self):
        pipeline = _build_immediate_answer_pipeline()
        sig1 = Signature(instruction="Answer A.", inputs=("question",), output="answer")
        sig2 = Signature(instruction="Answer B.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig1)
        program2 = program.with_signature(sig2)
        assert program.signature.instruction == "Answer A."
        assert program2.signature.instruction == "Answer B."

    def test_demonstrations_threaded_to_prompt(self):
        # Build a pipeline + program with demonstrations; the demonstrations
        # should appear in the rendered query passed to the operator.
        # We verify by intercepting the LLM prompt indirectly: demonstrations
        # appear in the operator's first prompt because the program prepends
        # them via _compose_query. Direct test: render should include them.
        pipeline = _build_immediate_answer_pipeline()
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        demo = Demonstration(
            example=Example(inputs={"question": "what is 1+1?"}, output="2"),
            trace=("compute",),
            score=1.0,
        )
        program = MultiHopProgram(pipeline=pipeline, signature=sig).with_demonstrations([demo])
        # Internal compose path:
        rendered = program._compose_query("what is 2+2?")
        assert "what is 1+1?" in rendered
        assert "Question: what is 2+2?" in rendered


# --- evaluate -----------------------------------------------------------


class TestEvaluate:
    def test_mean_score(self):
        pipeline = _build_immediate_answer_pipeline("42")
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)

        # Two examples — one expects "42" (score=1.0), one expects "x" (score=0.0).
        # But the StubLLM only has 1 response, so we need to extend or use a fresh pipeline per example.
        # Simpler: only one example.
        examples = [Example(inputs={"question": "q"}, output="42")]
        score = evaluate(
            program=program,
            examples=examples,
            eval_fn=lambda ex, out: 1.0 if out.output == ex.output else 0.0,
        )
        assert score == 1.0

    def test_empty_examples_rejected(self):
        pipeline = _build_immediate_answer_pipeline()
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        with pytest.raises(ValueError):
            evaluate(program=program, examples=[], eval_fn=lambda e, o: 1.0)

    def test_eval_fn_out_of_range_rejected(self):
        pipeline = _build_immediate_answer_pipeline()
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        with pytest.raises(ValueError):
            evaluate(
                program=program,
                examples=[Example(inputs={"question": "q"}, output="x")],
                eval_fn=lambda e, o: 1.5,  # out of range
            )


# --- BootstrapFewShot ---------------------------------------------------


class TestBootstrapFewShot:
    def _build_repeating_pipeline(self, n_examples: int, answer: str = "42") -> MultiHopPipeline:
        # StubLLM with N copies of the same answer response, so the same
        # pipeline can be called N times during compile + eval.
        responses = [
            f"Are follow up questions needed here? No\nSo the final answer is: {answer}\n"
        ] * n_examples
        llm = StubLLM(responses=responses)
        return MultiHopPipeline(
            router=BELLERouter(),
            self_ask=SelfAskOperator(llm=llm, retriever=StubRetriever(), max_hops=1),
            ircot=IRCoTOperator(llm=StubLLM(responses=[]), retriever=StubRetriever()),
        )

    def test_compile_keeps_high_score_demos(self):
        pipeline = self._build_repeating_pipeline(n_examples=3)
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)

        # All 3 examples expect "42" — all should score 1.0 → all kept.
        trainset = [
            Example(inputs={"question": "q1"}, output="42"),
            Example(inputs={"question": "q2"}, output="42"),
            Example(inputs={"question": "q3"}, output="42"),
        ]
        bf = BootstrapFewShot(max_bootstrapped_demos=2, min_score=0.5)
        compiled = bf.compile(
            program=program,
            trainset=trainset,
            eval_fn=lambda ex, out: 1.0 if out.output == ex.output else 0.0,
        )
        assert len(compiled.demonstrations) == 2
        assert all(d.score == 1.0 for d in compiled.demonstrations)

    def test_compile_filters_low_score(self):
        # All examples expect "wrong" → all score 0.0 → all filtered out.
        pipeline = self._build_repeating_pipeline(n_examples=3, answer="42")
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        trainset = [Example(inputs={"question": f"q{i}"}, output="wrong") for i in range(3)]
        bf = BootstrapFewShot(min_score=0.5)
        compiled = bf.compile(
            program=program,
            trainset=trainset,
            eval_fn=lambda ex, out: 1.0 if out.output == ex.output else 0.0,
        )
        assert len(compiled.demonstrations) == 0

    def test_compile_skip_failed(self):
        # Make the LLM run out so all calls fail (StubLLM raises).
        llm = StubLLM(responses=[])
        pipeline = MultiHopPipeline(
            router=BELLERouter(),
            self_ask=SelfAskOperator(llm=llm, retriever=StubRetriever(), max_hops=1),
            ircot=IRCoTOperator(llm=StubLLM(responses=[]), retriever=StubRetriever()),
        )
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        bf = BootstrapFewShot(skip_failed_completions=True)
        compiled = bf.compile(
            program=program,
            trainset=[Example(inputs={"question": "q"}, output="x")],
            eval_fn=lambda e, o: 1.0,
        )
        # Failed completions skipped → no demonstrations.
        assert compiled.demonstrations == ()

    def test_compile_invalid_max_demos(self):
        with pytest.raises(ValueError):
            BootstrapFewShot(max_bootstrapped_demos=-1)

    def test_compile_invalid_min_score(self):
        with pytest.raises(ValueError):
            BootstrapFewShot(min_score=1.5)

    def test_compile_eval_fn_out_of_range(self):
        pipeline = self._build_repeating_pipeline(n_examples=1)
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        bf = BootstrapFewShot()
        with pytest.raises(ValueError):
            bf.compile(
                program=program,
                trainset=[Example(inputs={"question": "q"}, output="x")],
                eval_fn=lambda e, o: 2.0,
            )

    def test_compile_returns_immutable(self):
        # The original program is unchanged after compile.
        pipeline = self._build_repeating_pipeline(n_examples=1)
        sig = Signature(instruction="Answer.", inputs=("question",), output="answer")
        program = MultiHopProgram(pipeline=pipeline, signature=sig)
        bf = BootstrapFewShot()
        bf.compile(
            program=program,
            trainset=[Example(inputs={"question": "q"}, output="42")],
            eval_fn=lambda e, o: 1.0,
        )
        assert program.demonstrations == ()
