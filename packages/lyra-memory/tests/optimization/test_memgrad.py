"""Tests for MemGrad Pipeline."""

import pytest

from lyra_memory.optimization.memgrad import (
    AgentTrajectory,
    FailurePattern,
    MemGradPipeline,
    RoleCluster,
    TextGrad,
)


class StubLLM:
    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or []
        self._idx = 0
        self.prompts: list[str] = []

    @property
    def responses(self) -> list[str]:
        return self._responses

    @responses.setter
    def responses(self, value: list[str]) -> None:
        self._responses = value
        self._idx = 0

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return "[]"


class TestTextGrad:
    def test_default_values(self):
        g = TextGrad(role="planner", gradient="improve planning")
        assert g.role == "planner"
        assert g.gradient == "improve planning"
        assert g.severity == 0.5
        assert g.pattern == "one-off"

    def test_custom_severity(self):
        g = TextGrad(role="executor", gradient="fix bug", severity=0.9, pattern="recurring")
        assert g.severity == 0.9
        assert g.pattern == "recurring"


class TestAgentTrajectory:
    def test_default_values(self):
        t = AgentTrajectory(task="build api", role="planner", outcome="success")
        assert t.task == "build api"
        assert t.role == "planner"
        assert t.outcome == "success"
        assert t.steps == []
        assert t.feedback == ""

    def test_with_steps_and_feedback(self):
        t = AgentTrajectory(
            task="debug pipeline",
            role="executor",
            outcome="failure",
            steps=["step1", "step2"],
            feedback="too slow",
        )
        assert len(t.steps) == 2
        assert t.feedback == "too slow"

    def test_auto_generated_id(self):
        t1 = AgentTrajectory(task="a", role="b", outcome="c")
        t2 = AgentTrajectory(task="a", role="b", outcome="c")
        assert t1.id != t2.id


class TestRoleCluster:
    def test_empty_cluster(self):
        c = RoleCluster(role="planner")
        assert c.role == "planner"
        assert c.gradients == []
        assert c.average_severity == 0.0
        assert c.recurring_count == 0

    def test_average_severity(self):
        g1 = TextGrad(role="planner", gradient="a", severity=0.8)
        g2 = TextGrad(role="planner", gradient="b", severity=0.4)
        c = RoleCluster(role="planner", gradients=[g1, g2])
        assert c.average_severity == pytest.approx(0.6)

    def test_recurring_count(self):
        g1 = TextGrad(role="planner", gradient="a", pattern="recurring")
        g2 = TextGrad(role="planner", gradient="b", pattern="one-off")
        g3 = TextGrad(role="planner", gradient="c", pattern="recurring")
        c = RoleCluster(role="planner", gradients=[g1, g2, g3])
        assert c.recurring_count == 2


class TestFailurePattern:
    def test_default_values(self):
        p = FailurePattern(role="planner", description="poor estimates")
        assert p.role == "planner"
        assert p.description == "poor estimates"
        assert p.frequency == 1
        assert p.severity == 0.5

    def test_record_occurrence(self):
        p = FailurePattern(role="executor", description="slow execution")
        p.record_occurrence()
        assert p.frequency == 2

    def test_auto_id(self):
        p1 = FailurePattern(role="a", description="b")
        p2 = FailurePattern(role="a", description="b")
        assert p1.id != p2.id


class TestMemGradPipeline:
    def _make_pipeline(self, responses: list[str] | None = None) -> MemGradPipeline:
        llm = StubLLM(responses=responses)
        return MemGradPipeline(llm=llm)

    def _gradients_json(self) -> str:
        return """[
            {"role": "planner", "gradient": "Plans lack specificity", "severity": 0.8, "pattern":
            "recurring"},
            {"role": "executor", "gradient": "Tool calls are too slow", "severity": 0.6, "pattern":
            "recurring"}
        ]"""

    # ── decompose_feedback ──

    async def test_decompose_empty_trajectories(self):
        pipeline = self._make_pipeline()
        result = await pipeline.decompose_feedback([])
        assert result == []

    async def test_decompose_parses_gradients(self):
        pipeline = self._make_pipeline(responses=[self._gradients_json()])
        trajectories = [
            AgentTrajectory(
                task="plan a project",
                role="planner",
                outcome="failure",
                feedback="plan was too vague",
            ),
        ]
        result = await pipeline.decompose_feedback(trajectories)
        assert len(result) == 2
        assert result[0].role == "planner"
        assert result[0].severity == 0.8
        assert result[1].role == "executor"

    async def test_decompose_includes_trajectory_in_prompt(self):
        pipeline = self._make_pipeline(responses=[self._gradients_json()])
        trajectories = [
            AgentTrajectory(
                task="fix authentication bug",
                role="executor",
                outcome="failure",
                feedback="missed edge case",
            ),
        ]
        await pipeline.decompose_feedback(trajectories)
        assert any("authentication bug" in p for p in pipeline.llm.prompts)
        assert any("missed edge case" in p for p in pipeline.llm.prompts)

    async def test_decompose_handles_invalid_json(self):
        pipeline = self._make_pipeline(responses=["not json"])
        trajectories = [AgentTrajectory(task="t", role="r", outcome="o")]
        result = await pipeline.decompose_feedback(trajectories)
        assert result == []

    async def test_decompose_handles_empty_json_array(self):
        pipeline = self._make_pipeline(responses=["[]"])
        trajectories = [AgentTrajectory(task="t", role="r", outcome="o")]
        result = await pipeline.decompose_feedback(trajectories)
        assert result == []

    # ── cluster_by_role ──

    async def test_cluster_by_role(self):
        pipeline = self._make_pipeline()
        gradients = [
            TextGrad(role="planner", gradient="g1"),
            TextGrad(role="planner", gradient="g2"),
            TextGrad(role="executor", gradient="g3"),
        ]
        clusters = await pipeline.cluster_by_role(gradients)
        assert len(clusters) == 2
        planner_cluster = next(c for c in clusters if c.role == "planner")
        assert len(planner_cluster.gradients) == 2

    async def test_cluster_empty_list(self):
        pipeline = self._make_pipeline()
        clusters = await pipeline.cluster_by_role([])
        assert clusters == []

    # ── optimize_prompt ──

    async def test_optimize_prompt_no_memories(self):
        pipeline = self._make_pipeline()
        result = await pipeline.optimize_prompt("planner", "original prompt", "", "")
        assert result == "original prompt"

    async def test_optimize_prompt_with_retrospective(self):
        pipeline = self._make_pipeline(responses=["revised prompt v2"])
        retro = "Past failure: plans were too vague"
        prosp = "When planning, add concrete milestones"
        result = await pipeline.optimize_prompt("planner", "original prompt", retro, prosp)
        assert result == "revised prompt v2"
        prompt_text = pipeline.llm.prompts[0]
        assert "too vague" in prompt_text
        assert "concrete milestones" in prompt_text

    async def test_format_trajectories(self):
        trajectories = [
            AgentTrajectory(
                task="debug build failure",
                role="executor",
                outcome="failure",
                steps=["s1", "s2"],
                feedback="incorrect approach",
            ),
        ]
        formatted = MemGradPipeline._format_trajectories(trajectories)
        assert "debug build failure" in formatted
        assert "executor" in formatted
        assert "incorrect approach" in formatted
