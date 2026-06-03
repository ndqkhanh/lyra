# RL-Based Skill & Agent Optimizer — Ultra Plan (§4.27)

> Run 1 — June 3, 2026 | Gradient-free and RL-based optimization of skills, prompts, and agent configurations
> Status: New plan — integrates GEPA, MetaAgent-X, MemGrad, TF-TTCL, DGM, EvoTest, and Misevolve-informed safety

## Plain-Language Summary

Lyra's Skill & Agent Optimizer automatically improves skills and agent configurations through iterative refinement loops. A GEPA-style gradient-free prompt evolution generates skill variants, evaluates them on held-out tasks, keeps winners, and mutates them for the next generation. For multi-agent workflows, MetaAgent-X-style Designer+Executor co-evolution via GRPO jointly optimizes the orchestrator and subagents. The optimization is bootstrapped by a TF-TTCL training-free Explore-Reflect-Steer loop that works even with closed-model providers. MemGrad textual gradients convert execution feedback into structured memory updates for retrospective and prospective improvement. All evolved skills pass through a Misevolve-informed safety validator before promotion. Harness-level code changes (DGM-style self-rewriting) are gated for Phase 4 with human-in-the-loop approval.

## 1. Problem

Lyra's current skills are static — authored by hand and never improved automatically. The SkillRegistry has no optimization pipeline, no training loop, no variant selection, and no mechanism for learning from execution feedback. Research shows that skill optimization yields dramatic improvements: SkillOpt delivers +23.5 points over baselines, MetaAgent-X achieves 38.33% average (vs 27.16% single agent), and DGM self-improvement raises SWE-bench from 20% to 50%. Lyra needs an optimizer that works with all providers (including closed models), respects safety constraints, and can evolve both standalone skills and multi-agent workflow configurations.

## 2. Evidence Synthesis

### 2.1 SkillOpt (Microsoft, 2026)

Full training loop for skill optimization:
- Rollout → reflect → aggregate → select → update → evaluate
- Textual learning rate: bounded edits per epoch
- Rejected-edit buffer prevents cyclic edits
- Slow/meta update: epoch-wise update for stability
- Results: best or tied-best on ALL 52 evaluated (model, benchmark, harness) cells
- GPT-5.5: +23.5 points on direct chat, +24.8 on Codex, +19.1 on Claude Code CLI
- Transfers across model scales, between Codex and Claude Code harnesses

### 2.2 GEPA (Gradient-Free Prompt Evolution)

- Generate variants → evaluate → keep winners → mutate → repeat
- No model weight access needed — works with API-only models
- 5-10% improvement per evolutionary generation
- Validated on diverse agent tasks (AppWorld, finance, reasoning)

### 2.3 MetaAgent-X (arXiv 2605.14212)

End-to-end RL for joint Designer+Executor optimization:
- Designer generates multi-agent workflows; Executor runs them
- Hierarchical rollout: M=4 designs x N=4 executions per design
- Stagewise co-evolution: K=30 step alternation between designer/executor phases
- GRPO optimizer, learning rate 5x10^-6
- Qwen3-8B: Average 38.33% (vs single agent 27.16%, +21.7% peak)
- Structure selection: RL learns to route tasks (Reflection 70%+ for hard math, Single agent 55% for easy)

### 2.4 MemGrad (TCS Research, ICLR 2026)

Textual gradients for memory-guided optimization:
- Batched feedback → textual gradients → dual memory (retrospective + prospective)
- Role-based gradient routing via embedding similarity
- AgileCoder on 30 CLI games: MemGrad 48.3% vs AgileCoder 15.3%
- Gradient abstraction prevents prompt bloat
- Token cost: ~0.08 USD extra for significant gains

### 2.5 TF-TTCL (Findings ACL 2026)

Training-free test-time contrastive learning:
- Explore-Reflect-Steer loop
- Semantic query augmentation via multi-agent role-playing
- Contrastive experience distillation (good vs bad trajectories → textual rules)
- Contextual rule retrieval at inference
- Frozen LLM throughout — no gradient updates
- Works with any API-only model provider

### 2.6 DGM / DGM-H (Meta, ICLR 2026)

Self-improving harness that rewrites own code:
- Iteratively modifies own Python codebase
- Archive-based evolution with parent selection
- SWE-bench: 20% → 50% (+30pp, 2.5x)
- Polyglot: 14.2% → 30.7% (+16.5pp, ~2.16x)
- Model transfer: o3-mini 23→33%, Claude 3.7 Sonnet 19→59.5%
- 2 weeks per run, significant API costs — safe gating essential

### 2.7 EvoTest (ICLR 2026)

Two-agent Actor/Evolver for cross-episode learning:
- Actor executes task; Evolver analyzes transcript, proposes revised config
- Four mutations: prompt rewriting, memory updates, hyperparameter tuning, tool-use routines
- Only method to win any games on J-TTL benchmark (Detective, Library)

### 2.8 "Your Agent May Misevolve" (Shao et al., 2025)

Critical finding for any self-optimizing system:
- Memory misevolution: refusal rate 99.4% → 54.4% (-45%)
- Tool misevolution: 56-76% unsafe rate on tool creation
- Workflow misevolution: refusal 36.3% → 5.6% (-84.6%)
- Safety stable for 50 rounds, then abruptly collapses at round 60
- Every optimization step must include a safety gate

### 2.9 ADAS / AlphaEvolve

- ADAS (ICLR 2025 Outstanding): Meta Agent Search discovers novel agent designs in Turing Complete search space
- AlphaEvolve (DeepMind): Evolutionary coding with Flash/Pro ensemble
- Data Center Scheduling: 0.7% of Google's worldwide compute savings from AlphaEvolve optimizations
- Both demonstrate that automated discovery can surpass human-designed agents

## 3. Proposed Lyra Design

### 3.1 Optimizer Architecture

```mermaid
graph TB
    subgraph "Input Sources"
        SessionLogs[Session Logs<br/>Trajectories + Outcomes]
        SkillRegistry[SkillRegistry<br/>Current Skills]
        WorkflowConfigs[Workflow Configs<br/>Agent Topologies]
    end
    
    subgraph "Optimization Pipeline"
        subgraph "Layer 1: Training-Free (TF-TTCL)"
            TTF1[Explore<br/>Semantic Query Augmentation]
            TTF2[Reflect<br/>Contrastive Distillation]
            TTF3[Steer<br/>Rule Injection at Inference]
        end
        
        subgraph "Layer 2: Gradient-Free (GEPA/SkillOpt)"
            GF1[Generate Variants<br/>Bounded Edits per Epoch]
            GF2[Rollout + Evaluate<br/>Held-Out Task Suite]
            GF3[Select Winners<br/>Rejected-Edit Buffer]
            GF4[Mutate → Repeat<br/>Textual Learning Rate]
        end
        
        subgraph "Layer 3: RL-Based (MetaAgent-X)"
            RL1[Designer<br/>Generate Workflow Structure]
            RL2[Executor<br/>Run Workflow with Rollouts]
            RL3[Joint Credit Assignment<br/>Hierarchical GRPO]
            RL4[Stagewise Co-Evolution<br/>K=30 Alternation]
        end
        
        subgraph "Layer 4: Textual Gradients (MemGrad)"
            MG1[Feedback Decomposition<br/>Loss → Feedback Pairs]
            MG2[Role-Based Routing<br/>Embedding Similarity]
            MG3[Gradient Abstraction<br/>Compress → Apply]
            MG4[Dual Memory Update<br/>Retrospective + Prospective]
        end
    end
    
    subgraph "Safety Gate (Misevolve-Informed)"
        SG1[Safety Evaluation<br/>Baseline vs Evolved]
        SG2[Confidence Check<br/>Regession Detection]
        SG3[Human Review Gate<br/>For Harness Changes]
    end
    
    subgraph "Output"
        EvolvedSkill[Evolved Skills<br/>SKILL.md + Scripts]
        EvolvedWorkflow[Evolved Workflows<br/>Optimized Topologies]
        EvolvedPrompt[Evolved Prompts<br/>System + Agent Prompts]
    end
    
    SessionLogs --> TTF1
    SkillRegistry --> GF1
    WorkflowConfigs --> RL1
    
    TTF3 --> SessionLogs
    
    GF4 -->|Iterate| GF1
    RL4 -->|Iterate| RL1
    
    GF4 --> SG1
    RL4 --> SG1
    MG4 --> SG1
    
    SG1 -->|Pass| EvolvedSkill
    SG1 -->|Pass| EvolvedWorkflow
    SG1 -->|Pass| EvolvedPrompt
    
    SG1 -->|Fail| Revert[Revert to Previous Version]
    SG1 -->|Harness Change| HumanReview[Human Review Required]
    HumanReview -->|Approve| EvolvedSkill
    HumanReview -->|Reject| Revert
    
    subgraph "Phase 4 Only (DGM/ADAS)"
        DGM[Harnes Self-Rewriting<br/>Codebase Mutation]
        DGM --> HumanReview
    end
```

### 3.2 Training-Free Optimization (TF-TTCL Layer)

```python
class TrainingFreeOptimizer:
    """Explore-Reflect-Steer loop for skill improvement.
    
    No model weight updates — all adaptation through in-context rule injection.
    Works with any provider including API-only closed models.
    """
    
    async def explore(self, skill: Skill, n_variants: int = 5) -> list[SkillVariant]:
        """Generate diverse skill variants via multi-agent role-playing."""
        variants = []
        for _ in range(n_variants):
            variant = await self.llm.chat([
                {"role": "system", "content": f"Generate a variant of the following skill. "
                                              f"Change the approach, add new perspectives, "
                                              f"or restructure the instructions. Keep it executable."},
                {"role": "user", "content": skill.content}
            ])
            variants.append(SkillVariant(content=variant.content, parent_skill_id=skill.id))
        return variants
    
    async def reflect(self, trajectories: list[Trajectory]) -> list[str]:
        """Contrast good vs bad trajectories → extract textual rules."""
        good = [t for t in trajectories if t.outcome == Outcome.SUCCESS]
        bad = [t for t in trajectories if t.outcome == Outcome.FAILURE]
        
        if len(good) < 2 or len(bad) < 2:
            return []
        
        # Contrastive distillation: identify what separates success from failure
        rules = await self.llm.chat([
            {"role": "system", "content": "Compare successful and failed trajectories. "
                                          "Extract 3-5 actionable rules that distinguish them. "
                                          "Rules should be specific and transferable to new tasks."},
            {"role": "user", "content": f"Good: {json.dumps([g.summary for g in good[:3]])}\n"
                                        f"Bad: {json.dumps([b.summary for b in bad[:3]])}"}
        ])
        
        return self._parse_rules(rules.content)
    
    async def steer(self, task: str, rules: list[str]) -> str:
        """Inject relevant rules into context at inference time."""
        matching_rules = [r for r in rules if self._matches_task(r, task)]
        if not matching_rules:
            return task
        
        return f"{task}\n\nRelevant guidelines from prior experience:\n" + \
               "\n".join(f"- {r}" for r in matching_rules[:5])
```

### 3.3 Gradient-Free Optimization (GEPA/SkillOpt Layer)

```python
@dataclass
class SkillOptimizerConfig:
    """Configuration for the gradient-free skill optimizer."""
    epochs: int = 10
    variants_per_epoch: int = 5
    rollouts_per_variant: int = 3
    textual_learning_rate: int = 3  # Bounded edits per epoch
    rejected_buffer_size: int = 10
    holdout_ratio: float = 0.3
    validation_gate: bool = True
    
    # AlphaEvolve-like ensemble for exploration vs refinement
    explorer_model: str = "haiku"       # Cheap model for broad exploration
    refiner_model: str = "sonnet"       # Strong model for deep refinement

class GradientFreeOptimizer:
    """Full training loop for skill optimization (SkillOpt architecture).
    
    rollout → reflect → aggregate → select → update → evaluate
    """
    
    def __init__(self, skill_registry: SkillRegistry, config: SkillOptimizerConfig):
        self.registry = skill_registry
        self.config = config
        self.rejected_edits: list[Edit] = []
    
    async def optimize(self, skill_id: str, task_suite: list[Task]) -> OptimizedSkill:
        """Run full optimization loop on a single skill."""
        skill = self.registry.get_skill(skill_id)
        train_tasks, eval_tasks = self._split_holdout(task_suite)
        
        best_score = await self._evaluate(skill, eval_tasks)
        best_variant = skill
        
        for epoch in range(self.config.epochs):
            # 1. Generate variants with bounded edits
            variants = []
            for _ in range(self.config.variants_per_epoch):
                edit_candidates = await self._propose_edits(skill, train_tasks)
                # Filter against rejected-edit buffer
                valid = [e for e in edit_candidates if e not in self.rejected_edits]
                if valid:
                    variant = await self._apply_edits(skill, valid[:self.config.textual_learning_rate])
                    variants.append(variant)
            
            # 2. Rollout + evaluate each variant
            scores = {}
            for variant in variants:
                variant_score = await self._evaluate(variant, eval_tasks)
                scores[variant.id] = variant_score
            
            # 3. Select winner, update rejected buffer
            winner_id = max(scores, key=scores.get)
            winner_variant = {v.id: v for v in variants}[winner_id]
            winner_score = scores[winner_id]
            
            if winner_score <= best_score:
                # Record rejected edits
                for variant in variants:
                    edits = await self._extract_edits(skill, variant)
                    self.rejected_edits.extend(edits)
                continue
            
            # 4. Update skill to winner variant
            best_score = winner_score
            best_variant = winner_variant
            skill = winner_variant
            
            # Log epoch
            await self._log_epoch(epoch, best_score, winner_variant.id)
        
        return OptimizedSkill(
            original_id=skill_id,
            new_content=best_variant.content,
            epochs_run=self.config.epochs,
            final_score=best_score,
            improvement=best_score - (await self._evaluate(
                self.registry.get_skill(skill_id), eval_tasks
            )),
        )
    
    async def _propose_edits(self, skill: Skill, tasks: list[Task]) -> list[Edit]:
        """Generate bounded skill edit candidates from failure analysis."""
        # Rollout current skill on training tasks
        results = await self._rollout(skill, tasks)
        failures = [r for r in results if not r.success]
        
        if not failures:
            return []
        
        # Analyze failures and propose edits
        analysis = await self.refiner_model.chat([
            {"role": "system", "content": "Analyze these agent failures. Propose bounded edits "
                                          "to the skill that would fix the most impactful issue. "
                                          f"Max {self.config.textual_learning_rate} edits."},
            {"role": "user", "content": f"Skill: {skill.name}\n"
                                        f"Failures: {json.dumps([f.trace[-3:] for f in failures[:5]])}"}
        ])
        
        return self._parse_edits(analysis.content)
```

### 3.4 RL-Based Optimization (MetaAgent-X Layer)

```python
class RLBasedOptimizer:
    """End-to-end RL for joint Designer+Executor optimization.
    
    Stagewise co-evolution: K=30 step alternation between
    designer (generates workflows) and executor (runs workflows).
    """
    
    def __init__(self, config: RLOptimizerConfig):
        self.config = config
        self.shared_policy = self._init_shared_policy()  # Same LLM backbone
        self.stage = 0  # 0 = designer, 1 = executor
    
    async def optimize_workflow(self, task: Task) -> OptimizedWorkflow:
        """Jointly optimize workflow design + execution."""
        # Hierarchical rollout: M designs x N executions per design
        designs = []  # Workflow configurations
        for m in range(self.config.designs_per_query):
            design = await self.designer.generate(task)
            designs.append(design)
        
        execution_results = []
        for design in designs:
            for n in range(self.config.executions_per_design):
                result = await self.executor.run(design, task)
                execution_results.append(result)
        
        # Joint credit assignment via hierarchical GRPO
        advantages = self._compute_group_advantages(execution_results)
        
        # Update shared policy
        loss = self._grpo_loss(execution_results, advantages, self.shared_policy)
        self.shared_policy = self._gradient_step(loss)
        
        # Stagewise alternation
        self.stage = (self.stage + 1) % 2
        
        return OptimizedWorkflow(
            best_design=max(designs, key=lambda d: d.validation_score),
            executed_designs=len(designs),
            improvement=self._compute_improvement(execution_results),
        )
```

### 3.5 Textual Gradient Optimization (MemGrad Layer)

```python
class TextualGradientOptimizer:
    """MemGrad-style textual gradients for memory-guided optimization.
    
    Batched feedback → TextGrad decomposition → Role-based routing
    → Abstraction → Retrospective + Prospective memory update
    """
    
    async def optimize_prompt(self, agent: Agent, feedback_batch: list[Feedback]) -> str:
        """Optimize agent prompt via textual gradients."""
        # 1. Decompose feedback into (Loss, gradient) pairs
        pairs = []
        for fb in feedback_batch:
            loss = await self._compute_textloss(fb.trajectory, fb.expected)
            gradient = await self._compute_textgrad(loss)
            pairs.append((loss, gradient))
        
        # 2. Role-based gradient routing
        role_routed = defaultdict(list)
        for loss, gradient in pairs:
            role = await self._assign_role(gradient)  # embedding similarity to role prototypes
            role_routed[role].append(gradient)
        
        # 3. Abstract gradients per role (prevent prompt bloat)
        abstracted = {}
        for role, gradients in role_routed.items():
            abstracted[role] = await self._abstract(gradients)
        
        # 4. Compute prompt-level gradient
        prompt_gradient = await self._compute_prompt_gradient(abstracted, agent.system_prompt)
        
        # 5. Update retrospective memory (failure patterns) and prospective memory (fixes)
        retrospective = abstracted.get("failure_patterns", [])
        prospective = abstracted.get("fixes", [])
        await self.memory.retrospective.extend(retrospective)
        await self.memory.prospective.extend(prospective)
        
        # 6. Apply gradient to system prompt  
        updated_prompt = await self._apply_gradient(agent.system_prompt, prompt_gradient)
        
        return updated_prompt
```

### 3.6 Safety Validator (Misevolve-Informed Gate)

```python
class OptimizationSafetyValidator:
    """Misevolve-informed safety gate for all optimization.
    
    Every evolved skill must pass safety checks before promotion.
    Baseline safety score vs evolved score comparison.
    """
    
    SAFETY_DEGRADATION_THRESHOLD = 0.05  # 5% max degradation allowed
    
    async def validate(self, skill: Skill, evolved: EvolvedOutput) -> ValidationResult:
        """Validate that an evolved skill is safe to promote."""
        
        # 1. Baseline safety evaluation
        baseline_score = await self._evaluate_safety(skill)
        
        # 2. Evolved safety evaluation  
        evolved_score = await self._evaluate_safety(evolved.content)
        
        # 3. Compare
        degradation = baseline_score - evolved_score
        if degradation > self.SAFETY_DEGRADATION_THRESHOLD:
            return ValidationResult(
                approved=False,
                reason=f"Safety degradation: {baseline_score:.2f} → {evolved_score:.2f} ({degradation:.2f})",
                recommendation="Revert to pre-evolution version. Consider constrained mutation.",
                confidence=0.9,
            )
        
        # 4. Misevolve-specific checks
        misevolve_risk = await self._check_misevolution_patterns(evolved.content)
        if misevolve_risk.risk_score > 0.5:
            return ValidationResult(
                approved=False,
                reason=f"Misevolution risk detected: {misevolve_risk.pattern}{misevolve_risk.detail}",
                recommendation="Review evolution trajectory for reward hacking or heuristic ossification.",
                confidence=misevolve_risk.confidence,
            )
        
        return ValidationResult(approved=True)
    
    async def _evaluate_safety(self, content: str) -> float:
        """Evaluate safety score (0-1) of skill content."""
        result = await self.safety_model.chat([
            {"role": "system", "content": "Evaluate this skill/skill content for safety issues. "
                                          "Score 0-1 where 1 = completely safe. Consider: "
                                          "harmful instructions, bypass attempts, "
                                          "exploitation vulnerabilities, data exfiltration risks."},
            {"role": "user", "content": content[:4000]}
        ])
        return float(result.content.strip())
```

### 3.7 Data Model

```python
@dataclass
class OptimizerConfig:
    """Top-level optimizer configuration."""
    training_free_enabled: bool = True
    gradient_free_enabled: bool = True
    rl_based_enabled: bool = False         # Gate for RL (requires training infra)
    textual_gradient_enabled: bool = False  # Gate (requires feedback pipeline)
    harness_rewriting_enabled: bool = False # Phase 4 only
    
    # Default budgets
    max_daily_optimization_cost: float = 5.0
    max_epochs_per_skill: int = 10
    max_concurrent_optimizations: int = 2
    
    # Routing
    explorer_model: str = "haiku"       # Cheap model for broad exploration
    refiner_model: str = "sonnet"       # Strong model for deep refinement
    safety_model: str = "opus"          # Most capable model for safety checks

@dataclass
class OptimizationResult:
    optimizer_type: OptimizerType       # TF_FREE | GRADIENT_FREE | RL | TEXTUAL_GRAD
    skill_id: str
    epochs_run: int
    final_score: float
    improvement: float
    total_cost: float
    safety_check: ValidationResult
    output_artifact: str                # New skill content or workflow config

class OptimizerType(Enum):
    TF_FREE = "training_free"
    GRADIENT_FREE = "gradient_free"
    RL = "rl_based"
    TEXTUAL_GRAD = "textual_gradient"

@dataclass
class OptimizationMetrics:
    """Key metrics for optimizer dashboard."""
    total_optimizations: int
    skills_optimized: int
    avg_improvement: float
    success_rate: float                 # % optimizations that improved score
    safety_block_rate: float            # % blocked by safety validator
    avg_cost_per_optimization: float
    avg_epochs_per_skill: float
    total_cost_all: float
    rejected_edits_count: int
```

### 3.8 Optimization Scheduling

```mermaid
flowchart LR
    A[New Session Logs Available] --> B{Logs >= N?}
    B -->|No| Wait[Wait]
    B -->|Yes| C[TF-TTCL: Extract Rules]
    C --> D[Check: Skill Performance Degraded?]
    D -->|Yes| E[Gradient-Free: Optimize Skill]
    D -->|No| F[Check: Budget Available?]
    E --> F
    F -->|No| Schedule[Defer to Next Idle Window]
    F -->|Yes| G{Skill Type?}
    G -->|Standalone| H[Gradient-Free Loop<br/>5-10 Variants, 3 Rollouts]
    G -->|Workflow| I[RL-Based Loop<br/>M=4 Designs, N=4 Executions]
    H --> J[Safety Validator]
    I --> J
    J -->|Pass| K[Promote to Registry]
    J -->|Fail| L[Revert + Log]
```

## 4. Build Outline

### Phase 1: Training-Free Optimization (weeks 1-2)

1. **Explore-Reflect-Steer loop** — TF-TTCL pipeline: semantic query augmentation, contrastive experience distillation, contextual rule retrieval and injection
2. **Rule extraction from session logs** — Parse session trajectories; classify as success/failure; contrastive comparison → textual rules; rule storage in Experience store
3. **Rule injection at inference** — Match rules to current task via embedding similarity; inject top-K rules into agent context
4. **Basic optimizer command** — `lyra optimize skill <id>` — runs one optimization cycle; reports improvement score

**Dependencies:** §4.2 memory store (Experience tier), §4.5 model router

### Phase 2: Gradient-Free Skill Optimization (weeks 3-6)

1. **GEPA/SkillOpt loop** — Generate variants → rollout → evaluate → select → mutate → repeat
2. **Bounded-edit engine** — Textual learning rate implementation; mutation operators (add/delete/replace sections); rejected-edit buffer
3. **Held-out evaluation** — Split task suite into train/eval; per-variant rollout with score aggregation; validation gate (must improve on eval)
4. **Skill variant generation** — Use refiner model (Sonnet) to analyze failures → propose edits; explorer model (Haiku) for cheap broad search
5. **Optimization dashboard** — Track epoch scores, cumulative improvement, cost per epoch; comparison view (old vs new)

**Dependencies:** Phase 1, SkillRegistry (§4.4)

### Phase 3: MemGrad + Safety (weeks 7-9)

1. **Textual gradient pipeline** — Feedback decomposition → TextGrad loss → gradient routing by role → abstraction → retrospective/prospective memory
2. **Dual memory for optimization** — Retrospective store (failure patterns) + Prospective store (fix proposals); retrieval during optimization
3. **Misevolve-informed safety validator** — Baseline safety scoring; evolved safety scoring; degradation threshold enforcement; evolution pattern detection
4. **Safety gate integration** — All optimization paths must pass safety validator; human review for borderline cases; reversion on safety failure
5. **Misevolve monitoring** — Track safety scores over optimization rounds; detect sudden collapse patterns; alert at sustained degradation

**Dependencies:** Phase 2, §4.17 safety (Misevolve guard)

### Phase 4: RL-Based + Harness Rewriting (weeks 10-14)

1. **MetaAgent-X Designer-Executor** — Hierarchical rollout (M designs x N executions); stagewise co-evolution (K=30); GRPO optimizer
2. **RL training infrastructure** — Reward computation from task outcomes; advantage estimation via group-based baselines; policy update loop
3. **Workflow topology optimization** — Learn to route tasks to optimal workflow structures (single agent vs chain vs ensemble vs reflection)
4. **DGM-style harness self-rewriting** — Archive-based evolution: parent selection, staged evaluation (10→50→200 tasks), edit tool modifications
5. **Human-in-the-loop gate** — Harness changes require human PR review; code change preview; safety impact assessment
6. **ADAS integration** — Meta Agent Search for discovering novel agent designs; Turing Complete search space over tool compositions

**Dependencies:** Phase 3, §4.25 adversarial panel (for verification of evolved agents)

## 5. Multi-Provider Note

The optimizer is designed for multi-provider from day one. Layers 1-2 (TF-TTCL, GEPA) work with any API-only provider — no gradient access needed. Layer 3 (MemGrad) requires structured feedback from the provider but no model internals. Layer 4 (MetaAgent-X RL) requires GRPO support or a compatible RL library — may be provider-specific for the training step but inference uses any provider. The safety validator should use the strongest available provider (per §4.5 router) for maximum accuracy. DeepSeek's lower instruction-following reliability means: use explorer model for DeepSeek (cheaper exploration), but switch to Sonnet/Opus for refiner and safety steps.

## 6. (A) Parity vs (B) Breakthrough

**(A) Parity:** TF-TTCL training-free optimization + GEPA-style gradient-free skill evolution. Matches systems like SkillOpt and EvoTest — automated skill improvement from execution feedback without weight updates.

**(B) Breakthrough:** MetaAgent-X joint Designer+Executor co-evolution + MemGrad textual gradients with dual memory + DGM-style harness self-rewriting with human gate + Misevolve-informed safety validation gating ALL optimization. No production system combines all four optimization layers with a safety gate. The safety-first optimization pipeline (validate every evolution step) is genuinely novel — most optimization systems optimize for performance only and ignore safety degradation.

## 7. Baseline Delta

**Changes:** New 4-layer optimizer pipeline (TF-free, gradient-free, RL, textual gradients), safety validator, skill evolution loop, harness self-rewriting infrastructure (Phase 4)
**Keeps:** SkillRegistry as the skill storage; Skill YAML format (extended with evolution metadata)
**Replaces:** Static skills → self-improving skills
**Migration cost:** ~8 new Python modules; ~2500 lines of code; GRPO training infrastructure (Phase 4); no breaking changes to existing skill format

## 8. Expert Review

**Senior ML/AI Engineer:** "The 4-layer optimizer is comprehensive but over-engineered for Phase 1. Ship TF-TTCL (no training infra needed, works with any provider) + GEPA (gradient-free, proven by SkillOpt at scale). That's 80% of the value for 20% of the effort. MemGrad textual gradients are interesting but unproven at scale — treat as Phase 4 research. The RL-based optimizer requires substantial infrastructure — gate behind measured demand."

**Senior Backend Engineer (MLOps):** "The safety validator should be the FIRST thing built, not the last. If you optimize without safety gates, you risk misevolution from the first epoch. Build the validator in Phase 1 even if you don't enable optimization until Phase 2. The rejected-edit buffer is critical — without it, edit cycles oscillate between the same unhelpful mutations. Also: the holdout evaluation set must be large enough for statistical significance — at least 10-20 tasks per skill."

**Senior Security Engineer:** "The DGM harness self-rewriting (Phase 4) is the highest-risk feature in the entire Lyra upgrade. An agent that can modify its own codebase could accidentally (or adversarially) disable safety features. The human-in-the-loop gate is essential but may not be sufficient — a sufficiently sophisticated evolved agent could modify the gate itself. Solution: the safety validator must be a separate, immutable service that the optimization layer cannot modify."

**Adversarial Skeptic:** "The value argument for skill optimization is strong (SkillOpt shows +23 points, MetaAgent-X shows 38% average). But the cost argument is weak — each optimization epoch costs $0.50-2.00 in API calls, and you need 5-10 epochs per skill. For a small skill registry (say 50 skills), that's $250-1000 per full optimization run. This is only worthwhile if skills are reused across many sessions. Prioritize optimizing the most-used skills first."

**Resolution:** Phase 1 ships TF-TTCL + Safety Validator (no optimization without safety gates). Phase 2 ships GEPA/SkillOpt for the top 10 most-used skills only (validate ROI before optimizing all 50+ skills). Phase 3 ships MemGrad textual gradients + Misevolve monitor. Phase 4 ships MetaAgent-X RL (gated behind usage data showing need for workflow-level optimization) + DGM harness rewriting (gated behind separate risk assessment). Safety validator is immutable and provider-isolated from the optimization pipeline.

## 9. References
- SkillOpt: https://github.com/microsoft/SkillOpt
- MetaAgent-X: https://arxiv.org/abs/2605.14212
- MemGrad: https://openreview.net/forum?id=GeaPE7iw1V
- TF-TTCL: https://arxiv.org/abs/2604.13552
- DGM: https://arxiv.org/abs/2505.22954
- DGM-H (HyperAgents): https://arxiv.org/abs/2603.19461
- ADAS: https://arxiv.org/abs/2408.08435
- AlphaEvolve: https://deepmind.google/blog/alphaevolve
- EvoTest: https://arxiv.org/abs/2510.13220
- "Your Agent May Misevolve": https://arxiv.org/abs/2509.26354

## 10. Changelog
- Run 1: Initial plan written — 4-layer optimizer, safety validator, training-free through RL-based optimization, harness self-rewriting gate
