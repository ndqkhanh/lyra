"""Phase 2 verifier: LLM-judge rubric scoring."""
from __future__ import annotations

import enum
import json
import re
from dataclasses import dataclass
from typing import Callable


class SubjectiveVerdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_MORE = "needs_more"


@dataclass
class SubjectiveResult:
    verdict: SubjectiveVerdict
    score: float
    notes: str


JudgeFn = Callable[[str], str]


_PROMPT = """You are a code reviewer. Score the agent's work against the rubric.

Rubric:
{rubric}

Evidence summary:
{evidence}

Return a single JSON object with keys:
    verdict (PASS | FAIL | NEEDS_MORE)
    score   (float 0..1)
    notes   (short string)
"""


def _parse(output: str) -> SubjectiveResult:
    try:
        obj = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        # Try extracting the first JSON-looking substring.
        m = re.search(r"\{.*\}", output, re.DOTALL)
        if not m:
            return SubjectiveResult(
                verdict=SubjectiveVerdict.NEEDS_MORE,
                score=0.0,
                notes=f"judge output not JSON; got: {output[:60]!r}",
            )
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return SubjectiveResult(
                verdict=SubjectiveVerdict.NEEDS_MORE,
                score=0.0,
                notes="judge output had invalid JSON",
            )

    raw = str(obj.get("verdict", "")).upper().strip()
    try:
        verdict = SubjectiveVerdict(raw.lower())
    except ValueError:
        verdict = SubjectiveVerdict.NEEDS_MORE

    try:
        score = float(obj.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(1.0, score))

    notes = str(obj.get("notes", ""))
    return SubjectiveResult(verdict=verdict, score=score, notes=notes)


def verify_subjective(
    *,
    rubric: str,
    evidence_summary: str,
    judge_llm: JudgeFn,
) -> SubjectiveResult:
    prompt = _PROMPT.format(rubric=rubric, evidence=evidence_summary)
    raw = judge_llm(prompt)
    return _parse(raw or "")
