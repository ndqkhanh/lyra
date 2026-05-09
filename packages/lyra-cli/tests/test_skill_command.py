"""Tests for ``lyra skill`` CLI (Phase N.3)."""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lyra_cli.commands.skill import skill_app


runner = CliRunner()


def _write_skill(src: Path, *, sid: str, version: str = "0.1.0", desc: str = "d") -> Path:
    """Materialise a minimal SKILL.md-rooted directory for installation."""
    skill_dir = src / sid
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nid: {sid}\nname: {sid}\nversion: {version}\ndescription: {desc}\n---\nbody\n"
    )
    return skill_dir


def test_add_local_path_succeeds(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    skill = _write_skill(src, sid="hello", desc="hi from skill")

    result = runner.invoke(
        skill_app,
        ["add", str(skill), "--target", str(target), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert payload["id"] == "hello"
    assert (target / "hello" / "SKILL.md").is_file()


def test_add_collision_without_force_fails(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    skill = _write_skill(src, sid="dup")

    runner.invoke(skill_app, ["add", str(skill), "--target", str(target)])
    second = runner.invoke(
        skill_app,
        ["add", str(skill), "--target", str(target), "--json"],
    )
    assert second.exit_code == 1
    payload = json.loads(second.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "already installed" in payload["error"]


def test_add_force_replaces(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="dup", desc="v1")
    runner.invoke(skill_app, ["add", str(src / "dup"), "--target", str(target)])

    src2 = tmp_path / "src2"
    _write_skill(src2, sid="dup", desc="v2")
    result = runner.invoke(
        skill_app,
        [
            "add",
            str(src2 / "dup"),
            "--target",
            str(target),
            "--force",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["replaced"] is True
    assert payload["description"] == "v2"


def test_list_command_emits_installed_skills(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="alpha")
    _write_skill(src, sid="beta")
    runner.invoke(skill_app, ["add", str(src / "alpha"), "--target", str(target)])
    runner.invoke(skill_app, ["add", str(src / "beta"), "--target", str(target)])

    result = runner.invoke(
        skill_app, ["list", "--target", str(target), "--json"]
    )
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout.strip().splitlines()[-1])
    assert {r["id"] for r in rows} == {"alpha", "beta"}


def test_remove_command_deletes_skill(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="bye")
    runner.invoke(skill_app, ["add", str(src / "bye"), "--target", str(target)])
    result = runner.invoke(
        skill_app, ["remove", "bye", "--target", str(target), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert not (target / "bye").exists()


def test_remove_unknown_skill_fails(tmp_path: Path) -> None:
    target = tmp_path / "skills"
    target.mkdir()
    result = runner.invoke(
        skill_app,
        ["remove", "missing", "--target", str(target), "--json"],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False


# ---------------------------------------------------------------------------
# stats (Phase O.3)
# ---------------------------------------------------------------------------


def _seed_ledger(
    tmp_path: Path,
    monkeypatch,
    *,
    rows: list[tuple[str, int, int, float, str]],
) -> None:
    """Populate a skill ledger under a tmp ``LYRA_HOME``.

    Each row is ``(skill_id, successes, failures, last_used_at, last_failure_reason)``.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))

    from lyra_skills.ledger import (
        SkillLedger,
        SkillStats,
        save_ledger,
    )

    ledger = SkillLedger()
    for sid, ok, bad, ts, reason in rows:
        stats = SkillStats(
            skill_id=sid,
            successes=ok,
            failures=bad,
            last_used_at=ts,
            last_failure_reason=reason,
        )
        ledger.skills[sid] = stats
    save_ledger(ledger)


def test_stats_json_lists_seeded_rows(
    tmp_path: Path, monkeypatch
) -> None:
    """``lyra skill stats --json`` returns one row per ledger entry.

    Each row is a flat dict with the documented columns so external
    tools (Grafana, jq pipelines) can consume it without parsing the
    Rich table.
    """
    import time

    now = time.time()
    _seed_ledger(
        tmp_path,
        monkeypatch,
        rows=[
            ("tdd-guide", 7, 1, now - 600, "stale heuristic"),
            ("brainstorming", 2, 5, now - 86400, "wrong domain"),
            ("dormant", 0, 0, 0.0, ""),
        ],
    )

    result = runner.invoke(skill_app, ["stats", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout.strip().splitlines()[-1])
    by_id = {r["id"]: r for r in rows}

    assert set(by_id.keys()) == {"tdd-guide", "brainstorming", "dormant"}
    tdd = by_id["tdd-guide"]
    assert tdd["successes"] == 7
    assert tdd["failures"] == 1
    assert tdd["utility"] > 0
    assert "last_used_at" in tdd

    brainstorming = by_id["brainstorming"]
    assert brainstorming["last_failure_reason"] == "wrong domain"
    assert brainstorming["utility"] < tdd["utility"]


def test_stats_default_orders_by_utility_desc(
    tmp_path: Path, monkeypatch
) -> None:
    """Without ``--json`` the Rich table sorts highest utility first.

    Reflective Learning is most useful when a quick glance highlights
    the strongest performers; failures bubble to the bottom for triage
    via ``lyra skill reflect``.
    """
    import time

    now = time.time()
    _seed_ledger(
        tmp_path,
        monkeypatch,
        rows=[
            ("low", 0, 4, now, "always wrong"),
            ("high", 9, 1, now, ""),
            ("middle", 3, 2, now, "sometimes off"),
        ],
    )

    result = runner.invoke(skill_app, ["stats"])
    assert result.exit_code == 0, result.output
    output = result.stdout
    high_pos = output.find("high")
    middle_pos = output.find("middle")
    low_pos = output.find("low")
    assert 0 <= high_pos < middle_pos < low_pos, (
        f"expected utility order high → middle → low; got positions "
        f"high={high_pos} middle={middle_pos} low={low_pos}\n{output}"
    )


def test_stats_top_limits_rows(
    tmp_path: Path, monkeypatch
) -> None:
    """``--top N`` clamps to the top-N by utility."""
    import time

    now = time.time()
    _seed_ledger(
        tmp_path,
        monkeypatch,
        rows=[
            ("a", 1, 0, now, ""),
            ("b", 2, 0, now, ""),
            ("c", 3, 0, now, ""),
        ],
    )

    result = runner.invoke(skill_app, ["stats", "--top", "2", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout.strip().splitlines()[-1])
    assert len(rows) == 2
    # Top by utility — recency-equal so successes win.
    assert [r["id"] for r in rows] == ["c", "b"]


def test_stats_handles_empty_ledger(
    tmp_path: Path, monkeypatch
) -> None:
    """No ledger file → friendly empty output, exit 0.

    First-time users (``lyra`` fresh install) shouldn't see a
    traceback when the ledger has never been touched.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))

    result = runner.invoke(skill_app, ["stats"])
    assert result.exit_code == 0, result.output
    assert "no skill activations" in result.stdout.lower()

    result_json = runner.invoke(skill_app, ["stats", "--json"])
    assert result_json.exit_code == 0
    rows = json.loads(result_json.stdout.strip().splitlines()[-1])
    assert rows == []


# ---------------------------------------------------------------------------
# reflect (Phase O.4 — propose improved SKILL.md from failures)
# ---------------------------------------------------------------------------


def _install_skill_with_body(
    src: Path, target: Path, *, sid: str, body: str
) -> Path:
    """Install a skill that includes a body section.

    ``body`` is the markdown that goes after the front-matter and
    becomes the meat of SKILL.md the LLM will rewrite.
    """
    skill_dir = src / sid
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = (
        f"---\nid: {sid}\nname: {sid}\nversion: 0.1.0\n"
        f"description: original\n---\n{body}\n"
    )
    (skill_dir / "SKILL.md").write_text(md)
    runner.invoke(
        skill_app, ["add", str(skill_dir), "--target", str(target)]
    )
    return target / sid / "SKILL.md"


def _seed_failure_history(
    monkeypatch,
    *,
    skill_id: str,
    last_failure_reason: str,
    failure_details: list[str] | None = None,
) -> None:
    """Record a series of failures for ``skill_id`` in the ledger."""
    import time

    from lyra_skills.ledger import (
        OUTCOME_FAILURE,
        OUTCOME_SUCCESS,
        SkillOutcome,
        record_outcome,
    )

    now = time.time()
    record_outcome(
        skill_id,
        SkillOutcome(
            ts=now,
            session_id="s",
            turn=1,
            kind=OUTCOME_FAILURE,
            detail=last_failure_reason,
        ),
    )
    for i, det in enumerate(failure_details or []):
        record_outcome(
            skill_id,
            SkillOutcome(
                ts=now - 60 * (i + 1),
                session_id="s",
                turn=i + 2,
                kind=OUTCOME_FAILURE,
                detail=det,
            ),
        )


def test_reflect_dry_run_does_not_modify_skill_md(
    tmp_path: Path, monkeypatch
) -> None:
    """Default ``reflect`` is dry-run: shows proposal, doesn't write.

    Reflective Learning must not silently mutate user-curated SKILL
    files. ``--apply`` is required to commit a rewrite.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    src = tmp_path / "src"
    target = tmp_path / "skills"
    skill_path = _install_skill_with_body(
        src, target, sid="planner", body="Plan tasks before coding."
    )
    _seed_failure_history(
        monkeypatch,
        skill_id="planner",
        last_failure_reason="user said: plan was too vague",
    )

    proposal_md = (
        "---\nid: planner\nname: planner\nversion: 0.2.0\n"
        "description: improved\n---\n"
        "Plan tasks before coding. Be concrete: enumerate file paths.\n"
    )

    def stub_llm(prompt: str) -> str:
        assert "planner" in prompt
        assert "plan was too vague" in prompt
        return proposal_md

    from lyra_cli.commands import skill as skill_module

    monkeypatch.setattr(skill_module, "_call_llm_for_reflection", stub_llm)

    result = runner.invoke(
        skill_app, ["reflect", "planner", "--target", str(target)]
    )
    assert result.exit_code == 0, result.output
    assert "proposal" in result.output.lower()
    on_disk = skill_path.read_text()
    assert "Plan tasks before coding." in on_disk
    assert "enumerate file paths" not in on_disk


def test_reflect_apply_writes_proposed_skill_md(
    tmp_path: Path, monkeypatch
) -> None:
    """``--apply`` writes the LLM proposal to disk.

    A backup file (``SKILL.md.bak``) must be left behind so users can
    revert a bad reflection without manually undoing the change.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    src = tmp_path / "src"
    target = tmp_path / "skills"
    skill_path = _install_skill_with_body(
        src, target, sid="planner", body="Plan tasks."
    )
    _seed_failure_history(
        monkeypatch,
        skill_id="planner",
        last_failure_reason="too vague",
    )

    proposal_md = (
        "---\nid: planner\nname: planner\nversion: 0.2.0\n"
        "description: improved\n---\n"
        "Plan tasks. Always enumerate file paths.\n"
    )
    from lyra_cli.commands import skill as skill_module

    monkeypatch.setattr(
        skill_module, "_call_llm_for_reflection", lambda _p: proposal_md
    )

    result = runner.invoke(
        skill_app,
        ["reflect", "planner", "--target", str(target), "--apply"],
    )
    assert result.exit_code == 0, result.output
    assert "applied" in result.output.lower()
    assert "enumerate file paths" in skill_path.read_text()
    assert (skill_path.parent / "SKILL.md.bak").exists()


def test_reflect_unknown_skill_fails(
    tmp_path: Path, monkeypatch
) -> None:
    """Reflect on a missing skill exits with a clear diagnostic."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    target = tmp_path / "skills"
    target.mkdir()
    result = runner.invoke(
        skill_app,
        ["reflect", "ghost", "--target", str(target), "--json"],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert "not installed" in payload["error"].lower()


def test_reflect_with_no_failures_short_circuits(
    tmp_path: Path, monkeypatch
) -> None:
    """No recorded failures → reflect refuses with a friendly message.

    Reflective Learning is failure-driven; with no failures there's
    nothing for the LLM to learn from. We surface that as an
    informational message rather than burning tokens on a no-op call.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _install_skill_with_body(
        src, target, sid="solid", body="Use SOLID principles."
    )

    from lyra_cli.commands import skill as skill_module

    def boom(_p: str) -> str:
        raise AssertionError("LLM must not be called when no failures")

    monkeypatch.setattr(skill_module, "_call_llm_for_reflection", boom)

    result = runner.invoke(
        skill_app, ["reflect", "solid", "--target", str(target)]
    )
    assert result.exit_code == 0, result.output
    assert "no failures" in result.output.lower()


def test_reflect_json_emits_proposal_payload(
    tmp_path: Path, monkeypatch
) -> None:
    """``--json`` returns a structured proposal row."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    src = tmp_path / "src"
    target = tmp_path / "skills"
    skill_path = _install_skill_with_body(
        src, target, sid="planner", body="Plan."
    )
    _seed_failure_history(
        monkeypatch,
        skill_id="planner",
        last_failure_reason="too vague",
    )

    proposal_md = "---\nid: planner\nname: planner\nversion: 0.2.0\n---\nbetter\n"
    from lyra_cli.commands import skill as skill_module

    monkeypatch.setattr(
        skill_module, "_call_llm_for_reflection", lambda _p: proposal_md
    )

    result = runner.invoke(
        skill_app,
        ["reflect", "planner", "--target", str(target), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert payload["id"] == "planner"
    assert payload["applied"] is False
    assert payload["proposal"] == proposal_md
    assert payload["path"] == str(skill_path)


# ---------------------------------------------------------------------------
# consolidate (Phase O.5 — dream daemon for new-skill candidates)
# ---------------------------------------------------------------------------


def _write_events_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e) for e in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_user_prompt_event(
    *, ts: str, line: str, session_id: str = "s1", turn: int = 1
) -> dict:
    return {
        "ts": ts,
        "kind": "user.prompt",
        "session_turn": turn,
        "data": {"mode": "chat", "line": line, "session_id": session_id},
    }


def test_consolidate_clusters_recurring_prompts(
    tmp_path: Path, monkeypatch
) -> None:
    """Consolidate groups similar prompts and proposes a skill per cluster.

    The "dream daemon" idea from Memento: when the same kind of
    request shows up repeatedly across sessions, propose a SKILL.md
    that captures the response pattern so the agent doesn't have to
    re-derive it every time.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    sessions_root = tmp_path / "sessions"
    _write_events_jsonl(
        sessions_root / "events.jsonl",
        [
            _make_user_prompt_event(ts="2026-01-01T00:00:00Z", line="optimize this SQL query for postgres", session_id="s1", turn=1),
            _make_user_prompt_event(ts="2026-01-02T00:00:00Z", line="please optimize this SQL query — it's slow", session_id="s2", turn=1),
            _make_user_prompt_event(ts="2026-01-03T00:00:00Z", line="optimize this SQL query and explain the plan", session_id="s3", turn=1),
            # Singleton — should not produce a candidate.
            _make_user_prompt_event(ts="2026-01-04T00:00:00Z", line="what's my current LLM provider?", session_id="s4", turn=1),
        ],
    )

    proposed_md = (
        "---\nid: sql-optimizer\nname: sql-optimizer\nversion: 0.1.0\n"
        "description: Help optimize SQL queries\nkeywords: [sql, optimize, query]\n"
        "---\nWhen the user asks about SQL optimization, ...\n"
    )

    from lyra_cli.commands import skill as skill_module

    captured_prompts: list[str] = []

    def stub(prompt: str) -> str:
        captured_prompts.append(prompt)
        return proposed_md

    monkeypatch.setattr(skill_module, "_call_llm_for_consolidation", stub)

    result = runner.invoke(
        skill_app,
        [
            "consolidate",
            "--from",
            str(sessions_root / "events.jsonl"),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    candidates = payload["candidates"]
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["id"] == "sql-optimizer"
    assert cand["cluster_size"] == 3
    assert "sql" in (cand["keywords"] or "").lower()
    assert "optimize" in cand["proposal"].lower()
    assert any("optimize this SQL query" in p for p in captured_prompts)


def test_consolidate_dry_run_writes_to_candidates_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """Without ``--apply`` proposals land under ``~/.lyra/skill_candidates/``.

    Users review the markdown directly before promoting any to
    ``~/.lyra/skills/`` via ``lyra skill add``.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    sessions_root = tmp_path / "sessions"
    _write_events_jsonl(
        sessions_root / "events.jsonl",
        [
            _make_user_prompt_event(ts="2026-01-01T00:00:00Z", line="convert markdown to html"),
            _make_user_prompt_event(ts="2026-01-02T00:00:00Z", line="render this markdown as html"),
            _make_user_prompt_event(ts="2026-01-03T00:00:00Z", line="markdown to html please"),
        ],
    )

    proposal = (
        "---\nid: md-to-html\nname: md-to-html\nversion: 0.1.0\n---\nrender markdown\n"
    )
    from lyra_cli.commands import skill as skill_module

    monkeypatch.setattr(
        skill_module, "_call_llm_for_consolidation", lambda _p: proposal
    )

    result = runner.invoke(
        skill_app,
        [
            "consolidate",
            "--from",
            str(sessions_root / "events.jsonl"),
        ],
    )
    assert result.exit_code == 0, result.output
    candidate_dir = tmp_path / ".lyra" / "skill_candidates" / "md-to-html"
    assert (candidate_dir / "SKILL.md").is_file()
    assert "md-to-html" in (candidate_dir / "SKILL.md").read_text()


def test_consolidate_apply_installs_into_skills_root(
    tmp_path: Path, monkeypatch
) -> None:
    """``--apply`` writes proposals into the live skills root.

    Phase O.5 deliberately keeps ``--apply`` opt-in because LLM-
    proposed skills can be hallucinated. This test pins the wiring
    so the user has a one-keystroke path from "I keep doing X" to
    "Lyra now ships an X skill".
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    sessions_root = tmp_path / "sessions"
    _write_events_jsonl(
        sessions_root / "events.jsonl",
        [
            _make_user_prompt_event(ts="2026-01-01T00:00:00Z", line="write a unit test for this function"),
            _make_user_prompt_event(ts="2026-01-02T00:00:00Z", line="write unit tests for the parser"),
            _make_user_prompt_event(ts="2026-01-03T00:00:00Z", line="please write unit tests"),
        ],
    )

    proposal = (
        "---\nid: unit-test-writer\nname: unit-test-writer\nversion: 0.1.0\n---\nbody\n"
    )
    from lyra_cli.commands import skill as skill_module

    monkeypatch.setattr(
        skill_module, "_call_llm_for_consolidation", lambda _p: proposal
    )

    result = runner.invoke(
        skill_app,
        [
            "consolidate",
            "--from",
            str(sessions_root / "events.jsonl"),
            "--apply",
        ],
    )
    assert result.exit_code == 0, result.output
    skills_root = tmp_path / ".lyra" / "skills"
    assert (skills_root / "unit-test-writer" / "SKILL.md").is_file()


def test_consolidate_handles_empty_events_log(
    tmp_path: Path, monkeypatch
) -> None:
    """Missing or empty events.jsonl → friendly empty result, no crash."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    nope = tmp_path / "missing.jsonl"

    from lyra_cli.commands import skill as skill_module

    def boom(_p: str) -> str:
        raise AssertionError("LLM must not be called when no clusters")

    monkeypatch.setattr(skill_module, "_call_llm_for_consolidation", boom)

    result = runner.invoke(
        skill_app, ["consolidate", "--from", str(nope), "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["candidates"] == []


def test_consolidate_skips_existing_skill_ids(
    tmp_path: Path, monkeypatch
) -> None:
    """If the LLM proposes a skill id already installed, skip without writing.

    Avoids both an accidental overwrite and a noisy duplicate
    proposal. The cluster is still reported but the candidate row
    is annotated ``skipped: existing``.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    src = tmp_path / "src"
    target = tmp_path / ".lyra" / "skills"
    _install_skill_with_body(src, target, sid="md-to-html", body="exists already")

    sessions_root = tmp_path / "sessions"
    _write_events_jsonl(
        sessions_root / "events.jsonl",
        [
            _make_user_prompt_event(ts="2026-01-01T00:00:00Z", line="markdown to html convert"),
            _make_user_prompt_event(ts="2026-01-02T00:00:00Z", line="markdown to html"),
            _make_user_prompt_event(ts="2026-01-03T00:00:00Z", line="convert markdown to html"),
        ],
    )

    proposal = (
        "---\nid: md-to-html\nname: md-to-html\nversion: 0.1.0\n---\nbody\n"
    )
    from lyra_cli.commands import skill as skill_module

    monkeypatch.setattr(
        skill_module, "_call_llm_for_consolidation", lambda _p: proposal
    )

    result = runner.invoke(
        skill_app,
        [
            "consolidate",
            "--from",
            str(sessions_root / "events.jsonl"),
            "--apply",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    candidates = payload["candidates"]
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["skipped_reason"] == "existing"
    assert (target / "md-to-html" / "SKILL.md").read_text().count("exists already") == 1
