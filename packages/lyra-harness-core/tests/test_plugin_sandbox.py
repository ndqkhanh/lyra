"""Tests for Plugin Sandbox — isolated execution environment."""
from __future__ import annotations

import pytest

from lyra_harness_core.plugins.manifest import parse_manifest, SandboxConfig
from lyra_harness_core.plugins.sandbox import (
    PluginSandbox,
    SandboxResult,
    validate_domain,
    validate_path,
)


# ---------------------------------------------------------------------------
# validate_domain
# ---------------------------------------------------------------------------


class TestValidateDomain:
    def test_exact_match(self):
        assert validate_domain("api.example.com", ("api.example.com",))

    def test_wildcard_match(self):
        assert validate_domain("api.example.com", ("*.example.com",))

    def test_wildcard_subdomain(self):
        assert validate_domain("sub.api.example.com", ("*.example.com",))

    def test_wildcard_no_match_different_tld(self):
        assert not validate_domain("api.example.org", ("*.example.com",))

    def test_localhost(self):
        assert validate_domain("localhost", ("localhost",))

    def test_ip_address(self):
        assert validate_domain("192.168.1.1", ("192.168.1.1",))

    def test_empty_allowlist_denies_all(self):
        assert not validate_domain("anything.com", ())

    def test_no_match(self):
        assert not validate_domain("evil.com", ("good.com", "safe.org"))

    def test_partial_match_insufficient(self):
        # "example.com" should not match "myexample.com"
        assert not validate_domain("myexample.com", ("example.com",))

    def test_multiple_entries(self):
        allowlist = ("api.github.com", "*.googleapis.com")
        assert validate_domain("api.github.com", allowlist)
        assert validate_domain("storage.googleapis.com", allowlist)
        assert not validate_domain("api.gitlab.com", allowlist)


# ---------------------------------------------------------------------------
# validate_path
# ---------------------------------------------------------------------------


class TestValidatePath:
    def test_exact_match(self, tmp_path):
        p = str(tmp_path)
        assert validate_path(p, (p,))

    def test_subpath_allowed(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        assert validate_path(str(sub), (str(tmp_path),))

    def test_no_match(self, tmp_path):
        assert not validate_path(str(tmp_path), ("/some/other/path",))

    def test_empty_allowlist_denies_all(self):
        assert not validate_path("/tmp/test", ())

    def test_expanded_home(self):
        import os
        home = os.path.expanduser("~")
        assert validate_path(f"{home}/.lyra/cache", ("~/.lyra/cache",))


# ---------------------------------------------------------------------------
# SandboxResult
# ---------------------------------------------------------------------------


class TestSandboxResult:
    def test_success(self):
        sr = SandboxResult(exit_code=0, stdout="ok", stderr="")
        assert sr.success is True

    def test_failure(self):
        sr = SandboxResult(exit_code=1, stdout="", stderr="error")
        assert sr.success is False

    def test_elapsed_default(self):
        sr = SandboxResult(exit_code=0, stdout="", stderr="")
        assert sr.elapsed_ms == 0.0


# ---------------------------------------------------------------------------
# PluginSandbox
# ---------------------------------------------------------------------------


class TestPluginSandbox:
    @pytest.fixture
    def manifest(self):
        return parse_manifest({
            "name": "test-plugin",
            "version": "1.0.0",
            "sandbox": {
                "network": ["api.example.com", "*.github.com"],
                "filesystem": ["/tmp/lyra-test/"],
            },
        })

    @pytest.fixture
    def sandbox(self, manifest):
        return PluginSandbox(manifest)

    def test_manifest_property(self, sandbox, manifest):
        assert sandbox.manifest is manifest

    def test_check_network_access_allowed(self, sandbox):
        assert sandbox.check_network_access("api.example.com")

    def test_check_network_access_wildcard(self, sandbox):
        assert sandbox.check_network_access("api.github.com")

    def test_check_network_access_denied(self, sandbox):
        assert not sandbox.check_network_access("evil.com")

    def test_check_filesystem_access_allowed(self, sandbox):
        assert sandbox.check_filesystem_access("/tmp/lyra-test/data.json")

    def test_check_filesystem_access_denied(self, sandbox):
        assert not sandbox.check_filesystem_access("/etc/passwd")

    def test_allowed_domains(self, sandbox):
        domains = sandbox.allowed_domains()
        assert "api.example.com" in domains
        assert "*.github.com" in domains

    def test_allowed_paths(self, sandbox):
        paths = sandbox.allowed_paths()
        assert "/tmp/lyra-test/" in paths

    def test_empty_sandbox_denies_network(self):
        m = parse_manifest({"name": "p", "version": "1.0.0"})
        sb = PluginSandbox(m)
        assert not sb.check_network_access("anything.com")

    def test_empty_sandbox_denies_filesystem(self):
        m = parse_manifest({"name": "p", "version": "1.0.0"})
        sb = PluginSandbox(m)
        assert not sb.check_filesystem_access("/tmp")

    def test_run_code_success(self, sandbox):
        result = sandbox.run_code("print('hello from sandbox')")
        assert result.success
        assert "hello from sandbox" in result.stdout

    def test_run_code_failure(self, sandbox):
        result = sandbox.run_code("raise ValueError('test error')")
        assert not result.success
        assert result.exit_code != 0

    def test_run_code_elapsed_tracked(self, sandbox):
        result = sandbox.run_code("x = 1 + 1")
        assert result.elapsed_ms >= 0

    def test_validate_environment_no_deps(self, sandbox):
        errors = sandbox.validate_environment()
        assert errors == []

    def test_validate_environment_missing_dep(self):
        m = parse_manifest({
            "name": "p",
            "version": "1.0.0",
            "dependencies": ["nonexistent_package_xyz_123"],
        })
        sb = PluginSandbox(m)
        errors = sb.validate_environment()
        assert len(errors) == 1
        assert "nonexistent_package_xyz_123" in errors[0]

    def test_run_code_stdout_captured(self, sandbox):
        result = sandbox.run_code("print('line1'); print('line2')")
        assert "line1" in result.stdout
        assert "line2" in result.stdout

    def test_run_code_stderr_captured(self, sandbox):
        result = sandbox.run_code("import sys; sys.stderr.write('err msg')")
        assert "err msg" in result.stderr
