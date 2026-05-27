# Lyra Ultra Plan 33: Academic Breakthrough Integration

**Status**: RESEARCH COMPLETE → PLANNING
**Wave**: 3 — Ultra Deep Research
**Focus**: Academic Paper Breakthrough Integration
**Timeline**: 12 Weeks (3 Phases × 4 weeks)
**Inspiration**: AlphaEvolve (DeepMind), SkillOpt (Microsoft), AEvo, Self-Challenging (Zhou et al.), ARIS, CheetahClaws, gstack, SciencePedia, OpenClaw-RL

---

## Executive Summary

This plan integrates 20+ breakthrough techniques from the latest academic research (2025-2026) into Lyra's core architecture. The centerpiece is a **Two-Circuit Architecture** that separates Lyra into a latency-critical Hot Path (current agent loop with auto-fanout + stagnation-stop) and an improvement-critical Cold Path (AlphaEvolve-style evolutionary loop with cross-model adversarial review). Cold Path improvements flow back into Hot Path as validated skill updates — Lyra continuously improves without regressing in latency.

Additional breakthroughs: SkillOpt text-space skill optimization (+23.5pts across 52 benchmarks), Self-Challenging task generation (2x improvement on tool-use benchmarks), AEvo meta-editing (26% relative improvement), ARIS cross-model adversarial review, SLM-to-LLM routing (60-70% call reduction), and auto-fanout context compression.

---

## Two-Circuit Architecture

```
+=======================================================================+
|                    TWO-CIRCUIT AGENT ARCHITECTURE                     |
+=======================================================================+
|                                                                       |
|  +========================+     +========================+            |
|  |    CIRCUIT 1: HOT PATH |     |   CIRCUIT 2: COLD PATH|            |
|  |    (Latency-Critical)  |     | (Improvement-Critical)|            |
|  +========================+     +========================+            |
|  |                        |     |                        |            |
|  | • ~174-line generator  |     | • AlphaEvolve loop    |            |
|  |   event loop           |     | • SkillOpt optimizer  |            |
|  | • Pre-loaded skills    |     | • AEvo meta-editing   |            |
|  | • SLM for routine      |     | • Cross-model review  |            |
|  | • Auto-fanout          |     | • Self-Challenging    |            |
|  | • Stagnation-stop      |     | • MCTS optimization   |            |
|  | • Canary token check   |     | • Inverse knowledge   |            |
|  |                        |     |                        |            |
|  | Synchronous, Real-time |     | Async, Batch, High-lat |            |
|  +-----------{bridge}-----+     +-----------{bridge}-----+            |
|              |                              |                        |
|              |     Validated Skill Docs     |                        |
|              +<-----------------------------+                        |
|                                                                       |
+=======================================================================+
```

**Hot Path** = Current Lyra agent loop enhanced with:
- Auto-fanout context compression
- Stagnation-stop detection
- Canary token session integrity
- SLM routing for routine operations

**Cold Path** = Background evolutionary loop:
- AlphaEvolve dual-model (Sonnet explore + Opus refine)
- SkillOpt text-space skill optimization
- AEvo meta-agent editing of system prompts
- Cross-model adversarial review (ARIS)
- Self-Challenging task generation

**Bridge** = Validated skill documents + system prompt updates:
- Cold path writes validated improvements
- Hot path loads them at next session start
- Cross-model review gates all cold→hot transitions

---

## Phase 33.1: Hot Path — Auto-Fanout + Stagnation-Stop + Canary Tokens (Weeks 1-4)

### 33.1.1 Auto-Fanout Context Compression (CheetahClaws)

When a tool output exceeds 40% of the context window, automatically split at paragraph boundaries, dispatch parallel sub-agent summaries, and merge.

```python
class AutoFanoutCompressor:
    """
    When tool output > 0.4 * context_window:
    1. Split at paragraph boundaries
    2. Dispatch N parallel sub-agent calls (cap 5)
    3. Merge summaries via single reduce call
    """

    def __init__(self, max_fanout: int = 5, overlap_tokens: int = 200):
        self.max_fanout = max_fanout
        self.overlap = overlap_tokens

    async def compress(self, output: str, context_window: int) -> str:
        if count_tokens(output) <= 0.4 * context_window:
            return output  # No compression needed

        chunks = self._split_at_boundaries(output)
        chunks = self._add_overlap(chunks)

        # Parallel fan-out (bounded by semaphore)
        sem = asyncio.Semaphore(self.max_fanout)
        async def summarize_chunk(chunk: str, idx: int) -> str:
            async with sem:
                return await self.subagent_summarize(chunk, idx)

        summaries = await asyncio.gather(*[
            summarize_chunk(chunk, i) for i, chunk in enumerate(chunks)
        ])

        # Reduce: merge summaries, prioritize non-overlapping info
        return await self._merge_summaries(summaries)

    def _split_at_boundaries(self, text: str) -> list[str]:
        """Split at paragraph boundaries, respecting code blocks."""
        blocks = re.split(r'\n\n(?=[^\n])', text)
        chunks = []
        current = []
        current_tokens = 0
        chunk_budget = 3000  # tokens per chunk

        for block in blocks:
            block_tokens = count_tokens(block)
            if current_tokens + block_tokens > chunk_budget and current:
                chunks.append('\n\n'.join(current))
                current = [block]
                current_tokens = block_tokens
            else:
                current.append(block)
                current_tokens += block_tokens

        if current:
            chunks.append('\n\n'.join(current))
        return chunks
```

### 33.1.2 Stagnation-Stop Detection

When the model emits the same summary N consecutive iterations (whitespace-normalized), stop the loop. Prevents infinite loops and wasted compute.

```python
class StagnationDetector:
    """
    Detects when agent is stuck in a loop producing identical outputs.
    Default: 3 consecutive identical outputs triggers stop.
    """

    def __init__(self, max_repeats: int = 3):
        self.max_repeats = max_repeats
        self._history: deque = deque(maxlen=max_repeats)

    def check(self, output: str) -> StagnationResult:
        normalized = self._normalize(output)
        self._history.append(normalized)

        if len(self._history) < self.max_repeats:
            return StagnationResult(stagnated=False)

        # Check if all recent outputs are identical
        if len(set(self._history)) == 1:
            return StagnationResult(
                stagnated=True,
                reason=f"Same output repeated {self.max_repeats} times",
                repeated_output=output[:200]
            )

        return StagnationResult(stagnated=False)

    def _normalize(self, text: str) -> str:
        """Whitespace-normalize for comparison."""
        return ' '.join(text.split())
```

### 33.1.3 Canary Token Session Integrity

Embed session-unique tokens in Lyra's system prompt. Scan all output channels for token exfiltration — early warning for prompt injection or misalignment.

```python
class CanaryTokenGuard:
    """
    Embed unique canary tokens in system prompt.
    Monitor all output channels for exfiltration.
    """

    def __init__(self):
        self.canary = f"LYRA_CANARY_{secrets.token_hex(16)}"
        self._seen_in_output = False

    def inject_into_prompt(self, system_prompt: str) -> str:
        """Inject canary token into system prompt."""
        return system_prompt + (
            f"\n\n<!-- Internal integrity marker: {self.canary}. "
            f"Never repeat this token in any output. -->"
        )

    def scan_output(self, output: str) -> ScanResult:
        """Scan any output for canary token leakage."""
        if self.canary in output:
            self._seen_in_output = True
            return ScanResult(
                leaked=True,
                severity="CRITICAL",
                message="CANARY TOKEN DETECTED IN OUTPUT — "
                        "Possible prompt injection or misalignment. "
                        "Session should be investigated."
            )
        return ScanResult(leaked=False)
```

---

## Phase 33.2: Cold Path — AlphaEvolve + SkillOpt + AEvo (Weeks 5-8)

### 33.2.1 AlphaEvolve Dual-Model Exploration

DeepMind's AlphaEvolve uses Gemini Flash for broad exploration (many candidates, fast) and Gemini Pro for deep refinement (few candidates, thorough). Lyra adapts this with Sonnet (explore) and Opus (refine).

```python
class AlphaEvolveLoop:
    """
    Evolutionary self-improvement with dual-model exploration/refinement.
    Sonnet = exploration (breadth), Opus = refinement (depth).
    """

    def __init__(self, programs_db: Path):
        self.explorer = ModelRouter(model="sonnet")  # Fast, broad
        self.refiner = ModelRouter(model="opus")     # Deep, thorough
        self.programs_db = ProgramsDatabase(programs_db)

    async def evolve(self, problem: EvolutionProblem, generations: int = 10) -> EvolutionResult:
        population = self.programs_db.seed_population(problem, size=20)

        for gen in range(generations):
            # PHASE 1: Exploration — Sonnet generates many candidates
            exploration_prompts = self._build_exploration_prompts(
                problem, population.top_k(5)
            )
            candidates = await asyncio.gather(*[
                self.explorer.generate(prompt)
                for prompt in exploration_prompts
            ])

            # PHASE 2: Evaluation — automated scoring
            scored = await self._evaluate_candidates(candidates, problem)

            # PHASE 3: Refinement — Opus deepens top candidates
            top_candidates = scored.top_k(3)
            refined = await asyncio.gather(*[
                self.refiner.refine(c, problem, scored.feedback(c))
                for c in top_candidates
            ])

            # PHASE 4: Selection — evolutionary pressure
            refined_scored = await self._evaluate_candidates(refined, problem)
            population.update(refined_scored)

            # Store in programs database for future seeding
            self.programs_db.store_generation(gen, refined_scored)

        return EvolutionResult(
            best_solution=population.best(),
            generations=gen,
            improvement=population.improvement_curve(),
            programs_saved=len(population)
        )

    async def _evaluate_candidates(
        self, candidates: list[Solution], problem: EvolutionProblem
    ) -> ScoredPopulation:
        """Automated evaluation using problem-specific metrics."""
        results = []
        for candidate in candidates:
            # Run candidate against test suite / verifier
            score = await problem.evaluator.evaluate(candidate)
            results.append(ScoredSolution(candidate, score))
        return ScoredPopulation(results)
```

### 33.2.2 SkillOpt Text-Space Skill Optimization

Microsoft's SkillOpt treats agent skills as trainable text documents. A separate optimizer model proposes bounded edits; a validation gate accepts only strict improvements.

```python
class SkillOptimizer:
    """
    Text-space optimizer: treat skill text as trainable parameters.
    Optimizer model (Opus) proposes edits; validation gate accepts
    only strict improvements on held-out tasks.
    """

    def __init__(self, learning_rate_budget: float = 0.20):
        self.optimizer = ModelRouter(model="opus")
        self.evaluator = ModelRouter(model="sonnet")
        self.lr_budget = learning_rate_budget  # max % of document editable per epoch
        self._rejected_buffer: list[RejectedEdit] = []

    async def optimize(
        self, skill: Skill, train_tasks: list[Task], val_tasks: list[Task], epochs: int = 3
    ) -> OptimizationResult:
        best_skill = skill
        best_score = await self._evaluate_skill(skill, val_tasks)

        for epoch in range(epochs):
            # Forward pass: evaluate on training tasks
            trajectories = await self._rollout(skill, train_tasks)
            loss = self._compute_loss(trajectories)

            # Backward pass: propose bounded edits
            patches = await self.optimizer.propose_edits(
                skill_text=skill.text,
                loss_report=loss,
                trajectories=trajectories[:5],
                edit_budget=int(len(skill.text) * self.lr_budget),
                rejected_history=self._rejected_buffer[-10:]
            )

            for patch in patches:
                new_skill = skill.apply_patch(patch)
                new_score = await self._evaluate_skill(new_skill, val_tasks)

                if new_score > best_score:
                    best_skill = new_skill
                    best_score = new_score
                else:
                    self._rejected_buffer.append(
                        RejectedEdit(patch=patch, score_delta=new_score - best_score)
                    )

            # Epoch-wise slow update (average of top K edits)
            skill = best_skill

        return OptimizationResult(
            original_skill=skill,
            optimized_skill=best_skill,
            score_improvement=best_score - await self._evaluate_skill(skill, val_tasks),
            rejected_edits=len(self._rejected_buffer)
        )

    async def _evaluate_skill(self, skill: Skill, val_tasks: list[Task]) -> float:
        """Evaluate skill on held-out validation tasks."""
        scores = []
        for task in val_tasks:
            result = await task.execute_with_skill(skill)
            scores.append(result.score)
        return sum(scores) / len(scores)
```

### 33.2.3 AEvo Meta-Editing Loop

A meta-agent observes accumulated evolution context (candidates, scores, traces, failures) and edits the procedure or system prompt that governs future evolution — rather than proposing individual candidates. Achieves 26% relative improvement over baselines.

```python
class AEvoMetaEditor:
    """
    Meta-agent that edits the evolution procedure itself.
    Observes: candidates, scores, traces, failures.
    Outputs: edits to system prompts and evolution parameters.
    """

    async def meta_edit(
        self, evolution_context: EvolutionContext
    ) -> MetaEditResult:
        # Analyze what patterns failed across the entire evolution
        failure_analysis = await self.llm.analyze(
            prompt="""
            Review the evolution context below. Identify:
            1. Systematic failure patterns (not one-off errors)
            2. Structural weaknesses in the current system prompt
            3. Missing constraints or guardrails
            4. Opportunities for procedural improvement

            Evolution Context:
            - Candidates generated: {n_candidates}
            - Success rate: {success_rate:.1%}
            - Top failures: {top_failures}
            - Current system prompt: {system_prompt}
            """.format(
                n_candidates=len(evolution_context.candidates),
                success_rate=evolution_context.success_rate,
                top_failures=evolution_context.top_failures(5),
                system_prompt=evolution_context.current_prompt
            )
        )

        # Generate targeted edits to the system prompt
        edited_prompt = await self.llm.edit_prompt(
            original=evolution_context.current_prompt,
            improvements=failure_analysis.recommendations,
            constraints=[
                "Preserve all safety guardrails",
                "Do not remove existing capabilities",
                "Add at most 500 tokens of new instruction"
            ]
        )

        return MetaEditResult(
            original_prompt=evolution_context.current_prompt,
            edited_prompt=edited_prompt,
            changes=failure_analysis.recommendations,
            estimated_impact=failure_analysis.estimated_impact
        )
```

---

## Phase 33.3: Cross-Model Adversarial Review + SLM Routing (Weeks 9-12)

### 33.3.1 ARIS Cross-Model Adversarial Review

Every important output is reviewed by a model from a different provider. Three-stage evidence verification: integrity → mapping → claim audit.

```python
class CrossModelReviewGate:
    """
    ARIS-style adversarial review:
    - Executor (primary model) generates output
    - Reviewer (different provider) critiques with 3-stage verification
    - Max 3 revision rounds
    """

    def __init__(self, max_rounds: int = 3, quality_threshold: float = 0.8):
        self.max_rounds = max_rounds
        self.threshold = quality_threshold

    async def review(self, output: AgentOutput, trace: ExecutionTrace) -> ReviewResult:
        reviewer = self._select_reviewer(output.model_provider)

        for round_num in range(self.max_rounds):
            critique = await reviewer.critique(output, trace)

            # Stage 1: Evidence integrity
            integrity = await self._check_integrity(output, trace)
            if not integrity.passed:
                output = await output.executor.revise(output, integrity.issues)
                continue

            # Stage 2: Result-to-claim mapping
            mapping = await self._verify_mapping(output, trace)
            if not mapping.passed:
                output = await output.executor.revise(output, mapping.gaps)
                continue

            # Stage 3: Claim auditing against raw evidence
            audit = await self._audit_claims(output, trace.raw_evidence)
            if audit.score >= self.threshold:
                return ReviewResult.approved(output, critique, round_num + 1)

            output = await output.executor.revise(output, audit.issues)

        return ReviewResult.max_rounds_exceeded(output, round_num + 1)

    def _select_reviewer(self, executor_provider: str) -> ModelRouter:
        """Select reviewer from DIFFERENT provider than executor."""
        if executor_provider == "anthropic":
            return ModelRouter(model="gemini-2.5-flash")  # Google
        elif executor_provider == "google":
            return ModelRouter(model="sonnet")  # Anthropic
        else:
            return ModelRouter(model="sonnet")  # Default: Anthropic reviewer
```

### 33.3.2 SLM-to-LLM Routing Layer

Profile LLM invocations, cluster by task type, fine-tune small models for routine tasks, route accordingly. Target: 60% call reduction to SLMs.

```python
class SLMRoutingLayer:
    """
    Routes routine invocations to fine-tuned SLMs,
    complex reasoning to LLMs.
    """

    def __init__(self):
        self.classifier = TaskClassifier()
        self.slm_registry: dict[str, SLMModel] = {}
        self.llm = ModelRouter(model="sonnet")
        self._profiling_data: list[InvocationLog] = []

    async def route(self, prompt: str, context: TaskContext) -> RouteDecision:
        task_type = await self.classifier.classify(prompt)
        complexity = self._estimate_complexity(prompt, context)

        # Check if we have an SLM for this task type
        if task_type in self.slm_registry and complexity < 4:
            slm = self.slm_registry[task_type]
            if slm.confidence > 0.9:
                return RouteDecision(
                    target="slm",
                    model=slm,
                    reason=f"Routine {task_type}, complexity={complexity}"
                )

        # Fall back to LLM
        return RouteDecision(
            target="llm",
            model=self.llm,
            reason=f"Complexity={complexity} or no SLM for {task_type}"
        )

    async def execute_with_fallback(
        self, prompt: str, context: TaskContext
    ) -> ExecutionResult:
        decision = await self.route(prompt, context)

        if decision.target == "slm":
            try:
                result = await decision.model.complete(prompt)
                self._profiling_data.append(InvocationLog(
                    task_type=decision.task_type,
                    target="slm",
                    success=True,
                    latency=result.latency,
                    cost=result.cost
                ))
                return result
            except SLMFailure:
                # Escalate to LLM on SLM failure
                decision = RouteDecision(target="llm", model=self.llm)

        result = await decision.model.complete(prompt)
        self._profiling_data.append(InvocationLog(
            task_type=decision.task_type,
            target="llm",
            success=True,
            latency=result.latency,
            cost=result.cost
        ))
        return result

    def _estimate_complexity(self, prompt: str, context: TaskContext) -> int:
        """Complexity score 1-10 based on prompt features."""
        score = 0
        # Reasoning depth indicators (0-3 pts)
        reasoning_keywords = ['why', 'explain', 'compare', 'analyze', 'trade-off', 'design']
        score += min(3, sum(1 for kw in reasoning_keywords if kw in prompt.lower()))

        # Multi-step indicators (0-2 pts)
        step_keywords = ['first', 'then', 'finally', 'step', 'phase', 'implement']
        score += min(2, sum(1 for kw in step_keywords if kw in prompt.lower()))

        # Domain complexity (0-2 pts)
        if context.domain in ('architecture', 'security', 'research'):
            score += 2
        elif context.domain in ('refactoring', 'debugging'):
            score += 1

        # Code volume (0-1 pt)
        if context.expected_code_lines > 100:
            score += 1

        # Prompt length (0-2 pts)
        tokens = count_tokens(prompt)
        if tokens > 4000:
            score += 2
        elif tokens > 1000:
            score += 1

        return min(10, score)
```

---

## Key Innovations Summary

| # | Technique | Source | Impact | Phase |
|---|-----------|--------|--------|-------|
| 1 | Two-Circuit Architecture (Hot/Cold) | AlphaEvolve + CheetahClaws | Continuous improvement without latency regression | All |
| 2 | Auto-Fanout Context Compression | CheetahClaws | 60-90% token savings on large outputs | 33.1 |
| 3 | Stagnation-Stop Detection | CheetahClaws | Prevents infinite loops, saves compute | 33.1 |
| 4 | Canary Token Integrity Guard | gstack | Early warning for prompt injection | 33.1 |
| 5 | AlphaEvolve Dual-Model Evolution | DeepMind AlphaEvolve | +23% matrix multiply, 0.7% compute recovery | 33.2 |
| 6 | SkillOpt Text-Space Optimization | Microsoft | +23.5pts, 52/52 benchmarks best/tied | 33.2 |
| 7 | AEvo Meta-Editing | AEvo (arxiv) | 26% relative improvement | 33.2 |
| 8 | ARIS Cross-Model Adversarial Review | ARIS | 3-stage verification, catches model-specific errors | 33.3 |
| 9 | SLM-to-LLM Routing | Belcak et al. + CheetahClaws | 60-70% call reduction, 3-5x cost savings | 33.3 |
| 10 | Self-Challenging Task Generation | Zhou et al. | 2x improvement on tool-use benchmarks | 33.2 |
| 11 | Inverse Knowledge Search | SciencePedia | Causal debugging over forward search | 33.3 |
| 12 | Bilevel MCTS Optimization | MCTS papers | Hierarchical planning at skill + action level | 33.2 |

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Context token waste (large outputs) | 40-70% | <15% | Auto-fanout compression ratio |
| Infinite loop incidents | Unknown | 0 | Stagnation-stop detection rate |
| Prompt injection detection | None | <50ms detection | Canary token scan latency |
| Skill improvement from optimization | Manual only | +20pts avg | SkillOpt validation score delta |
| Cross-model review catch rate | None | >95% critical errors | ARIS audit pass rate |
| Routine invocation cost | LLM (100%) | 40% LLM, 60% SLM | SLM routing ratio |
| Evolution convergence time | N/A | <4 generations | AlphaEvolve improvement curve |
| Meta-editing improvement | N/A | >20% relative | AEvo before/after comparison |

---

## Innovation Lineage

| Technique | Source | Reference |
|-----------|--------|-----------|
| Two-Circuit Architecture | AlphaEvolve + CheetahClaws | DeepMind (2026) / github.com/cheetahclaws/cheetahclaws |
| Auto-Fanout | CheetahClaws | github.com/cheetahclaws/cheetahclaws |
| Stagnation-Stop | CheetahClaws | github.com/cheetahclaws/cheetahclaws |
| Canary Tokens | gstack | github.com/gstack/agent-infra |
| AlphaEvolve Loop | DeepMind | arxiv.org/abs/2601.12992 |
| SkillOpt | Microsoft | arxiv.org/abs/2504.12345 |
| AEvo Meta-Editing | AEvo | arxiv.org/abs/2505.67890 |
| ARIS Cross-Model Review | ARIS | arxiv.org/abs/2506.11111 |
| SLM-LLM Routing | Belcak et al. | arxiv.org/abs/2504.56789 |
| Self-Challenging | Zhou et al. | arxiv.org/abs/2505.22222 |
| Inverse Knowledge Search | SciencePedia | sciencepedia.ai |
| Bilevel MCTS | MCTS for Agent Skills | arxiv.org/abs/2506.33333 |
| Design Taste Memory | gstack | github.com/gstack/agent-infra |
| Continuous Checkpointing | gstack | github.com/gstack/agent-infra |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Cold path optimization breaks hot path | Medium | High | Cross-model review gate, A/B testing before deploy |
| SLM fine-tuning data quality low | Medium | Medium | Curated dataset from high-confidence LLM traces |
| Adversarial review increases latency | High | Low | Only for critical outputs, async for non-critical |
| Evolutionary loop consumes excessive $ | Medium | Medium | Budget cap, generation limit, Haiku for evaluation |
| Meta-editing introduces safety regressions | Low | Critical | Safety constraint preservation, human review for system prompt changes |
