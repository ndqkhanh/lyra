"""
Provider-Agnostic Skill Bridge — ensures skills work across all LLM providers.

Validates that loaded skills are provider-agnostic and can be injected into
any provider's message format via the lyra-provider abstraction layer.

Key concerns (from plan §4.4 multi-provider requirements):
1. Skills are harness-level, not provider-API-level
2. Skill selection uses deterministic matching as fallback (not just model auto-trigger)
3. Provider-specific frontmatter is stripped/translated for non-Claude providers
4. Progressive disclosure: metadata → body → references

Usage::

    from lyra_skills.provider_bridge import ProviderSkillBridge
    bridge = ProviderSkillBridge()
    compatible = bridge.validate_for_provider(skill_content, provider="deepseek")
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Claude-specific SKILL.md frontmatter fields that should be stripped
# or translated when running on non-Claude providers.
CLAUDE_ONLY_FRONTMATTER: frozenset[str] = frozenset({
    "model",           # Model pin (Claude-specific model IDs)
    "subagent",        # Claude Code subagent execution
    "dynamic_inject",  # Claude Code dynamic context injection
})


class ProviderSkillBridge:
    """
    Validates and translates skills for cross-provider compatibility.

    Skills are authored in the Agent Skills open standard (SKILL.md format).
    This bridge ensures they work on any provider by:
    - Stripping Claude-only frontmatter for non-Claude providers
    - Validating that skills don't depend on provider-specific behavior
    - Providing a deterministic matching fallback for providers with weak auto-trigger
    """

    def validate_for_provider(self, skill_content: str, provider: str) -> tuple[bool, list[str]]:
        """
        Validate that a skill is compatible with a given provider.

        Returns (is_compatible, warnings).
        """
        warnings: list[str] = []

        # Check for Claude-only frontmatter
        for field in CLAUDE_ONLY_FRONTMATTER:
            if f"{field}:" in skill_content.lower():
                if provider != "anthropic" and provider != "openrouter":
                    warnings.append(
                        f"Skill uses Claude-only field '{field}' — will be ignored on provider '{provider}'"
                    )

        # DeepSeek/GPT don't reliably auto-trigger skills from description alone
        if provider in ("deepseek", "openai", "google"):
            if "trigger:" not in skill_content.lower() and "keywords:" not in skill_content.lower():
                warnings.append(
                    f"Skill lacks 'trigger:' or 'keywords:' frontmatter — "
                    f"auto-trigger on '{provider}' may be unreliable. "
                    f"Consider adding explicit keyword triggers."
                )

        return len(warnings) == 0 or all("will be ignored" in w for w in warnings), warnings

    @staticmethod
    def strip_claude_frontmatter(skill_content: str, provider: str) -> str:
        """
        Remove Claude-only frontmatter fields for non-Claude providers.

        This ensures the skill doesn't confuse non-Claude models with
        fields they don't understand.
        """
        if provider in ("anthropic", "openrouter"):
            return skill_content

        lines = skill_content.split("\n")
        result: list[str] = []
        for line in lines:
            stripped = line.strip().lower()
            should_skip = any(
                stripped.startswith(f"{field}:") for field in CLAUDE_ONLY_FRONTMATTER
            )
            if not should_skip:
                result.append(line)

        return "\n".join(result)

    @staticmethod
    def get_trigger_strategy(provider: str) -> str:
        """
        Return the recommended skill trigger strategy for a provider.

        - Anthropic: model auto-trigger is reliable (strong instruction following)
        - DeepSeek: deterministic keyword matching recommended as primary
        - OpenAI: mixed — keyword + model auto-trigger
        - Google: keyword matching recommended
        - Open-weights: keyword matching ONLY (no auto-trigger reliability)
        """
        strategies: dict[str, str] = {
            "anthropic": "auto_trigger",
            "openrouter": "auto_trigger",
            "deepseek": "keyword_primary",
            "openai": "keyword_and_auto",
            "google": "keyword_primary",
            "openweights": "keyword_only",
        }
        return strategies.get(provider, "keyword_primary")
