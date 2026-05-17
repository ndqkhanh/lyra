"""Two-stage detector for spec-worthiness classification."""

from __future__ import annotations
import re
import time
import os
from typing import Any
from functools import lru_cache

from .models import Verdict

# Spec-worthy signals
SPEC_VERBS = r'\b(build|create|implement|design|architect|add)\b'
MULTI_STEP_NOUNS = r'\b(system|module|subsystem|feature|pipeline|framework|integration|engine)\b'
SCOPE_INDICATORS = r'\b(whole|end-to-end|production|mvp|v1)\b'

# Exemption signals
EXEMPT_VERBS = r'\b(fix|patch|update|bump|rename|small|quick|typo|one-liner|run|test|check|show)\b'
FILE_REFERENCE = r'\b(line\s+\d+|\.py|\.ts|\.js|\.md)\b'

THRESHOLD = 0.7
MAX_PROMPT_LENGTH = 10000  # Truncate very long prompts


class Detector:
    """Classifies prompts as spec-worthy or not."""

    def __init__(self, llm_client: Any = None):
        self.llm_client = llm_client
        self._spec_verbs = re.compile(SPEC_VERBS, re.IGNORECASE)
        self._multi_step = re.compile(MULTI_STEP_NOUNS, re.IGNORECASE)
        self._scope = re.compile(SCOPE_INDICATORS, re.IGNORECASE)
        self._exempt = re.compile(EXEMPT_VERBS, re.IGNORECASE)
        self._file_ref = re.compile(FILE_REFERENCE, re.IGNORECASE)

    async def classify(self, prompt: str, active_phase: str = "idle") -> Verdict:
        """Classify prompt as spec-worthy or not."""
        start = time.perf_counter()

        # Truncate very long prompts
        if len(prompt) > MAX_PROMPT_LENGTH:
            prompt = prompt[:MAX_PROMPT_LENGTH]

        # Always-bypass conditions
        if prompt.startswith('/'):
            return Verdict(False, 1.0, "slash command", "slash command", 0)

        if os.getenv('LYRA_AUTOSPEC', 'on') == 'off':
            return Verdict(False, 1.0, "disabled via env", "LYRA_AUTOSPEC=off", 0)

        if active_phase != "idle":
            return Verdict(False, 1.0, "already active", "spec-kit already running", 0)

        # Stage 1: Rule-based (cached)
        confidence = self._rule_based_score_cached(prompt)
        latency = (time.perf_counter() - start) * 1000

        # Clear verdict from rules
        if confidence >= THRESHOLD:
            return Verdict(True, confidence, "rule-based: spec-worthy", None, latency)

        if confidence <= 0.3:
            return Verdict(False, confidence, "rule-based: not spec-worthy",
                         "simple task or query", latency)

        # Stage 2: LLM-assisted (ambiguous band 0.3-0.7)
        if self.llm_client and 0.3 < confidence < THRESHOLD:
            llm_verdict = await self._llm_classify(prompt)
            latency = (time.perf_counter() - start) * 1000
            return Verdict(
                llm_verdict['spec_worthy'],
                llm_verdict['confidence'],
                f"llm-assisted: {llm_verdict['reasoning']}",
                None if llm_verdict['spec_worthy'] else "llm classified as simple",
                latency
            )

        # Default: not spec-worthy
        return Verdict(False, confidence, "below threshold", "insufficient signals", latency)

    @lru_cache(maxsize=128)
    def _rule_based_score_cached(self, prompt: str) -> float:
        """Cached version of rule-based scoring."""
        return self._rule_based_score(prompt)

    def _rule_based_score(self, prompt: str) -> float:
        """Calculate confidence score using heuristics."""
        score = 0.5  # Start at neutral
        words = len(prompt.split())

        # Positive signals
        if self._spec_verbs.search(prompt):
            score += 0.25
        if self._multi_step.search(prompt):
            score += 0.25
        if self._scope.search(prompt):
            score += 0.15
        if words > 80:
            score += 0.2
        elif words > 40:
            score += 0.1

        # Negative signals
        if self._exempt.search(prompt):
            score -= 0.4
        if self._file_ref.search(prompt):
            score -= 0.3
        if words < 10:
            score -= 0.5

        return max(0.0, min(1.0, score))

    async def _llm_classify(self, prompt: str) -> dict:
        """Use LLM for ambiguous cases."""
        # Placeholder - will implement with actual LLM call
        return {
            'spec_worthy': False,
            'confidence': 0.5,
            'reasoning': 'llm not configured'
        }
