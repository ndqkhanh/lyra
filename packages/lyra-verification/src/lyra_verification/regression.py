"""Layer 3 — Offline Deep: Agent Regression Testing.

Implements:
- Behavioral fingerprinting from agent outputs
- Cosine-similarity-based regression detection
- SPRT (Sequential Probability Ratio Test) for statistical regression
- Regression power estimation
- Full regression suite execution
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence

from lyra_verification.models import (
    BehavioralFingerprint,
    RegressionVerdict,
)

logger = logging.getLogger(__name__)

# Default metrics extracted from agent outputs
_FINGERPRINT_METRICS = [
    "avg_response_length",
    "vocab_diversity",
    "avg_sentence_length",
    "pronoun_ratio",
    "hedging_ratio",
    "uncertainty_ratio",
    "list_ratio",
    "code_block_ratio",
]


class AgentRegressionTester:
    """Regression testing for agent behavioural changes.

    Compares a baseline agent session's behavioural fingerprint against
    a current run to detect regressions — unintended changes in style,
    content patterns, or quality.
    """

    def create_behavioral_fingerprint(
        self,
        agent_outputs: Sequence[str],
    ) -> BehavioralFingerprint:
        """Build a behavioural profile from a sequence of agent outputs.

        Extracts a set of summary statistics (fingerprint metrics)
        that characterise the agent's behaviour.
        """
        if not agent_outputs:
            return BehavioralFingerprint(metrics={}, sample_size=0)

        all_text = " ".join(agent_outputs)
        words = all_text.split()
        n_words = len(words)

        if n_words == 0:
            return BehavioralFingerprint(metrics={}, sample_size=len(agent_outputs))

        # Average response length
        avg_response_length = sum(len(o.split()) for o in agent_outputs) / len(agent_outputs)

        # Vocabulary diversity
        unique_words = len({w.lower() for w in words})
        vocab_diversity = unique_words / max(n_words, 1)

        # Average sentence length (split on sentence boundaries)
        sentences = [
            s.strip()
            for out in agent_outputs
            for s in out.replace("!", ".").replace("?", ".").split(".")
            if s.strip()
        ]
        avg_sentence_length = (
            sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        )

        # Pronoun ratio
        pronouns = {"i", "you", "he", "she", "it", "we", "they",
                     "me", "him", "her", "us", "them",
                     "my", "your", "his", "its", "our", "their"}
        pronoun_count = sum(1 for w in words if w.lower() in pronouns)
        pronoun_ratio = pronoun_count / n_words

        # Hedging ratio
        hedges = {"maybe", "perhaps", "possibly", "might", "could",
                   "seems", "appears", "likely", "probably", "sort of",
                   "kind of", "i think", "i believe"}
        hedging_count = sum(1 for w in words if w.lower() in hedges)
        hedging_ratio = hedging_count / n_words

        # Uncertainty ratio
        uncertainty_words = {"unclear", "uncertain", "unknown", "ambiguous",
                              "unlikely", "questionable", "speculative",
                              "tentative", "hypothetical", "presumably"}
        uncertainty_count = sum(1 for w in words if w.lower() in uncertainty_words)
        uncertainty_ratio = uncertainty_count / n_words

        # List ratio
        list_lines = sum(
            1 for out in agent_outputs
            for line in out.split("\n")
            if line.strip().startswith(("-", "*", "1.", "2.", "3."))
        )
        total_lines = sum(1 for out in agent_outputs for line in out.split("\n"))
        list_ratio = list_lines / max(total_lines, 1)

        # Code block ratio
        code_blocks = 0
        in_block = False
        for out in agent_outputs:
            for line in out.split("\n"):
                if line.strip().startswith("```"):
                    in_block = not in_block
                    code_blocks += 1
        code_block_ratio = code_blocks / max(len(agent_outputs), 1)

        metrics = {
            "avg_response_length": avg_response_length,
            "vocab_diversity": vocab_diversity,
            "avg_sentence_length": avg_sentence_length,
            "pronoun_ratio": pronoun_ratio,
            "hedging_ratio": hedging_ratio,
            "uncertainty_ratio": uncertainty_ratio,
            "list_ratio": list_ratio,
            "code_block_ratio": code_block_ratio,
        }

        return BehavioralFingerprint(
            metrics=metrics,
            sample_size=len(agent_outputs),
        )

    def compare_fingerprints(
        self,
        baseline: BehavioralFingerprint,
        current: BehavioralFingerprint,
        threshold: float = 0.85,
    ) -> tuple[bool, float, dict[str, float]]:
        """Detect regression between two fingerprints.

        Parameters
        ----------
        baseline : BehavioralFingerprint
            The reference fingerprint.
        current : BehavioralFingerprint
            The fingerprint under test.
        threshold : float
            Minimum cosine similarity to pass (default 0.85).

        Returns
        -------
        passed : bool
            True if similarity >= threshold.
        similarity : float
            Cosine similarity between fingerprints.
        per_metric_changes : dict
            Relative change for each shared metric.
        """
        similarity = baseline.cosine_similarity(current)

        per_metric_changes: dict[str, float] = {}
        all_keys = set(baseline.metrics) | set(current.metrics)
        for key in all_keys:
            b = baseline.metrics.get(key, 0.0)
            c = current.metrics.get(key, 0.0)
            if b != 0.0:
                per_metric_changes[key] = (c - b) / abs(b)
            else:
                per_metric_changes[key] = c if c != 0.0 else 0.0

        passed = similarity >= threshold
        return passed, similarity, per_metric_changes

    def statistical_test(
        self,
        baseline: Sequence[float],
        current: Sequence[float],
        alpha: float = 0.05,
        beta: float = 0.20,
        delta: float = 0.1,
    ) -> tuple[bool, float, int]:
        """SPRT (Sequential Probability Ratio Test) for regression.

        Parameters
        ----------
        baseline : sequence of float
            Baseline metric values.
        current : sequence of float
            Current metric values.
        alpha : float
            Type I error rate (default 0.05).
        beta : float
            Type II error rate (default 0.20).
        delta : float
            Minimum detectable effect size (default 0.1).

        Returns
        -------
        regression_detected : bool
            True if SPRT rejects the null (no regression).
        log_likelihood_ratio : float
            Cumulative LLR.
        n_samples : int
            Number of samples consumed.
        """
        if not baseline or not current:
            return False, 0.0, 0

        # Pooled variance estimate
        n_b, n_c = len(baseline), len(current)
        mean_b = sum(baseline) / n_b
        mean_c = sum(current) / n_c
        var_b = sum((x - mean_b) ** 2 for x in baseline) / max(n_b - 1, 1)
        var_c = sum((x - mean_c) ** 2 for x in current) / max(n_c - 1, 1)
        pooled_var = ((n_b - 1) * var_b + (n_c - 1) * var_c) / max(n_b + n_c - 2, 1)

        # Guard against degenerate (near-)zero variance
        if pooled_var < 1e-12:
            return abs(mean_c - mean_b) > delta, 0.0, min(n_b, n_c)

        # SPRT boundaries
        a = math.log(beta / (1.0 - alpha))
        b = math.log((1.0 - beta) / alpha)

        # Sequential LLR: paired difference test H0: mu=0 vs H1: mu=delta
        log_likelihood_ratio = 0.0
        n_samples = 0
        for x_b, x_c in zip(baseline, current, strict=False):
            n_samples += 1
            diff = x_c - x_b
            log_likelihood_ratio += (
                delta * (diff - delta / 2.0) / (pooled_var + 1e-12)
            )

            if log_likelihood_ratio >= b:
                return True, log_likelihood_ratio, n_samples
            if log_likelihood_ratio <= a:
                return False, log_likelihood_ratio, n_samples

        # Inconclusive — fall back to effect size check
        effect = abs(mean_c - mean_b) / max(math.sqrt(pooled_var), 1e-10)
        return effect > delta / 2.0, log_likelihood_ratio, n_samples

    def compute_regression_power(
        self,
        n_samples: int,
        effect_size: float = 0.5,
        alpha: float = 0.05,
    ) -> float:
        """Compute statistical power for regression detection.

        Uses a simplified power formula for a two-sided t-test.
        Returns a value in [0, 1].
        """
        if n_samples < 2 or effect_size <= 0:
            return 0.0

        # Non-centrality parameter
        ncp = effect_size * math.sqrt(n_samples)

        # Approximate power via z-test simplification
        z_alpha = 1.96  # two-sided, alpha=0.05
        power = 1.0 - 0.5 * math.erfc((ncp - z_alpha) / math.sqrt(2))
        return max(0.0, min(power, 1.0))

    def run_regression_suite(
        self,
        agent_fn: Callable[..., str],
        test_cases: Sequence[str],
        baseline_fingerprint: BehavioralFingerprint | None = None,
    ) -> tuple[list[RegressionVerdict], BehavioralFingerprint]:
        """Run a full regression test suite.

        Parameters
        ----------
        agent_fn : callable
            Function that takes a prompt (str) and returns a response (str).
        test_cases : sequence of str
            Prompts to evaluate.
        baseline_fingerprint : BehavioralFingerprint, optional
            The reference fingerprint. If None, the current run becomes
            the baseline (no regression check possible).

        Returns
        -------
        verdicts : list of RegressionVerdict
            Per-test-case results.
        current_fingerprint : BehavioralFingerprint
            Fingerprint from the current run.
        """
        outputs: list[str] = []
        verdicts: list[RegressionVerdict] = []

        for prompt in test_cases:
            try:
                response = agent_fn(prompt)
            except Exception as exc:
                logger.error("Agent failed on prompt %r: %s", prompt[:50], exc)
                verdicts.append(
                    RegressionVerdict(
                        test_name=f"prompt_{prompt[:30]}",
                        passed=False,
                        similarity=0.0,
                        details=f"Agent raised exception: {exc}",
                    )
                )
                continue

            outputs.append(response)
            verdicts.append(
                RegressionVerdict(
                    test_name=f"prompt_{prompt[:30]}",
                    passed=True,
                    similarity=1.0,
                    details="response generated successfully",
                )
            )

        current_bp = self.create_behavioral_fingerprint(outputs)

        # Cross-check against baseline if provided
        if baseline_fingerprint is not None and outputs:
            passed, similarity, changes = self.compare_fingerprints(
                baseline_fingerprint, current_bp
            )
            verdicts.append(
                RegressionVerdict(
                    test_name="overall_fingerprint",
                    passed=passed,
                    similarity=similarity,
                    details=f"similarity={similarity:.4f}, changes={changes}",
                )
            )

        return verdicts, current_bp
