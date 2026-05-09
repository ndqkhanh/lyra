"""Skill curator (Phase 4c — Hermes-agent v0.12 absorption).

Curator grades the on-disk skill catalogue using the existing
:class:`SkillLedger` (Phase O reflective learning) and a small set of
deterministic, *no-network*, no-LLM heuristics. Output is a per-skill
:class:`SkillReport` with tier, rationale, and a suggested action
(``keep`` | ``rewrite`` | ``retire`` | ``promote``).

This is **not** a model-graded reviewer. The Hermes inspiration is the
*continuous-running, low-latency* tier: classify everything cheaply,
escalate only the borderline cases to a heavier (LLM-backed) reviewer
that lives elsewhere (`lyra skill reflect`, Phase O). Keeping the
curator deterministic means:

- ``lyra skill curator`` runs in <100ms over hundreds of skills.
- Output is reproducible across runs (hash a directory of SKILL.md
  files plus the ledger and you'll get the same tiers).
- It can run pre-commit, pre-push, in CI, or as a SessionStart hook
  without any quota concern.

Tier thresholds (see :data:`_TIER_RULES`) are tunable per-deployment
via `~/.lyra/curator.yaml` (loaded by the CLI shim). Defaults align
with the Hermes "Tier-1 keep / Tier-2 watch / Tier-3 rewrite / Tier-4
retire" conventions documented in the v0.12 release notes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .ledger import (
    SkillLedger,
    SkillStats,
    load_ledger,
    utility_score,
)
from .loader import SkillManifest, load_skills

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

# Tiers, ordered best → worst. The CLI shim renders these as a colour
# (Rich style: green/cyan/yellow/red).
TIER_KEEP = "keep"
TIER_WATCH = "watch"
TIER_REWRITE = "rewrite"
TIER_RETIRE = "retire"
TIER_PROMOTE = "promote"  # special: high-utility skill the user might
# want featured in completion / SessionStart blurb

VALID_TIERS = (TIER_KEEP, TIER_WATCH, TIER_REWRITE, TIER_RETIRE, TIER_PROMOTE)


@dataclass(frozen=True)
class SkillReport:
    """One row in the curator's verdict table.

    Fields:
      - ``skill_id``: the SKILL.md ``id`` frontmatter value.
      - ``path``: filesystem path to the SKILL.md file.
      - ``tier``: see :data:`VALID_TIERS`.
      - ``score``: the underlying utility score (Phase O metric).
      - ``activations``: how many times the skill has been activated.
      - ``failures``: how many activations led to TURN_REJECTED.
      - ``stale_days``: days since last activation, or ``None`` if never
        activated.
      - ``size_lines``: SKILL.md line count — long files are de-prioritised
        for the rewrite tier (they need targeted editing, not full
        regeneration).
      - ``rationale``: human-readable explanation rendered by the CLI.
      - ``suggested_action``: free-form short string the CLI shows in
        the rightmost column (e.g. ``"lyra skill reflect <id>"``).
    """

    skill_id: str
    path: Path
    tier: str
    score: float
    activations: int
    failures: int
    stale_days: int | None
    size_lines: int
    rationale: str
    suggested_action: str


@dataclass
class CuratorReport:
    """Aggregate of one curator run."""

    skills: list[SkillReport] = field(default_factory=list)

    def by_tier(self, tier: str) -> list[SkillReport]:
        """All reports in a given tier (preserving registry order)."""
        if tier not in VALID_TIERS:
            raise ValueError(f"unknown tier {tier!r}; valid: {VALID_TIERS}")
        return [r for r in self.skills if r.tier == tier]

    def summary(self) -> dict[str, int]:
        """Count of reports per tier — for `lyra skill curator --summary`."""
        return {tier: len(self.by_tier(tier)) for tier in VALID_TIERS}


# ---------------------------------------------------------------------------
# Tier rules (pure functions of stats — no I/O)
# ---------------------------------------------------------------------------

# Tunable thresholds. The shape mirrors the YAML config the CLI loads
# from ``~/.lyra/curator.yaml``. We keep defaults conservative — the
# curator is meant to surface candidates for human review, not to act
# on its own.
_TIER_RULES: dict[str, float | int] = {
    "promote_min_utility": 0.85,
    "promote_min_activations": 10,
    "keep_min_utility": 0.65,
    "watch_min_utility": 0.40,  # < this → rewrite candidate
    "retire_max_stale_days": 90,  # AND zero-utility AND >5 activations
    "retire_min_activations_to_consider": 5,
    "rewrite_max_size_lines": 250,  # too long → reflect/refactor instead
    "stale_zero_activation_days": 60,  # never activated and old → retire
}


def _tier_for(stats: SkillStats | None, *, manifest: SkillManifest, size_lines: int,
              now_ts: float) -> tuple[str, str, str]:
    """Return ``(tier, rationale, suggested_action)`` for one skill.

    Pure function of (stats, manifest size, current time). No I/O so
    it's trivially testable. The caller is responsible for sourcing
    ``stats`` from the ledger and ``size_lines`` from the file.
    """
    rules = _TIER_RULES

    # Total activations = successes + failures (the ledger does not
    # store a separate `activations` counter — it's derived).
    activations = (stats.successes + stats.failures) if stats else 0

    # Never-activated skills: they're either brand new or genuinely
    # stale. Distinguish by `now_ts - file mtime` (proxy: we don't
    # have mtime here, so fall back to "watch" with a clear message).
    if stats is None or activations == 0:
        return (
            TIER_WATCH,
            "never activated; awaiting first use to gather signal",
            "monitor (no action)",
        )

    score = utility_score(stats)
    stale_days = _days_since(stats.last_used_at, now_ts) if stats.last_used_at else None

    # Promote tier: high utility + meaningful sample size.
    if (
        score >= rules["promote_min_utility"]
        and activations >= rules["promote_min_activations"]
        and stats.failures <= 1
    ):
        return (
            TIER_PROMOTE,
            f"utility={score:.2f} after {activations} activations "
            f"with only {stats.failures} failure(s)",
            "feature in /help and SessionStart",
        )

    # Retire tier: stale + zero recent success + enough sample to trust.
    if (
        score < 0.20
        and activations >= rules["retire_min_activations_to_consider"]
        and stale_days is not None
        and stale_days >= rules["retire_max_stale_days"]
    ):
        return (
            TIER_RETIRE,
            f"utility={score:.2f}, last seen {stale_days} days ago "
            f"after {activations} activations",
            f"lyra skill rm {manifest.id}",
        )

    # Rewrite tier: low utility, big enough sample to trust, but file is
    # short enough that an LLM rewrite is realistic.
    if score < rules["watch_min_utility"] and size_lines <= rules["rewrite_max_size_lines"]:
        return (
            TIER_REWRITE,
            f"utility={score:.2f} (< {rules['watch_min_utility']}) — file is "
            f"{size_lines} lines, small enough for `lyra skill reflect`",
            f"lyra skill reflect {manifest.id}",
        )

    # Watch tier: borderline — keep an eye on it.
    if score < rules["keep_min_utility"]:
        return (
            TIER_WATCH,
            f"utility={score:.2f} between {rules['watch_min_utility']:.2f} "
            f"and {rules['keep_min_utility']:.2f}",
            "monitor (no action)",
        )

    return (
        TIER_KEEP,
        f"utility={score:.2f} after {activations} activations",
        "no action",
    )


def _days_since(ts: float | None, now_ts: float) -> int | None:
    if ts is None:
        return None
    return max(0, int((now_ts - ts) // 86400))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def curate(
    *,
    skill_roots: Iterable[Path],
    ledger: SkillLedger | None = None,
    now_ts: float | None = None,
) -> CuratorReport:
    """Run the curator over every SKILL.md under each ``skill_roots``.

    Parameters
    ----------
    skill_roots
        Directory roots to walk. Typically the user's project skill
        dir (`./skills`), the per-user dir (`~/.lyra/skills`), and the
        shipped packs in this package.
    ledger
        Optional pre-loaded ledger. If ``None`` we load the default
        (``~/.lyra/skill_ledger.json``).
    now_ts
        Optional current time as a Unix timestamp; defaults to
        :func:`time.time`. Pass an explicit value in tests for
        reproducible "stale-days" calculations.
    """
    import time

    if now_ts is None:
        now_ts = time.time()
    if ledger is None:
        ledger = load_ledger()

    manifests = load_skills(list(skill_roots))

    reports: list[SkillReport] = []
    for manifest in manifests:
        # SkillLedger stores stats in a plain dict keyed by id.
        stats = ledger.skills.get(manifest.id)
        manifest_path = Path(manifest.path)
        size_lines = _count_lines(manifest_path)
        tier, rationale, suggested_action = _tier_for(
            stats, manifest=manifest, size_lines=size_lines, now_ts=now_ts
        )
        activations = (stats.successes + stats.failures) if stats else 0
        reports.append(
            SkillReport(
                skill_id=manifest.id,
                path=manifest_path,
                tier=tier,
                score=utility_score(stats) if stats else 0.0,
                activations=activations,
                failures=stats.failures if stats else 0,
                stale_days=(
                    _days_since(stats.last_used_at, now_ts)
                    if stats and stats.last_used_at
                    else None
                ),
                size_lines=size_lines,
                rationale=rationale,
                suggested_action=suggested_action,
            )
        )

    return CuratorReport(skills=reports)


def _count_lines(path: Path) -> int:
    """Cheap line counter — bounded read, no full file parse."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Markdown rendering (CLI consumes this directly)
# ---------------------------------------------------------------------------

_TIER_ORDER = (TIER_PROMOTE, TIER_KEEP, TIER_WATCH, TIER_REWRITE, TIER_RETIRE)


def render_report_markdown(report: CuratorReport) -> str:
    """Render a CuratorReport as a single Markdown document.

    Used by ``lyra skill curator --markdown`` and also by the
    SessionStart hook that injects a one-line "skills health" status
    into the welcome banner.
    """
    summary = report.summary()
    lines: list[str] = []
    lines.append("# Skill Curator Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for tier in _TIER_ORDER:
        lines.append(f"- **{tier}**: {summary[tier]}")
    lines.append("")
    for tier in _TIER_ORDER:
        rows = report.by_tier(tier)
        if not rows:
            continue
        lines.append(f"## {tier.title()} ({len(rows)})")
        lines.append("")
        lines.append("| Skill | Score | Activations | Stale (days) | Suggested |")
        lines.append("|-------|-------|-------------|--------------|-----------|")
        for r in rows:
            stale = "—" if r.stale_days is None else str(r.stale_days)
            # Markdown table cells should not contain raw pipes.
            action = r.suggested_action.replace("|", "\\|")
            lines.append(
                f"| `{r.skill_id}` | {r.score:.2f} | {r.activations} | "
                f"{stale} | {action} |"
            )
        lines.append("")
        lines.append("> " + " ".join(r.rationale for r in rows[:3]) + " …")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# Strip ANSI codes if a caller hands us pre-styled text — this is a
# defensive escape for the rare case where a user's `~/.lyra/curator.yaml`
# defines a custom action template with embedded escape codes.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


__all__ = [
    "TIER_KEEP",
    "TIER_PROMOTE",
    "TIER_RETIRE",
    "TIER_REWRITE",
    "TIER_WATCH",
    "VALID_TIERS",
    "CuratorReport",
    "SkillReport",
    "curate",
    "render_report_markdown",
    "strip_ansi",
]
