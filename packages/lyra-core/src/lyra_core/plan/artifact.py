"""Plan artifact schema and (de)serialisation.

Format is Markdown with YAML frontmatter — human-readable, git-commitable,
machine-parseable. See ``docs/blocks/02-plan-mode.md`` for the full contract.

Phase 4 (v2.1.7) introduces a *tolerant* :func:`load_plan`: real LLMs
don't always emit the strict ``---\\n…---\\n# Plan: …`` shape we
designed for. The tolerant parser walks a cascade — strict first
(fast path), then prose-prefixed strict, then code-fenced YAML, then
JSON, then a ``# Plan:`` header without frontmatter (synthesize fm),
and finally pure prose synthesis. Every fallback emits an HIR
``planner.format_drift`` event so ``lyra doctor`` can surface "your
provider keeps emitting non-canonical plans".
"""
from __future__ import annotations

import hashlib
import json as _json
import re
import time
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class PlanValidationError(Exception):
    """Raised by ``Plan.lint`` or ``load_plan`` when the plan violates invariants."""


class FeatureItem(BaseModel):
    skill: str = Field(..., min_length=1, description="Atomic skill id (e.g. 'edit').")
    description: str = Field(..., min_length=1)

    @field_validator("skill")
    @classmethod
    def _skill_slug(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-\.]+$", v):
            raise ValueError(f"invalid skill slug: {v!r}")
        return v


class Plan(BaseModel):
    # --- frontmatter ------------------------------------------------------
    session_id: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    planner_model: str = Field(..., min_length=1)
    estimated_cost_usd: float = Field(..., ge=0.0)
    goal_hash: str = Field(..., pattern=r"^sha256:[0-9a-fA-F]+$")

    # --- body -------------------------------------------------------------
    title: str = Field(..., min_length=1)
    acceptance_tests: list[str] = Field(default_factory=list)
    expected_files: list[str] = Field(default_factory=list)
    forbidden_files: list[str] = Field(default_factory=list)
    feature_items: list[FeatureItem] = Field(...)
    open_questions: list[str] = Field(default_factory=list)
    notes: str = Field(default="")

    @field_validator("feature_items")
    @classmethod
    def _non_empty(cls, v: list[FeatureItem]) -> list[FeatureItem]:
        if not v:
            raise ValueError("plan must have at least one feature item")
        return v

    # --- invariants not expressible in pydantic field validators ----------

    def lint(self) -> None:
        """Enforce cross-field invariants. See block 02 §Failure modes.

        1. If ``acceptance_tests`` is empty, at least one feature item must
           be a ``test_gen``-style skill.
        2. No duplicate feature items (same ``skill`` + ``description``).
        """
        if not self.acceptance_tests:
            has_test_gen = any(
                it.skill in {"test_gen", "test-gen", "test_generation"}
                for it in self.feature_items
            )
            if not has_test_gen:
                raise PlanValidationError(
                    "plan has no acceptance_tests and no test_gen feature item; "
                    "either list acceptance tests or include a test_gen skill"
                )

        seen: set[tuple[str, str]] = set()
        for it in self.feature_items:
            key = (it.skill, it.description.strip())
            if key in seen:
                raise PlanValidationError(
                    f"duplicate feature item: skill={it.skill!r} "
                    f"description={it.description!r}"
                )
            seen.add(key)


# --------------------------------------------------------------------------
# Markdown ↔ Plan
# --------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+Plan:\s*(.+)$", re.MULTILINE)
_FEATURE_ITEM_RE = re.compile(r"^\s*\d+\.\s+\*\*\(([^)]+)\)\*\*\s+(.+?)\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*-\s+(.+?)\s*$")


def _section(body: str, name: str) -> str:
    """Return the text of section ``## <name>`` up to the next ``##`` header."""
    pat = re.compile(
        rf"^##\s+{re.escape(name)}\s*\n(.*?)(?=^##\s|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pat.search(body)
    return (m.group(1) if m else "").strip("\n")


def _list_items(section_text: str) -> list[str]:
    out: list[str] = []
    for line in section_text.splitlines():
        m = _LIST_ITEM_RE.match(line)
        if m:
            out.append(m.group(1).strip())
    return out


def render_plan(plan: Plan) -> str:
    """Render a Plan as Markdown + YAML frontmatter."""
    fm = {
        "session_id": plan.session_id,
        "created_at": plan.created_at,
        "planner_model": plan.planner_model,
        "estimated_cost_usd": plan.estimated_cost_usd,
        "goal_hash": plan.goal_hash,
    }
    fm_text = yaml.safe_dump(fm, sort_keys=False, default_flow_style=False).strip()

    def _bullets(items: list[str]) -> str:
        if not items:
            return ""
        return "\n".join(f"- {it}" for it in items)

    feature_lines = [
        f"{i}. **({fi.skill})** {fi.description}"
        for i, fi in enumerate(plan.feature_items, start=1)
    ]

    parts = [
        "---",
        fm_text,
        "---",
        "",
        f"# Plan: {plan.title}",
        "",
        "## Acceptance tests",
        _bullets(plan.acceptance_tests),
        "",
        "## Expected files",
        _bullets(plan.expected_files),
        "",
        "## Forbidden files",
        _bullets(plan.forbidden_files),
        "",
        "## Feature items",
        "\n".join(feature_lines),
        "",
        "## Open questions",
        _bullets(plan.open_questions),
        "",
        "## Notes",
        plan.notes.strip(),
        "",
    ]
    return "\n".join(parts) + "\n"


_CODE_FENCE_YAML_RE = re.compile(
    r"^```(?:ya?ml)?\s*\n(.*?)\n```\s*\n(.*)\Z", re.DOTALL | re.MULTILINE
)
_PLAN_HEADER_RE = re.compile(r"^#\s+Plan:\s*(.+)$", re.MULTILINE)


def _emit_format_drift(reason: str) -> None:
    """Emit an HIR event so ``lyra doctor`` can surface format drift."""
    try:
        from lyra_core.hir import events as hir_events

        hir_events.emit("planner.format_drift", reason=reason)
    except Exception:
        # HIR is best-effort; format-drift telemetry must never break parsing.
        pass


def _synth_defaults(*, task_hint: Optional[str], planner_model: str) -> dict[str, Any]:
    """Build a minimal valid frontmatter dict for the synthesizer paths.

    The strict :class:`Plan` schema requires non-empty ``session_id``,
    ``created_at``, ``planner_model``, and a ``sha256:<hex>`` goal_hash.
    We populate them deterministically from the task hint so the same
    prose always yields the same synthesized goal_hash (handy for
    test snapshots and idempotent caches).
    """
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    goal_seed = (task_hint or "synthesized-plan").encode("utf-8")
    goal_hash = "sha256:" + hashlib.sha256(goal_seed).hexdigest()
    return {
        "session_id": f"synth-{int(time.time())}",
        "created_at": now_iso,
        "planner_model": planner_model or "fallback-synth",
        "estimated_cost_usd": 0.0,
        "goal_hash": goal_hash,
    }


def _build_plan_from_body(
    body: str, fm: dict[str, Any]
) -> Plan:
    """Parse a Markdown ``# Plan:`` body using the supplied frontmatter dict.

    Shared between the strict path and the "fenced YAML / synthesized
    frontmatter" paths so we never duplicate the section-walking logic.
    """
    title_m = _TITLE_RE.search(body)
    if not title_m:
        raise PlanValidationError("missing '# Plan: <title>' header")
    title = title_m.group(1).strip()

    acceptance = _list_items(_section(body, "Acceptance tests"))
    expected = _list_items(_section(body, "Expected files"))
    forbidden = _list_items(_section(body, "Forbidden files"))
    features: list[FeatureItem] = []
    for line in _section(body, "Feature items").splitlines():
        fm_item = _FEATURE_ITEM_RE.match(line)
        if fm_item:
            features.append(
                FeatureItem(
                    skill=fm_item.group(1), description=fm_item.group(2)
                )
            )
    questions = _list_items(_section(body, "Open questions"))
    notes = _section(body, "Notes")

    if not features:
        # The Markdown body had a ``# Plan:`` header but no feature items.
        # Synthesize a single ``test_gen`` so the Plan model's
        # non-empty-feature-items invariant holds.
        features = [
            FeatureItem(
                skill="test_gen",
                description=f"Write a failing test for: {title}",
            )
        ]

    try:
        plan = Plan(
            session_id=str(fm.get("session_id", "")),
            created_at=str(fm.get("created_at", "")),
            planner_model=str(fm.get("planner_model", "")),
            estimated_cost_usd=float(fm.get("estimated_cost_usd", 0.0) or 0.0),
            goal_hash=str(fm.get("goal_hash", "")),
            title=title,
            acceptance_tests=acceptance,
            expected_files=expected,
            forbidden_files=forbidden,
            feature_items=features,
            open_questions=questions,
            notes=notes,
        )
    except Exception as e:
        raise PlanValidationError(f"plan construction failed: {e}") from e
    return plan


def _try_strict(text: str) -> Optional[Plan]:
    """Strict-shape parse: ``---\\n…---\\n# Plan: …``.

    Tolerates a prose prefix before the first fence — if the model
    starts with "Sure, here's the plan:" we just chop it off.
    Returns ``None`` (not raises) when the strict shape isn't found
    so callers can fall through to the next strategy.
    """
    idx = text.find("---\n")
    if idx == -1:
        return None
    block = text[idx:]
    m = _FRONTMATTER_RE.match(block)
    if not m:
        return None
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    try:
        return _build_plan_from_body(body, fm)
    except PlanValidationError:
        return None


def _try_code_fenced_yaml(text: str, *, task_hint: Optional[str]) -> Optional[Plan]:
    r"""Detect a ``\`\`\`yaml ... \`\`\``` block followed by a Markdown plan body."""
    m = _CODE_FENCE_YAML_RE.search(text)
    if not m:
        return None
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None
    # Fill in any required field the model omitted (synth defaults
    # never overwrite a present value).
    defaults = _synth_defaults(
        task_hint=task_hint,
        planner_model=str(fm.get("planner_model") or "code-fenced-fm"),
    )
    for k, v in defaults.items():
        fm.setdefault(k, v)
    try:
        plan = _build_plan_from_body(body, fm)
    except PlanValidationError:
        return None
    _emit_format_drift("code_fenced_yaml")
    return plan


def _try_json(text: str, *, task_hint: Optional[str]) -> Optional[Plan]:
    """Detect a JSON object response and translate it into a Plan."""
    stripped = text.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return None
    try:
        data = _json.loads(stripped)
    except _json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    # Accept either a top-level Plan object or ``{"plan": {...}}``.
    payload = data.get("plan", data)
    if not isinstance(payload, dict):
        return None

    defaults = _synth_defaults(
        task_hint=task_hint,
        planner_model=str(payload.get("planner_model") or "json-shape"),
    )
    fm = {
        "session_id": payload.get("session_id") or defaults["session_id"],
        "created_at": payload.get("created_at") or defaults["created_at"],
        "planner_model": payload.get("planner_model") or defaults["planner_model"],
        "estimated_cost_usd": float(
            payload.get("estimated_cost_usd", 0.0) or 0.0
        ),
        "goal_hash": payload.get("goal_hash") or defaults["goal_hash"],
    }

    title = str(payload.get("title", "")).strip() or (task_hint or "Synthesized plan")
    feature_items_raw = payload.get("feature_items") or []
    features: list[FeatureItem] = []
    for item in feature_items_raw:
        if isinstance(item, dict) and item.get("skill") and item.get("description"):
            features.append(
                FeatureItem(
                    skill=str(item["skill"]),
                    description=str(item["description"]),
                )
            )
    if not features:
        features = [
            FeatureItem(
                skill="test_gen",
                description=f"Write a failing test for: {title}",
            )
        ]

    try:
        plan = Plan(
            session_id=str(fm["session_id"]),
            created_at=str(fm["created_at"]),
            planner_model=str(fm["planner_model"]),
            estimated_cost_usd=float(fm["estimated_cost_usd"]),
            goal_hash=str(fm["goal_hash"]),
            title=title,
            acceptance_tests=[
                str(x) for x in (payload.get("acceptance_tests") or [])
            ],
            expected_files=[
                str(x) for x in (payload.get("expected_files") or [])
            ],
            forbidden_files=[
                str(x) for x in (payload.get("forbidden_files") or [])
            ],
            feature_items=features,
            open_questions=[
                str(x) for x in (payload.get("open_questions") or [])
            ],
            notes=str(payload.get("notes") or ""),
        )
    except Exception:
        return None
    _emit_format_drift("json_response")
    return plan


def _try_synthesized_frontmatter(text: str, *, task_hint: Optional[str]) -> Optional[Plan]:
    """Body has ``# Plan: …`` but no frontmatter — synthesize defaults."""
    if not _PLAN_HEADER_RE.search(text):
        return None
    fm = _synth_defaults(task_hint=task_hint, planner_model="synth-no-frontmatter")
    try:
        plan = _build_plan_from_body(text, fm)
    except PlanValidationError:
        return None
    _emit_format_drift("missing_frontmatter")
    return plan


def _synthesize_from_prose(text: str, *, task_hint: Optional[str]) -> Plan:
    """Last-resort: build a minimal Plan from pure prose."""
    summary = text.strip().splitlines()[0] if text.strip() else "(no output)"
    title = (task_hint or summary)[:80] or "Synthesized plan"
    fm = _synth_defaults(task_hint=task_hint, planner_model="prose-synth")
    plan = Plan(
        session_id=str(fm["session_id"]),
        created_at=str(fm["created_at"]),
        planner_model=str(fm["planner_model"]),
        estimated_cost_usd=0.0,
        goal_hash=str(fm["goal_hash"]),
        title=title,
        acceptance_tests=[],
        expected_files=[],
        forbidden_files=[],
        feature_items=[
            FeatureItem(
                skill="test_gen",
                description=f"Write a failing test for: {title}",
            ),
            FeatureItem(
                skill="edit",
                description="Implement the smallest diff that passes the test",
            ),
        ],
        open_questions=[],
        notes=text.strip()[:2000],
    )
    _emit_format_drift("pure_prose")
    return plan


def _extract_plan_block(text: str) -> str:
    """Strict extractor kept for back-compat callers.

    New code should use :func:`load_plan`, which falls through to the
    tolerant cascade. This function still raises when no fence is
    found so existing tests that depend on the strict behaviour stay
    valid.
    """
    idx = text.find("---\n")
    if idx == -1:
        raise PlanValidationError("plan block not found (no '---' frontmatter fence)")
    return text[idx:]


def load_plan(text: str, *, task_hint: Optional[str] = None) -> Plan:
    """Parse a plan artifact text back into a :class:`Plan`.

    The parser walks a cascade of progressively-looser strategies
    (strict frontmatter → prose-prefixed strict → code-fenced YAML →
    JSON object → no-frontmatter Markdown → pure prose). Every
    fallback emits a ``planner.format_drift`` HIR event so the
    operator can see when their provider is stretching the format.

    Args:
        text: Raw model output as returned by :class:`AgentLoop`.
        task_hint: Original task description, used to build a sensible
            title and goal_hash in the synthesizing fallbacks. Pass
            it whenever you have it; absence isn't fatal.

    Raises:
        PlanValidationError: ``text`` is empty/whitespace-only.
    """
    if not text or not text.strip():
        raise PlanValidationError("plan input is empty")

    for strategy in (
        _try_strict,
    ):
        plan = strategy(text)
        if plan is not None:
            return plan

    for strategy_with_hint in (
        _try_code_fenced_yaml,
        _try_json,
        _try_synthesized_frontmatter,
    ):
        plan = strategy_with_hint(text, task_hint=task_hint)
        if plan is not None:
            return plan

    return _synthesize_from_prose(text, task_hint=task_hint)
