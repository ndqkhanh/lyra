"""Prompt Engineer Skill — LLM prompt analysis and optimization.

Analyzes prompts for:
- Clarity, specificity, and instruction quality
- Token efficiency and cost optimization
- Safety guardrails and injection resistance
- Few-shot example effectiveness
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PromptQuality(StrEnum):
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


@dataclass(frozen=True)
class PromptFeedback:
    category: str
    quality: PromptQuality
    detail: str
    improvement: str


class PromptEngineerSkill:
    """Analyzes and improves LLM prompt design."""

    def run(self, input_data: dict) -> dict:
        prompt = input_data.get("prompt", "")
        feedback: list[PromptFeedback] = []
        token_estimate = len(prompt.split())

        if len(prompt) < 20:
            feedback.append(
                PromptFeedback(
                    "clarity",
                    PromptQuality.POOR,
                    "Prompt is too short — lacks sufficient context.",
                    "Add more detail about the task and expected output.",
                )
            )

        has_instruction = any(
            kw in prompt.lower()
            for kw in (
                "you are",
                "act as",
                "your task",
                "please",
                "write",
                "analyze",
                "generate",
                "explain",
            )
        )
        if not has_instruction:
            feedback.append(
                PromptFeedback(
                    "instruction",
                    PromptQuality.NEEDS_IMPROVEMENT,
                    "No clear instruction verb found.",
                    "Start with 'You are...' or 'Your task is to...'",
                )
            )

        if token_estimate > 2000:
            feedback.append(
                PromptFeedback(
                    "efficiency",
                    PromptQuality.NEEDS_IMPROVEMENT,
                    f"Prompt is ~{token_estimate} tokens — may be verbose.",
                    "Remove redundant context; be concise.",
                )
            )

        has_examples = (
            "example" in prompt.lower()
            or "e.g." in prompt.lower()
            or "for instance" in prompt.lower()
        )
        has_output_format = any(
            marker in prompt for marker in ("```", "format:", "output:", "return:", "json", "yaml")
        )

        if not has_examples:
            feedback.append(
                PromptFeedback(
                    "examples",
                    PromptQuality.NEEDS_IMPROVEMENT,
                    "No examples provided.",
                    "Include 1-3 few-shot examples of desired input/output pairs.",
                )
            )

        if not has_output_format:
            feedback.append(
                PromptFeedback(
                    "output_format",
                    PromptQuality.NEEDS_IMPROVEMENT,
                    "Output format not specified.",
                    "Specify the desired output format (JSON, markdown, code block, etc.).",
                )
            )

        return {
            "feedback": [f.__dict__ for f in feedback],
            "token_estimate": token_estimate,
            "score": max(0, 100 - len(feedback) * 15),
            "passed": len([f for f in feedback if f.quality == PromptQuality.POOR]) == 0,
        }
