"""Tests for secret scanning tool."""
from __future__ import annotations

from pathlib import Path

from lyra_tools.secrets_scan import sec_secrets_scan, _should_skip


class TestShouldSkip:
    def test_skips_pyc(self) -> None:
        assert _should_skip(Path("foo/bar.pyc")) is True

    def test_skips_node_modules(self) -> None:
        assert _should_skip(Path("node_modules/foo/index.js")) is True

    def test_skips_dot_git(self) -> None:
        assert _should_skip(Path("project/.git/config")) is True

    def test_skips_lock_file(self) -> None:
        assert _should_skip(Path("package-lock.json")) is True

    def test_skips_png(self) -> None:
        assert _should_skip(Path("screenshot.png")) is True

    def test_allows_py_file(self) -> None:
        assert _should_skip(Path("src/main.py")) is False


class TestSecretsScan:
    def test_scan_clean_directory(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')\nx = 42\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path))
        assert result["severity"] == "clean"
        assert result["count"] == 0

    def test_detects_aws_access_key(self, tmp_path: Path) -> None:
        (tmp_path / "config.py").write_text("AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path))
        assert result["count"] > 0
        assert any("aws_access_key" == f["type"] for f in result["findings"])

    def test_detects_github_token(self, tmp_path: Path) -> None:
        (tmp_path / "env.py").write_text("GITHUB_TOKEN=ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789aBcD\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path))
        assert result["count"] > 0
        assert any("github_token" == f["type"] for f in result["findings"])

    def test_detects_openai_key(self, tmp_path: Path) -> None:
        (tmp_path / "secrets.py").write_text("openai_key = 'sk-proj-abcdefghijklmnopqrstuvwxyz123456'\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path))
        assert result["count"] > 0
        assert any("openai_key" == f["type"] for f in result["findings"])

    def test_detects_jwt_in_file(self, tmp_path: Path) -> None:
        token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8g"
        (tmp_path / "token.txt").write_text(f"Authorization: Bearer {token}\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path))
        assert result["count"] > 0
        assert any("jwt_token" == f["type"] for f in result["findings"])

    def test_detects_basic_auth_url(self, tmp_path: Path) -> None:
        (tmp_path / "config.txt").write_text("url = 'https://admin:secret123@example.com/api'\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path))
        assert result["count"] > 0

    def test_scan_missing_path(self, tmp_path: Path) -> None:
        result = sec_secrets_scan(str(tmp_path / "nope"), repo_root=str(tmp_path))
        assert "error" in result

    def test_findings_have_redacted_context(self, tmp_path: Path) -> None:
        (tmp_path / "env").write_text("export AWS_KEY=AKIAIOSFODNN7EXAMPLE\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path))
        for f in result["findings"]:
            assert "REDACTED" in f["context"]
            assert "AKIA" not in f["context"]

    def test_respects_max_files(self, tmp_path: Path) -> None:
        for i in range(20):
            (tmp_path / f"file_{i}.py").write_text(f"key_{i} = 'sk-test-key-{i}'\n")
        result = sec_secrets_scan(str(tmp_path), repo_root=str(tmp_path), max_files=5)
        assert result["files_scanned"] <= 5
