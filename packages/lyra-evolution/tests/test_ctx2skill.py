"""Tests for Phase H — Ctx2Skill extraction and Cross-Time Replay validation."""
from lyra_evolution.ctx2skill import (
    Ctx2SkillExtractor,
    CrossTimeReplayValidator,
    ExtractionResult,
    SkillDraft,
    TraceRecord,
)


def make_trace(
    trace_id="t1",
    task="deploy a service to production",
    steps=None,
    tools=None,
    outcome="success",
    context_tag="web",
) -> TraceRecord:
    return TraceRecord(
        trace_id=trace_id,
        task_description=task,
        steps=steps or ["build image", "push image", "apply manifest"],
        tools_used=tools or ["docker", "kubectl"],
        outcome=outcome,
        context_tag=context_tag,
    )


class TestTraceRecord:
    def test_succeeded_true(self):
        t = make_trace(outcome="success")
        assert t.succeeded

    def test_succeeded_false(self):
        t = make_trace(outcome="failure")
        assert not t.succeeded

    def test_succeeded_case_insensitive(self):
        t = make_trace(outcome="SUCCESS")
        assert t.succeeded


class TestCtx2SkillExtractor:
    def test_extract_successful_trace(self):
        extractor = Ctx2SkillExtractor()
        trace = make_trace()
        draft = extractor.extract(trace)
        assert draft is not None
        assert isinstance(draft, SkillDraft)

    def test_extract_failed_trace_returns_none(self):
        extractor = Ctx2SkillExtractor()
        trace = make_trace(outcome="failure")
        assert extractor.extract(trace) is None

    def test_extract_too_few_steps_returns_none(self):
        extractor = Ctx2SkillExtractor(min_steps=3)
        trace = make_trace(steps=["only one step"])
        assert extractor.extract(trace) is None

    def test_extract_populates_instructions(self):
        extractor = Ctx2SkillExtractor()
        trace = make_trace(steps=["step A", "step B", "step C"])
        draft = extractor.extract(trace)
        assert draft.instructions == ["step A", "step B", "step C"]

    def test_extract_deduplicates_tools(self):
        extractor = Ctx2SkillExtractor()
        trace = make_trace(tools=["docker", "docker", "kubectl"])
        draft = extractor.extract(trace)
        assert len(draft.tools_required) == len(set(draft.tools_required))

    def test_extract_records_source_trace(self):
        extractor = Ctx2SkillExtractor()
        trace = make_trace(trace_id="trace-99")
        draft = extractor.extract(trace)
        assert "trace-99" in draft.source_traces

    def test_extract_derives_name(self):
        extractor = Ctx2SkillExtractor()
        trace = make_trace(task="deploy a service to production")
        draft = extractor.extract(trace)
        assert len(draft.name) > 0

    def test_extract_derives_triggers(self):
        extractor = Ctx2SkillExtractor()
        trace = make_trace(task="when deploying, use this procedure")
        draft = extractor.extract(trace)
        assert len(draft.triggers) > 0


class TestSkillDraft:
    def test_to_skill_md_contains_name(self):
        draft = SkillDraft(
            name="deploy-service",
            description="Deploys a service",
            instructions=["build", "push"],
        )
        md = draft.to_skill_md()
        assert "# deploy-service" in md
        assert "1. build" in md
        assert "2. push" in md

    def test_to_skill_md_contains_triggers(self):
        draft = SkillDraft(
            name="test-skill",
            description="Test",
            triggers=["when deploying"],
        )
        md = draft.to_skill_md()
        assert "When to use" in md
        assert "when deploying" in md


class TestCrossTimeReplayValidator:
    def test_fails_with_too_few_contexts(self):
        validator = CrossTimeReplayValidator(min_contexts=2)
        draft = SkillDraft(name="my-skill", description="Test")
        validator.record_success("my-skill", "web")
        passed, reason = validator.validate(draft)
        assert not passed
        assert "1 context" in reason

    def test_passes_with_sufficient_contexts(self):
        validator = CrossTimeReplayValidator(min_contexts=2)
        draft = SkillDraft(name="my-skill", description="Test")
        validator.record_success("my-skill", "web")
        validator.record_success("my-skill", "cli")
        passed, reason = validator.validate(draft)
        assert passed
        assert "2 contexts" in reason

    def test_duplicate_contexts_not_double_counted(self):
        validator = CrossTimeReplayValidator(min_contexts=2)
        validator.record_success("s", "web")
        validator.record_success("s", "web")  # same context
        assert validator.context_count("s") == 1

    def test_context_count_unknown_skill(self):
        validator = CrossTimeReplayValidator()
        assert validator.context_count("unknown") == 0


class TestTryAdmit:
    def test_try_admit_accepted(self):
        extractor = Ctx2SkillExtractor()
        validator = CrossTimeReplayValidator(min_contexts=1)
        trace = make_trace()
        draft = extractor.extract(trace)
        validator.record_success(draft.name, "web")
        result = extractor.try_admit(draft, validator)
        assert isinstance(result, ExtractionResult)
        assert result.accepted

    def test_try_admit_rejected(self):
        extractor = Ctx2SkillExtractor()
        validator = CrossTimeReplayValidator(min_contexts=3)
        trace = make_trace()
        draft = extractor.extract(trace)
        validator.record_success(draft.name, "web")
        result = extractor.try_admit(draft, validator)
        assert not result.accepted
        assert result.draft is None
