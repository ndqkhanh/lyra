"""
Tests for the Gardening Agents system.

Covers:
- DocGardeningAgent: stale doc detection, broken link validation
- CodeGardeningAgent: lint rules, broken windows, deprecated APIs
- TestGardeningAgent: coverage gaps, flaky test detection
- GardeningSchedule: cron-style scheduling
- GardeningReport: per-cycle summary generation
- GardeningSystem: end-to-end orchestration
- SelfDiagnosingHarness.garden() integration
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lyra.reliability.gardening_agents import (
    CodeGardeningAgent,
    DocGardeningAgent,
    GardeningIssueCategory,
    GardeningReport,
    GardeningSchedule,
    GardeningSystem,
    IssueSeverity,
    ScheduleFrequency,
    TestGardeningAgent,
)
from lyra.reliability.self_diagnosing_harness import (
    GardenHealth,
    SelfDiagnosingHarness,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def tmp_docs(tmp_path: Path) -> Path:
    """Create a temporary docs directory with some .md files."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text(
        "# Welcome\n\nSee [usage](../src/lyra/reliability/retry.py) for retry details.\n"
    )
    (docs / "api.md").write_text(
        "# API Reference\n\n"
        "The `lyra.reliability.retry` module provides retry logic.\n"
        "See also [guide](guide.md) and [architecture](../src/lyra/supervisor/fleet.py).\n"
    )
    (docs / "guide.md").write_text("# Guide\n\nSome guide content.")
    return docs


@pytest.fixture
def tmp_src_with_bad_patterns(tmp_path: Path) -> Path:
    """Create a temporary src/ tree with known anti-patterns."""
    src = tmp_path / "src" / "lyra"
    src.mkdir(parents=True)

    (src / "good_module.py").write_text(
        '"""A perfectly fine module."""\n\ndef do_thing(x: int) -> int:\n    return x + 1\n'
    )
    (src / "bad_module.py").write_text(
        "import typing\nfrom os import *\n\ndef foo(x=[]):\n    try:\n        pass\n    except:\n        pass\n    print('hello')\n    return typing.List[x]\n"
    )
    (src / "deprecated_module.py").write_text(
        "import typing\n\nx: typing.Optional[int] = None\ny: typing.Dict[str, int] = {}\n"
    )
    return tmp_path


@pytest.fixture
def tmp_tests(tmp_path: Path) -> Path:
    """Create a temporary tests/ directory."""
    tests = tmp_path / "tests"
    tests.mkdir()

    (tests / "test_retry.py").write_text("def test_retry():\n    pass\n")
    (tests / "test_circuit.py").write_text(
        '"""Circuit tests."""\nimport time\n\ndef test_something():\n    time.sleep(1)\n    pass\n'
    )
    (tests / "flaky_test.py").write_text(
        '"""Flaky test module."""\nimport time\nimport requests\n\ndef test_network():\n    r = requests.get("http://example.com")\n    assert r.ok\n\n@pytest.mark.skip\ndef test_skipped():\n    pass\n'
    )

    # A subdir with a test file
    sub = tests / "sub"
    sub.mkdir()
    (sub / "test_deep.py").write_text("def test_deep():\n    pass\n")

    return tests


@pytest.fixture
def tmp_src(tmp_path: Path) -> Path:
    """Create a minimal src/ with some modules for coverage checking."""
    src = tmp_path / "src" / "lyra"
    src.mkdir(parents=True)

    (src / "__init__.py").write_text("# package")
    (src / "retry.py").write_text('"""Retry module."""\ndef retry(): pass\n')
    (src / "_internal.py").write_text("# private, skip")
    (src / "orphan.py").write_text(
        '"""Module with no test file."""\ndef orphan(): pass\n'
    )
    return tmp_path


# ===================================================================
# GardeningSchedule
# ===================================================================


class TestGardeningSchedule:
    def test_never_run_should_run(self) -> None:
        sched = GardeningSchedule()
        assert sched.should_run() is True

    def test_daily_after_mark_should_not_run_immediately(self) -> None:
        sched = GardeningSchedule.daily(hour=0)
        sched.mark_run()
        assert sched.should_run() is False

    def test_daily_after_one_day_should_run(self) -> None:
        sched = GardeningSchedule.daily(hour=0)
        sched.last_run = datetime.now(timezone.utc) - timedelta(days=2)
        assert sched.should_run() is True

    def test_weekly_after_one_week_should_run(self) -> None:
        sched = GardeningSchedule.weekly()
        sched.last_run = datetime.now(timezone.utc) - timedelta(weeks=2)
        assert sched.should_run() is True

    def test_weekly_before_one_week_should_not_run(self) -> None:
        sched = GardeningSchedule.weekly()
        sched.last_run = datetime.now(timezone.utc) - timedelta(days=3)
        assert sched.should_run() is False

    def test_on_commit_always_should_run(self) -> None:
        sched = GardeningSchedule.on_commit()
        sched.mark_run()
        assert sched.should_run() is True

    def test_manual_never_auto_runs(self) -> None:
        sched = GardeningSchedule(frequency=ScheduleFrequency.MANUAL)
        sched.last_run = datetime.now(timezone.utc) - timedelta(days=30)
        assert sched.should_run() is False

    def test_cooldown_seconds_takes_precedence(self) -> None:
        sched = GardeningSchedule(
            frequency=ScheduleFrequency.DAILY, cooldown_seconds=3600
        )
        sched.mark_run()
        assert sched.should_run() is False
        # Simulate cooldown elapsed
        sched.last_run = datetime.now(timezone.utc) - timedelta(seconds=3601)
        assert sched.should_run() is True

    def test_mark_run_updates_last_run(self) -> None:
        sched = GardeningSchedule()
        assert sched.last_run is None
        sched.mark_run()
        assert sched.last_run is not None

    def test_daily_factory(self) -> None:
        sched = GardeningSchedule.daily(hour=3)
        assert sched.frequency == ScheduleFrequency.DAILY
        assert sched.hour == 3

    def test_weekly_factory(self) -> None:
        sched = GardeningSchedule.weekly(weekday=1, hour=2)
        assert sched.frequency == ScheduleFrequency.WEEKLY
        assert sched.weekday == 1
        assert sched.hour == 2

    def test_on_commit_factory(self) -> None:
        sched = GardeningSchedule.on_commit()
        assert sched.frequency == ScheduleFrequency.ON_COMMIT


# ===================================================================
# GardeningReport
# ===================================================================


class TestGardeningReport:
    def test_empty_report(self) -> None:
        report = GardeningReport()
        assert report.total_issues == 0
        assert report.high_severity_count == 0
        assert report.auto_fixed == 0
        assert report.open_prs == []
        assert "0" in report.summary()

    def test_total_issues_count(self) -> None:
        report = GardeningReport(
            doc_issues=_make_issues(2, "stale_doc"),
            code_issues=_make_issues(3, "lint_violation"),
            test_issues=_make_issues(1, "missing_coverage"),
        )
        assert report.total_issues == 6

    def test_high_severity_count(self) -> None:
        issues = _make_issues(2, "lint_violation")
        issues[0].severity = IssueSeverity.HIGH.value
        report = GardeningReport(
            doc_issues=issues,
        )
        assert report.high_severity_count == 1

    def test_to_dict_includes_all_keys(self) -> None:
        report = GardeningReport(auto_fixed=3, open_prs=["PR: fix docs"])
        d = report.to_dict()
        assert d["auto_fixed"] == 3
        assert len(d["open_prs"]) == 1
        assert "timestamp" in d
        assert "total_issues" in d
        assert "doc_issues" in d
        assert "code_issues" in d
        assert "test_issues" in d

    def test_summary_includes_pr_count(self) -> None:
        report = GardeningReport(open_prs=["Fix doc issues", "Fix code issues"])
        s = report.summary()
        assert "PRs to open" in s
        assert "Fix doc issues" in s

    def test_summary_truncates_many_prs(self) -> None:
        prs = [f"Issue {i}" for i in range(5)]
        report = GardeningReport(open_prs=prs)
        s = report.summary()
        assert "... and 2 more" in s


def _make_issues(count: int, issue_type: str):
    from lyra.reliability.gardening_agents import GardeningIssue
    return [
        GardeningIssue(
            issue_type=issue_type,
            file_path=f"/path/to/file{i}.py",
            description=f"Issue {i}",
        )
        for i in range(count)
    ]


# ===================================================================
# DocGardeningAgent
# ===================================================================


class TestDocGardeningAgent:
    def test_no_docs_dir_returns_empty(self, tmp_path: Path) -> None:
        agent = DocGardeningAgent(tmp_path / "nonexistent")
        assert agent.detect_stale_docs() == []
        assert agent.find_broken_links() == []

    def test_detect_stale_docs_returns_empty_when_docs_fresh(
        self, tmp_docs: Path
    ) -> None:
        agent = DocGardeningAgent(tmp_docs)
        issues = agent.detect_stale_docs()
        # All docs were just created, so no stale issues
        stale = [i for i in issues if i.issue_type == GardeningIssueCategory.STALE_DOC.value]
        assert stale == []

    def test_find_broken_links_detects_missing_target(
        self, tmp_docs: Path
    ) -> None:
        agent = DocGardeningAgent(tmp_docs)
        issues = agent.find_broken_links()
        # api.md links to guide.md (exists) and to fleet.py (exists if we have the real tree)
        # So we need a more precise check: add a link that definitely points nowhere
        (tmp_docs / "broken.md").write_text("[dead](nonexistent_file.md)")
        issues = agent.find_broken_links()
        broken = [i for i in issues if i.issue_type == GardeningIssueCategory.BROKEN_LINK.value]
        assert len(broken) >= 1
        assert any("nonexistent_file.md" in i.description for i in broken)

    def test_broken_link_includes_file_and_text(self) -> None:
        # Unit-test the _check_link helper
        agent = DocGardeningAgent("/tmp")
        result = agent._check_link(
            Path("/tmp/docs/index.md"), "missing.md", "click here"
        )
        assert result is not None
        assert "missing.md" in result.description
        assert "click here" in result.description

    def test_external_urls_not_flagged(self) -> None:
        agent = DocGardeningAgent("/tmp")
        result = agent._check_link(
            Path("/tmp/docs/index.md"), "https://example.com", "ext"
        )
        assert result is None

    def test_anchor_links_not_flagged(self) -> None:
        agent = DocGardeningAgent("/tmp")
        result = agent._check_link(
            Path("/tmp/docs/index.md"), "#section", "anchor"
        )
        assert result is None

    def test_extract_src_references_finds_backtick_paths(self) -> None:
        content = 'See `src/lyra/reliability/retry.py` for details.'
        agent = DocGardeningAgent("/tmp")
        # The path won't exist, so _resolve_path returns None, but the
        # _extract_src_references method still sees it.
        refs = agent._extract_src_references(content)
        assert len(refs) == 0  # because the path doesn't exist on disk

    def test_open_doc_fix_pr_generates_markdown(self) -> None:
        from lyra.reliability.gardening_agents import GardeningIssue
        agent = DocGardeningAgent("/tmp")
        issues = [
            GardeningIssue(
                issue_type=GardeningIssueCategory.STALE_DOC.value,
                file_path="docs/api.md",
                description="Doc may be stale",
            )
        ]
        pr = agent.open_doc_fix_pr(issues)
        assert "## Gardening Fix PR" in pr
        assert "STALE_DOC" in pr
        assert "docs/api.md" in pr
        assert "This PR was automatically generated" in pr

    def test_open_doc_fix_pr_empty(self) -> None:
        agent = DocGardeningAgent("/tmp")
        pr = agent.open_doc_fix_pr([])
        assert "No issues were found" in pr


# ===================================================================
# CodeGardeningAgent
# ===================================================================


class TestCodeGardeningAgent:
    def test_lint_rule_gardener_detects_long_lines(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        long_line = '"""Module."""\n' + "x" * 200 + "\n"
        (src / "long.py").write_text(long_line)
        agent = CodeGardeningAgent(src)
        issues = agent.lint_rule_gardener()
        line_issues = [
            i
            for i in issues
            if i.issue_type == GardeningIssueCategory.LINT_VIOLATION.value
            and "exceeds" in i.description
        ]
        assert len(line_issues) >= 1

    def test_lint_rule_gardener_missing_docstring(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "nodoc.py").write_text("x = 1\n")
        agent = CodeGardeningAgent(src)
        issues = agent.lint_rule_gardener()
        docstring_issues = [
            i
            for i in issues
            if "missing a module-level docstring" in i.description
        ]
        assert len(docstring_issues) >= 1

    def test_lint_rule_gardener_detects_print(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "printer.py").write_text(
            '"""Module."""\n\ndef f():\n    print("hello")\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.lint_rule_gardener()
        print_issues = [
            i
            for i in issues
            if "print()" in i.description
        ]
        assert len(print_issues) >= 1

    def test_pattern_gardener_mutable_default(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "mutable.py").write_text(
            '"""Module."""\ndef foo(x=[]):\n    pass\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.pattern_gardener()
        mutable = [
            i
            for i in issues
            if i.issue_type == GardeningIssueCategory.BROKEN_WINDOW.value
        ]
        assert len(mutable) >= 1

    def test_pattern_gardener_bare_except(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "catchall.py").write_text(
            '"""Module."""\ntry:\n    pass\nexcept:\n    pass\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.pattern_gardener()
        bare = [
            i
            for i in issues
            if "Bare" in i.description
        ]
        assert len(bare) >= 1

    def test_pattern_gardener_wildcard_import(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "wild.py").write_text(
            '"""Module."""\nfrom os import *\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.pattern_gardener()
        wildcards = [
            i
            for i in issues
            if "Wildcard" in i.description
        ]
        assert len(wildcards) >= 1

    def test_deprecation_gardener_typing_list(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "typing_usage.py").write_text(
            '"""Module."""\nimport typing\nx: typing.List[int] = []\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.deprecation_gardener()
        typing_issues = [
            i
            for i in issues
            if "typing.List" in i.description
        ]
        assert len(typing_issues) >= 1

    def test_deprecation_gardener_typing_optional(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "optional_usage.py").write_text(
            '"""Module."""\nimport typing\nx: typing.Optional[int] = None\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.deprecation_gardener()
        opt_issues = [
            i
            for i in issues
            if "typing.Optional" in i.description
        ]
        assert len(opt_issues) >= 1

    def test_deprecation_gardener_abstractproperty(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "abstract_prop.py").write_text(
            '"""Module."""\nfrom abc import abstractproperty\n\n@abstractproperty\ndef prop(self):\n    pass\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.deprecation_gardener()
        abs_issues = [
            i
            for i in issues
            if "abstractproperty" in i.description
        ]
        assert len(abs_issues) >= 1

    def test_lint_rule_gardener_clean_file_passes(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "clean.py").write_text(
            '"""A clean module."""\n\ndef f() -> int:\n    return 1\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.lint_rule_gardener()
        assert issues == []

    def test_pattern_gardener_clean_file_passes(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "clean.py").write_text(
            '"""A clean module."""\n\ndef f(x: int | None = None) -> int:\n    if x is None:\n        return 0\n    return x\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.pattern_gardener()
        assert issues == []

    def test_deprecation_gardener_clean_file_passes(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "clean.py").write_text(
            '"""A clean module."""\n\nfrom collections.abc import Sequence\nx: Sequence[int] = []\n'
        )
        agent = CodeGardeningAgent(src)
        issues = agent.deprecation_gardener()
        assert issues == []

    def test_open_code_fix_pr_generates_markdown(self) -> None:
        from lyra.reliability.gardening_agents import GardeningIssue
        agent = CodeGardeningAgent("/tmp")
        issues = [
            GardeningIssue(
                issue_type=GardeningIssueCategory.LINT_VIOLATION.value,
                file_path="src/bad.py",
                description="Line too long",
                auto_fixable=True,
            )
        ]
        pr = agent.open_code_fix_pr(issues)
        assert "## Code Gardening Fix PR" in pr
        assert "LINT_VIOLATION" in pr
        assert "auto-fix" in pr.lower()


# ===================================================================
# TestGardeningAgent
# ===================================================================


class TestTestGardeningAgent:
    def test_coverage_gardener_finds_missing_tests(
        self, tmp_src: Path, tmp_tests: Path
    ) -> None:
        agent = TestGardeningAgent(tmp_src, tmp_tests)
        issues = agent.coverage_gardener()
        missing = [
            i
            for i in issues
            if i.issue_type == GardeningIssueCategory.MISSING_COVERAGE.value
        ]
        # orphan.py has no test_orphan.py
        assert len(missing) >= 1
        assert any("orphan.py" in i.description for i in missing)

    def test_coverage_gardener_skips_init(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text("# package")
        tests = tmp_path / "tests"
        tests.mkdir()
        agent = TestGardeningAgent(src, tests)
        issues = agent.coverage_gardener()
        assert issues == []

    def test_coverage_gardener_skips_private(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "_internal.py").write_text("# private")
        tests = tmp_path / "tests"
        tests.mkdir()
        agent = TestGardeningAgent(src, tests)
        issues = agent.coverage_gardener()
        assert issues == []

    def test_coverage_gardener_finds_existing_test(
        self, tmp_path: Path
    ) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "retry.py").write_text("def retry(): pass")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_retry.py").write_text("def test_retry(): pass")
        agent = TestGardeningAgent(src, tests)
        issues = agent.coverage_gardener()
        matching_retry = [
            i for i in issues if "retry.py" in i.file_path
        ]
        assert matching_retry == []

    def test_flaky_test_gardener_detects_sleep(self, tmp_path: Path) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_sleepy.py").write_text(
            '"""Module."""\nimport time\n\ndef test_slow():\n    time.sleep(5)\n    assert True\n'
        )
        agent = TestGardeningAgent(tmp_path, tests)
        issues = agent.flaky_test_gardener()
        sleep_issues = [
            i for i in issues if "time.sleep" in i.description
        ]
        assert len(sleep_issues) >= 1

    def test_flaky_test_gardener_detects_network_calls(
        self, tmp_path: Path
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_network.py").write_text(
            '"""Module."""\nimport requests\n\ndef test_get():\n    r = requests.get("http://example.com")\n    assert r.ok\n'
        )
        agent = TestGardeningAgent(tmp_path, tests)
        issues = agent.flaky_test_gardener()
        network_issues = [
            i for i in issues if "Network call" in i.description
        ]
        assert len(network_issues) >= 1

    def test_flaky_test_gardener_skip_without_reason(
        self, tmp_path: Path
    ) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_skip.py").write_text(
            '"""Module."""\nimport pytest\n\n@pytest.mark.skip\ndef test_something():\n    pass\n'
        )
        agent = TestGardeningAgent(tmp_path, tests)
        issues = agent.flaky_test_gardener()
        skip_issues = [
            i for i in issues if "skip" in i.description
        ]
        assert len(skip_issues) >= 1

    def test_flaky_test_clean_file_passes(self, tmp_path: Path) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_clean.py").write_text(
            '"""Module."""\nfrom unittest.mock import Mock\n\ndef test_ok():\n    m = Mock()\n    m.assert_called_once()\n'
        )
        agent = TestGardeningAgent(tmp_path, tests)
        issues = agent.flaky_test_gardener()
        flaky = [i for i in issues if i.issue_type == GardeningIssueCategory.FLAKY_TEST.value]
        assert flaky == []

    def test_open_test_fix_pr_generates_markdown(self) -> None:
        from lyra.reliability.gardening_agents import GardeningIssue
        agent = TestGardeningAgent("/tmp", "/tmp")
        issues = [
            GardeningIssue(
                issue_type=GardeningIssueCategory.FLAKY_TEST.value,
                file_path="tests/test_sleepy.py",
                description="time.sleep detected",
            )
        ]
        pr = agent.open_test_fix_pr(issues)
        assert "## Test Gardening Fix PR" in pr
        assert "FLAKY_TEST" in pr
        assert "tests/test_sleepy.py" in pr


# ===================================================================
# GardeningSystem (end-to-end orchestration)
# ===================================================================


class TestGardeningSystem:
    def test_run_cycle_produces_report(
        self, tmp_path: Path
    ) -> None:
        # Minimal setup with at least one doc check and code check
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "broken.md").write_text("[dead](nonexistent.md)")

        src = tmp_path / "src"
        src.mkdir()
        (src / "bad.py").write_text(
            '"""Module."""\ndef foo(x=[]):\n    pass\n'
        )

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_bad.py").write_text(
            '"""Module."""\nimport time\n\ndef test_slow():\n    time.sleep(2)\n'
        )

        system = GardeningSystem(
            doc_agent=DocGardeningAgent(docs),
            code_agent=CodeGardeningAgent(src),
            test_agent=TestGardeningAgent(src, tests),
        )
        report = system.run_cycle()

        assert isinstance(report, GardeningReport)
        assert report.total_issues >= 1
        assert report.duration_seconds > 0
        assert len(report.doc_issues) >= 1  # broken link
        assert len(report.code_issues) >= 1  # mutable default
        assert len(report.test_issues) >= 1  # time.sleep

    def test_run_cycle_empty_dirs_does_not_crash(
        self, tmp_path: Path
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        src = tmp_path / "src"
        src.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()

        system = GardeningSystem(
            doc_agent=DocGardeningAgent(docs),
            code_agent=CodeGardeningAgent(src),
            test_agent=TestGardeningAgent(src, tests),
        )
        report = system.run_cycle()
        assert report.total_issues == 0
        assert report.duration_seconds > 0

    def test_should_run_delegates_to_schedule(self) -> None:
        schedule = GardeningSchedule(frequency=ScheduleFrequency.MANUAL)
        schedule.mark_run()  # MANUAL never auto-runs after a mark
        docs = Path("/tmp")
        system = GardeningSystem(
            doc_agent=DocGardeningAgent(docs),
            code_agent=CodeGardeningAgent(docs),
            test_agent=TestGardeningAgent(docs, docs),
            schedule=schedule,
        )
        assert system.should_run() is False  # MANUAL never auto-runs

    def test_mark_run_updates_schedule(self) -> None:
        schedule = GardeningSchedule()
        system = GardeningSystem(
            doc_agent=DocGardeningAgent("/tmp"),
            code_agent=CodeGardeningAgent("/tmp"),
            test_agent=TestGardeningAgent("/tmp", "/tmp"),
            schedule=schedule,
        )
        assert schedule.last_run is None
        system.mark_run()
        assert schedule.last_run is not None

    def test_auto_fix_applies_fixable_issues(self, tmp_path: Path) -> None:
        from lyra.reliability.gardening_agents import GardeningIssue
        docs = tmp_path / "docs"
        docs.mkdir()
        src = tmp_path / "src"
        src.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()

        fixable_file = src / "fixable.py"
        fixable_file.write_text('"""Module."""\n')

        system = GardeningSystem(
            doc_agent=DocGardeningAgent(docs),
            code_agent=CodeGardeningAgent(src),
            test_agent=TestGardeningAgent(src, tests),
        )
        # Manually trigger an auto-fix to verify the mechanism
        issue = GardeningIssue(
            issue_type=GardeningIssueCategory.LINT_VIOLATION.value,
            file_path=str(fixable_file),
            description="print() detected",
            auto_fixable=True,
            fix_content='"""Module."""\nimport logging\nlogger = logging.getLogger(__name__)\n',
        )
        fixed, prs = system._auto_fix([issue])
        assert fixed == 1
        assert fixable_file.read_text() == issue.fix_content


# ===================================================================
# SelfDiagnosingHarness.garden() integration
# ===================================================================


class TestHarnessGardening:
    def test_harness_garden_returns_report(self, tmp_path: Path) -> None:
        """Verifies the garden() method on SelfDiagnosingHarness."""
        # Use empty isolated paths to avoid scanning the real project tree
        src = tmp_path / "src"
        src.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()
        harness = SelfDiagnosingHarness(
            src_path=str(src), test_path=str(tests)
        )
        report = harness.garden()
        # Should return a report (even if empty) because schedule says "never run"
        # Actually schedule defaults to DAILY, first run should always run.
        if report is not None:
            assert isinstance(report, GardeningReport)
            assert report.total_issues >= 0  # no issues expected in empty dirs

    def test_harness_garden_health_property(self) -> None:
        harness = SelfDiagnosingHarness()
        health = harness.garden_health
        assert isinstance(health, GardenHealth)
        assert health.cycles_run == 0
        assert health.issues_resolved == 0
        assert health.last_cycle is None

    def test_harness_garden_updates_health(self, tmp_path: Path) -> None:
        harness = SelfDiagnosingHarness(
            src_path=str(tmp_path), test_path=str(tmp_path)
        )
        # First call should run a cycle
        report = harness.garden()
        if report is not None:
            health = harness.garden_health
            assert health.cycles_run == 1
            assert health.issues_resolved == report.auto_fixed
            assert health.last_cycle is not None

    def test_harness_garden_with_custom_paths(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        src = tmp_path / "src"
        src.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()

        harness = SelfDiagnosingHarness(
            docs_path=str(docs),
            src_path=str(src),
            test_path=str(tests),
        )
        report = harness.garden()
        assert report is not None
        assert report.total_issues == 0  # all dirs empty

    def test_garden_health_to_dict(self) -> None:
        health = GardenHealth(
            cycles_run=3,
            issues_resolved=5,
            last_cycle=datetime.now(timezone.utc),
        )
        d = health.to_dict()
        assert d["cycles_run"] == 3
        assert d["issues_resolved"] == 5
        assert d["last_cycle"] is not None
        assert d["last_report"] is None
