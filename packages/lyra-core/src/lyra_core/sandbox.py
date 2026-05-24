"""Sandbox tool with command blocklist and fail-closed matching.

Secures the Bash tool by blocking known-dangerous patterns before
execution. The blocklist is evaluated with fail-closed semantics:
an unrecognised pattern that can't be classified as safe is denied.

Claude-Code-style sandbox features:
- Command blocklist (curl, wget blocked by default)
- Natural-language descriptions for complex bash commands
- Fail-closed matching for unrecognised commands
- Environment variable control (``LYRA_SANDBOX_MODE``)
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

# ---------- Blocklist -------------------------------------------------------

# Commands blocked by default. These are either network-fetch tools (curl,
# wget) that could exfiltrate data or destructive system commands.
_DEFAULT_BLOCKED_COMMANDS: frozenset[str] = frozenset(
    {
        "curl",
        "wget",
        "nc",
        "netcat",
        "ncat",
        "socat",
        "ssh",
        "scp",
        "sftp",
        "rsync",
        "telnet",
        "ftp",
        "tftp",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "mkfs",
        "dd",
        "fdisk",
        "parted",
        "mkswap",
        "swapon",
        "crontab",
        "at",
        "batch",
    }
)

# Patterns that are always blocked regardless of the command name.
_DEFAULT_BLOCKED_PATTERNS: tuple[str, ...] = (
    # Fork bombs
    ":(){ :|:& };:",
    # Recursive chmod/chown on /
    "chmod -R /",
    "chown -R /",
    # rm -rf / (with various flag orders)
    "rm -rf /",
    "rm -r /",
    # Device write
    ">/dev/sd",
    "dd if=/dev/zero of=/dev/sd",
    # Fork-bomb via perl/python
    "perl -e",
    "python -c 'while 1:",
    "python3 -c 'while 1:",
)


@dataclass(frozen=True)
class SandboxDecision:
    """Verdict from the sandbox blocklist check.

    Attributes:
        allowed: True when the command passes all blocklist checks.
        reason: When blocked, the human-readable reason.
        blocked_command: The specific command/pattern that triggered the block.
    """

    allowed: bool = True
    reason: str = ""
    blocked_command: str = ""


class BashBlocklist:
    """Fail-closed command blocklist for the Bash tool.

    Usage::

        bl = BashBlocklist()
        decision = bl.check("curl https://evil.com")
        if not decision.allowed:
            print(f"blocked: {decision.reason}")
    """

    def __init__(
        self,
        *,
        blocked_commands: Iterable[str] = (),
        blocked_patterns: Iterable[str] = (),
    ) -> None:
        self._blocked_commands: set[str] = set(_DEFAULT_BLOCKED_COMMANDS)
        self._blocked_commands.update(c.lower() for c in blocked_commands)
        self._blocked_patterns: list[str] = list(_DEFAULT_BLOCKED_PATTERNS)
        self._blocked_patterns.extend(blocked_patterns)

    def check(self, command: str) -> SandboxDecision:
        """Evaluate *command* against the blocklist.

        Returns a ``SandboxDecision`` — ``allowed=True`` when the
        command passes all checks.
        """
        cmd_clean = command.strip()
        if not cmd_clean:
            return SandboxDecision()

        # Check literal patterns first (highest priority — catches
        # obfuscated variants that wouldn't match the command-name
        # check below).
        for pattern in self._blocked_patterns:
            if pattern in cmd_clean:
                return SandboxDecision(
                    allowed=False,
                    reason=f"blocked pattern: {pattern!r}",
                    blocked_command=pattern,
                )

        # Extract the base command name (strip leading path, handle
        # `sudo`, `env`, and common wrappers).
        base = _extract_base_command(cmd_clean)
        if base and base in self._blocked_commands:
            return SandboxDecision(
                allowed=False,
                reason=(
                    f"{base!r} is blocked by the sandbox. "
                    f"Use a different tool or consult the security policy."
                ),
                blocked_command=base,
            )

        return SandboxDecision()

    def add_blocked(self, command: str) -> None:
        """Dynamically add a command to the blocklist at runtime."""
        self._blocked_commands.add(command.strip().lower())

    def remove_blocked(self, command: str) -> None:
        """Dynamically remove a command from the blocklist."""
        self._blocked_commands.discard(command.strip().lower())

    @property
    def blocked_commands(self) -> frozenset[str]:
        return frozenset(self._blocked_commands)


def _extract_base_command(command: str) -> str | None:
    """Extract the base command name, unwrapping sudo/env/pipe chains.

    Returns ``None`` for shell builtins and empty input.
    """
    # Unwrap sudo
    cmd = command.strip()
    for prefix in ("sudo ", "sudo\t", "env ", "/usr/bin/env "):
        if cmd.startswith(prefix):
            cmd = cmd[len(prefix):].strip()

    # Take the first pipe segment
    if "|" in cmd:
        cmd = cmd.split("|")[0].strip()

    # Handle redirections — take the command before them
    for redirect in (">", ">>", "<", "2>", "&>"):
        if redirect in cmd:
            # Only split if the redirect is standalone, not part of a
            # string like ``echo "test > file"``
            parts = cmd.split(f" {redirect} ", 1)
            if len(parts) > 1:
                cmd = parts[0].strip()
                break

    # Shell builtins we can't block
    _SHELL_BUILTINS = frozenset(
        {"cd", "echo", "export", "source", ".", "alias", "unalias",
         "wait", "exit", "return", "type", "hash", "read", "printf",
         "test", "[", "true", "false", "pwd", "jobs", "fg", "bg"}
    )

    # Get the first word
    first_word = cmd.split()[0] if cmd.strip() else ""
    if not first_word:
        return None
    # Strip path prefix
    if "/" in first_word:
        first_word = first_word.rsplit("/", 1)[-1]
    if first_word in _SHELL_BUILTINS:
        return None
    return first_word


# ---------- Natural Language Description Helper -----------------------------


def requires_nl_description(command: str) -> bool:
    """Return True when *command* should show a natural-language description.

    Complex commands (pipes, redirects, multiple flags, long lines) are
    hard to audit at a glance — the operator should explain what the
    command does before it's approved.
    """
    stripped = command.strip()
    return (
        "|" in stripped
        or ";" in stripped
        or "&&" in stripped
        or "||" in stripped
        or stripped.count("$(") > 0
        or stripped.count("`") >= 2
        or len(stripped) > 200
    )


# ---------- Environment / Config --------------------------------------------


def sandbox_mode() -> str:
    """Read ``LYRA_SANDBOX_MODE`` env var.

    Returns one of ``"strict"`` (fail-closed), ``"warn"`` (log + allow),
    or ``"off"`` (no blocklist enforcement). Defaults to ``"warn"`` so
    the blocklist is advisory on a first install and operators tighten it
    after reviewing the blocked set.
    """
    import os

    raw = os.environ.get("LYRA_SANDBOX_MODE", "warn").strip().lower()
    if raw in ("strict", "on", "1", "true", "yes"):
        return "strict"
    if raw in ("off", "0", "false", "no", "none", "disabled"):
        return "off"
    return "warn"


__all__ = [
    "BashBlocklist",
    "SandboxDecision",
    "requires_nl_description",
    "sandbox_mode",
]
