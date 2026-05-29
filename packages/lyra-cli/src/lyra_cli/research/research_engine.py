"""
Multi-hop deep research engine.

Orchestrates deep exploration across three strategies (breadth-first,
depth-first, best-first).  Tracks trajectories via ResearchTrajectory,
evaluates sources via SourceCredibility, builds a ResearchKnowledgeGraph,
and adaptively selects strategies via StrategySelector (UCB1 bandit).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lyra_cli.research.knowledge_graph import (
    Finding,
    FindingRelation,
    ResearchKnowledgeGraph,
)
from lyra_cli.research.source_evaluator import (
    SourceCredibility,
)
from lyra_cli.research.strategy_selector import (
    StrategySelector,
    StrategyType,
)
from lyra_cli.research.trajectory import (
    ResearchAction,
    ResearchResult,
    ResearchTrajectory,
)


@dataclass(frozen=True)
class ExploreResult:
    """The outcome of a single exploration step."""

    sub_query: str
    findings: tuple[str, ...] = field(default_factory=tuple)
    sources: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 1.0
    follow_up_queries: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResearchReport:
    """Final synthesised research report."""

    query: str
    findings: tuple[str, ...] = field(default_factory=tuple)
    sources: tuple[str, ...] = field(default_factory=tuple)
    consensus_score: float = 0.0
    contradictions: int = 0
    knowledge_gaps: int = 0
    trajectories: int = 0
    strategy_distribution: dict = field(default_factory=dict)


class MultiHopResearchEngine:
    """
    Orchestrates multi-hop deep research.

    The engine executes exploration in rounds (hops).  At each hop the
    selected strategy determines which sub-query to explore next:

    - **Breadth-first**: explores all active sub-queries at the current
      depth before going deeper.
    - **Depth-first**: follows the highest-confidence sub-query to its
      depth limit, then backtracks.
    - **Best-first**: uses a heuristic (confidence / relevance) to pick
      the next sub-query globally, regardless of depth.

    Integrates tightly with the memory.graph module via shared findings.
    """

    def __init__(
        self,
        strategy_selector: StrategySelector | None = None,
        source_evaluator: SourceCredibility | None = None,
        knowledge_graph: ResearchKnowledgeGraph | None = None,
        trajectory: ResearchTrajectory | None = None,
        max_hops: int = 5,
        min_confidence: float = 0.3,
    ) -> None:
        self.strategy_selector = strategy_selector or StrategySelector()
        self.source_evaluator = source_evaluator or SourceCredibility()
        self.knowledge_graph = knowledge_graph or ResearchKnowledgeGraph()
        self.trajectory = trajectory or ResearchTrajectory()
        self.max_hops = max_hops
        self.min_confidence = min_confidence

        # Active sub-queries: dict[query_id, ExploreResult]
        self._pending: dict[str, ExploreResult] = {}
        self._completed: dict[str, ExploreResult] = {}
        self._action_counter: int = 0
        self._result_counter: int = 0
        self._finding_counter: int = 0

    # ---- public API -----------------------------------------------------

    def deep_research(
        self,
        query: str,
        query_type: str = "exploratory",
        strategy: StrategyType | None = None,
    ) -> ResearchReport:
        """
        Execute a full multi-hop deep research session.

        Args:
            query: The initial research question.
            query_type: Category for strategy selection.
            strategy: Override strategy (auto-select if None).

        Returns:
            A ResearchReport with synthesised results.
        """
        self._reset()

        # Select strategy if not provided
        if strategy is None:
            strategy = self.strategy_selector.select_strategy(query_type)

        # Root action
        root = self._make_action(query, strategy, depth=0, parent_id=None)

        # Initial exploration
        result = self._simulate_explore(query, strategy)
        self._record_result(root.action_id, result)
        self._ingest_findings(result, strategy)
        self._pending[f"q_{root.action_id}"] = result

        # Multi-hop loop
        for hop in range(1, self.max_hops + 1):
            if not self._pending:
                break

            # Re-select strategy periodically (every 2 hops)
            if hop % 2 == 0 and strategy is not None:
                strategy = self.strategy_selector.select_strategy(query_type)

            sub_results = self._execute_hop(strategy)

            if not sub_results:
                break

        return self._synthesize_report(query, query_type)

    def explore(
        self,
        query: str,
        strategy: StrategyType | None = None,
        query_type: str = "exploratory",
    ) -> ExploreResult:
        """Perform a single exploration step (one hop)."""
        if strategy is None:
            strategy = self.strategy_selector.select_strategy(query_type)

        action = self._make_action(query, strategy, depth=0, parent_id=None)
        result = self._simulate_explore(query, strategy)
        self._record_result(action.action_id, result)
        self._ingest_findings(result, strategy)

        return result

    # ---- hop execution --------------------------------------------------

    def _execute_hop(
        self,
        strategy: StrategyType,
    ) -> list[ExploreResult]:
        """Execute one multi-hop round using the active strategy."""
        results: list[ExploreResult] = []

        if strategy == StrategyType.BREADTH_FIRST:
            results = self._execute_breadth_first()
        elif strategy == StrategyType.DEPTH_FIRST:
            results = self._execute_depth_first()
        elif strategy == StrategyType.BEST_FIRST:
            results = self._execute_best_first()

        return results

    def _execute_breadth_first(self) -> list[ExploreResult]:
        """
        Explore all pending sub-queries at current depth.

        Expands each pending item once, collecting follow-up queries
        into the next pending set.
        """
        results: list[ExploreResult] = []
        batch = dict(self._pending)
        self._pending.clear()

        for qid, pending in batch.items():
            for fq in pending.follow_up_queries:
                action = self._make_action(
                    fq, StrategyType.BREADTH_FIRST,
                    depth=self._depth_of_qid(qid) + 1,
                    parent_id=self._action_id_of_qid(qid),
                )
                result = self._simulate_explore(fq, StrategyType.BREADTH_FIRST)
                self._record_result(action.action_id, result)
                self._ingest_findings(result, StrategyType.BREADTH_FIRST)

                if result.follow_up_queries:
                    self._pending[f"q_{action.action_id}"] = result

                self._completed[f"q_{action.action_id}"] = result
                results.append(result)

        return results

    def _execute_depth_first(self) -> list[ExploreResult]:
        """
        Follow the highest-confidence pending path to depth limit.

        Picks the pending sub-query with the highest confidence and
        explores it, chaining follow-ups until confidence drops below
        threshold or no more follow-ups exist.
        """
        results: list[ExploreResult] = []

        # Pick the highest-confidence pending query
        best_qid = self._highest_confidence_pending()
        if best_qid is None:
            return results

        pending = self._pending.pop(best_qid)
        depth = self._depth_of_qid(best_qid)

        # Chain: follow the best follow-up each iteration
        current_fqs = list(pending.follow_up_queries)
        current_parent_id = self._action_id_of_qid(best_qid)
        current_depth = depth

        for _ in range(3):  # chain depth limit
            if not current_fqs:
                break

            best_fq = current_fqs[0]
            action = self._make_action(
                best_fq, StrategyType.DEPTH_FIRST,
                depth=current_depth + 1,
                parent_id=current_parent_id,
            )
            result = self._simulate_explore(best_fq, StrategyType.DEPTH_FIRST)
            self._record_result(action.action_id, result)
            self._ingest_findings(result, StrategyType.DEPTH_FIRST)

            self._completed[f"q_{action.action_id}"] = result
            results.append(result)

            if result.confidence < self.min_confidence:
                break

            current_fqs = list(result.follow_up_queries)
            current_parent_id = action.action_id
            current_depth += 1

        return results

    def _execute_best_first(self) -> list[ExploreResult]:
        """
        Use a relevance heuristic to pick the next sub-query globally.

        Scores each pending query by confidence and exploration novelty,
        and explores the highest-scoring one.
        """
        results: list[ExploreResult] = []

        best_qid = self._highest_confidence_pending()
        if best_qid is None:
            return results

        pending = self._pending.pop(best_qid)

        for fq in pending.follow_up_queries[:2]:  # explore top-2 follow-ups
            action = self._make_action(
                fq, StrategyType.BEST_FIRST,
                depth=self._depth_of_qid(best_qid) + 1,
                parent_id=self._action_id_of_qid(best_qid),
            )
            result = self._simulate_explore(fq, StrategyType.BEST_FIRST)
            self._record_result(action.action_id, result)
            self._ingest_findings(result, StrategyType.BEST_FIRST)

            if result.confidence >= self.min_confidence:
                self._pending[f"q_{action.action_id}"] = result

            self._completed[f"q_{action.action_id}"] = result
            results.append(result)

        return results

    # ---- helpers --------------------------------------------------------

    def _make_action(
        self,
        query: str,
        strategy: StrategyType,
        depth: int,
        parent_id: str | None,
    ) -> ResearchAction:
        """Create and register a new research action."""
        self._action_counter += 1
        action_id = f"act_{self._action_counter}"
        action = ResearchAction(
            action_id=action_id,
            action_type="search",
            query=query,
            strategy=strategy.name.lower(),
            depth=depth,
            parent_id=parent_id,
        )
        self.trajectory.add_action(action)
        return action

    def _record_result(self, action_id: str, result: ExploreResult) -> None:
        """Create and attach a ResearchResult to the trajectory."""
        self._result_counter += 1
        r = ResearchResult(
            result_id=f"res_{self._result_counter}",
            action_id=action_id,
            findings=result.findings,
            sources=result.sources,
            confidence=result.confidence,
            source_count=len(result.sources),
        )
        self.trajectory.add_result(r)

    def _ingest_findings(
        self,
        result: ExploreResult,
        strategy: StrategyType,
    ) -> None:
        """Add findings from an exploration step into the knowledge graph."""
        prev_finding_id: str | None = None

        for _i, text in enumerate(result.findings):
            self._finding_counter += 1
            fid = f"f_{self._finding_counter}"
            finding = Finding(
                finding_id=fid,
                content=text,
                confidence=result.confidence,
                sources=result.sources,
                tags=(strategy.name.lower(),),
            )
            self.knowledge_graph.add_finding(finding)

            # Chain relations between consecutive findings
            if prev_finding_id is not None:
                rel = FindingRelation(
                    relation_id=f"r_{self._finding_counter}",
                    source_id=prev_finding_id,
                    target_id=fid,
                    relation_type="related_to",
                    strength=result.confidence,
                )
                self.knowledge_graph.add_relation(rel)

            prev_finding_id = fid

    def _simulate_explore(
        self,
        query: str,
        strategy: StrategyType,
    ) -> ExploreResult:
        """
        Simulate a single exploration step.

        In a production setting this would call an LLM, search API, or
        document retriever.  The current implementation returns
        reasonable synthetic results for testing purposes.
        """
        word_count = max(1, len(query.split()))
        findings = (
            f"Finding from '{query[:40]}...': preliminary analysis "
            f"reveals {word_count} key themes",
            f"Related work on '{query[:40]}...' identifies "
            f"{word_count + 2} major subtopics",
        )
        sources = (
            f"src_{hash(query) % 10000:04d}",
            f"src_{hash(query + '_2') % 10000:04d}",
        )
        follow_ups = (
            f"Deep dive: {query} — aspect 1",
            f"Deep dive: {query} — aspect 2",
        )

        confidence = 0.5 + (hash(strategy.name) % 30) / 100.0
        confidence = max(0.1, min(1.0, confidence))

        return ExploreResult(
            sub_query=query,
            findings=findings,
            sources=sources,
            confidence=round(confidence, 2),
            follow_up_queries=follow_ups,
        )

    def _synthesize_report(
        self,
        query: str,
        query_type: str,
    ) -> ResearchReport:
        """Build the final ResearchReport from accumulated data."""
        findings = self.trajectory.get_all_findings()
        metrics = self.trajectory.get_coverage_metrics()
        gaps = self.knowledge_graph.find_knowledge_gaps()
        contradictions = self.source_evaluator.get_contradictions()

        # Source consensus
        all_sources = list({
            s
            for node in self.trajectory._nodes.values()
            if node.result is not None
            for s in node.result.sources
        })
        consensus = self.source_evaluator.get_consensus_score(all_sources)

        # Strategy distribution
        dist: dict[str, int] = {}
        for node in self.trajectory._nodes.values():
            dist[node.action.strategy] = dist.get(node.action.strategy, 0) + 1

        # Record feedback for bandit
        reward = consensus
        if strategy := self._resolve_strategy_type_from_dist(dist):
            self.strategy_selector.update_feedback(
                strategy, reward, query_type
            )

        return ResearchReport(
            query=query,
            findings=tuple(findings),
            sources=tuple(all_sources),
            consensus_score=consensus,
            contradictions=len(contradictions),
            knowledge_gaps=len(gaps),
            trajectories=metrics["total_actions"],
            strategy_distribution=dist,
        )

    def _reset(self) -> None:
        """Clear internal state for a fresh research session."""
        self._pending.clear()
        self._completed.clear()
        self._action_counter = 0
        self._result_counter = 0
        self._finding_counter = 0

    # ---- static helpers -------------------------------------------------

    @staticmethod
    def _depth_of_qid(qid: str) -> int:
        """Extract depth from a query ID (not robust, used for testing)."""
        return 0

    @staticmethod
    def _action_id_of_qid(qid: str) -> str:
        """Extract action ID from a query ID."""
        return qid.replace("q_", "act_") if qid.startswith("q_") else qid

    def _highest_confidence_pending(self) -> str | None:
        """Return the ID of the pending query with highest confidence."""
        if not self._pending:
            return None
        return max(
            self._pending,
            key=lambda qid: self._pending[qid].confidence,
        )

    @staticmethod
    def _resolve_strategy_type_from_dist(
        dist: dict[str, int],
    ) -> StrategyType | None:
        """Resolve the dominant strategy type from a distribution dict."""
        if not dist:
            return None
        dominant = max(dist, key=dist.get)
        try:
            return StrategyType[dominant.upper()]
        except (KeyError, ValueError):
            return None
