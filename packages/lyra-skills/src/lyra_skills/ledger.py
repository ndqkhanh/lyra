"""Phase O.1 — Skill ledger: persistent per-skill outcome history.

The ledger is the bookkeeping half of Memento-style **Read-Write
Reflective Learning**. Every time a progressive skill activates
during a turn, the harness records a :class:`SkillOutcome` against
the skill's id (``OUTCOME_SUCCESS`` / ``OUTCOME_FAILURE`` /
``OUTCOME_NEUTRAL``). The Write phase (``lyra skill reflect``) and
the recency-boosted utility score read those records back to:

* tie-break the skill router when two progressive skills both match a
  prompt (Phase O.6),
* surface ``lyra skill stats`` (Phase O.3),
* feed reflective rewrites with the actual failure transcripts
  (Phase O.4),
* propose new-skill candidates from clusters of successful turns
  that no existing skill claimed (Phase O.5).

Storage shape — JSON at ``$LYRA_HOME/skill_ledger.json``::

    {
      "version": 1,
      "skills": {
        "tdd-discipline": {
          "skill_id": "tdd-discipline",
          "successes": 42,
          "failures": 3,
          "last_used_at": 1748899200.0,
          "last_failure_reason": "tool returned non-zero",
          "history": [{"ts": ..., "kind": "success", ...}, ...]
        }
      }
    }

Why JSON, not SQLite? Three reasons:

1. The data is *small* (one row per skill, bounded history each).
2. Inspectability matters more than write throughput here — users
   should be able to ``cat`` the ledger to see why their skill is
   getting ranked low.
3. ``lyra-skills`` is a leaf package; pulling in a DB driver would
   break that.

Concurrency: the ledger does *atomic* writes via tempfile +
``os.replace``. There is no lock around the read-modify-write
because losing one neutral activation record across a race between
two concurrent REPLs is acceptable for analytics. Counts are still
correct because each ``record_outcome`` is RMW under the assumption
of low contention.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


LEDGER_VERSION = 1

OUTCOME_SUCCESS = "success"
OUTCOME_FAILURE = "failure"
OUTCOME_NEUTRAL = "neutral"

_KNOWN_KINDS = frozenset({OUTCOME_SUCCESS, OUTCOME_FAILURE, OUTCOME_NEUTRAL})

# Per-skill rolling history cap. 50 keeps the ledger inspectable
# (a few KB at most per skill) while giving the Write phase enough
# transcripts to reflect on patterns.
MAX_HISTORY = 50

# Recency boost: a skill used within the last 7 days gets a +10%
# multiplier on its raw utility, decaying to no boost over 60 days.
# This biases the router toward recently-validated skills without
# erasing the long-term signal — older but proven skills still rank.
_RECENCY_FRESH_DAYS = 7.0
_RECENCY_DECAY_DAYS = 60.0
_RECENCY_BOOST = 0.10


@dataclass
class SkillOutcome:
    """One record of how a skill activation went.

    ``kind`` must be one of :data:`OUTCOME_SUCCESS` /
    :data:`OUTCOME_FAILURE` / :data:`OUTCOME_NEUTRAL`. Anything else
    raises :class:`ValueError` at construction so corrupt data can't
    sneak past the ledger and confuse the utility math later.

    ``error_kind`` is a free-form tag (we suggest values like
    ``"execution_error"`` / ``"timeout"`` / ``"input_invalid"`` —
    inspired by Memento-Skills' ``ErrorType`` enum) to let
    ``lyra skill reflect`` group failures by category.
    """

    ts: float
    session_id: str
    turn: int
    kind: str
    detail: str = ""
    error_kind: str = ""

    def __post_init__(self) -> None:
        if self.kind not in _KNOWN_KINDS:
            raise ValueError(
                f"unknown SkillOutcome kind: {self.kind!r} "
                f"(expected one of {sorted(_KNOWN_KINDS)})"
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ts": float(self.ts),
            "session_id": self.session_id,
            "turn": int(self.turn),
            "kind": self.kind,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.error_kind:
            d["error_kind"] = self.error_kind
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillOutcome":
        return cls(
            ts=float(data.get("ts", 0.0)),
            session_id=str(data.get("session_id", "")),
            turn=int(data.get("turn", 0)),
            kind=str(data.get("kind", OUTCOME_NEUTRAL)),
            detail=str(data.get("detail", "")),
            error_kind=str(data.get("error_kind", "")),
        )


@dataclass
class SkillStats:
    """Aggregate stats + recent history for one skill id."""

    skill_id: str
    successes: int = 0
    failures: int = 0
    last_used_at: float = 0.0
    last_failure_reason: str = ""
    history: list[SkillOutcome] = field(default_factory=list)

    @property
    def utility(self) -> float:
        return utility_score(self)

    def record(self, outcome: SkillOutcome) -> None:
        if outcome.kind == OUTCOME_SUCCESS:
            self.successes += 1
        elif outcome.kind == OUTCOME_FAILURE:
            self.failures += 1
            if outcome.detail:
                self.last_failure_reason = outcome.detail
        self.last_used_at = max(self.last_used_at, outcome.ts)
        self.history.append(outcome)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "successes": self.successes,
            "failures": self.failures,
            "last_used_at": self.last_used_at,
            "last_failure_reason": self.last_failure_reason,
            "history": [o.to_dict() for o in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillStats":
        history_raw = data.get("history") or []
        return cls(
            skill_id=str(data.get("skill_id", "")),
            successes=int(data.get("successes", 0)),
            failures=int(data.get("failures", 0)),
            last_used_at=float(data.get("last_used_at", 0.0)),
            last_failure_reason=str(data.get("last_failure_reason", "")),
            history=[SkillOutcome.from_dict(o) for o in history_raw],
        )


@dataclass
class SkillLedger:
    """Container for the on-disk ledger blob.

    Acts mostly as a typed dict-of-stats; the heavy lifting lives in
    free functions (:func:`record_outcome` / :func:`load_ledger` /
    :func:`save_ledger`) so callers from the CLI side don't need to
    pin a long-lived ledger object.
    """

    version: int = LEDGER_VERSION
    skills: dict[str, SkillStats] = field(default_factory=dict)

    def record(self, skill_id: str, outcome: SkillOutcome) -> SkillStats:
        stats = self.skills.get(skill_id)
        if stats is None:
            stats = SkillStats(skill_id=skill_id)
            self.skills[skill_id] = stats
        stats.record(outcome)
        return stats

    def get(self, skill_id: str) -> SkillStats:
        stats = self.skills.get(skill_id)
        if stats is None:
            stats = SkillStats(skill_id=skill_id)
            self.skills[skill_id] = stats
        return stats

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "skills": {sid: s.to_dict() for sid, s in self.skills.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillLedger":
        skills_raw = data.get("skills") or {}
        skills: dict[str, SkillStats] = {}
        for sid, payload in skills_raw.items():
            if not isinstance(payload, dict):
                continue
            stats = SkillStats.from_dict(payload)
            if not stats.skill_id:
                stats.skill_id = sid
            skills[sid] = stats
        return cls(
            version=int(data.get("version", LEDGER_VERSION)),
            skills=skills,
        )


# ── Path resolution ──────────────────────────────────────────────


def default_ledger_path() -> Path:
    """``$LYRA_HOME/skill_ledger.json`` if ``LYRA_HOME`` is set, else
    ``~/.lyra/skill_ledger.json``.

    This mirrors the convention used by :mod:`lyra_cli.config_io`
    so the wizard, doctor, and ledger all agree on where state
    lives.
    """
    home_env = os.environ.get("LYRA_HOME")
    if home_env:
        return Path(home_env).expanduser() / "skill_ledger.json"
    return Path(os.environ.get("HOME", ".")).expanduser() / ".lyra" / "skill_ledger.json"


# ── load / save ──────────────────────────────────────────────────


def load_ledger(path: Path | str | None = None) -> SkillLedger:
    """Read the ledger from *path* (or the default).

    Missing file ⇒ empty ledger. Malformed JSON ⇒ empty ledger and
    the corrupt file is renamed with a ``.corrupt`` suffix (so the
    user can post-mortem without losing the bytes).
    """
    p = _resolve(path)
    if not p.is_file():
        return SkillLedger()
    raw = p.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            p.rename(p.with_suffix(p.suffix + ".corrupt"))
        except OSError:
            pass
        return SkillLedger()
    if not isinstance(data, dict):
        return SkillLedger()
    return SkillLedger.from_dict(data)


def save_ledger(ledger: SkillLedger, path: Path | str | None = None) -> Path:
    """Atomically persist *ledger* to *path*.

    Uses tempfile + ``os.replace`` so a crash mid-write leaves the
    previous ledger intact. The temp file is cleaned up on failure
    so the parent dir doesn't accumulate ``.ledger.<random>`` cruft.
    Permissions are *not* set to 0600 because the ledger is not
    sensitive (it's just analytics) — matching the openness of the
    skills directory itself.
    """
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(ledger.to_dict(), indent=2, sort_keys=True) + "\n"

    fd, tmp = tempfile.mkstemp(prefix=".ledger.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


def record_outcome(
    skill_id: str,
    outcome: SkillOutcome,
    *,
    path: Path | str | None = None,
) -> SkillStats:
    """Convenience: load → record → save in one call.

    The hot path during a turn — every progressive activation runs
    this once. If the file is missing, it's created on the first
    call.
    """
    led = load_ledger(path)
    stats = led.record(skill_id, outcome)
    save_ledger(led, path)
    return stats


# ── Scoring ──────────────────────────────────────────────────────


def utility_score(stats: SkillStats) -> float:
    """Return a number in roughly ``[-1.1, +1.1]`` summarising how
    useful this skill has been.

    Base score is the standard ``(s - f) / (s + f)`` ratio (so 0 for
    an unused skill, +1 for all-success, -1 for all-failure). On top
    of that, we apply a recency boost: if the skill was used in the
    last :data:`_RECENCY_FRESH_DAYS` it gets a small positive nudge
    that decays to zero over :data:`_RECENCY_DECAY_DAYS`. The base
    score sign is preserved (we don't boost a hot failure into a
    success).

    Tie-break behaviour: this is precisely what lets Phase O.6 prefer
    "tdd-discipline used yesterday with 5/5 successes" over
    "tdd-rituals used 60 days ago with 5/5 successes" when both
    match the same keyword.
    """
    s = stats.successes
    f = stats.failures
    total = s + f
    if total == 0:
        return 0.0
    base = (s - f) / total

    if stats.last_used_at <= 0.0:
        return base

    age_days = max(0.0, (time.time() - stats.last_used_at) / 86400.0)
    if age_days >= _RECENCY_DECAY_DAYS:
        return base
    # Linear decay from full boost at age 0 to no boost at the cap.
    # Scale by sign(base) so negative scores aren't accidentally
    # bumped *toward* positive territory. ``math.copysign`` keeps the
    # zero-base case at zero too.
    decay = max(0.0, 1.0 - age_days / _RECENCY_DECAY_DAYS)
    if age_days < _RECENCY_FRESH_DAYS:
        decay = 1.0  # full boost while genuinely fresh
    boost = _RECENCY_BOOST * decay
    return base + math.copysign(boost, base) if base != 0.0 else base


def top_n(ledger: SkillLedger, n: int = 10) -> list[SkillStats]:
    """Return at most *n* skills sorted by utility (desc).

    Tie-breakers, in order:

    1. **Activation count** (``successes + failures``) — higher
       confidence beats lower confidence at equal utility.
    2. **Last-used timestamp** — fresh experience beats stale.

    This ordering matches what we want on the ``lyra skill stats``
    table *and* in Phase O.6's utility-aware router: when two
    progressive skills tie on keyword match, the one with the
    longer track record at the same success ratio wins.
    """
    items = list(ledger.skills.values())
    items.sort(
        key=lambda s: (
            utility_score(s),
            s.successes + s.failures,
            s.last_used_at,
        ),
        reverse=True,
    )
    return items[: max(0, n)]


# ── Internals ────────────────────────────────────────────────────


def _resolve(path: Path | str | None) -> Path:
    if path is None:
        return default_ledger_path()
    return Path(path).expanduser()


__all__ = [
    "LEDGER_VERSION",
    "MAX_HISTORY",
    "OUTCOME_FAILURE",
    "OUTCOME_NEUTRAL",
    "OUTCOME_SUCCESS",
    "SkillLedger",
    "SkillOutcome",
    "SkillStats",
    "default_ledger_path",
    "load_ledger",
    "record_outcome",
    "save_ledger",
    "top_n",
    "utility_score",
]
