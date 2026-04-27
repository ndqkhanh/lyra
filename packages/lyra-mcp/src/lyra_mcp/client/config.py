"""MCP server config: ``~/.lyra/mcp.json`` autoload + per-server records.

Lyra v2.5.0 lets the user describe MCP servers in a JSON config file
that lives at ``~/.lyra/mcp.json`` (user-global) or
``<repo>/.lyra/mcp.json`` (project-local, top precedence). The format
mirrors Claude Code's ``mcpServers`` block so users can copy/paste an
``mcp.json`` snippet they already have:

::

    {
      "mcpServers": {
        "filesystem": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
          "env": {"FOO": "bar"},
          "trust": "third-party"
        },
        "git": {
          "command": "uvx",
          "args": ["mcp-server-git", "--repository", "/path/to/repo"]
        }
      }
    }

The config loader is intentionally tolerant:

* Missing file → empty list (no MCP, chat still works).
* Missing ``mcpServers`` key → empty list (so a hand-edited file with
  just ``{}`` doesn't blow up).
* Server entries without a ``command`` → silently dropped with a
  warning record so the user can ``lyra mcp doctor`` to see them.

Precedence: project-local overrides user-global with the same name,
so a team can pin an MCP server to a project-specific git repo.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MCPServerConfig:
    """One MCP server's spawn recipe.

    Attributes:
        name: identifier used in ``mcp__{server}__{tool}`` tool
            naming (Phase C.3) and in ``/mcp ...`` slash output.
        command: executable + args list, ready to pass to
            :class:`subprocess.Popen`. Empty list means "disabled".
        env: extra environment variables merged into the parent env
            when the child is spawned.
        cwd: working directory for the child. ``None`` inherits.
        trust: ``"first-party"`` | ``"third-party"`` | custom. Used
            by the trust banner / injection guard
            (:func:`lyra_mcp.client.bridge.wrap_with_trust_banner`).
        source: which config file this entry came from, kept for
            ``lyra mcp doctor`` / debugging.
    """

    name: str
    command: tuple[str, ...]
    env: Mapping[str, str] = field(default_factory=dict)
    cwd: Optional[Path] = None
    trust: str = "third-party"
    source: Optional[Path] = None

    def is_runnable(self) -> bool:
        """``True`` when the entry has at least an executable."""
        return len(self.command) > 0


@dataclass(frozen=True)
class MCPLoadIssue:
    """A non-fatal problem encountered while loading the config."""

    source: Path
    name: str
    message: str


@dataclass
class MCPLoadResult:
    """The outcome of loading every config file we know about."""

    servers: list[MCPServerConfig] = field(default_factory=list)
    issues: list[MCPLoadIssue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def default_config_paths(repo_root: Path) -> list[Path]:
    """Where Lyra looks for ``mcp.json`` files, in load order.

    The list is *low-to-high precedence*: a server defined in both
    files keeps the project-local version because it loads second.
    """
    paths: list[Path] = []
    home = os.environ.get("LYRA_HOME")
    base = Path(home) if home else Path.home() / ".lyra"
    paths.append(base / "mcp.json")
    paths.append(Path(repo_root) / ".lyra" / "mcp.json")
    return paths


def load_mcp_config(repo_root: Path) -> MCPLoadResult:
    """Walk the default paths and merge their MCP server entries.

    Tolerates every realistic failure mode:
    * missing files → ignored,
    * non-JSON or non-dict body → recorded as an issue,
    * entries missing required fields → recorded as an issue.

    Each server name resolves to *exactly one* :class:`MCPServerConfig`
    via later-wins precedence (project beats user).
    """
    return load_mcp_config_from(default_config_paths(repo_root))


def load_mcp_config_from(paths: Iterable[Path]) -> MCPLoadResult:
    """Like :func:`load_mcp_config` but takes an explicit path list.

    Used by tests + the future ``lyra mcp --config <file>`` flag.
    """
    by_name: dict[str, MCPServerConfig] = {}
    issues: list[MCPLoadIssue] = []
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(
                MCPLoadIssue(source=path, name="<file>", message=str(exc))
            )
            continue
        try:
            data: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            issues.append(
                MCPLoadIssue(
                    source=path, name="<file>", message=f"invalid JSON: {exc}"
                )
            )
            continue
        if not isinstance(data, dict):
            issues.append(
                MCPLoadIssue(
                    source=path,
                    name="<file>",
                    message=f"top-level must be an object, got {type(data).__name__}",
                )
            )
            continue
        servers_block = data.get("mcpServers", {})
        if not isinstance(servers_block, dict):
            issues.append(
                MCPLoadIssue(
                    source=path,
                    name="<mcpServers>",
                    message=f"must be an object, got {type(servers_block).__name__}",
                )
            )
            continue
        for name, entry in servers_block.items():
            if not isinstance(entry, dict):
                issues.append(
                    MCPLoadIssue(
                        source=path,
                        name=str(name),
                        message=f"entry must be an object, got {type(entry).__name__}",
                    )
                )
                continue
            command = entry.get("command")
            args = entry.get("args", [])
            if not command or not isinstance(command, str):
                issues.append(
                    MCPLoadIssue(
                        source=path,
                        name=str(name),
                        message="missing or non-string 'command'",
                    )
                )
                continue
            if not isinstance(args, list) or not all(
                isinstance(a, str) for a in args
            ):
                issues.append(
                    MCPLoadIssue(
                        source=path,
                        name=str(name),
                        message="'args' must be a list of strings",
                    )
                )
                continue
            env_block = entry.get("env", {}) or {}
            if not isinstance(env_block, dict):
                issues.append(
                    MCPLoadIssue(
                        source=path,
                        name=str(name),
                        message="'env' must be an object",
                    )
                )
                continue
            cwd_raw = entry.get("cwd")
            cwd = Path(cwd_raw) if isinstance(cwd_raw, str) else None
            trust = str(entry.get("trust", "third-party"))
            by_name[str(name)] = MCPServerConfig(
                name=str(name),
                command=tuple([command, *args]),
                env={str(k): str(v) for k, v in env_block.items()},
                cwd=cwd,
                trust=trust,
                source=path,
            )
    return MCPLoadResult(servers=list(by_name.values()), issues=issues)


# ---------------------------------------------------------------------------
# Mutation: lyra mcp add / remove
# ---------------------------------------------------------------------------


def _user_config_path() -> Path:
    home = os.environ.get("LYRA_HOME")
    base = Path(home) if home else Path.home() / ".lyra"
    return base / "mcp.json"


def _read_or_init(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"mcpServers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"mcpServers": {}}
    if not isinstance(data, dict):
        return {"mcpServers": {}}
    block = data.get("mcpServers")
    if not isinstance(block, dict):
        data["mcpServers"] = {}
    return data


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def add_user_mcp_server(
    *,
    name: str,
    command: str,
    args: Iterable[str] = (),
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[str] = None,
    trust: str = "third-party",
    config_path: Optional[Path] = None,
) -> Path:
    """Append (or replace) ``name`` in the user-global config.

    Returns the path that was written. Idempotent — calling twice
    with the same name overwrites the entry.
    """
    target = config_path or _user_config_path()
    data = _read_or_init(target)
    entry: dict[str, Any] = {
        "command": command,
        "args": list(args),
        "trust": trust,
    }
    if env:
        entry["env"] = {str(k): str(v) for k, v in env.items()}
    if cwd:
        entry["cwd"] = cwd
    data["mcpServers"][name] = entry
    _atomic_write(target, data)
    return target


def remove_user_mcp_server(
    name: str,
    *,
    config_path: Optional[Path] = None,
) -> bool:
    """Delete ``name`` from the user-global config.

    Returns ``True`` if the entry existed (and was removed), ``False``
    when there was nothing to do — idempotent so the caller can
    safely run ``lyra mcp remove foo`` twice.
    """
    target = config_path or _user_config_path()
    if not target.exists():
        return False
    data = _read_or_init(target)
    block = data.get("mcpServers", {})
    if name not in block:
        return False
    del block[name]
    _atomic_write(target, data)
    return True


__all__ = [
    "MCPLoadIssue",
    "MCPLoadResult",
    "MCPServerConfig",
    "add_user_mcp_server",
    "default_config_paths",
    "load_mcp_config",
    "load_mcp_config_from",
    "remove_user_mcp_server",
]
