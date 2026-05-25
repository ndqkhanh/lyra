"""Safe code execution engine with multi-sandbox support."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Sequence

from .docker_sandbox import DockerConfig, DockerSandbox
from .exceptions import CodeRequest, ExecutionError, ExecutionResult, Language, SecurityScanError
from .process_sandbox import ProcessConfig, ProcessSandbox
from .security_scanner import ScanConfig, SecurityPolicy, SecurityScanner


@dataclass(frozen=True)
class ExecutionPolicy:
    """Constraints for code execution."""

    allowed_languages: tuple[Language, ...] = (
        Language.PYTHON,
        Language.BASH,
        Language.GENERIC,
    )
    max_code_length: int = 100_000
    forbidden_patterns: tuple[str, ...] = ()
    require_review: bool = True


@dataclass(frozen=True)
class ExecutionMetrics:
    """Aggregated execution statistics."""

    total: int = 0
    success: int = 0
    timeout: int = 0
    killed: int = 0
    avg_duration: float = 0.0


class ExecutionEngine:
    """Orchestrates safe code execution across sandbox types."""

    def __init__(
        self,
        policy: ExecutionPolicy | None = None,
        scan_config: ScanConfig | None = None,
        security_policy: SecurityPolicy | None = None,
    ) -> None:
        self._policy = policy or ExecutionPolicy()
        self._scan_config = scan_config or ScanConfig()
        self._security_policy = security_policy or SecurityPolicy()
        self._executions: list[ExecutionResult] = []

    def execute(
        self,
        request: CodeRequest,
        sandbox_type: str = "process",
    ) -> ExecutionResult:
        """Execute code in a sandbox and return the result."""
        self._validate_request(request)

        # Security scan
        scan_result = SecurityScanner.scan_code(
            request.code,
            language=request.language,
            policy=self._security_policy,
        )
        if not scan_result.passed and self._scan_config.auto_block_critical:
            raise SecurityScanError(
                f"Security scan failed: {scan_result.blocked_patterns}"
            )

        # Route to sandbox
        start = time.monotonic()
        result = self._route_execution(request, sandbox_type)
        duration = time.monotonic() - start

        exec_result = ExecutionResult(
            output=result.output,
            stderr=result.stderr,
            return_code=result.return_code,
            duration_ms=duration * 1000,
            timed_out=result.timed_out,
            was_killed=result.was_killed,
            sandbox_type_used=sandbox_type,
        )
        self._executions.append(exec_result)
        return exec_result

    def batch_execute(
        self,
        requests: Sequence[CodeRequest],
        sandbox_type: str = "process",
    ) -> list[ExecutionResult]:
        """Execute multiple code requests sequentially and return results."""
        results: list[ExecutionResult] = []
        for req in requests:
            try:
                result = self.execute(req, sandbox_type=sandbox_type)
            except SecurityScanError as e:
                result = ExecutionResult(
                    output="",
                    stderr=str(e),
                    return_code=1,
                    duration_ms=0.0,
                )
            results.append(result)
        return results

    def get_metrics(self) -> ExecutionMetrics:
        """Return aggregate execution statistics."""
        total = len(self._executions)
        if total == 0:
            return ExecutionMetrics()
        success = sum(1 for e in self._executions if e.return_code == 0)
        timeout = sum(1 for e in self._executions if e.timed_out)
        killed = sum(1 for e in self._executions if e.was_killed)
        avg_dur = sum(e.duration_ms for e in self._executions) / total
        return ExecutionMetrics(
            total=total,
            success=success,
            timeout=timeout,
            killed=killed,
            avg_duration=avg_dur,
        )

    def _validate_request(self, request: CodeRequest) -> None:
        """Validate that a code request meets policy requirements."""
        if request.language not in self._policy.allowed_languages:
            raise ExecutionError(
                f"Language {request.language.value} is not allowed by policy"
            )
        if len(request.code) > self._policy.max_code_length:
            raise ExecutionError(
                f"Code length {len(request.code)} exceeds max {self._policy.max_code_length}"
            )
        for pattern in self._policy.forbidden_patterns:
            if pattern in request.code:
                raise ExecutionError(f"Code contains forbidden pattern: {pattern}")

    def _route_execution(
        self,
        request: CodeRequest,
        sandbox_type: str,
    ) -> ExecutionResult:
        """Route execution to the appropriate sandbox."""
        if sandbox_type == "docker":
            return self._execute_docker(request)
        # Default: process sandbox
        return self._execute_process(request)

    def _execute_process(self, request: CodeRequest) -> ExecutionResult:
        """Execute via subprocess sandbox."""
        command_map = {
            Language.PYTHON: ("python3", "-c", request.code),
            Language.BASH: ("bash", "-c", request.code),
            Language.GENERIC: ("sh", "-c", request.code),
            Language.JAVASCRIPT: ("node", "-e", request.code),
        }
        cmd = command_map.get(request.language)
        if cmd is None:
            cmd = ("sh", "-c", request.code)

        config = ProcessConfig(
            command=cmd,
            timeout=30,
        )
        proc_result = ProcessSandbox.execute(config)
        return ExecutionResult(
            output=proc_result.stdout,
            stderr=proc_result.stderr,
            return_code=proc_result.exit_code,
            duration_ms=proc_result.duration * 1000,
            was_killed=proc_result.was_killed,
            sandbox_type_used="process",
        )

    def _execute_docker(self, request: CodeRequest) -> ExecutionResult:
        """Execute via Docker sandbox."""
        docker_config = DockerConfig(
            image="python:3.11-alpine",
            command=("/bin/sh", "-c", request.code),
        )
        container_id = DockerSandbox.create_container(docker_config)
        DockerSandbox.start_container(container_id)
        result = DockerSandbox.execute_in_container(container_id, request.code)
        DockerSandbox.stop_container(container_id)
        return ExecutionResult(
            output=result.output,
            stderr=result.stderr,
            return_code=result.return_code,
            duration_ms=result.duration_ms,
            timed_out=result.timed_out,
            was_killed=result.was_killed,
            sandbox_type_used="docker",
        )

    @property
    def execution_count(self) -> int:
        """Return total execution count."""
        return len(self._executions)
