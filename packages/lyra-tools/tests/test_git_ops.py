"""Tests for git tool implementations — git_status, git_diff, git_log."""
from __future__ import annotations

from lyra_tools.git_ops import git_status, git_diff, git_log


class TestGitStatus:
    def test_returns_status_in_git_repo(self) -> None:
        """Running from within the lyra git repository should succeed."""
        result = git_status(path=".")
        # Should find the repo or return an error gracefully
        assert "repository" in result
        assert "branch" in result

    def test_returns_files_array(self) -> None:
        result = git_status(path=".")
        assert "files" in result
        assert isinstance(result["files"], list)


class TestGitDiff:
    def test_diff_against_head(self) -> None:
        result = git_diff(path=".")
        assert "repository" in result
        assert "patch" in result

    def test_diff_staged(self) -> None:
        result = git_diff(path=".", staged=True)
        assert "staged" in result
        assert result["staged"] is True


class TestGitLog:
    def test_log_returns_commits(self) -> None:
        result = git_log(n=3, path=".")
        assert "commits" in result
        assert result["count"] <= 3

    def test_log_oneline_format(self) -> None:
        result = git_log(n=1, path=".", format="oneline")
        if result["commits"]:
            # Oneline format: "<hash> <message>"
            assert len(result["commits"][0].split(" ", 1)) == 2
