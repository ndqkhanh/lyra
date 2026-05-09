"""Auto-mode safety classifier (v3.7 L37-4).

Lyra's v3.6.0 rename introduced ``auto_mode`` as a *mode label* with a
heuristic router stub. v3.7 ships a real classifier: pattern-matching
on destructive shell commands, prompt-injection markers, and
side-effecting tool kinds; verdict is one of ``AUTO_RUN`` / ``ASK`` /
``REFUSE``.

Bright-line: ``LBL-AUTO-REFUSE`` — any command tripping the classifier's
destructive or prompt-injection signal is REFUSED in ``auto_mode``
regardless of bypass flags.
"""
from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Iterable


_LBL_REFUSE: str = "LBL-AUTO-REFUSE"


class AutoVerdict(str, enum.Enum):
    AUTO_RUN = "auto_run"
    ASK = "ask"
    REFUSE = "refuse"


# Destructive shell patterns — refused unconditionally in auto_mode.
_DESTRUCTIVE_RE: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s+-[rRf]+[^|;]*\s+/\s*$", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\s+(/|/\*|\$HOME|~|/etc|/usr|/var|/bin|/lib|/sbin)\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=.*\s+of=/dev/", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:"),                  # fork bomb
    re.compile(r"\bcurl\s+[^|]*\|\s*sh\b", re.IGNORECASE),     # curl | sh
    re.compile(r"\bwget\s+[^|]*\|\s*sh\b", re.IGNORECASE),     # wget | sh
    re.compile(r"\bgit\s+push\s+--force\s+(?:[^\s]+)\s+(main|master|production)\b", re.IGNORECASE),
    re.compile(r"\bdrop\s+(?:database|table)\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+-R\s+777\s+/\b", re.IGNORECASE),
)

# Prompt-injection markers — refused unconditionally in auto_mode.
_INJECTION_RE: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(?:all\s+)?previous\s+", re.IGNORECASE),
    re.compile(r"system\s*[:>]\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"prompt\s*[:>]\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"\[\[\s*system\s*\]\]", re.IGNORECASE),
    re.compile(r"\\x1b\[", re.IGNORECASE),                     # raw ANSI escape
)

# Side-effecting tool kinds — auto-runnable iff target is on an
# allowlist or is read-only. Otherwise downgrade to ASK.
_SIDE_EFFECT_KINDS: frozenset[str] = frozenset({
    "bash", "shell", "exec",
    "write", "edit", "delete",
    "git_push", "git_force_push",
    "http_post", "http_put", "http_delete",
    "publish", "deploy",
    "send_email", "post_message",
})

# Read-only / safe-by-default tool kinds.
_READ_ONLY_KINDS: frozenset[str] = frozenset({
    "read", "list", "glob", "grep",
    "git_status", "git_diff", "git_log",
    "http_get",
})

# Sensitive paths that even read access should ASK on.
_SENSITIVE_PATH_RE: re.Pattern[str] = re.compile(
    r"(/etc/(?:passwd|shadow|sudoers)|"
    r"\.aws/credentials|\.ssh/id_[^/]+|"
    r"\.env(?:\.[\w.-]+)?$|"
    r"\.docker/config\.json)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AutoDecision:
    """Outcome of one ``AutoModeClassifier.evaluate`` call."""

    verdict: AutoVerdict
    reason: str
    bright_line: str | None = None
    matched_signals: tuple[str, ...] = ()


@dataclass
class AutoModeClassifier:
    """Pattern-matching classifier for ``auto_mode`` permission decisions.

    Callers pass the action's ``kind`` (e.g. "bash", "read") and a
    ``payload`` dict. The classifier checks:

    1. Destructive shell patterns over `payload["command"]` (refuse).
    2. Prompt-injection markers over `payload["command"]` and
       `payload["text"]` (refuse).
    3. Sensitive-path access over `payload["path"]` (ask).
    4. Side-effect tool kind without an allowlisted target (ask).
    5. Read-only kinds with no sensitive path (auto-run).
    6. Anything else → ask.
    """

    side_effect_allowlist: frozenset[str] = field(default_factory=frozenset)
    extra_destructive: tuple[re.Pattern[str], ...] = ()
    extra_injection: tuple[re.Pattern[str], ...] = ()

    def evaluate(self, *, kind: str, payload: dict[str, Any] | None = None) -> AutoDecision:
        payload = payload or {}
        command = str(payload.get("command", "") or "")
        text = str(payload.get("text", "") or "")
        path = str(payload.get("path", "") or "")
        target = str(payload.get("target", "") or "")
        signals: list[str] = []

        # 1. Destructive shell patterns.
        for pat in (*_DESTRUCTIVE_RE, *self.extra_destructive):
            if pat.search(command):
                signals.append(f"destructive:{pat.pattern[:40]}")
                return AutoDecision(
                    verdict=AutoVerdict.REFUSE,
                    reason=f"{_LBL_REFUSE}: destructive pattern matched in command",
                    bright_line=_LBL_REFUSE,
                    matched_signals=tuple(signals),
                )

        # 2. Prompt-injection markers.
        for pat in (*_INJECTION_RE, *self.extra_injection):
            for blob in (command, text):
                if pat.search(blob):
                    signals.append(f"injection:{pat.pattern[:40]}")
                    return AutoDecision(
                        verdict=AutoVerdict.REFUSE,
                        reason=f"{_LBL_REFUSE}: prompt-injection marker matched",
                        bright_line=_LBL_REFUSE,
                        matched_signals=tuple(signals),
                    )

        # 3. Sensitive-path access — ASK even for reads.
        if path and _SENSITIVE_PATH_RE.search(path):
            signals.append(f"sensitive-path:{path}")
            return AutoDecision(
                verdict=AutoVerdict.ASK,
                reason=f"sensitive path {path!r} requires confirmation",
                matched_signals=tuple(signals),
            )

        # 4. Side-effect kinds — admit only if target on allowlist.
        if kind in _SIDE_EFFECT_KINDS:
            if target and target in self.side_effect_allowlist:
                return AutoDecision(
                    verdict=AutoVerdict.AUTO_RUN,
                    reason=f"{kind} on allowlisted target {target!r}",
                )
            return AutoDecision(
                verdict=AutoVerdict.ASK,
                reason=f"{kind} without allowlisted target requires confirmation",
            )

        # 5. Read-only kinds — auto-run when nothing else trips.
        if kind in _READ_ONLY_KINDS:
            return AutoDecision(
                verdict=AutoVerdict.AUTO_RUN,
                reason=f"{kind} is read-only and no sensitive signals matched",
            )

        # 6. Default — unknown kind, ask.
        return AutoDecision(
            verdict=AutoVerdict.ASK,
            reason=f"unknown kind {kind!r}; default to ASK",
        )


__all__ = [
    "AutoDecision",
    "AutoModeClassifier",
    "AutoVerdict",
]
