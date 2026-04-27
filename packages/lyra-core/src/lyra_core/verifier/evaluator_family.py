"""Evaluator family detection for degraded-eval tagging.

Running evaluator and agent in the same model family is a known failure mode
(the judge rubber-stamps the agent). We surface this as ``degraded_eval=same_family``.
"""
from __future__ import annotations

import enum


class EvaluatorFamily(str, enum.Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    META = "meta"
    MISTRAL = "mistral"
    UNKNOWN = "unknown"


_VENDOR_MAP = {
    "anthropic": EvaluatorFamily.ANTHROPIC,
    "claude": EvaluatorFamily.ANTHROPIC,
    "openai": EvaluatorFamily.OPENAI,
    "gpt": EvaluatorFamily.OPENAI,
    "o1": EvaluatorFamily.OPENAI,
    "google": EvaluatorFamily.GOOGLE,
    "gemini": EvaluatorFamily.GOOGLE,
    "meta": EvaluatorFamily.META,
    "llama": EvaluatorFamily.META,
    "mistral": EvaluatorFamily.MISTRAL,
}


def detect_family(model_id: str) -> EvaluatorFamily:
    lower = model_id.lower()
    for needle, family in _VENDOR_MAP.items():
        if needle in lower:
            return family
    return EvaluatorFamily.UNKNOWN


def is_degraded_eval(*, agent_model: str, judge_model: str) -> bool:
    return detect_family(agent_model) is detect_family(judge_model)
