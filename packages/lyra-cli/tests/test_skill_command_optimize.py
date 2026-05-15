"""``lyra skill optimize`` CLI integration (Phase O.7).

Real LLM is monkeypatched: a scripted stub returns canned JSON for
Executor/Analyst/Mutator roles so the loop runs end-to-end without
network. Argus is forced off via ``--no-argus`` because the cascade
construction shells out to ``$LYRA_HOME`` state we don't want to
mutate during tests.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lyra_cli.commands import skill as skill_cmd
from lyra_cli.commands.skill import skill_app


runner = CliRunner()


_SKILL_BODY = """---
id: test-skill
name: Test Skill
version: 0.1.0
description: A skill we will optimize.
---
# Test Skill

When asked, respond with FOO.
"""


def _install_skill(target_root: Path, sid: str = "test-skill") -> Path:
    """Drop a SKILL.md under ``target_root/<sid>/`` for the optimize command."""
    skill_dir = target_root / sid
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(_SKILL_BODY, encoding="utf-8")
    return skill_dir / "SKILL.md"


def _write_scenarios(path: Path) -> Path:
    path.write_text(
        "- prompt: \"say something\"\n"
        "  eval: \"did the response include the required suffix?\"\n",
        encoding="utf-8",
    )
    return path


def _extract_body(executor_prompt: str) -> str:
    """Pull the SKILL.md body out of the executor template.

    The template wraps the body between ``SKILL.md body:\\n---\\n``
    and ``\\n---\\n\\nUser prompt:`` — we slice between those
    anchors so the stub can decide pass/fail based on body content
    alone, not the eval criterion text.
    """
    start = executor_prompt.find("SKILL.md body:\n---\n")
    end = executor_prompt.find("\n---\n\nUser prompt:")
    if start < 0 or end < 0:
        return ""
    return executor_prompt[start + len("SKILL.md body:\n---\n") : end]


def _scripted_llm(
    *,
    mutate_old: str = "FOO",
    mutate_new: str = "FOO-BAR",
    pass_when: str = "FOO-BAR",
):
    """Return a stand-in for ``_call_llm_for_optimize``.

    The router inspects the system prompt to figure out which role
    the optimizer is calling (Executor / Analyst / Mutator) and
    returns the matching canned JSON.
    """

    def _stub(prompt: str, *, system: str = "", max_tokens: int = 2048) -> str:
        if "diagnose" in system.lower():
            return json.dumps(
                {
                    "diagnosis": "skill lacks the suffix",
                    "target_section": "body",
                    "strategy": "add_constraint",
                }
            )
        if "ONE small edit" in system:
            return json.dumps(
                {
                    "old_text": mutate_old,
                    "new_text": mutate_new,
                    "reasoning": "anchor the required suffix",
                }
            )
        # Executor — pass only when the mutation lands in the body.
        passed = pass_when in _extract_body(prompt)
        return json.dumps({"passed": passed, "reason": ""})

    return _stub


def test_optimize_dry_run_reports_score(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "skills"
    skill_md = _install_skill(target)
    scenarios = _write_scenarios(tmp_path / "scenarios.yaml")

    monkeypatch.setattr(skill_cmd, "_call_llm_for_optimize", _scripted_llm())
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra_home"))

    result = runner.invoke(
        skill_app,
        [
            "optimize",
            "test-skill",
            "--scenarios",
            str(scenarios),
            "--target",
            str(target),
            "--no-argus",
            "--max-rounds",
            "3",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert payload["skill_id"] == "test-skill"
    assert payload["initial_score"] == 0.0
    assert payload["final_score"] == 1.0
    assert payload["target_reached"] is True
    assert payload["accepted_rounds"] == 1
    assert payload["applied"] is False
    # Dry-run must not have rewritten the SKILL.md.
    assert "FOO-BAR" not in skill_md.read_text(encoding="utf-8")


def test_optimize_apply_writes_backup_and_new_body(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "skills"
    skill_md = _install_skill(target)
    scenarios = _write_scenarios(tmp_path / "scenarios.yaml")

    monkeypatch.setattr(skill_cmd, "_call_llm_for_optimize", _scripted_llm())
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra_home"))

    result = runner.invoke(
        skill_app,
        [
            "optimize",
            "test-skill",
            "--scenarios",
            str(scenarios),
            "--target",
            str(target),
            "--no-argus",
            "--max-rounds",
            "3",
            "--apply",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["applied"] is True
    new_body = skill_md.read_text(encoding="utf-8")
    assert "FOO-BAR" in new_body
    backup = skill_md.with_suffix(".md.bak")
    assert backup.is_file()
    assert "FOO-BAR" not in backup.read_text(encoding="utf-8")

    # Mutation log was written under $LYRA_HOME.
    log = tmp_path / "lyra_home" / "skill_mutations.jsonl"
    assert log.is_file()
    rows = [
        json.loads(line)
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(r["skill_id"] == "test-skill" and r["accepted"] for r in rows)


def test_optimize_missing_skill_errors(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "skills"
    scenarios = _write_scenarios(tmp_path / "scenarios.yaml")
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra_home"))

    result = runner.invoke(
        skill_app,
        [
            "optimize",
            "ghost",
            "--scenarios",
            str(scenarios),
            "--target",
            str(target),
            "--no-argus",
            "--json",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "not installed" in payload["error"]


def test_optimize_rejects_bad_scenarios_yaml(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "skills"
    _install_skill(target)
    bad = tmp_path / "bad.yaml"
    bad.write_text("not a list\n", encoding="utf-8")
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / "lyra_home"))

    result = runner.invoke(
        skill_app,
        [
            "optimize",
            "test-skill",
            "--scenarios",
            str(bad),
            "--target",
            str(target),
            "--no-argus",
            "--json",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "list of" in payload["error"]
