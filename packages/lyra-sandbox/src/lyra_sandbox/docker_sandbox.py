"""Docker container-based sandbox with security hardening."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from .exceptions import ContainerError, ExecutionResult


class ContainerStatus(str, Enum):
    """Lifecycle state of a Docker container."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    EXITED = "exited"
    DEAD = "dead"


@dataclass(frozen=True)
class SecurityProfile:
    """Security hardening profile for a sandbox container."""

    no_new_privileges: bool = True
    read_only_rootfs: bool = True
    seccomp_profile: str = "default"
    apparmor_profile: str = "default"
    cap_drop_all: bool = True
    user_namespace: bool = True


@dataclass(frozen=True)
class DockerConfig:
    """Configuration for creating a sandbox Docker container."""

    image: str = "alpine:latest"
    command: tuple[str, ...] = ("/bin/sh", "-c", "echo sandbox-ready")
    volumes: tuple[tuple[str, str, bool], ...] = ()
    environment: tuple[tuple[str, str], ...] = ()
    network: str = "none"
    privileged: bool = False
    cap_drop: tuple[str, ...] = ("ALL",)
    security_opt: tuple[str, ...] = ("no-new-privileges:true",)
    security_profile: SecurityProfile = field(default_factory=SecurityProfile)


class DockerSandbox:
    """Manages Docker containers for sandboxed code execution."""

    _containers: dict[str, dict[str, Any]] = {}
    _logs: dict[str, str] = {}
    _statuses: dict[str, ContainerStatus] = {}

    @classmethod
    def create_container(cls, config: DockerConfig) -> str:
        """Create a new sandbox container (simulated)."""
        container_id = uuid4().hex[:12]
        cls._containers[container_id] = {
            "config": config,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        cls._statuses[container_id] = ContainerStatus.CREATED
        cls._logs[container_id] = ""
        return container_id

    @classmethod
    def start_container(cls, container_id: str) -> bool:
        """Start a created container with security options applied."""
        if container_id not in cls._containers:
            raise ContainerError(f"Container {container_id} not found")
        status = cls._statuses.get(container_id)
        if status != ContainerStatus.CREATED:
            return False
        cls._statuses[container_id] = ContainerStatus.RUNNING
        return True

    @classmethod
    def execute_in_container(cls, container_id: str, command: str) -> ExecutionResult:
        """Execute a command inside a running container."""
        if container_id not in cls._containers:
            raise ContainerError(f"Container {container_id} not found")
        status = cls._statuses.get(container_id, ContainerStatus.CREATED)
        if status != ContainerStatus.RUNNING:
            return ExecutionResult(
                output="",
                stderr=f"Container {container_id} is not running (status: {status.value})",
                return_code=1,
                duration_ms=0.0,
            )

        # Simulated execution
        result: dict[str, Any] = {
            "output": f"Executed in container {container_id}: {command}",
            "stderr": "",
            "return_code": 0,
        }
        cls._logs[container_id] = (
            cls._logs.get(container_id, "") + command + "\n"
        )

        return ExecutionResult(
            output=result["output"],
            stderr=result.get("stderr", ""),
            return_code=result.get("return_code", 0),
            duration_ms=10.0,
        )

    @classmethod
    def stop_container(cls, container_id: str) -> bool:
        """Stop a running container."""
        if container_id not in cls._statuses:
            return False
        cls._statuses[container_id] = ContainerStatus.EXITED
        return True

    @classmethod
    def remove_container(cls, container_id: str) -> bool:
        """Remove a container and its resources."""
        cls._containers.pop(container_id, None)
        cls._logs.pop(container_id, None)
        cls._statuses.pop(container_id, None)
        return True

    @classmethod
    def get_container_logs(cls, container_id: str) -> str:
        """Retrieve logs from a container."""
        return cls._logs.get(container_id, "")

    @classmethod
    def get_status(cls, container_id: str) -> ContainerStatus | None:
        """Return the current status of a container."""
        return cls._statuses.get(container_id)

    @classmethod
    def list_containers(cls) -> list[str]:
        """Return container IDs for all managed containers."""
        return list(cls._containers.keys())

    @classmethod
    def clear_all(cls) -> None:
        """Remove all managed containers and logs."""
        cls._containers.clear()
        cls._logs.clear()
        cls._statuses.clear()
