"""Claude-Code-style declarative permission grammar.

Complements :mod:`lyra_core.permissions.stack` (runtime guards like
destructive-pattern and secrets-scan) by adding **user-declared rules**:

.. code-block:: json

    {
      "permissions": {
        "allow": ["Read", "Glob", "Grep", "Bash(git status)", "Bash(git log *)"],
        "ask":   ["Edit(./src/**)", "Write(./src/**)"],
        "deny":  ["Bash(rm -rf *)", "Read(./.env*)"]
      }
    }

A rule is ``Tool`` (matches every invocation of that tool) or
``Tool(specifier)`` where the specifier is a tool-specific glob — for
``Bash`` it matches the command string after stripping any leading
``VAR=val`` env-var assignments; for ``Edit`` / ``Read`` / ``Write`` /
``Grep`` / ``Glob`` it matches the ``path``/``pattern`` argument.

Decision order is **deny → ask → allow**, first match wins. A rule
that doesn't match falls through; if nothing matches, the default is
``ASK`` for write/exec tools and ``ALLOW`` for read-only tools.

Why a grammar instead of more guards: lets users declare project
policy in a settings file without writing Python. ``policy.yaml``
(Lyra v2.x) was the seed; this module formalises it into a parseable,
testable surface that can be loaded from any settings layer.
"""
from __future__ import annotations

import enum
import fnmatch
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional


class Verdict(str, enum.Enum):
    """Outcome of evaluating one (rule, invocation) pair."""

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


# Tools whose default decision (when no rule matches) is ``ALLOW``.
# Mirrors Claude Code: read-only tools auto-approve so the typical
# "look at the code" prompt never blocks on a confirmation cascade.
READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {"Read", "Glob", "Grep", "LSP", "ListMcpResourcesTool", "ReadMcpResourceTool"}
)


@dataclass(frozen=True)
class Rule:
    """A parsed rule like ``Bash(git push *)``.

    ``specifier`` is ``None`` for a bare ``Tool`` rule (matches any
    invocation of that tool). Storing the literal source text on the
    rule is cheap and lets the matcher report *which* rule fired,
    which the REPL surfaces in confirmation toasts.
    """

    tool: str
    specifier: Optional[str]
    source: str

    @property
    def is_bare(self) -> bool:
        """A rule with no specifier matches every invocation."""
        return self.specifier is None


_RULE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?\s*$")
# Bash specifier pre-strip: drop leading ``VAR=val ...`` assignments
# before matching, so ``FOO=bar git push origin main`` and
# ``npm test && git push`` both match ``Bash(git push *)``.
_BASH_VAR_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*=\S+\s+)+")


class RuleParseError(ValueError):
    """Raised when a rule string can't be parsed."""


def parse_rule(text: str) -> Rule:
    """Parse a rule literal into a :class:`Rule`.

    Raises :class:`RuleParseError` on malformed input. The grammar is
    intentionally tiny — keeping it regex-driven means user-editable
    settings files don't need a YAML schema validator.
    """
    if not isinstance(text, str) or not text.strip():
        raise RuleParseError(f"rule must be a non-empty string, got {text!r}")
    match = _RULE_RE.match(text)
    if match is None:
        raise RuleParseError(f"unparseable rule: {text!r}")
    tool = match.group(1)
    spec = match.group(2)
    if spec is not None:
        spec = spec.strip()
    return Rule(tool=tool, specifier=spec or None, source=text.strip())


def _bash_command_from_args(args: Mapping[str, Any]) -> str:
    """Extract the canonical command string from a Bash invocation."""
    cmd = args.get("command")
    if isinstance(cmd, str):
        return _BASH_VAR_RE.sub("", cmd, count=1).strip()
    return ""


def _path_from_args(args: Mapping[str, Any]) -> str:
    """Extract a path-like field from any tool's args (best-effort).

    Order chosen to match the field names tools actually use; the
    first hit wins so a tool that has both ``path`` and ``pattern``
    (e.g. Grep) prefers the more specific ``path``.
    """
    for key in ("path", "file_path", "target", "pattern", "glob_pattern"):
        value = args.get(key)
        if isinstance(value, str):
            return value
    return ""


def _matches_specifier(rule: Rule, tool_name: str, args: Mapping[str, Any]) -> bool:
    """Return True iff ``rule.specifier`` matches the given invocation.

    Bare rules always match; bash rules match the command string with
    a glob; everything else matches the canonical path field with
    ``fnmatch`` so ``./src/**`` works the way users expect (case-
    sensitive, ``**`` for any directory depth).
    """
    if rule.is_bare:
        return True
    spec = rule.specifier or ""
    if tool_name == "Bash":
        cmd = _bash_command_from_args(args)
        return fnmatch.fnmatchcase(cmd, spec)
    path = _path_from_args(args)
    if not path:
        return False
    # ``**`` semantics: fnmatch treats ``*`` as "no slash" but ``**``
    # is what users expect for "any depth". Normalise by collapsing
    # ``**`` runs to a single ``*`` *only when matching*; the source
    # text keeps the literal ``**`` so error messages stay readable.
    if "**" in spec:
        spec = spec.replace("**", "*")
    return fnmatch.fnmatchcase(path, spec)


@dataclass
class PolicyMatch:
    """The first rule that fired during a policy check (for telemetry)."""

    verdict: Verdict
    rule: Rule

    @property
    def is_blocking(self) -> bool:
        return self.verdict == Verdict.DENY


class Policy:
    """Three-list rule set evaluated deny → ask → allow.

    Construction is cheap (no compilation, just rule storage) so the
    REPL can rebuild the policy on every settings reload without
    measurable cost.
    """

    def __init__(
        self,
        *,
        allow: Iterable[Rule] = (),
        ask: Iterable[Rule] = (),
        deny: Iterable[Rule] = (),
    ) -> None:
        self.allow: tuple[Rule, ...] = tuple(allow)
        self.ask: tuple[Rule, ...] = tuple(ask)
        self.deny: tuple[Rule, ...] = tuple(deny)

    @classmethod
    def from_strings(
        cls,
        *,
        allow: Iterable[str] = (),
        ask: Iterable[str] = (),
        deny: Iterable[str] = (),
    ) -> "Policy":
        """Convenience constructor from raw rule literals.

        Skips empty entries silently so a settings file with a stray
        blank line doesn't crash the load — but a malformed rule still
        raises so users notice typos at config-time.
        """
        return cls(
            allow=[parse_rule(s) for s in allow if str(s).strip()],
            ask=[parse_rule(s) for s in ask if str(s).strip()],
            deny=[parse_rule(s) for s in deny if str(s).strip()],
        )

    def decide(self, tool_name: str, args: Mapping[str, Any]) -> PolicyMatch:
        """Return the first matching rule (deny → ask → allow order).

        When nothing matches we synthesise a default rule whose
        verdict reflects whether the tool is read-only, so the caller
        always gets a :class:`PolicyMatch` and can log a uniform
        "rule that fired" entry without special-casing the no-match
        case.
        """
        for rule in self.deny:
            if rule.tool == tool_name and _matches_specifier(rule, tool_name, args):
                return PolicyMatch(Verdict.DENY, rule)
        for rule in self.ask:
            if rule.tool == tool_name and _matches_specifier(rule, tool_name, args):
                return PolicyMatch(Verdict.ASK, rule)
        for rule in self.allow:
            if rule.tool == tool_name and _matches_specifier(rule, tool_name, args):
                return PolicyMatch(Verdict.ALLOW, rule)
        # Default verdict: read-only tools auto-allow, everything else asks.
        default_verdict = (
            Verdict.ALLOW if tool_name in READ_ONLY_TOOLS else Verdict.ASK
        )
        return PolicyMatch(
            default_verdict,
            Rule(tool=tool_name, specifier=None, source="<default>"),
        )

    def is_empty(self) -> bool:
        """True when no user rules are loaded (default policy applies)."""
        return not (self.allow or self.ask or self.deny)


def policy_from_mapping(payload: Mapping[str, Any]) -> Policy:
    """Build a :class:`Policy` from a settings.json-style mapping.

    Accepts the CC shape (``permissions: {allow, ask, deny}``) and
    silently tolerates missing keys so partial settings files don't
    require boilerplate. Non-list values raise so config errors
    surface at load time, not on the first tool call.
    """
    perms = payload.get("permissions") if "permissions" in payload else payload
    if not isinstance(perms, Mapping):
        raise RuleParseError(
            f"permissions block must be a mapping, got {type(perms).__name__}"
        )

    def _list(key: str) -> list[str]:
        raw = perms.get(key, [])
        if raw is None:
            return []
        if not isinstance(raw, (list, tuple)):
            raise RuleParseError(
                f"permissions.{key} must be a list, got {type(raw).__name__}"
            )
        return [str(item) for item in raw]

    return Policy.from_strings(
        allow=_list("allow"),
        ask=_list("ask"),
        deny=_list("deny"),
    )


__all__ = [
    "Policy",
    "PolicyMatch",
    "READ_ONLY_TOOLS",
    "Rule",
    "RuleParseError",
    "Verdict",
    "parse_rule",
    "policy_from_mapping",
]
