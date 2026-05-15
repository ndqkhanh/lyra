"""Named permission profiles for investigate mode.

DCI-Agent-Lite confines its agent to ``--cwd <corpus_root>`` with a
short allowlist of shell binaries. Lyra's permissions grammar can
already express that constraint, but the v3.13 contract is that ops
get two named presets they can switch between without rewriting
grammar rules:

* :data:`READ_ONLY` — read-only mount; no writes anywhere; allowlist
  restricted to the DCI workhorse binaries (``rg find sed head tail
  wc awk sort uniq xargs cat ls``); no network. The default.
* :data:`READ_WRITE` — same allowlist plus ``mkdir`` and writes that
  land *inside* the mount; still no network.

The profile is a pure value object. The actual enforcement lives in
the tool factory (which reads :attr:`allowed_commands` and
:attr:`read_only`) and in the host's permissions grammar (which
reads :attr:`write_root` and :attr:`allow_network`). Wiring the
grammar to consume these profiles is one follow-up bundle — the
profile itself ships standalone so the wiring lands as a single
opt-in seam.

Cite: arXiv:2605.05242 §3; DCI-Agent-Lite README "--cwd <corpus_root>".
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Default DCI allowlist — matches the DCI-Agent-Lite system prompt's
# RQ6 finding on which binaries dominate the trajectory.
_DCI_DEFAULT_ALLOWLIST: tuple[str, ...] = (
    "rg", "grep", "find", "sed", "head", "tail",
    "wc", "awk", "sort", "uniq", "xargs", "cat", "ls",
)


@dataclass(frozen=True)
class InvestigateProfile:
    """One named permissions profile for an investigate-mode run.

    Attributes:
        name: Profile id used for telemetry / logs.
        read_only: When ``True``, the tool factory rejects every write
            attempt; the permissions grammar additionally rejects
            ``mkdir`` and file-overwrite ops.
        allowed_commands: The set of binary names the ``execute_code``
            tool will let through. Default = DCI's workhorse list.
        allow_network: When ``False``, the host's permissions grammar
            should deny outbound sockets from the agent.
        write_root: When non-``None`` and ``read_only`` is ``False``,
            writes are gated to paths under this directory (typically
            the corpus mount root). Used by the grammar.
    """

    name: str
    read_only: bool = True
    allowed_commands: tuple[str, ...] = _DCI_DEFAULT_ALLOWLIST
    allow_network: bool = False
    write_root: Path | None = None

    def __post_init__(self) -> None:
        if self.read_only and self.write_root is not None:
            raise ValueError(
                f"profile {self.name!r}: write_root must be None when read_only",
            )
        if not self.read_only and self.write_root is None:
            raise ValueError(
                f"profile {self.name!r}: write_root must be set when not read_only",
            )

    @property
    def allowed_set(self) -> frozenset[str]:
        """Frozen view of :attr:`allowed_commands` for cheap membership."""
        return frozenset(self.allowed_commands)


READ_ONLY: InvestigateProfile = InvestigateProfile(
    name="investigate-readonly",
    read_only=True,
)
"""The default DCI profile. Used by :class:`InvestigationRunner` unless overridden."""


def read_write(mount_root: Path) -> InvestigateProfile:
    """Build the writable profile gated to *mount_root*.

    There is no module-level ``READ_WRITE`` constant because the
    write root is mount-specific; the host passes its corpus root
    explicitly.
    """
    return InvestigateProfile(
        name="investigate-rw",
        read_only=False,
        write_root=mount_root,
    )


__all__ = ["READ_ONLY", "InvestigateProfile", "read_write"]
