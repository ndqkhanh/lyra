# Research Capabilities V2: Multi-Hop + Deep Research + Self-Evolving

**Version:** 2.0.0
**Date:** 2026-05-30
**Status:** Implementation Design - Ready
**Based on:** Orion framework, 20+ research papers, Phase 3 Research

---

## Executive Summary

Research Capabilities V2 introduces Orion-inspired multi-hop reasoning (4.33× faster), citation network traversal, cross-source synthesis with contradiction detection, and self-evolving research strategies. Achieves 3× deeper research with 20%+ accuracy improvement.

### Key Performance Targets

| Metric | V1 (Current) | V2 (Target) | Improvement |
|--------|-------------|-------------|-------------|
| Research Depth | 1× | 3× | 3× deeper |
| Multi-Hop Speed | Baseline | 4.33× | 4.33× faster |
| Accuracy | Baseline | +20% | 20% improvement |
| Citation Coverage | ~50% | 90%+ | 40pp improvement |
| Strategy Adaptation | Manual | Self-evolving | New capability |

---

## I. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                   RESEARCH ENGINE V2                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. MULTI-HOP REASONING (Orion-Inspired)                   │   │
│  │ Query decomposition → Sub-queries → Intermediate results   │   │
│  │ Cross-hop synthesis → Final answer                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. CITATION NETWORK TRAVERSAL                             │   │
│  │ Forward citations | Backward citations                    │   │
│  │ Impact analysis | Trend detection                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. CROSS-SOURCE SYNTHESIS                                 │   │
│  │ Contradiction detection | Evidence weighting              │   │
│  │ Consensus building | Confidence scoring                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. SELF-EVOLVING STRATEGIES                               │   │
│  │ Performance feedback | Strategy adaptation                │   │
│  │ Learning from failures | A/B strategy testing             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## II. Core Components

### 2.1 Multi-Hop Reasoning (Orion Framework)

```python
class MultiHopReasoner:
    """Orion-inspired multi-hop reasoning: decompose → execute → synthesize."""

    def __init__(self, claude_client):
        self.decomposer = QueryDecomposer(claude_client)
        self.executor = HopExecutor()
        self.synthesizer = AnswerSynthesizer(claude_client)
        self.validator = HopValidator()

    async def reason(self, query: ResearchQuery) -> MultiHopResult:
        """Execute multi-hop reasoning pipeline."""
        # Step 1: Decompose query into sub-queries
        decomposition = await self.decomposer.decompose(query)
        hops = decomposition.hops

        # Step 2: Execute each hop, feeding results forward
        hop_results = []
        accumulated_context = query.context

        for i, hop in enumerate(hops):
            hop_input = HopInput(
                query=hop,
                context=accumulated_context,
                previous_results=hop_results,
                hop_index=i
            )

            result = await self.executor.execute(hop_input)
            validated = await self.validator.validate(result, hop)

            if validated.confidence < 0.5:
                # Retry with refined query
                refined = await self.decomposer.refine(hop, validated)
                result = await self.executor.execute(refined)
                validated = await self.validator.validate(result, refined)

            hop_results.append(validated)
            accumulated_context = self._merge_context(
                accumulated_context, validated
            )

        # Step 3: Synthesize final answer
        synthesis = await self.synthesizer.synthesize(
            original_query=query,
            hop_results=hop_results,
            decomposition=decomposition
        )

        return MultiHopResult(
            query=query,
            hops=hop_results,
            synthesis=synthesis,
            hop_count=len(hops),
            confidence=synthesis.confidence,
            reasoning_trace=self._build_trace(decomposition, hop_results)
        )
```

### 2.2 Citation Network Traversal

```python
class CitationNetwork:
    """Forward/backward citation traversal with impact analysis."""

    def __init__(self):
        self.graph = CitationGraph()
        self.impact_analyzer = ImpactAnalyzer()
        self.trend_detector = TrendDetector()

    async def traverse(
        self, seed_papers: list[str], strategy: TraversalStrategy
    ) -> CitationNetworkResult:
        """Traverse citation network from seed papers."""
        visited = set(seed_papers)
        frontier = list(seed_papers)
        papers: dict[str, PaperAnalysis] = {}

        for depth in range(strategy.max_depth):
            next_frontier = []

            for paper_id in frontier:
                paper = await self._fetch_paper(paper_id)
                analysis = await self._analyze_paper(paper)
                papers[paper_id] = analysis

                # Forward citations (papers citing this one)
                if strategy.forward:
                    forward = await self._get_citations(paper_id, 'forward')
                    next_frontier.extend(
                        f for f in forward if f not in visited
                    )

                # Backward citations (papers cited by this one)
                if strategy.backward:
                    backward = await self._get_citations(paper_id, 'backward')
                    next_frontier.extend(
                        b for b in backward if b not in visited
                    )

                visited.add(paper_id)

            # Apply impact filter
            next_frontier = self.impact_analyzer.filter(
                next_frontier,
                min_citations=strategy.min_citations,
                min_h_index=strategy.min_h_index,
                venue_prestige=strategy.min_venue_tier
            )

            frontier = next_frontier
            if not frontier:
                break

        # Detect trends
        trends = self.trend_detector.detect(papers.values())

        return CitationNetworkResult(
            papers=papers,
            graph=self.graph,
            trends=trends,
            depth_reached=depth,
            coverage=len(visited)
        )
```

### 2.3 Cross-Source Synthesis

```python
class CrossSourceSynthesizer:
    """Contradiction detection, evidence weighting, consensus building."""

    def __init__(self):
        self.contradiction_detector = ContradictionDetector()
        self.evidence_weighter = EvidenceWeighter()
        self.consensus_builder = ConsensusBuilder()

    async def synthesize(
        self, sources: list[SourceAnalysis]
    ) -> SynthesisResult:
        """Synthesize findings across multiple sources."""
        # Detect contradictions between sources
        contradictions = self.contradiction_detector.detect(sources)

        # Weight evidence by source quality
        weighted = self.evidence_weighter.weight(
            sources,
            factors=[
                WeightFactor.RECENCY,
                WeightFactor.VENUE_PRESTIGE,
                WeightFactor.CITATION_COUNT,
                WeightFactor.METHODOLOGY_RIGOR,
                WeightFactor.SAMPLE_SIZE,
                WeightFactor.REPRODUCIBILITY
            ]
        )

        # Build consensus
        consensus = await self.consensus_builder.build(
            weighted_sources=weighted,
            contradictions=contradictions,
            confidence_threshold=0.7
        )

        # Identify areas of agreement and disagreement
        agreements = consensus.areas_of_agreement
        disputes = consensus.areas_of_dispute
        gaps = consensus.knowledge_gaps

        return SynthesisResult(
            findings=consensus.findings,
            confidence=consensus.confidence,
            agreements=agreements,
            disputes=disputes,
            gaps=gaps,
            contradictions=contradictions,
            source_weights=weighted.weights,
            recommendation=consensus.recommendation
        )
```

### 2.4 Self-Evolving Research Strategies

```python
class SelfEvolvingStrategies:
    """Strategies that learn and improve from research outcomes."""

    def __init__(self):
        self.strategy_registry = StrategyRegistry()
        self.performance_tracker = PerformanceTracker()
        self.strategy_mutator = StrategyMutator()

    async def select_strategy(
        self, query: ResearchQuery
    ) -> ResearchStrategy:
        """Select best strategy based on historical performance."""
        similar_queries = self.performance_tracker.find_similar(query)

        if len(similar_queries) < 10:
            return self.strategy_registry.get_default(query.type)

        # Score strategies by performance on similar queries
        strategy_scores = defaultdict(list)
        for sq in similar_queries:
            strategy_scores[sq.strategy_id].append(sq.outcome.score)

        best_strategy = max(
            strategy_scores,
            key=lambda s: np.mean(strategy_scores[s])
        )

        return self.strategy_registry.get(best_strategy)

    async def learn_from_outcome(
        self, query: ResearchQuery, strategy: ResearchStrategy,
        outcome: ResearchOutcome
    ):
        """Learn from research outcome to improve future strategies."""
        # Track performance
        self.performance_tracker.record(query, strategy, outcome)

        # If outcome is poor, analyze why
        if outcome.score < 0.6:
            failure_analysis = await self._analyze_failure(
                query, strategy, outcome
            )

            # Generate improved strategy variant
            improved = await self.strategy_mutator.mutate(
                strategy,
                guided_by=failure_analysis,
                mutation_rate=0.3
            )

            # Register as candidate
            self.strategy_registry.register_candidate(improved)

    async def evolve_strategies(self) -> EvolutionReport:
        """Periodic batch evolution of strategies."""
        all_performance = self.performance_tracker.get_all()

        # Identify underperforming strategies
        underperformers = [
            s for s, perf in all_performance.items()
            if perf.avg_score < 0.5 and perf.sample_size >= 20
        ]

        # Generate and test variants
        improved = []
        for strategy_id in underperformers:
            strategy = self.strategy_registry.get(strategy_id)
            variants = await self.strategy_mutator.generate_variants(
                strategy, count=5
            )

            # A/B test variants against original
            for variant in variants:
                result = await self._ab_test_strategy(
                    strategy, variant, min_samples=30
                )
                if result.variant_better:
                    self.strategy_registry.promote(variant)
                    improved.append(variant)

        return EvolutionReport(
            strategies_evaluated=len(underperformers),
            improved=len(improved),
            avg_improvement=self._calculate_avg_improvement(improved)
        )
```

---

## III. Implementation Phases

### Phase 1: Multi-Hop Reasoning (Weeks 1-4)
- Orion-inspired query decomposer
- Hop executor with context accumulation
- Answer synthesizer
- Hop validator with retry
- **Tests:** 30 unit tests

### Phase 2: Citation Network (Weeks 5-8)
- Citation graph builder
- Forward/backward traversal
- Impact analysis (citations, h-index, venue)
- Trend detection (emerging directions)
- **Tests:** 25 unit tests + 10 integration

### Phase 3: Cross-Source Synthesis (Weeks 9-11)
- Contradiction detection engine
- Evidence weighting system
- Consensus builder
- Knowledge gap identification
- **Tests:** 25 unit tests + 15 integration

### Phase 4: Self-Evolution (Weeks 12-14)
- Performance tracking system
- Strategy mutation engine
- A/B testing for strategies
- Learning from failures
- **Tests:** 30 unit tests + 15 integration

---

## IV. Testing Plan

| Test Type | Count | Coverage |
|-----------|-------|----------|
| Multi-hop reasoning | 30 | 90% |
| Query decomposition | 20 | 95% |
| Citation traversal | 25 | 90% |
| Impact analysis | 15 | 90% |
| Contradiction detection | 20 | 95% |
| Evidence weighting | 15 | 90% |
| Consensus building | 15 | 90% |
| Strategy evolution | 20 | 90% |
| Integration | 25 | N/A |
| E2E | 15 | N/A |
| **Total** | **200** | **90%+** |

---

## V. Success Metrics

- [ ] 3× deeper research capability
- [ ] 20%+ accuracy improvement
- [ ] 4.33× faster multi-hop reasoning
- [ ] 90%+ citation coverage
- [ ] Contradiction detection working across sources
- [ ] Self-evolving strategies demonstrate improvement
- [ ] 200+ tests, 90%+ coverage
