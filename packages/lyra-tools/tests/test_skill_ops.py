"""Tests for skill operations tools."""
from __future__ import annotations

from lyra_tools.skill_ops import (
    skill_execute,
    skill_info,
    skill_install,
    skill_list,
    skill_uninstall,
)


class TestSkillList:
    def test_list_all_skills(self):
        result = skill_list()

        assert "skills" in result
        assert "count" in result
        assert result["count"] >= 0

    def test_list_with_category_filter(self):
        result = skill_list(category="code")

        assert result["category"] == "code"
        assert "skills" in result

    def test_list_with_tags_filter(self):
        result = skill_list(tags=["python", "testing"])

        assert result["tags"] == ["python", "testing"]
        assert "skills" in result

    def test_list_include_disabled(self):
        result = skill_list(include_disabled=True)

        assert "skills" in result


class TestSkillInfo:
    def test_info_not_found(self):
        result = skill_info(skill_id="nonexistent")

        assert result["found"] is False
        assert "error" in result

    def test_info_empty_id_errors(self):
        result = skill_info(skill_id="")

        assert result["found"] is False
        assert "error" in result


class TestSkillExecute:
    def test_execute_not_found(self):
        result = skill_execute(skill_id="nonexistent")

        assert result["executed"] is False
        assert "error" in result

    def test_execute_with_args(self):
        result = skill_execute(
            skill_id="test_skill",
            args={"param1": "value1"},
        )

        assert "executed" in result

    def test_execute_with_context(self):
        result = skill_execute(
            skill_id="test_skill",
            context={"repo_root": "/tmp/test"},
        )

        assert "executed" in result

    def test_execute_empty_id_errors(self):
        result = skill_execute(skill_id="")

        assert result["executed"] is False
        assert "error" in result


class TestSkillInstall:
    def test_install_user_scope(self):
        result = skill_install(
            source="https://example.com/skill.tar.gz",
            scope="user",
        )

        assert "installed" in result
        assert result["scope"] == "user"

    def test_install_project_scope(self):
        result = skill_install(
            source="/path/to/skill",
            scope="project",
        )

        assert "installed" in result
        assert result["scope"] == "project"

    def test_install_with_force(self):
        result = skill_install(
            source="skill-id",
            force=True,
        )

        assert "installed" in result

    def test_install_invalid_scope_errors(self):
        result = skill_install(
            source="test",
            scope="invalid",
        )

        assert result["installed"] is False
        assert "error" in result
        assert "scope" in result["error"]


class TestSkillUninstall:
    def test_uninstall_requires_confirmation(self):
        result = skill_uninstall(skill_id="test_skill")

        assert result["uninstalled"] is False
        assert "error" in result
        assert "confirm" in result["error"]

    def test_uninstall_with_confirmation(self):
        result = skill_uninstall(
            skill_id="test_skill",
            confirm=True,
        )

        assert "uninstalled" in result

    def test_uninstall_user_scope(self):
        result = skill_uninstall(
            skill_id="test_skill",
            scope="user",
            confirm=True,
        )

        assert result["scope"] == "user"

    def test_uninstall_project_scope(self):
        result = skill_uninstall(
            skill_id="test_skill",
            scope="project",
            confirm=True,
        )

        assert result["scope"] == "project"

    def test_uninstall_invalid_scope_errors(self):
        result = skill_uninstall(
            skill_id="test_skill",
            scope="invalid",
            confirm=True,
        )

        assert result["uninstalled"] is False
        assert "error" in result
