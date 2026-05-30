"""Tests for Path-Pattern + Regex Allow/Deny Rules (P1-X #15)."""
from __future__ import annotations

import pytest

from lyra_harness_core.scope_rules import (
    PatternKind,
    RuleEffect,
    Scope,
    ScopeMatch,
    ScopeRule,
    ScopeRuleEngine,
    ScopeRuleSet,
    build_default_engine,
    build_default_filesystem_rules,
    build_default_network_rules,
    build_default_shell_rules,
)


# ---------------------------------------------------------------------------
# Scope, RuleEffect, PatternKind
# ---------------------------------------------------------------------------


class TestScope:
    def test_values(self):
        assert Scope.FILESYSTEM.value == "filesystem"
        assert Scope.NETWORK.value == "network"
        assert Scope.SHELL.value == "shell"
        assert Scope.ALL.value == "all"

    def test_string_enum(self):
        assert isinstance(Scope.FILESYSTEM, str)


class TestRuleEffect:
    def test_values(self):
        assert RuleEffect.ALLOW.value == "allow"
        assert RuleEffect.DENY.value == "deny"


class TestPatternKind:
    def test_values(self):
        assert PatternKind.GLOB.value == "glob"
        assert PatternKind.REGEX.value == "regex"


# ---------------------------------------------------------------------------
# ScopeRule
# ---------------------------------------------------------------------------


class TestScopeRule:
    def test_minimal(self):
        r = ScopeRule(name="test", pattern="*.py", effect=RuleEffect.ALLOW)
        assert r.name == "test"
        assert r.pattern == "*.py"
        assert r.effect == RuleEffect.ALLOW
        assert r.scope == Scope.ALL
        assert r.kind == PatternKind.GLOB
        assert r.priority == 0

    def test_frozen(self):
        r = ScopeRule(name="x", pattern="*", effect=RuleEffect.ALLOW)
        with pytest.raises(Exception):
            r.priority = 10  # type: ignore[misc]

    def test_matches_glob(self):
        r = ScopeRule(name="py", pattern="*.py", effect=RuleEffect.ALLOW)
        assert r.matches("main.py")
        assert not r.matches("main.txt")

    def test_matches_glob_case_sensitive(self):
        r = ScopeRule(name="py", pattern="*.py", effect=RuleEffect.ALLOW)
        assert r.matches("main.py")
        assert not r.matches("main.PY")

    def test_matches_regex(self):
        r = ScopeRule(
            name="ip",
            pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
            effect=RuleEffect.DENY,
            kind=PatternKind.REGEX,
        )
        assert r.matches("192.168.1.1")
        assert r.matches("10.0.0.1")
        assert not r.matches("not.an.ip")
        assert not r.matches("example.com")

    def test_matches_regex_partial(self):
        r = ScopeRule(
            name="internal",
            pattern=r"^10\.",
            effect=RuleEffect.DENY,
            kind=PatternKind.REGEX,
        )
        assert r.matches("10.0.0.1")
        assert not r.matches("192.168.1.1")

    def test_to_dict(self):
        r = ScopeRule(
            name="block",
            pattern="/etc/**",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            priority=50,
        )
        d = r.to_dict()
        assert d["name"] == "block"
        assert d["pattern"] == "/etc/**"
        assert d["effect"] == "deny"
        assert d["scope"] == "filesystem"
        assert d["priority"] == 50

    def test_with_description(self):
        r = ScopeRule(
            name="r1",
            pattern="*",
            effect=RuleEffect.ALLOW,
            description="allow all",
        )
        assert r.description == "allow all"


# ---------------------------------------------------------------------------
# ScopeMatch
# ---------------------------------------------------------------------------


class TestScopeMatch:
    def test_allowed_default(self):
        m = ScopeMatch(allowed=True)
        assert m.allowed
        assert m.matched_rule is None

    def test_denied_with_rule(self):
        m = ScopeMatch(allowed=False, matched_rule="deny_ssh", reason="denied by rule")
        assert not m.allowed
        assert m.matched_rule == "deny_ssh"

    def test_frozen(self):
        m = ScopeMatch(allowed=True)
        with pytest.raises(Exception):
            m.allowed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ScopeRuleSet
# ---------------------------------------------------------------------------


class TestScopeRuleSet:
    @pytest.fixture
    def rs(self):
        return ScopeRuleSet()

    def test_empty_default_allow(self, rs):
        result = rs.evaluate("/any/path", Scope.FILESYSTEM)
        assert result.allowed
        assert "default allow" in result.reason

    def test_add_and_evaluate(self, rs):
        rs.add(ScopeRule(
            name="deny_py",
            pattern="*.py",
            effect=RuleEffect.DENY,
            priority=10,
        ))
        assert rs.is_denied("main.py", Scope.FILESYSTEM)
        assert rs.is_allowed("main.txt", Scope.FILESYSTEM)

    def test_priority_ordering(self, rs):
        rs.add(ScopeRule(
            name="allow_py",
            pattern="*.py",
            effect=RuleEffect.ALLOW,
            priority=5,
        ))
        rs.add(ScopeRule(
            name="deny_secret",
            pattern="secret.py",
            effect=RuleEffect.DENY,
            priority=10,
        ))
        # secret.py matches both patterns; higher priority "deny_secret" wins
        result = rs.evaluate("secret.py", Scope.FILESYSTEM)
        assert not result.allowed
        assert result.matched_rule == "deny_secret"

    def test_priority_allow_wins_when_higher(self, rs):
        rs.add(ScopeRule(
            name="deny_all_py",
            pattern="*.py",
            effect=RuleEffect.DENY,
            priority=5,
        ))
        rs.add(ScopeRule(
            name="allow_special",
            pattern="special.py",
            effect=RuleEffect.ALLOW,
            priority=10,
        ))
        result = rs.evaluate("special.py", Scope.FILESYSTEM)
        assert result.allowed
        assert result.matched_rule == "allow_special"

    def test_rules_sorted_by_priority(self, rs):
        rs.add(ScopeRule(name="low", pattern="*", effect=RuleEffect.ALLOW, priority=1))
        rs.add(ScopeRule(name="high", pattern="*", effect=RuleEffect.DENY, priority=100))
        priorities = [r.priority for r in rs.rules]
        assert priorities == [100, 1]

    def test_remove(self, rs):
        rs.add(ScopeRule(name="r1", pattern="*", effect=RuleEffect.ALLOW))
        assert rs.remove("r1")
        assert not rs.has("r1")

    def test_remove_nonexistent(self, rs):
        assert not rs.remove("nope")

    def test_scope_filtering(self, rs):
        rs.add(ScopeRule(
            name="fs_only",
            pattern="*.py",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
        ))
        rs.add(ScopeRule(
            name="all_scopes",
            pattern="*.log",
            effect=RuleEffect.DENY,
            scope=Scope.ALL,
        ))
        # fs_only only applies to FILESYSTEM
        assert rs.is_denied("main.py", Scope.FILESYSTEM)
        assert rs.is_allowed("main.py", Scope.NETWORK)

        # all_scopes applies everywhere
        assert rs.is_denied("debug.log", Scope.FILESYSTEM)
        assert rs.is_denied("debug.log", Scope.NETWORK)
        assert rs.is_denied("debug.log", Scope.SHELL)

    def test_rule_count(self, rs):
        assert rs.rule_count == 0
        rs.add(ScopeRule(name="r1", pattern="*", effect=RuleEffect.ALLOW))
        rs.add(ScopeRule(name="r2", pattern="*", effect=RuleEffect.DENY))
        assert rs.rule_count == 2

    def test_to_dict(self, rs):
        rs.add(ScopeRule(name="r1", pattern="*", effect=RuleEffect.ALLOW))
        d = rs.to_dict()
        assert "rules" in d
        assert len(d["rules"]) == 1

    def test_evaluate_returns_reason(self, rs):
        rs.add(ScopeRule(
            name="block_tmp",
            pattern="/tmp/**",
            effect=RuleEffect.DENY,
            priority=10,
        ))
        result = rs.evaluate("/tmp/secret", Scope.FILESYSTEM)
        assert "block_tmp" in result.reason
        assert "deny" in result.reason

    def test_is_allowed_convenience(self, rs):
        rs.add(ScopeRule(
            name="block",
            pattern="/etc/**",
            effect=RuleEffect.DENY,
            priority=10,
        ))
        assert rs.is_allowed("/home/user/file.txt", Scope.FILESYSTEM)
        assert rs.is_denied("/etc/passwd", Scope.FILESYSTEM)

    def test_has(self, rs):
        rs.add(ScopeRule(name="exists", pattern="*", effect=RuleEffect.ALLOW))
        assert rs.has("exists")
        assert not rs.has("nope")

    def test_rules_for_scope(self, rs):
        rs.add(ScopeRule(
            name="fs", pattern="*.py", effect=RuleEffect.ALLOW, scope=Scope.FILESYSTEM,
        ))
        rs.add(ScopeRule(
            name="net", pattern="*.com", effect=RuleEffect.DENY, scope=Scope.NETWORK,
        ))
        rs.add(ScopeRule(
            name="all", pattern="*.log", effect=RuleEffect.DENY, scope=Scope.ALL,
        ))
        fs_rules = rs.rules_for_scope(Scope.FILESYSTEM)
        assert len(fs_rules) == 2  # fs + all
        net_rules = rs.rules_for_scope(Scope.NETWORK)
        assert len(net_rules) == 2  # net + all


# ---------------------------------------------------------------------------
# ScopeRuleEngine
# ---------------------------------------------------------------------------


class TestScopeRuleEngine:
    @pytest.fixture
    def engine(self):
        return ScopeRuleEngine()

    def test_empty_allows_all(self, engine):
        assert engine.is_allowed("/any/path", Scope.FILESYSTEM)
        assert engine.is_allowed("https://any.com", Scope.NETWORK)
        assert engine.is_allowed("ls -la", Scope.SHELL)

    def test_add_rule_to_specific_scope(self, engine):
        engine.add_rule(ScopeRule(
            name="fs_deny_py",
            pattern="*.py",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            priority=10,
        ))
        assert not engine.is_allowed("main.py", Scope.FILESYSTEM)
        # Rule should NOT affect other scopes
        assert engine.is_allowed("main.py", Scope.NETWORK)
        assert engine.is_allowed("main.py", Scope.SHELL)

    def test_add_rule_to_all_scopes(self, engine):
        engine.add_rule(ScopeRule(
            name="deny_secret",
            pattern="secret*",
            effect=RuleEffect.DENY,
            scope=Scope.ALL,
            priority=10,
        ))
        assert not engine.is_allowed("secret.txt", Scope.FILESYSTEM)
        assert not engine.is_allowed("secret.txt", Scope.NETWORK)
        assert not engine.is_allowed("secret.txt", Scope.SHELL)

    def test_remove_rule(self, engine):
        engine.add_rule(ScopeRule(
            name="block", pattern="/etc/*", effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM, priority=10,
        ))
        assert not engine.is_allowed("/etc/passwd", Scope.FILESYSTEM)
        assert engine.remove_rule("block")
        assert engine.is_allowed("/etc/passwd", Scope.FILESYSTEM)

    def test_remove_nonexistent(self, engine):
        assert not engine.remove_rule("nope")

    def test_total_rules(self, engine):
        assert engine.total_rules == 0
        engine.add_rule(ScopeRule(
            name="r1", pattern="*", effect=RuleEffect.ALLOW, scope=Scope.ALL,
        ))
        # Scope.ALL rules get added to all 3 scopes
        assert engine.total_rules == 3
        engine.add_rule(ScopeRule(
            name="r2", pattern="*", effect=RuleEffect.ALLOW, scope=Scope.FILESYSTEM,
        ))
        assert engine.total_rules == 4  # 3(from r1) + 1(from r2)

    def test_evaluate_with_priority(self, engine):
        engine.add_rule(ScopeRule(
            name="deny_all",
            pattern="*",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            priority=5,
        ))
        engine.add_rule(ScopeRule(
            name="allow_txt",
            pattern="*.txt",
            effect=RuleEffect.ALLOW,
            scope=Scope.FILESYSTEM,
            priority=10,
        ))
        assert engine.is_allowed("readme.txt", Scope.FILESYSTEM)
        assert not engine.is_allowed("main.py", Scope.FILESYSTEM)

    def test_to_dict(self, engine):
        engine.add_rule(ScopeRule(
            name="r1", pattern="*", effect=RuleEffect.ALLOW, scope=Scope.FILESYSTEM,
        ))
        d = engine.to_dict()
        assert "filesystem" in d
        assert "network" in d
        assert "shell" in d

    def test_regex_rule(self, engine):
        engine.add_rule(ScopeRule(
            name="deny_internal_ip",
            pattern=r"^10\.",
            effect=RuleEffect.DENY,
            scope=Scope.NETWORK,
            kind=PatternKind.REGEX,
            priority=10,
        ))
        assert not engine.is_allowed("10.0.0.1", Scope.NETWORK)
        assert engine.is_allowed("8.8.8.8", Scope.NETWORK)


# ---------------------------------------------------------------------------
# Pre-built Rule Sets
# ---------------------------------------------------------------------------


class TestBuildDefaultFilesystemRules:
    @pytest.fixture
    def rs(self):
        return build_default_filesystem_rules()

    def test_denies_system_files(self, rs):
        assert rs.is_denied("/etc/passwd", Scope.FILESYSTEM)
        assert rs.is_denied("/etc/shadow", Scope.FILESYSTEM)

    def test_denies_ssh_keys(self, rs):
        assert rs.is_denied("/home/user/.ssh/id_rsa", Scope.FILESYSTEM)

    def test_denies_env_files(self, rs):
        assert rs.is_denied("/app/.env", Scope.FILESYSTEM)
        assert rs.is_denied("/app/.env.local", Scope.FILESYSTEM)

    def test_denies_system_virtual_fs(self, rs):
        assert rs.is_denied("/sys/class", Scope.FILESYSTEM)
        assert rs.is_denied("/proc/cpuinfo", Scope.FILESYSTEM)
        assert rs.is_denied("/dev/null", Scope.FILESYSTEM)

    def test_allows_normal_paths(self, rs):
        assert rs.is_allowed("/home/user/document.txt", Scope.FILESYSTEM)
        assert rs.is_allowed("/tmp/data.json", Scope.FILESYSTEM)

    def test_has_multiple_rules(self, rs):
        assert rs.rule_count > 3


class TestBuildDefaultNetworkRules:
    @pytest.fixture
    def rs(self):
        return build_default_network_rules()

    def test_denies_private_ranges(self, rs):
        assert rs.is_denied("10.0.0.1", Scope.NETWORK)
        assert rs.is_denied("172.16.0.1", Scope.NETWORK)
        assert rs.is_denied("192.168.1.1", Scope.NETWORK)
        assert rs.is_denied("127.0.0.1", Scope.NETWORK)

    def test_denies_metadata_service(self, rs):
        assert rs.is_denied("169.254.169.254", Scope.NETWORK)

    def test_allows_public_ips(self, rs):
        assert rs.is_allowed("8.8.8.8", Scope.NETWORK)
        assert rs.is_allowed("1.1.1.1", Scope.NETWORK)

    def test_allows_domains(self, rs):
        assert rs.is_allowed("example.com", Scope.NETWORK)
        assert rs.is_allowed("api.openai.com", Scope.NETWORK)


class TestBuildDefaultShellRules:
    @pytest.fixture
    def rs(self):
        return build_default_shell_rules()

    def test_denies_destructive_commands(self, rs):
        assert rs.is_denied("rm -rf /", Scope.SHELL)
        assert rs.is_denied("rm -rf /*", Scope.SHELL)

    def test_denies_format_commands(self, rs):
        assert rs.is_denied("mkfs.ext4 /dev/sda", Scope.SHELL)

    def test_denies_fork_bomb(self, rs):
        assert rs.is_denied(":(){ :|:& };:", Scope.SHELL)

    def test_denies_raw_device_write(self, rs):
        assert rs.is_denied("echo data > /dev/sda", Scope.SHELL)

    def test_denies_chmod_777_root(self, rs):
        assert rs.is_denied("chmod 777 /", Scope.SHELL)

    def test_allows_normal_commands(self, rs):
        assert rs.is_allowed("ls -la", Scope.SHELL)
        assert rs.is_allowed("cat file.txt", Scope.SHELL)
        assert rs.is_allowed("python script.py", Scope.SHELL)


class TestBuildDefaultEngine:
    @pytest.fixture
    def engine(self):
        return build_default_engine()

    def test_has_rules_in_all_scopes(self, engine):
        assert engine.total_rules > 0
        assert engine.filesystem.rule_count > 0
        assert engine.network.rule_count > 0
        assert engine.shell.rule_count > 0

    def test_filesystem_protection(self, engine):
        assert not engine.is_allowed("/etc/shadow", Scope.FILESYSTEM)
        assert engine.is_allowed("/home/user/doc.txt", Scope.FILESYSTEM)

    def test_network_protection(self, engine):
        assert not engine.is_allowed("10.0.0.5", Scope.NETWORK)
        assert engine.is_allowed("8.8.8.8", Scope.NETWORK)

    def test_shell_protection(self, engine):
        assert not engine.is_allowed("rm -rf /", Scope.SHELL)
        assert engine.is_allowed("ls -la", Scope.SHELL)


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestScopeRulesIntegration:
    def test_full_workflow(self):
        engine = ScopeRuleEngine()

        # Setup: deny sensitive paths, allow everything else
        engine.add_rule(ScopeRule(
            name="deny_secrets",
            pattern="/**/.env*",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            priority=10,
        ))
        engine.add_rule(ScopeRule(
            name="deny_system",
            pattern="/etc/**",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            priority=10,
        ))
        engine.add_rule(ScopeRule(
            name="deny_internal_network",
            pattern=r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)",
            effect=RuleEffect.DENY,
            scope=Scope.NETWORK,
            kind=PatternKind.REGEX,
            priority=10,
        ))
        engine.add_rule(ScopeRule(
            name="deny_dangerous_shell",
            pattern="rm -rf /*",
            effect=RuleEffect.DENY,
            scope=Scope.SHELL,
            priority=10,
        ))

        # Filesystem: safe paths allowed
        assert engine.is_allowed("/home/user/project/main.py", Scope.FILESYSTEM)
        assert engine.is_allowed("/tmp/build/output.log", Scope.FILESYSTEM)

        # Filesystem: sensitive paths denied
        assert not engine.is_allowed("/etc/passwd", Scope.FILESYSTEM)
        assert not engine.is_allowed("/app/.env", Scope.FILESYSTEM)
        assert not engine.is_allowed("/app/.env.production", Scope.FILESYSTEM)

        # Network: public OK, internal blocked
        assert engine.is_allowed("api.github.com", Scope.NETWORK)
        assert not engine.is_allowed("10.0.0.1", Scope.NETWORK)
        assert not engine.is_allowed("192.168.1.100", Scope.NETWORK)

        # Shell: dangerous blocked, normal OK
        assert engine.is_allowed("git status", Scope.SHELL)
        assert not engine.is_allowed("rm -rf /", Scope.SHELL)

        # Can add exceptions
        engine.add_rule(ScopeRule(
            name="allow_config_env",
            pattern="/**/config.env",
            effect=RuleEffect.ALLOW,
            scope=Scope.FILESYSTEM,
            priority=20,
        ))
        assert engine.is_allowed("/app/config.env", Scope.FILESYSTEM)
        # But other .env files still denied
        assert not engine.is_allowed("/app/.env", Scope.FILESYSTEM)

    def test_dynamic_rule_management(self):
        """Test adding/removing rules dynamically."""
        engine = ScopeRuleEngine()

        # Initially all allowed
        assert engine.is_allowed("/tmp/test.py", Scope.FILESYSTEM)

        # Add a deny rule
        engine.add_rule(ScopeRule(
            name="temp_block",
            pattern="/tmp/*.py",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            priority=10,
        ))
        assert not engine.is_allowed("/tmp/test.py", Scope.FILESYSTEM)

        # Remove it
        engine.remove_rule("temp_block")
        assert engine.is_allowed("/tmp/test.py", Scope.FILESYSTEM)

    def test_mixed_glob_and_regex(self):
        """Test that glob and regex rules work together."""
        engine = ScopeRuleEngine()

        # Glob: block .env files
        engine.add_rule(ScopeRule(
            name="glob_env",
            pattern="*.env",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            kind=PatternKind.GLOB,
            priority=10,
        ))
        # Regex: block any path containing 'secret'
        engine.add_rule(ScopeRule(
            name="regex_secret",
            pattern=r"secret",
            effect=RuleEffect.DENY,
            scope=Scope.FILESYSTEM,
            kind=PatternKind.REGEX,
            priority=10,
        ))

        assert not engine.is_allowed(".env", Scope.FILESYSTEM)  # glob match
        assert not engine.is_allowed("/path/to/secret.key", Scope.FILESYSTEM)  # regex match
        assert engine.is_allowed("/normal/path/file.txt", Scope.FILESYSTEM)
