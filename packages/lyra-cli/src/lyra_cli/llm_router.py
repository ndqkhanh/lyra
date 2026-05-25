"""Provider-based model routing.

Routes tasks to appropriate models WITHIN a single provider's family.
When user selects Anthropic, routes between opus/sonnet/haiku.
When user selects DeepSeek, routes between v4-pro/v4-flash/chat.

This replaces the old cross-provider task routing which mixed models
from different providers unpredictably.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderModelFamily:
    """Model family for a single provider.

    Maps task types to specific models within the provider's lineup.
    """
    provider: str
    reasoning: str  # Deep analysis, complex tasks
    coding: str     # Implementation, debugging
    quick: str      # Fast lookups, simple questions
    creative: str   # Writing, ideation
    planning: str   # Architecture, strategy


# Provider-specific model families
PROVIDER_FAMILIES: dict[str, ProviderModelFamily] = {
    "anthropic": ProviderModelFamily(
        provider="anthropic",
        reasoning="claude-opus-4.7",
        coding="claude-sonnet-4.6",
        quick="claude-haiku-4.5",
        creative="claude-opus-4.7",
        planning="claude-opus-4.7",
    ),
    "deepseek": ProviderModelFamily(
        provider="deepseek",
        reasoning="deepseek-v4-pro",
        coding="deepseek-v4-flash",
        quick="deepseek-chat",
        creative="deepseek-v4-pro",
        planning="deepseek-v4-pro",
    ),
    "openai": ProviderModelFamily(
        provider="openai",
        reasoning="o3",
        coding="gpt-4o",
        quick="gpt-3.5-turbo",
        creative="gpt-4o",
        planning="o3",
    ),
    "openai-reasoning": ProviderModelFamily(
        provider="openai-reasoning",
        reasoning="o3",
        coding="o3-mini",
        quick="o3-mini",
        creative="o3",
        planning="o3",
    ),
    "gemini": ProviderModelFamily(
        provider="gemini",
        reasoning="gemini-2.5-pro-preview",
        coding="gemini-2.5-pro-preview",
        quick="gemini-2.5-flash",
        creative="gemini-2.5-pro-preview",
        planning="gemini-2.5-pro-preview",
    ),
    "xai": ProviderModelFamily(
        provider="xai",
        reasoning="grok-2-latest",
        coding="grok-2-latest",
        quick="grok-2-latest",
        creative="grok-2-latest",
        planning="grok-2-latest",
    ),
    "groq": ProviderModelFamily(
        provider="groq",
        reasoning="llama-3.3-70b-versatile",
        coding="llama-3.3-70b-versatile",
        quick="llama-3.3-70b-versatile",
        creative="llama-3.3-70b-versatile",
        planning="llama-3.3-70b-versatile",
    ),
    "cerebras": ProviderModelFamily(
        provider="cerebras",
        reasoning="llama-3.3-70b",
        coding="llama-3.3-70b",
        quick="llama-3.3-70b",
        creative="llama-3.3-70b",
        planning="llama-3.3-70b",
    ),
    "mistral": ProviderModelFamily(
        provider="mistral",
        reasoning="mistral-large-latest",
        coding="codestral-latest",
        quick="mistral-small-latest",
        creative="mistral-large-latest",
        planning="mistral-large-latest",
    ),
    "qwen": ProviderModelFamily(
        provider="qwen",
        reasoning="qwen-max",
        coding="qwen-coder-turbo",
        quick="qwen-turbo",
        creative="qwen-max",
        planning="qwen-max",
    ),
    "ollama": ProviderModelFamily(
        provider="ollama",
        reasoning="llama3.1",
        coding="qwen2.5-coder",
        quick="llama3.1",
        creative="llama3.1",
        planning="llama3.1",
    ),
}


# Task detection keywords (unchanged from original)
_TASK_KEYWORDS = {
    "reasoning": (
        "explain", "analyze", "why", "how", "reason", "think",
        "evaluate", "compare", "contrast", "synthesize", "critique",
        "assess", "interpret", "justify", "argue", "debate",
        "implications", "consequences", "philosophy", "ethics",
    ),
    "coding": (
        "implement", "code", "fix", "refactor", "bug", "write",
        "build", "create", "develop", "add", "change", "update",
        "modify", "rewrite", "optimize", "test", "deploy",
        "function", "class", "module", "api", "endpoint",
        "component", "hook", "middleware", "database", "query",
    ),
    "quick": (
        "what", "when", "where", "who", "list", "show", "find",
        "search", "lookup", "define", "definition", "spell",
        "translate", "summarize", "tldr", "quick", "simple",
        "count", "how many", "check", "status",
    ),
    "creative": (
        "write", "draft", "compose", "story", "poem", "essay",
        "blog", "article", "email", "message", "letter",
        "brainstorm", "ideate", "creative", "design", "imagine",
        "generate", "outline", "proposal", "pitch",
    ),
    "planning": (
        "plan", "architecture", "design", "strategy", "roadmap",
        "system", "structure", "organize", "workflow", "pipeline",
        "infrastructure", "scaffold", "template", "framework",
        "pattern", "approach", "methodology", "process",
    ),
}


def detect_task_type(prompt: str) -> str:
    """Detect task type from prompt.

    Returns one of: "reasoning", "coding", "quick", "creative", "planning"
    Defaults to "coding" if no clear match.
    """
    if not prompt or not prompt.strip():
        return "coding"

    lower = prompt.lower().strip()
    words = set(lower.split())

    scores: dict[str, int] = {}

    for task_type, keywords in _TASK_KEYWORDS.items():
        score = 0
        for kw in keywords:
            # Multi-word keywords get higher weight
            if " " in kw:
                if kw in lower:
                    score += 3
            elif kw in words:
                score += 1
        scores[task_type] = score

    # Return task type with highest score, default to coding
    if not scores or max(scores.values()) == 0:
        return "coding"

    return max(scores.items(), key=lambda x: x[1])[0]


def route_model_for_task(prompt: str, provider: str) -> str | None:
    """Route to appropriate model within provider's family.

    Args:
        prompt: User's message
        provider: Active provider key (e.g. "anthropic", "deepseek")

    Returns:
        Model slug for the task, or None if provider not found
    """
    family = PROVIDER_FAMILIES.get(provider)
    if not family:
        return None

    task_type = detect_task_type(prompt)
    return getattr(family, task_type)


def get_provider_family(provider: str) -> ProviderModelFamily | None:
    """Get model family for a provider."""
    return PROVIDER_FAMILIES.get(provider)


def get_provider_default_model(provider: str) -> str | None:
    """Get default model for a provider (coding tier)."""
    family = PROVIDER_FAMILIES.get(provider)
    return family.coding if family else None


__all__ = [
    "ProviderModelFamily",
    "PROVIDER_FAMILIES",
    "detect_task_type",
    "route_model_for_task",
    "get_provider_family",
    "get_provider_default_model",
]
