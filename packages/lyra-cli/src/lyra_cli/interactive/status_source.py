"""Lightweight status source for the slim REPL footer.

The footer row in Claude-Code/opencode-style CLIs shows a one-line
contextual status: ``cwd · mode · model · LSP:N · MCP:M``. We centralize
the source of truth in :class:`StatusSource` so the AgentLoop (or any
other owner) can ``update(...)`` it without the REPL knowing the
producer's internals. The REPL's bottom-toolbar function calls
:meth:`render` each refresh.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock


@dataclass
class StatusSource:
    """Shared bag of footer-line fields.

    Fields are plain strings (or integers for counts). All writes go
    through :meth:`update` to stay thread-safe since the AgentLoop may
    run plugins on worker threads.
    """

    cwd: Path = field(default_factory=Path.cwd)
    mode: str = "edit_automatically"
    model: str = "unknown"
    permissions: str = ""  # "" | "normal" | "strict" | "yolo" — empty hides the field
    lsp_count: int = 0
    mcp_count: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    turn: int = 0
    branch: str = ""
    session_id: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    _lock: Lock = field(default_factory=Lock, repr=False)

    def update(self, **kv: object) -> None:
        """Update any subset of fields atomically."""
        with self._lock:
            for key, value in kv.items():
                if key == "extra" and isinstance(value, dict):
                    self.extra.update({str(k): str(v) for k, v in value.items()})
                elif hasattr(self, key):
                    setattr(self, key, value)

    def render(self, *, max_width: int | None = None) -> str:
        """Return the compact footer string.

        The cwd is shortened with ``~`` expansion so even deep paths
        fit; numeric fields are hidden when zero so the footer doesn't
        shout ``LSP:0 · MCP:0`` at users who aren't using them.
        """
        with self._lock:
            cwd = str(self.cwd)
            home = str(Path.home())
            if cwd.startswith(home):
                cwd = "~" + cwd[len(home):]

            parts = [f"cwd:{cwd}", f"mode:{self.mode}", f"model:{self.model}"]
            if self.lsp_count:
                parts.append(f"LSP:{self.lsp_count}")
            if self.mcp_count:
                parts.append(f"MCP:{self.mcp_count}")
            if self.tokens:
                parts.append(f"{self.tokens} tokens")
            if self.cost_usd:
                parts.append(f"${self.cost_usd:.2f}")
            for key, value in self.extra.items():
                parts.append(f"{key}:{value}")

        line = " · ".join(parts)
        if max_width is not None and len(line) > max_width:
            line = line[: max_width - 1] + "…"
        return line

    @classmethod
    def from_env(cls) -> "StatusSource":
        """Factory that populates sensible defaults from the environment."""
        return cls(
            cwd=Path(os.environ.get("PWD", Path.cwd())),
            mode=os.environ.get("OPEN_HARNESS_MODE", "edit_automatically"),
            model=os.environ.get("OPEN_HARNESS_MODEL", "unknown"),
        )


__all__ = ["StatusSource"]
