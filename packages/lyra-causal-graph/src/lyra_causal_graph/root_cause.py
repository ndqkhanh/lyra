"""Root cause analysis — causal chain traversal, attribution, and intervention recommendation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .causal_graph import CausalGraph, EdgeType
from .errors import RootCauseError

logger = logging.getLogger(__name__)

__all__ = [
    "RootCause",
    "AttributionScore",
    "RootCauseConfig",
    "RootCauseAnalyzer",
]


# ── Data Types ────────────────────────────────────────────────────────────────


@dataclass
class RootCause:
    """A candidate root cause with attribution and supporting evidence.

    Attributes:
        node_id: The identified root cause node.
        score: Overall attribution score [0, 1].
        causal_path: List of nodes from root to the effect.
        explanation: Human-readable causal explanation.
        recommended_interventions: Suggested actions to address the root cause.
        evidence: Supporting causal evidence.
    """

    node_id: str
    score: float
    causal_path: list[str] = field(default_factory=list)
    explanation: str = ""
    recommended_interventions: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"RootCause({self.node_id}, score={self.score:.3f})"


@dataclass
class AttributionScore:
    """Attribution contribution for a specific causal factor.

    Attributes:
        factor: Name of the causal factor (node).
        contribution: Marginal contribution to the effect [0, 1].
        indirect: Whether the contribution is via an intermediate node.
        path: Causal path from factor to effect.
    """

    factor: str
    contribution: float
    indirect: bool = False
    path: list[str] = field(default_factory=list)


@dataclass
class RootCauseConfig:
    """Configuration for root cause analysis.

    Attributes:
        max_path_length: Maximum causal chain length to explore.
        min_attribution_threshold: Minimum score for reporting a root cause.
        top_k: Maximum number of root causes to return.
        anomaly_sensitivity: Z-score threshold for anomaly detection.
        use_transfer_entropy: Whether to incorporate TE in scoring.
        random_seed: Seed for reproducibility.
    """

    max_path_length: int = 10
    min_attribution_threshold: float = 0.05
    top_k: int = 5
    anomaly_sensitivity: float = 2.0
    use_transfer_entropy: bool = True
    random_seed: int | None = None


# ── Root Cause Analyzer ──────────────────────────────────────────────────────


class RootCauseAnalyzer:
    """Analyze causal graphs to identify root causes, attribute scores,
    and recommend interventions.

    The analyzer performs:
    1. Causal chain traversal from observed effects to potential root causes
    2. Attribution scoring based on causal strength and path structure
    3. Correlation of anomalies with causal paths
    4. Prioritized intervention recommendations

    Typical usage::

        analyzer = RootCauseAnalyzer()
        causes = analyzer.find_root_causes(graph, effect_node="Y")
        for cause in causes:
            print(f"{cause.node_id}: {cause.score:.3f} — {cause.explanation}")
    """

    def __init__(self, config: RootCauseConfig | None = None) -> None:
        self._config = config or RootCauseConfig()

    @property
    def config(self) -> RootCauseConfig:
        return self._config

    # ── Root Cause Discovery ─────────────────────────────────────────────

    def find_root_causes(
        self,
        graph: CausalGraph,
        effect_node: str,
        data: dict[str, np.ndarray] | None = None,
    ) -> list[RootCause]:
        """Identify candidate root causes for an observed effect.

        Traverses the causal graph backwards from the effect node,
        scoring each ancestor as a potential root cause.

        Args:
            graph: The causal graph to analyze.
            effect_node: The node whose causes we seek.
            data: Optional observational data for evidence-based scoring.

        Returns:
            List of ``RootCause`` candidates sorted by score (descending).
        """
        if effect_node not in graph.nodes:
            raise RootCauseError(f"Effect node '{effect_node}' not found in graph.")

        ancestors = graph.ancestors(effect_node)
        ancestors.discard(effect_node)

        if not ancestors:
            logger.warning("No ancestors found for effect node '%s'.", effect_node)
            return []

        candidates: list[RootCause] = []

        for ancestor in sorted(ancestors):
            paths = graph.find_all_paths(ancestor, effect_node, self._config.max_path_length)
            if not paths:
                continue

            best_path = self._select_best_path(graph, paths)
            score = self._score_root_cause(graph, ancestor, effect_node, best_path, data)
            explanation = self._build_explanation(graph, ancestor, effect_node, best_path, score)
            interventions = self._recommend_interventions(graph, ancestor, effect_node)

            candidates.append(
                RootCause(
                    node_id=ancestor,
                    score=score,
                    causal_path=best_path,
                    explanation=explanation,
                    recommended_interventions=interventions,
                    evidence={
                        "num_paths": len(paths),
                        "path_lengths": [len(p) for p in paths],
                    },
                )
            )

        # Sort by score descending, apply threshold and top-k
        candidates.sort(key=lambda rc: rc.score, reverse=True)
        candidates = [rc for rc in candidates if rc.score >= self._config.min_attribution_threshold]
        candidates = candidates[: self._config.top_k]

        logger.info(
            "Found %d root causes for '%s' (threshold=%.3f)",
            len(candidates),
            effect_node,
            self._config.min_attribution_threshold,
        )
        return candidates

    def _select_best_path(self, graph: CausalGraph, paths: list[list[str]]) -> list[str]:
        """Select the most significant causal path from a list.

        Criteria: shorter paths preferred; ties broken by edge strength.
        """
        if not paths:
            return []

        best_path = paths[0]
        best_score = self._path_score(graph, best_path)

        for path in paths[1:]:
            score = self._path_score(graph, path)
            if score > best_score:
                best_score = score
                best_path = path

        return best_path

    def _path_score(self, graph: CausalGraph, path: list[str]) -> float:
        """Score a causal path based on edge strengths and length."""
        if len(path) < 2:
            return 0.0

        total_strength = 1.0
        for i in range(len(path) - 1):
            edge = graph.get_edge(path[i], path[i + 1])
            strength = edge.strength if edge else 0.0
            total_strength *= 0.5 + 0.5 * strength

        # Penalize longer paths slightly
        length_penalty = 1.0 / np.sqrt(len(path))
        return total_strength * length_penalty

    def _score_root_cause(
        self,
        graph: CausalGraph,
        ancestor: str,
        effect: str,
        path: list[str],
        data: dict[str, np.ndarray] | None,
    ) -> float:
        """Compute attribution score for a candidate root cause.

        Combines:
        - Path strength (product of edge strengths along path)
        - Path length penalty (shorter path = more direct cause)
        - Anomaly correlation (if data is provided)
        - Causal connectivity (number of unique paths)
        """
        score = self._path_score(graph, path)

        # Number of paths bonus
        all_paths = len(graph.find_all_paths(ancestor, effect, self._config.max_path_length))
        connectivity_bonus = min(0.2, 0.05 * all_paths)
        score += connectivity_bonus

        # Anomaly correlation
        if data is not None and ancestor in data and effect in data:
            anomaly_score = self._anomaly_correlation(data[ancestor], data[effect])
            score = 0.7 * score + 0.3 * anomaly_score

        # Direct connection bonus
        edge = graph.get_edge(ancestor, effect)
        if edge is not None:
            score = 0.7 * score + 0.3 * edge.strength

        return float(np.clip(score, 0.0, 1.0))

    def _anomaly_correlation(self, cause_data: np.ndarray, effect_data: np.ndarray) -> float:
        """Score how strongly anomalies in cause align with anomalies in effect.

        An anomaly is defined as a value exceeding z-score threshold.
        """
        min_len = min(len(cause_data), len(effect_data))
        if min_len < 10:
            return 0.5

        cause_z = np.abs(
            (cause_data[:min_len] - np.mean(cause_data[:min_len]))
            / (np.std(cause_data[:min_len]) + 1e-10)
        )
        effect_z = np.abs(
            (effect_data[:min_len] - np.mean(effect_data[:min_len]))
            / (np.std(effect_data[:min_len]) + 1e-10)
        )

        threshold = self._config.anomaly_sensitivity
        cause_anom = cause_z > threshold
        effect_anom = effect_z > threshold

        if cause_anom.sum() == 0:
            return 0.0

        # Precision: given cause anomaly, how often is effect anomalous?
        precision = (cause_anom & effect_anom).sum() / cause_anom.sum()
        return float(precision)

    # ── Attribution ──────────────────────────────────────────────────────

    def attribute(
        self,
        graph: CausalGraph,
        effect_node: str,
        data: dict[str, np.ndarray] | None = None,
    ) -> list[AttributionScore]:
        """Compute attribution scores for all causal factors of an effect.

        Uses a Shapley-inspired marginal contribution approach:
        each ancestor's contribution is proportional to the path
        strength from it to the effect, normalized across all ancestors.

        Args:
            graph: The causal graph.
            effect_node: The node to attribute causes for.
            data: Optional data for empirical attribution.

        Returns:
            List of ``AttributionScore`` sorted by contribution (descending).
        """
        ancestors = graph.ancestors(effect_node)
        ancestors.discard(effect_node)

        if not ancestors:
            return []

        scores: list[AttributionScore] = []
        raw_scores: dict[str, float] = {}

        for ancestor in sorted(ancestors):
            paths = graph.find_all_paths(ancestor, effect_node, self._config.max_path_length)
            if not paths:
                continue

            best_path = self._select_best_path(graph, paths)
            contribution = self._path_score(graph, best_path)
            raw_scores[ancestor] = contribution

            scores.append(
                AttributionScore(
                    factor=ancestor,
                    contribution=contribution,
                    indirect=len(best_path) > 2,  # more than direct edge
                    path=best_path,
                )
            )

        # Normalize contributions to sum to 1
        total = sum(s.contribution for s in scores)
        if total > 0:
            for s in scores:
                s.contribution /= total

        scores.sort(key=lambda s: s.contribution, reverse=True)
        return scores

    # ── Intervention Recommendation ──────────────────────────────────────

    def _recommend_interventions(
        self,
        graph: CausalGraph,
        root_cause: str,
        effect_node: str,
    ) -> list[str]:
        """Generate intervention recommendations based on causal structure.

        Args:
            graph: The causal graph.
            root_cause: The identified root cause node.
            effect_node: The downstream effect.

        Returns:
            List of recommended intervention descriptions.
        """
        recommendations: list[str] = []

        paths = graph.find_all_paths(root_cause, effect_node, self._config.max_path_length)

        # Direct connection
        direct_edge = graph.get_edge(root_cause, effect_node)
        if direct_edge is not None:
            recommendations.append(
                f"Directly modulate '{root_cause}' to influence '{effect_node}' "
                f"(edge strength: {direct_edge.strength:.2f})"
            )

        # Mediator-based intervention
        for path in paths:
            if len(path) >= 3:
                mediator = path[1]
                recommendations.append(
                    f"Intervene on mediator '{mediator}' to block "
                    f"causal path {root_cause} -> {' -> '.join(path[1:])}"
                )
                break  # only suggest the first mediator

        # If root_cause is a confounder
        for _edge_id, edge in graph.edges.items():
            if edge.edge_type == EdgeType.BIDIRECTED and root_cause in (
                edge.source_id,
                edge.target_id,
            ):
                other = edge.target_id if edge.source_id == root_cause else edge.source_id
                recommendations.append(
                    f"Control for unobserved confounder between '{root_cause}' and '{other}'"
                )

        if not recommendations:
            recommendations.append(
                f"Monitor '{root_cause}' as a potential upstream factor of '{effect_node}'"
            )

        return recommendations

    # ── Explanation ──────────────────────────────────────────────────────

    def _build_explanation(
        self,
        graph: CausalGraph,
        root_cause: str,
        effect_node: str,
        path: list[str],
        score: float,
    ) -> str:
        """Build a human-readable causal explanation string."""
        node = graph.nodes.get(root_cause)
        root_name = node.name if node else root_cause

        effect_node_obj = graph.nodes.get(effect_node)
        effect_name = effect_node_obj.name if effect_node_obj else effect_node

        path_desc = " -> ".join(path)

        if score > 0.7:
            strength_desc = "strongly"
        elif score > 0.4:
            strength_desc = "moderately"
        else:
            strength_desc = "weakly"

        return (
            f"'{root_name}' is a {strength_desc} contributing root cause of '{effect_name}' "
            f"(score: {score:.3f}). Causal path: {path_desc}."
        )

    # ── Path Analysis ────────────────────────────────────────────────────

    def trace_causal_chains(
        self,
        graph: CausalGraph,
        source: str,
        target: str,
    ) -> list[dict[str, Any]]:
        """Detailed trace of all causal chains from source to target.

        Args:
            graph: The causal graph.
            source: Source node.
            target: Target node.

        Returns:
            List of chain descriptions with scores.
        """
        paths = graph.find_all_paths(source, target, self._config.max_path_length)

        chains: list[dict[str, Any]] = []
        for path in paths:
            edge_details = []
            for i in range(len(path) - 1):
                edge = graph.get_edge(path[i], path[i + 1])
                edge_details.append(
                    {
                        "from": path[i],
                        "to": path[i + 1],
                        "type": edge.edge_type.value if edge else "unknown",
                        "strength": edge.strength if edge else 0.0,
                        "confidence": edge.confidence if edge else 0.0,
                    }
                )

            chains.append(
                {
                    "path": path,
                    "length": len(path) - 1,
                    "score": self._path_score(graph, path),
                    "edges": edge_details,
                }
            )

        chains.sort(key=lambda c: c["score"], reverse=True)
        return chains

    # ── Batch Analysis ───────────────────────────────────────────────────

    async def analyze_async(
        self,
        graph: CausalGraph,
        effect_nodes: list[str],
        data: dict[str, np.ndarray] | None = None,
    ) -> dict[str, list[RootCause]]:
        """Async analysis for multiple effect nodes.

        Args:
            graph: The causal graph.
            effect_nodes: List of effect nodes to analyze.
            data: Optional observational data.

        Returns:
            Dict mapping each effect node to its list of root causes.
        """
        results: dict[str, list[RootCause]] = {}
        for node in effect_nodes:
            try:
                results[node] = self.find_root_causes(graph, node, data)
            except RootCauseError as exc:
                logger.warning("Skipping node '%s': %s", node, exc)
                results[node] = []
        return results

    def __repr__(self) -> str:
        return(
            f"RootCauseAnalyzer(top_k={self._config.top_k}, threshold="
            f"{self._config.min_attribution_threshold})"
        )
