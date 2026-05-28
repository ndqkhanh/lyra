"""Tests for RetrospectiveMemory and ProspectiveMemory."""


from lyra_memory.optimization.dual_memory import (
    CorrectiveIntention,
    ProspectiveMemory,
    RetrospectiveMemory,
)
from lyra_memory.optimization.memgrad import FailurePattern, TextGrad


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
        return "When encountering X, do Y because Z."


class TestCorrectiveIntention:
    def test_default_values(self):
        c = CorrectiveIntention(role="planner", intention="When X, do Y because Z.")
        assert c.role == "planner"
        assert c.intention == "When X, do Y because Z."
        assert c.confidence == 0.7
        assert c.source_gradient == ""

    def test_with_source_gradient(self):
        c = CorrectiveIntention(
            role="executor",
            intention="When slow, optimize.",
            source_gradient="Tool calls too slow",
            confidence=0.9,
        )
        assert c.source_gradient == "Tool calls too slow"
        assert c.confidence == 0.9

    def test_auto_id(self):
        c1 = CorrectiveIntention(role="a", intention="b")
        c2 = CorrectiveIntention(role="a", intention="b")
        assert c1.id != c2.id


class TestRetrospectiveMemory:
    def _make_gradients(self) -> list[TextGrad]:
        return [
            TextGrad(role="planner", gradient="Plans lack specific milestones", severity=0.8, pattern="recurring"),
            TextGrad(role="planner", gradient="Time estimates consistently wrong", severity=0.7, pattern="recurring"),
            TextGrad(role="executor", gradient="Tool calls are too slow", severity=0.6, pattern="recurring"),
            TextGrad(role="planner", gradient="Minor formatting issue", severity=0.2, pattern="one-off"),
        ]

    def test_update_stores_significant_patterns(self):
        rm = RetrospectiveMemory()
        rm.update("planner", self._make_gradients()[:2])
        assert len(rm.patterns["planner"]) == 2

    def test_update_filters_low_severity(self):
        rm = RetrospectiveMemory()
        rm.update("planner", self._make_gradients())
        assert len(rm.patterns["planner"]) == 3
        severities = {p.severity for p in rm.patterns["planner"]}
        assert 0.2 not in severities

    def test_update_merges_similar_patterns(self):
        rm = RetrospectiveMemory()
        rm.update("planner", [
            TextGrad(role="planner", gradient="Specific milestone tracking missing", severity=0.8),
        ])
        rm.update("planner", [
            TextGrad(role="planner", gradient="Missing milestone tracking for tasks", severity=0.7),
        ])
        assert len(rm.patterns["planner"]) == 1
        assert rm.patterns["planner"][0].frequency == 2

    def test_get_formats_patterns(self):
        rm = RetrospectiveMemory()
        rm.update("planner", self._make_gradients())
        output = rm.get("planner")
        assert "Past failure patterns:" in output
        assert "Plans lack specific milestones" in output

    def test_get_nonexistent_role(self):
        rm = RetrospectiveMemory()
        assert rm.get("nobody") == ""

    def test_get_top_patterns(self):
        rm = RetrospectiveMemory()
        rm.update("planner", self._make_gradients())
        rm.patterns["planner"][0].record_occurrence()
        top = rm.get_top_patterns("planner", n=1)
        assert len(top) == 1
        assert top[0].frequency == 2

    def test_total_patterns(self):
        rm = RetrospectiveMemory()
        rm.update("planner", self._make_gradients()[:2])
        rm.update("executor", self._make_gradients()[2:])
        assert rm.total_patterns == 3

    def test_clear(self):
        rm = RetrospectiveMemory()
        rm.update("planner", self._make_gradients())
        rm.clear()
        assert rm.total_patterns == 0

    def test_find_similar_no_overlap(self):
        rm = RetrospectiveMemory()

        existing = FailurePattern(role="planner", description="slow database queries timeout")
        rm.patterns["planner"] = [existing]
        new = FailurePattern(role="planner", description="python formatting style issues")
        result = rm._find_similar("planner", new)
        assert result is None

    def test_find_similar_with_overlap(self):
        rm = RetrospectiveMemory()

        existing = FailurePattern(role="planner", description="specific milestone tracking missing for plans")
        rm.patterns["planner"] = [existing]
        new = FailurePattern(role="planner", description="missing milestone tracking for specific tasks")
        result = rm._find_similar("planner", new)
        assert result is not None
        assert result.description == "specific milestone tracking missing for plans"


class TestProspectiveMemory:
    def _make_gradients(self) -> list[TextGrad]:
        return [
            TextGrad(role="planner", gradient="Plans lack specific milestones", severity=0.8),
            TextGrad(role="executor", gradient="Tool calls too slow", severity=0.6),
        ]

    async def test_update_creates_intentions(self):
        llm = StubLLM()
        pm = ProspectiveMemory(llm=llm)
        await pm.update("planner", self._make_gradients()[:1])
        assert len(pm.intentions["planner"]) == 1
        assert pm.intentions["planner"][0].role == "planner"

    async def test_update_uses_llm_for_intention_formulation(self):
        llm = StubLLM(responses=["When starting a plan, list 3 concrete milestones because specificity ensures alignment."])
        pm = ProspectiveMemory(llm=llm)
        await pm.update("planner", self._make_gradients()[:1])
        assert "list 3 concrete milestones" in pm.intentions["planner"][0].intention

    async def test_get_formats_intentions(self):
        llm = StubLLM(responses=[
            "When X, do Y because Z.",
            "When A, do B because C.",
        ])
        pm = ProspectiveMemory(llm=llm)
        await pm.update("planner", self._make_gradients())
        output = pm.get("planner")
        assert "Corrective intentions:" in output
        assert "When X, do Y because Z." in output

    async def test_get_nonexistent_role(self):
        pm = ProspectiveMemory(llm=StubLLM())
        assert pm.get("nobody") == ""

    async def test_total_intentions(self):
        llm = StubLLM(responses=[
            "When X, do Y because Z.",
            "When A, do B because C.",
        ])
        pm = ProspectiveMemory(llm=llm)
        await pm.update("planner", self._make_gradients()[:1])
        await pm.update("executor", self._make_gradients()[1:])
        assert pm.total_intentions == 2

    async def test_clear(self):
        llm = StubLLM()
        pm = ProspectiveMemory(llm=llm)
        await pm.update("planner", self._make_gradients()[:1])
        pm.clear()
        assert pm.total_intentions == 0
