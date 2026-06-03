<table width="100%"><tr><td style="background: linear-gradient(135deg, #8b5cf6, #a78bfa, #c084fc); padding: 2px; border-radius: 8px;"><table width="100%"><tr><td style="background: #0d1117; padding: 12px 20px; border-radius: 6px;">

# <span style="color: #c084fc;">Changelog</span>

</td></tr></table></td></tr></table>

All notable changes to the Lyra project.

---

## <img src="https://img.shields.io/badge/3.0-UPCOMING-ef4444?style=for-the-badge&labelColor=1e1e2e">

### Breakthrough Release — 4-Phase Roadmap

Based on the [lyra-upgrade/](lyra-upgrade/) research corpus: 340+ sources deep-read, 3-round adversarial architecture debate, cross-source synthesis. Lyra is 2-4 years behind the frontier on every dimension — this release closes the gap.

<table width="100%"><tr><td style="background: linear-gradient(135deg, #ef444415, #f8717110); border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 0 8px 8px 0;">

#### <span style="color: #f87171;">Phase 1 — Foundation (Months 1-2): "Useful Single-Session Lyra"</span>
- **Provider abstraction layer** + 3-tier task-type router (Impact: 5, Effort: 3)
- **Embedding search** + hybrid retrieval for memory (Impact: 5, Effort: 2)
- **Port 330+ claude-skills** + progressive disclosure loader (Impact: 5, Effort: 3)
- **EnterWorktree tool** — standalone worktree isolation (Impact: 4, Effort: 2)
- **Core tools**: Bash, Read, Write, Edit, Glob, Grep (Impact: 5, Effort: 3)
- **25+ lifecycle hook events** (Impact: 4, Effort: 2)
- **Deny-first permission model** (Impact: 4, Effort: 2)
- 4 color themes + keybindings config

**Phase 1 outcome:** Lyra works as a capable single-session agent with model routing, semantic memory, 330+ skills, worktree isolation, and proper tools + hooks + permissions.

#### <span style="color: #fbbf24;">Phase 2 — Graph + Workflows (Months 3-4): "Multi-Agent Lyra"</span>
- **Graph memory** (Zettelkasten) + LP-RAG link prediction + cost-sensitive routing (Impact: 5, Effort: 4)
- **Dynamic workflow engine**: agent/parallel/pipeline primitives (Impact: 5, Effort: 4)
- **Auto-compaction** + Anthropic 3-strategy framework + lean-ctx output compression (Impact: 5, Effort: 3)
- **Langfuse/Phoenix tracing** + token observatory + τ-bench eval harness (Impact: 4, Effort: 3)
- **MCTS planning layer** (AFlow + SWE-Search pattern, +23% SWE-Solve) (Impact: 4, Effort: 4)
- **Bundled deep-research workflow** (fan-out -> cross-check -> cited report) (Impact: 5, Effort: 3)
- Token accounting per session + cost dashboard

**Phase 2 outcome:** Lyra can fan out sub-agents with structured workflows, graph memory, context management, and deep research capability — all in a single session.

#### <span style="color: #34d399;">Phase 3 — Fleet + Voice (Months 5-7): "Unattended Fleet Lyra"</span>
- **Supervisor daemon** + fleet view TUI + background sessions (Impact: 5, Effort: 5)
- **Continuous-operation loop** — unattended sessions, cheap row summaries (Impact: 5, Effort: 4)
- **Push-to-talk voice mode** (Whisper + Kokoro, provider-swappable) (Impact: 5, Effort: 4)
- **LLM-based dreaming engine** (review -> dedup -> reorganize) (Impact: 5, Effort: 4)
- **Steer-by-exception**: peek/reply/attach from fleet view (Impact: 4, Effort: 3)
- **MCP server integration** + bundle top-10 MCP servers (Impact: 4, Effort: 3)
- Plugin system + checkpointing + session resume

**Phase 3 outcome:** Lyra runs unattended fleets, speaks/understands voice, consolidates memories during idle, and steers by exception.

#### <span style="color: #a78bfa;">Phase 4 — Self-Evolution + Desktop + Safety (Months 8-9): "Self-Improving Omni-Agent"</span>
- **Anonymized bias-corrected adversarial verification** (3 verifiers + skeptic, >=2/3 voting) (Impact: 5, Effort: 3)
- **GEPA-style skill evolution** + "Misevolve"-informed safety validator (Impact: 5, Effort: 5)
- **Self-evolving skills** (trajectory -> pattern -> skill) (Impact: 5, Effort: 4)
- **lyra-desktop** (Electron/React GUI + multimodal I/O) (Impact: 5, Effort: 5)
- **5-layer defense-in-depth** (LlamaFirewall + NeMo + sandboxing + Progent SMT) (Impact: 5, Effort: 5)
- Uncertainty estimation + confidence calibration (Impact: 4, Effort: 3)
- RAG pipeline + code indexing + freshness management (Impact: 4, Effort: 4)
- Full-duplex voice: barge-in, streaming TTS, emotion (Impact: 4, Effort: 4)
- **Field-theoretic dreaming** (PDE consolidation) — gated behind bake-off (Impact: 5, Effort: 5)

**Phase 4 outcome:** Lyra is a self-improving, safety-gated, desktop-capable omni-agent with full-duplex voice, adversarial verification, and RL-optimized skills.

**References:** [MASTER-PLAN.md](lyra-upgrade/MASTER-PLAN.md) | [BREAKTHROUGH-ARCHITECTURE.md](lyra-upgrade/BREAKTHROUGH-ARCHITECTURE.md) | [SYNTHESIS.md](lyra-upgrade/SYNTHESIS.md) | [ARCHITECTURE-DEBATE.md](lyra-upgrade/ARCHITECTURE-DEBATE.md)

</td></tr></table>

---

## <img src="https://img.shields.io/badge/7.2.1-2026--05--31-f97316?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #fb923c;">🚀 Ultra Upgrade — 9 Tiers Shipped</span>

<table width="100%"><tr><td style="background: linear-gradient(135deg, #f9731615, #fb923c10); border-left: 4px solid #f97316; padding: 12px 16px; border-radius: 0 8px 8px 0;">

#### <span style="color: #f97316;">Tier 1 — Provider & Reasoning Foundation</span>
- **`lyra-effort`**: 6-level effort scale (low→ultracode) with per-provider mapping
- **`lyra-provider`**: AbstractProvider protocol, Anthropic/DeepSeek/OpenAI adapters, CapabilityMatrix, ProviderError taxonomy
- Ultracode = xhigh budget + orchestration toggle invariant (NOT a 6th API tier)
- 84 tests, 4/4 expert review PASS

#### <span style="color: #fb923c;">Tier 2 — Memory & Context Spine</span>
- **A-MEM Zettelkasten linking**: bidirectional typed links, auto-linking, Hebbian decay, BFS traversal
- **Write fast-path** (CRITICAL-1 fix): admission batching, backpressure signaling, 5s timeout
- **Cost-sensitive retrieval**: 5-tier cascade (Working→Episodic→Semantic→Archive→LLM)
- **`lyra-context`**: Auto-compaction engine with 4 progressive strategies
- 32 tests, 3/3 expert review PASS

#### <span style="color: #fbbf24;">Tier 3 — Orchestration & Autonomy (Lyra's Ultracode)</span>
- **`lyra-workflow`**: Dynamic Workflow Engine (16-concurrent cap, pause/resume, ScriptVM safety)
- **AVP middleware**: SABER MutationGate + 3-critic DecisionMatrix with consensus voting
- **Auto-Orchestrator**: keyword-based complexity estimator with configurable threshold
- 37 tests, 3/3 expert review PASS

#### <span style="color: #34d399;">Tier 4 — Capability Surface</span>
- **`lyra-plugins`**: Plugin manifest, discovery, sandboxed loading, permission gating
- **`lyra-hooks`**: PreToolUse/PostToolUse/Stop hooks with glob matcher
- **`lyra-sessions`**: Git-native session management with checkpointing
- **`lyra-tools/provider_bridge.py`**: Provider integration seam

#### <span style="color: #60a5fa;">Tier 5 — Skills System</span>
- **`lyra-skills/provider_bridge.py`**: Provider-agnostic skill validation, Claude frontmatter stripping, per-provider trigger strategies

#### <span style="color: #a78bfa;">Tier 7 — Reliability & Safety</span>
- **`lyra-safety`**: 4-layer defense-in-depth (InputGuard + CaMeL + NeMo + Progent)
- **EvolutionSafetyGate**: 5-gate pipeline for skill/memory evolution safety
- **MisevolveDefense**: alignment drift detection + checkpoint/rollback
- CRITICAL-3 fix: explicit fail-open/fail-closed per layer
- 23 tests, 95% coverage, 2/2 expert review PASS

#### <span style="color: #f472b6;">Review & Remediation</span>
- 6 review gates executed with independent expert panels
- 3 CRITICAL/HIGH findings remediated (API key leak, aiohttp error swallowing, dual-truth capabilities)
- Independent end-to-end audit against BREAKTHROUGH-ARCHITECTURE.md

</td></tr></table>

#### Shipped Packages (9 new)
`lyra-effort` · `lyra-provider` · `lyra-workflow` · `lyra-safety` · `lyra-context` · `lyra-hooks` · `lyra-sessions` · `lyra-plugins` · provider bridges (tools + skills)

#### Extended Packages (4)
`lyra-router` · `lyra-memory` · `lyra-tools` · `lyra-skills`

#### Architecture Invariants Verified
✅ Ultracode = xhigh + orchestration · ✅ Provider heterogeneity at boundary · ✅ 3-critic AVP consensus · ✅ CRITICAL-1 fix (fast-path + batching + backpressure) · ✅ CRITICAL-3 fix (fail-open/fail-closed per layer) · ✅ API key masking in logs · ✅ Skills harness-level + provider-agnostic

---

## <img src="https://img.shields.io/badge/7.1.0-2026--05--27-8b5cf6?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #c084fc;">AGI Ultra Upgrade — 6 Phases Complete</span>

<table width="100%"><tr><td style="background: linear-gradient(135deg, #7c3aed15, #8b5cf610); border-left: 4px solid #8b5cf6; padding: 12px 16px; border-radius: 0 8px 8px 0;">

#### <span style="color: #a78bfa;">Phase 4 — Agent Fleet: Parallel Fan-Out + Squads</span>
- FleetOrchestrator for parallel fan-out execution
- SquadLead with role-based topology (PM/Architect/Engineer/QA)
- RecursiveLink latent-space inter-agent communication (75.6% token reduction)
- Shared task lists with polling and inter-agent messaging
- Worktree isolation for subagent execution

#### <span style="color: #818cf8;">Phase 3 — L0-L3 Memory Architecture + KG Integration</span>
- 8-level memory hierarchy: Sensory → Episodic → Semantic → Procedural → Strategic → Meta → Collective → Eternal
- Dream 4-phase consolidation: Orient → Gather → Consolidate → Prune
- A-MAC 5-factor admission control (utility, confidence, novelty, recency, type)
- CoMem async memory pipeline (n-step-off decoupled, 1.4x latency improvement)
- Knowledge Graph pre-indexing with temporal KGs
- Hybrid BM25+vector retrieval with RRF fusion and MRAgent reconstruction
- Dual-process retrieval: System 1 (<50ms fast) + System 2 (<200ms deliberate)

#### <span style="color: #60a5fa;">Phase 2 — 4-Layer Intelligent Router + Cost Cascading</span>
- 5-layer task-aware routing: classify → estimate → match → optimize → history
- Confidence-thresholded escalation to stronger models
- Cost cascade chains with automatic fallback across 16+ providers
- Performance history tracking for learned routing decisions

#### <span style="color: #f87171;">Phase 1 — Parallax COS Safety Architecture</span>
- Cognitive-Executive structural separation (98.9% block rate)
- 6-layer safety: Input Validation → COS Split → Permission Gating → Multi-Agent Validation → Behavioral Monitoring → Continuous Assurance
- AgentShield with 5 scanners and 102 rules
- TokenObservatory with 13 categories and 7 waste pattern detectors
- PRISM drift detection with auto-repair via GEPA re-optimization
- ARIS 3-stage adversarial review (integrity → claim → audit)

</td></tr></table>

### <span style="color: #34d399;">Phase 34 — Production Deployment & Safety</span>
- Production-ready deployment pipeline with canary releases
- PRISM continuous monitoring for prompt drift detection
- Auto-rollback on regression detection
- Cross-model verification safety guarantees

### <span style="color: #fbbf24;">Phase 33 — Knowledge Graph & Pre-Indexing</span>
- Pre-indexed temporal knowledge graphs for codebase understanding
- Causal graph construction and counterfactual reasoning
- Graph-based agent memory with entity linking and deduplication
- DCI zero-index retrieval for direct corpus interaction

### <span style="color: #f472b6;">Phase 32 — Self-Improvement Engine</span>
- Meta-Harness outer-loop harness code optimization (+7.7pts, 4x fewer tokens)
- AEvo meta-editor for procedure evolution (26% relative improvement)
- GEPA v2 multi-agent prompt evolution with Pareto frontier selection
- Trace2Skill automatic skill extraction from successful execution traces

### <span style="color: #fb923c;">Phase 31 — UI/UX Transformation</span>
- Complete Ink/React 19 TUI rewrite with 25 theme presets
- 40+ keybindings with vim mode integration
- Claude Code-style terminal interface with Warp block model
- CESP v1.0 voice protocol with 6-layer sound pack hierarchy
- Fantasy voice packs: Warcraft III Peon, StarCraft Marine, Cyberpunk Netrunner

---

## <img src="https://img.shields.io/badge/7.0.0-2026--05--27-7c3aed?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #a78bfa;">Phase 5: Breakthrough Production (5.1–5.4)</span>

<table width="100%"><tr><td style="background: linear-gradient(135deg, #7c3aed15, #3b82f610); border-left: 4px solid #7c3aed; padding: 12px 16px; border-radius: 0 8px 8px 0;">

#### <span style="color: #c084fc;">Phase 5.4 — Production Consolidation</span>
- **UI**: New components (AgentTree, Markdown, ModelPicker, PhaseTracker), hooks, modes (Debug/Standard/Minimal), render optimization utilities, vitest test infrastructure
- **Model Router v2**: Task classifier, complexity estimator, confidence escalation, performance history tracking
- **Continual Learning**: Instinct module (TDD patterns, codebase conventions), Metaclaw module (cross-session learning)
- **Production Hardening**: Conformal prediction, escape prevention, failure pattern detection, reliability scoring, trajectory analysis
- **Evolution Phase 3**: Restructured into analysis/generation/sandbox subpackages with dedicated models and tests
- **Reasoning**: ReAct engine (Reason + Act interleaved), updated reasoning types, engine test suite
- **Core**: API module (core/errors/response), messaging module (eventbus/message/router/types), breakthrough tests
- **New packages**: lyra-integrity (ARIS 3-stage adversarial review), lyra-tools (code quality, file ops, git ops, network ops, secrets scan, tool registry)
- **UI overhaul**: Ink-based TUI (lyra-ink package), comprehensive component library, slash command system, gateway client, theme presets

#### <span style="color: #818cf8;">Phase 5.3 — MCP Protocol Integration</span>
- MCP server + enterprise gateway with trust banners and injection guards
- Progressive tool discovery with deferred schema loading
- Bidirectional MCP: Lyra as consumer and server

#### <span style="color: #60a5fa;">Phase 5.2 — Skills Ecosystem v2</span>
- 56 skills across 14 packs
- SkillOpt text-space optimizer integration
- Cross-skill knowledge transfer with Skill Weaving

#### <span style="color: #34d399;">Phase 5.1 — NeuroMemory Architecture</span>
- A-MAC Admission Control for memory writes
- Health Monitor for memory system diagnostics
- Dream 4-phase consolidation (Orient→Gather→Consolidate→Prune)
- ICLR 2026 MemAgent Workshop papers integrated (A-Mem, MRAgent, MemGrad, CoMem, CraniMem, etc.)

</td></tr></table>

### <span style="color: #fbbf24;">Phase 4 — Production Hardening</span>
- Tool Pipelines with DAG-based execution
- Hot Reload for configuration changes
- Goal Decomposer for complex task breakdown
- Benchmark Harness with pass@k evaluation

### <span style="color: #f87171;">Phase 3 — Self-Improvement</span>
- 4-Gate Skill Validation pipeline
- Cross-Skill Knowledge Transfer
- GEPA v2 prompt evolution integration

### <span style="color: #fb923c;">Phase 2 — Compound Intelligence</span>
- Task Decomposer for hierarchical planning
- 5-Slot Model Router (reasoning/coding/quick/creative/planning)
- Latent Bridge for inter-agent state sharing
- Hash Editor for content-addressable edits
- Quality Arbiter for output validation

### <span style="color: #22d3ee;">Phase 1 — Safety Governance Framework</span>
- 4 approval gates (plan, auto-edit, bypass, auto-mode)
- Reasoning Monitor for chain-of-thought auditing
- Crypto Audit trail for tamper-proof logs
- Alignment Monitor for value drift detection

### <span style="color: #f472b6;">Plan 28 — Plugin Ecosystem + Theme Engine</span>
- Sound Effects System with 12 event categories
- Theme Engine with 12 curated themes (Catppuccin, Tokyo Night, Dracula, Nord, Gruvbox, etc.)
- Plugin architecture for extensibility

### <span style="color: #a78bfa;">Plan 27 — MemAgent Breakthrough Memory</span>
- 20 ICLR 2026 MemAgent Workshop papers integrated across 8 phases (27.1–27.8)
- Agentic Zettelkasten Memory (A-Mem), Active Memory Reconstruction (MRAgent)
- Neuroscience-Grounded Cognitive Architecture, MemGrad Self-Optimization
- CoMem Async Memory Pipeline, Cost-Sensitive Multi-Store Routing
- Modular Compression, Gated Consolidation, Memory Transplant, Heuristic Pool

### <span style="color: #34d399;">Plan 20 — Open-Ended Learner + Agent Arena</span>
- Challenge platform for agent evaluation
- Open-ended learning environment

### <span style="color: #60a5fa;">Plan 19 — Challenge Evaluation Engine</span>
- Multi-metric evaluation framework
- Adversarial challenge generation

---

## <img src="https://img.shields.io/badge/6.0.0-2026--05--25-6366f1?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #f87171;">Breaking Changes</span>

#### Single-Provider Model Routing
Replaced multi-provider fallback system with predictable single-provider routing.

<table width="100%"><tr><td style="background: #1e293b; padding: 12px 16px; border-radius: 8px;">

**Before (v5.x):**
```yaml
fallback_chain: [anthropic, deepseek, openai]  # Unpredictable cascading
```

**After (v6.0.0):**
```yaml
primary_provider: anthropic  # Pick ONE provider explicitly
enable_task_routing: true    # Smart routing within provider family
```

</td></tr></table>

**Why this change?**
- **Predictable**: Always know which provider you're using
- **Cost-aware**: Choose provider based on pricing (DeepSeek is 10-20x cheaper)
- **Quality-aware**: Choose provider based on model quality
- **Transparent**: Clear errors instead of silent fallbacks

### <span style="color: #34d399;">Added</span>

- **Provider-based model families**: Each provider now has a defined model family (reasoning/coding/quick/creative/planning tiers)
- **Session provider tracking**: `LYRA_ACTIVE_PROVIDER` env var tracks active provider
- **Config migration**: Automatic migration from `fallback_chain` to `primary_provider`
- **Provider routing API**: `route_model_for_task(prompt, provider)` routes within provider family
- **11 provider families**: Anthropic, DeepSeek, OpenAI, OpenAI-Reasoning, Gemini, xAI, Groq, Cerebras, Mistral, Qwen, Ollama

### <span style="color: #fbbf24;">Changed</span>

- **Config schema v4**: Replaced `fallback_chain` with `primary_provider` and `enable_task_routing`
- **Task routing**: Now routes within provider family instead of across providers
- **Auto mode**: Picks ONE provider and sticks with it (no more cascading)
- **llm_factory.py**: All provider builders now set `LYRA_ACTIVE_PROVIDER` env var
- **session.py**: Added `active_provider` field and `route_model_for_task()` method

### <span style="color: #f472b6;">Deprecated</span>

- **llm_fallback.py**: `FallbackExecutor` class deprecated (use `build_llm()` instead)
- **DEFAULT_FALLBACK_CHAIN**: Removed from public API
- **Cross-provider task routing**: No longer supported

### Migration

See [MIGRATION.md](./MIGRATION.md) for detailed migration guide.

**Quick migration:**
```bash
# Upgrade
pip install --upgrade lyra-cli

# Set primary provider
lyra config set primary_provider anthropic  # or deepseek, openai, etc.

# Verify
lyra config show
```

### Testing

- Added 37 unit tests for provider routing and config migration
- All tests passing with 100% coverage of new routing logic

---

## <img src="https://img.shields.io/badge/5.0.0-2026--05--24-8b5cf6?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #34d399;">Added</span>
- **135+ composable packages** across three tiers: Foundation, Breakthrough, AGI Ascent
- **Multi-agent orchestration** with PrimaryAgent + specialist agents (Code, Test, Review, Research)
- **Hierarchical 8-level memory system** with STM/LTM, hybrid BM25+vector retrieval, and consolidation
- **Hook system** for PreToolUse, PostToolUse, SessionStart, SessionEnd, and Stop events
- **Rule engine** across 10 categories (coding style, security, testing, patterns, etc.)
- **Skill registry** with 150+ trigger patterns and cross-source (ECC) import
- **AgentShield** security scanner: secrets, command injection, path traversal, SQLi, XSS
- **TokenObservatory** with 13 activity categories and 7 waste pattern detectors
- **TokenOptimizer** with model selection, context compression, and prompt caching
- **Cross-platform adapter layer** (Claude Code, Cursor, VS Code, JetBrains)
- **Task coordination**: allocator, load balancer, dependency manager, conflict resolver
- **ECC agent/skill import** with YAML frontmatter parsing
- **Unified agent registry** with multi-index dispatch
- **Deep reasoning engine** (CoT, tree search, multi-agent debate, hypothesis generation)
- **10-step research pipeline** with 7+ academic sources and citation traversal
- **Self-evolution** via GEPA prompt optimization and continuous learning
- Root-level `ARCHITECTURE.md` with Mermaid diagrams

### <span style="color: #fbbf24;">Changed</span>
- Migrated from Textual TUI to Typer CLI + prompt_toolkit REPL (93% code reduction)
- Migrated from single-package to monorepo architecture
- Split kernel (`lyra-core`) from application (`lyra-cli`)
- TypeScript UI repackaged as separate workspace modules (`ui-core`, `ui-terminal`, `ui-transport`)

### <span style="color: #f87171;">Removed</span>
- Textual-based TUI v1 (~18.5K lines removed)
- Legacy single-package structure

---

## <img src="https://img.shields.io/badge/4.0.0-2026--05--18-06b6d4?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #34d399;">Added</span>
- Multi-agent coordination (TaskAllocator, LoadBalancer, DependencyManager, ConflictResolver)
- Memory consolidation pipeline (STM → LTM with pattern extraction)
- Hook engine with priority-based async execution
- Rule engine with multi-category evaluation
- ECC agent integration framework

---

## <img src="https://img.shields.io/badge/3.0.0-2026--05--12-10b981?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #34d399;">Added</span>
- Agent base class with communication, memory, and execution tracking
- PrimaryAgent orchestrator with specialist delegation
- Short-term and long-term memory stores with JSON persistence
- Core task/result data models with validation
- Initial skill registry and parser

---

## <img src="https://img.shields.io/badge/2.0.0-2026--04--27-f97316?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #34d399;">Added</span>
- Multi-provider LLM support (Anthropic, OpenAI, DeepSeek, Gemini, xAI, Mistral)
- Streaming SSE responses
- Interactive CLI with slash commands
- Model picker UI with keyboard navigation
- Provider-agnostic AliasRegistry

---

## <img src="https://img.shields.io/badge/1.0.0-2026--04--15-ef4444?style=for-the-badge&labelColor=1e1e2e">

### <span style="color: #34d399;">Added</span>
- Initial release with Anthropic Claude integration
- Basic CLI with Typer
- Task-based model routing
- Configuration persistence (`~/.lyra/`)
