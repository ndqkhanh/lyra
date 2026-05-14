"""Tests for Phase G — SSL skill representation."""
from lyra_skills.ssl_repr import (
    SSLLogical,
    SSLNormalizer,
    SSLScheduling,
    SSLSkill,
    ssl_matches,
)


class TestSSLScheduling:
    def test_matches_query_true(self):
        sched = SSLScheduling(triggers=["deploy", "release"])
        assert sched.matches_query("how do I deploy this service?")

    def test_matches_query_false(self):
        sched = SSLScheduling(triggers=["deploy"])
        assert not sched.matches_query("how do I revert a commit?")

    def test_matches_query_case_insensitive(self):
        sched = SSLScheduling(triggers=["DEPLOY"])
        assert sched.matches_query("deploy the service")

    def test_empty_triggers_no_match(self):
        sched = SSLScheduling()
        assert not sched.matches_query("anything")


class TestSSLLogical:
    def test_risk_level_high(self):
        log = SSLLogical(side_effects=["deletes all records"])
        assert log.risk_level == "high"

    def test_risk_level_high_action(self):
        log = SSLLogical(actions=["drop the table"])
        assert log.risk_level == "high"

    def test_risk_level_medium(self):
        log = SSLLogical(side_effects=["writes to file"])
        assert log.risk_level == "medium"

    def test_risk_level_low(self):
        log = SSLLogical(actions=["reads config"])
        assert log.risk_level == "low"


class TestSSLSkillFrontmatter:
    def test_to_frontmatter_contains_name(self):
        skill = SSLSkill(
            skill_id="test-id",
            name="Deploy Service",
            description="Deploy a microservice",
        )
        fm = skill.to_frontmatter()
        assert "name: Deploy Service" in fm
        assert "---" in fm

    def test_to_frontmatter_contains_risk(self):
        skill = SSLSkill(
            skill_id="t",
            name="Nuke DB",
            logical=SSLLogical(actions=["drop all tables"]),
        )
        fm = skill.to_frontmatter()
        assert "ssl_risk: high" in fm


class TestSSLNormalizer:
    def _norm(self, text: str):
        return SSLNormalizer().normalize("sid", "Test Skill", text)

    def test_extracts_triggers(self):
        text = "When deploying, run this skill.\nUse when releasing new versions."
        skill = self._norm(text)
        assert len(skill.scheduling.triggers) >= 1

    def test_extracts_steps(self):
        text = "## Instructions\n1. Build the image\n2. Push to registry\n3. Update manifest"
        skill = self._norm(text)
        assert len(skill.structural.execution_steps) >= 2

    def test_extracts_tools(self):
        text = "Run: docker build\nExecute: kubectl apply"
        skill = self._norm(text)
        assert len(skill.logical.tools_required) >= 1

    def test_workflow_parallel(self):
        text = "Run steps in parallel for speed."
        skill = self._norm(text)
        assert skill.structural.workflow_type == "parallel"

    def test_workflow_conditional(self):
        text = "If the test passes else revert."
        skill = self._norm(text)
        assert skill.structural.workflow_type == "conditional"

    def test_workflow_loop(self):
        text = "Repeat until all items are processed."
        skill = self._norm(text)
        assert skill.structural.workflow_type == "loop"

    def test_workflow_sequential_default(self):
        skill = self._norm("Step one. Step two.")
        assert skill.structural.workflow_type == "sequential"

    def test_estimated_turns_from_steps(self):
        text = "1. Do A\n2. Do B\n3. Do C"
        skill = self._norm(text)
        assert skill.structural.estimated_turns >= 1

    def test_description_extracted(self):
        text = "This skill handles deployments.\n# Title"
        skill = self._norm(text)
        assert "deployment" in skill.description.lower()

    def test_raw_text_preserved(self):
        text = "Raw skill content here."
        skill = self._norm(text)
        assert skill.raw_text == text


class TestSSLMatches:
    def _make_skill(self, triggers, risk):
        from lyra_skills.ssl_repr import SSLLogical, SSLScheduling, SSLSkill
        return SSLSkill(
            skill_id="s",
            name="Test",
            scheduling=SSLScheduling(triggers=triggers),
            logical=SSLLogical(side_effects=(["deletes"] if risk == "high" else [])),
        )

    def test_matches_trigger_no_cap(self):
        skill = self._make_skill(["deploy"], "high")
        assert ssl_matches(skill, "deploy the service")

    def test_no_match_wrong_trigger(self):
        skill = self._make_skill(["deploy"], "low")
        assert not ssl_matches(skill, "revert a commit")

    def test_risk_cap_blocks_high_risk(self):
        skill = self._make_skill(["deploy"], "high")
        assert not ssl_matches(skill, "deploy now", risk_cap="medium")

    def test_risk_cap_allows_equal_risk(self):
        skill = self._make_skill(["deploy"], "low")
        assert ssl_matches(skill, "deploy now", risk_cap="medium")
