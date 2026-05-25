"""Sandbox image building, caching, and lifecycle management."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Sequence

from .exceptions import ImageError


class ImageBuildStatus(str, Enum):
    """Current state of an image build."""

    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
    CACHED = "cached"


@dataclass(frozen=True)
class SandboxImage:
    """A built sandbox image ready for container creation."""

    image_id: str
    name: str
    tag: str = "latest"
    base: str = "alpine:latest"
    packages: tuple[str, ...] = ()
    size_mb: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hash: str = ""


@dataclass(frozen=True)
class ImageConfig:
    """Configuration for building a new sandbox image."""

    base_image: str = "alpine:latest"
    packages: tuple[str, ...] = ()
    env_vars: tuple[tuple[str, str], ...] = ()
    entrypoint: str = "/bin/sh"
    work_dir: str = "/workspace"


# Pre-built image definitions
PYTHON_SAFE = ImageConfig(
    base_image="python:3.11-alpine",
    packages=("numpy", "pandas"),
    env_vars=(("PYTHONDONTWRITEBYTECODE", "1"),),
    entrypoint="python",
)

NODE_SAFE = ImageConfig(
    base_image="node:20-alpine",
    packages=(),
    env_vars=(("NODE_ENV", "production"),),
    entrypoint="node",
)

BASH_RESTRICTED = ImageConfig(
    base_image="alpine:latest",
    packages=("bash", "coreutils"),
    entrypoint="/bin/bash",
)

EMPTY_BOX = ImageConfig(
    base_image="scratch",
    packages=(),
    entrypoint="/bin/true",
)


class ImageManager:
    """Manages sandbox image lifecycles including building and caching."""

    _images: dict[str, SandboxImage] = {}
    _build_statuses: dict[str, ImageBuildStatus] = {}

    @classmethod
    def build_image(cls, config: ImageConfig) -> SandboxImage:
        """Build a sandbox image from configuration (simulated)."""
        raw = json.dumps(
            {
                "base": config.base_image,
                "packages": config.packages,
                "entrypoint": config.entrypoint,
            },
            sort_keys=True,
        )
        image_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        # Deduplication via hash
        for existing in cls._images.values():
            if existing.hash == image_hash:
                return existing

        image_id = f"lyra-{image_hash}"
        image = SandboxImage(
            image_id=image_id,
            name=config.base_image.split(":")[0],
            packages=config.packages,
            base=config.base_image,
            hash=image_hash,
        )
        cls._images[image_id] = image
        cls._build_statuses[image_id] = ImageBuildStatus.READY
        return image

    @classmethod
    def cache_image(cls, image: SandboxImage) -> bool:
        """Cache an image for reuse."""
        cls._images[image.image_id] = image
        cls._build_statuses[image.image_id] = ImageBuildStatus.CACHED
        return True

    @classmethod
    def get_image(cls, image_id: str) -> SandboxImage | None:
        """Retrieve a previously built or cached image by ID."""
        return cls._images.get(image_id)

    @classmethod
    def list_images(cls) -> list[SandboxImage]:
        """Return all managed images."""
        return list(cls._images.values())

    @classmethod
    def remove_image(cls, image_id: str) -> bool:
        """Delete an image from the manager."""
        cls._images.pop(image_id, None)
        cls._build_statuses.pop(image_id, None)
        return True

    @classmethod
    def get_build_status(cls, image_id: str) -> ImageBuildStatus | None:
        """Return the build status of an image."""
        return cls._build_statuses.get(image_id)

    @classmethod
    def clear_images(cls) -> None:
        """Remove all images from the manager."""
        cls._images.clear()
        cls._build_statuses.clear()
