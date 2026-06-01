# Phase 3 Research Findings: Skills Systems & Model Routing

## Research Summary

Comprehensive analysis of 20+ skills systems and 5 routing frameworks to inform Lyra's Phase 3 architecture.

---

## §3.7 Skills Systems Research

| System | Stars | Key Innovation | Skill Format | Provider-Agnostic | Notes |
|--------|-------|----------------|--------------|-------------------|-------|
| **SkillNet** (ZJU-NLP) | N/A | Knowledge graph with semantic search API; 500K+ skills marketplace | Markdown packages with YAML frontmatter | ✅ Yes | REST API for search/download/create/evaluate; 5-dimensional quality scoring; relationship analysis (similar_to, belong_to, compose_with, depend_on) |
| **SkillOpt** (Microsoft) | 3,196 | Text-space optimization with validation gates; trajectory-driven skill evolution | Markdown documents (`best_skill.md`) | ✅ Yes | Trains skills like neural networks (epochs, batch size, learning rate); supports QA, embodied agents, math, code generation |
| **andrej-karpathy-skills** | 162,449 | Four principles addressing LLM failure modes | Single `CLAUDE.md` file | ✅ Yes | Think before coding, simplicity first, surgical changes, goal-driven execution; verification-centric approach |
| **obsidian-skills** (kepano) | 33,681 | Agent Skills specification (agentskills.io); cross-agent compatibility | `SKILL.md` per skill in `skills/` directory | ✅ Yes | Obsidian Markdown, Bases, JSON Canvas, CLI integration; marketplace-installable |
| **CLI-Anything** (HKUDS) | 41,362 | 7-phase automated CLI generation for any software; authentic integration | `SKILL.md` with YAML frontmatter + Click CLI | ✅ Yes | 2,330 passing tests across 18 apps; agent-native with `--json` flag; CLI-Hub meta-skill for discovery |
| **academic-research-skills** | 24,467 | 10-stage research pipeline with integrity gates | Multi-skill bundle (research/write/review/pipeline) | ✅ Yes | Human-in-the-loop design; 3-layer citation anchors; anti-hallucination infrastructure; Material Passport for cross-session resume |
| **claude-skills** (alirezarezvani) | 16,613 | 337 skills across 9 domains | Organized by domain/role | ✅ Yes | Engineering, marketing, product, compliance, C-level, research, business ops, commercial, finance, productivity |
| **SkillOS** (EvolvingAgentsLabs) | 35 | Skills as programs; markdown-based OS | Markdown with YAML frontmatter; 3-level hierarchy (Domain/Family/Skill) | ✅ Yes | 61% token reduction via lazy loading; Recursive Context Isolation for mid-tier models; dialects compress 50-99% |
| **CheetahClaws** | 703 | Python-native Claude Code reimplementation; 174-line agent loop | Markdown with argument substitution | ✅ Yes (8+ providers) | Multi-provider (Anthropic, OpenAI, Gemini, Kimi, Qwen, DeepSeek, MiniMax, Ollama); fork/inline execution modes; autonomous background agents |
| **oh-my-openagent** | 60,305 | Category-based model routing; hash-anchored edits (Hashline) | `SKILL.md` with embedded MCPs | ✅ Yes | Discipline agents (Sisyphus, Hephaestus, Prometheus, Oracle); Team Mode (8 parallel members); skill-embedded MCPs spin up on-demand |

### Key Patterns Identified

#### 1. Skill Representation Formats
- **Markdown + YAML frontmatter** (dominant): SkillNet, SkillOpt, SkillOS, obsidian-skills, CLI-Anything
- **Single-file guidelines** (minimalist): andrej-karpathy-skills
- **Multi-file bundles** (complex workflows): academic-research-skills
- **Domain-organized collections** (scale): claude-skills (337 skills across 9 domains)

#### 2. Discovery & Selection Mechanisms
- **Semantic search** (SkillNet): Vector similarity + keyword matching + category filtering
- **Marketplace** (obsidian-skills, academic-research-skills): Plugin-based installation
- **Lazy loading** (SkillOS): 3-level hierarchy with 61% token reduction
- **Intent-based activation** (academic-research-skills): Mode detection from natural language
- **Category-based routing** (oh-my-openagent): Request by category, not model name

#### 3. Quality Assurance
- **5-dimensional scoring** (SkillNet): Safety, Completeness, Executability, Maintainability, Cost-Awareness
- **Validation gates** (SkillOpt): Hard/soft/mixed gates for skill selection
- **Integrity checks** (academic-research-skills): Mandatory gates at stages 2.5 and 4.5
- **Relationship analysis** (SkillNet): Auto-discover similar_to, belong_to, compose_with, depend_on edges
- **Test coverage** (CLI-Anything): 2,330 passing tests across 18 applications

#### 4. Execution Patterns
- **Inline vs. Fork** (CheetahClaws): Run in current context or spawn isolated sub-agent
- **Background agents** (CheetahClaws, oh-my-openagent): Autonomous loops with stagnation detection
- **Team execution** (oh-my-openagent): Lead agent + 8 parallel members with dedicated tools
- **Recursive Context Isolation** (SkillOS): Fresh context per delegated agent (5.2x output improvement)

#### 5. Self-Improvement Mechanisms
- **Trajectory-driven optimization** (SkillOpt): Skills evolve based on execution traces
- **Relationship discovery** (SkillNet): Auto-analyze connections between skills
- **Material Passport** (academic-research-skills): Cross-session resume capability
- **Skill creation from logs** (SkillNet): Convert trajectories, GitHub repos, documents, prompts into skills

---

## §3.14 Model Routing Research

| Framework | Key Innovation | Routing Strategy | Cost Savings | Provider Support | Notes |
|-----------|----------------|------------------|--------------|------------------|-------|
| **RouteLLM** (lm-sys) | 4 trained routers (mf, sw_ranking, BERT, Causal LLM) | Calculate strong model win rate; route if > threshold | Up to 85% cost reduction at 95% GPT-4 performance | Any model pair via LiteLLM | Routers trained on preference data; transfer learning across model pairs |
| **BEST-Route** (Microsoft) | Dynamic sampling depth (best-of-n) | Route to model + number of samples based on query difficulty | Up to 60% cost reduction with <1% performance drop | Multi-model | Cheap models with multiple samples can beat expensive single-sample models |
| **HybridLLM** (Microsoft) | DeBERTa-based classifier with reward models | Binary routing between model pairs | Significant cost reduction (paper doesn't specify exact %) | Multi-model | Oracle reward model (armoRM) for ground truth; proxy reward model for runtime |
| **FrugalGPT** | LLM cascade strategy | Route through sequence of models, escalate only when necessary | Up to 98% cost reduction matching GPT-4; 4% accuracy improvement at same cost | Heterogeneous pricing across APIs | Learns query-specific routing patterns; prompt adaptation + LLM approximation + cascade |

### Key Routing Insights

#### 1. Routing Decision Mechanisms
- **Preference-based** (RouteLLM): Human preference data as training signal
- **Difficulty-based** (BEST-Route): Query difficulty determines model + sampling depth
- **Reward-based** (HybridLLM): Reward models score outputs for routing decisions
- **Cascade** (FrugalGPT): Sequential escalation through model tiers

#### 2. Cost Optimization Strategies
- **Threshold calibration** (RouteLLM): Adjust threshold to control strong model usage %
- **Multi-sampling** (BEST-Route): Generate multiple responses from cheap models
- **Early stopping** (FrugalGPT): Stop cascade when quality threshold met
- **Transfer learning** (RouteLLM): Routers maintain performance when models swapped

#### 3. Performance Metrics
- **Win rate** (RouteLLM): Conditional probability strong model beats weak model
- **Reward scores** (HybridLLM): armoRM oracle + proxy reward models
- **Accuracy vs. cost** (FrugalGPT): Pareto frontier optimization
- **Performance drop** (BEST-Route): <1% degradation acceptable for 60% cost reduction

---

## §3.18 Self-Improving Agents Research

| System | Key Innovation | Self-Improvement Mechanism | Validation | Results |
|--------|----------------|---------------------------|------------|---------|
| **Darwin Gödel Machine** | Empirical validation replaces formal proofs | Archive-based evolution; samples agent, generates variant, grows tree | Coding benchmarks (SWE-bench, Polyglot) | SWE-bench: 20.0% → 50.0%; Polyglot: 14.2% → 30.7% |
| **ADAS** (Microsoft) | Meta agent programs new agents in code | Progressively invents agents with novel designs; builds on archive of discoveries | Cross-domain transfer (coding, science, math) | Invented agents outperform hand-designed; maintain performance across domains/models |
| **SEAL** | Test-time training with self-generated data | Generate solutions → filter via self-consistency/reward → fine-tune → repeat | Self-consistency voting or learned reward functions | SQuAD: 75.7% → 81.0%; ARC: +2-3 percentage points |
| **Self-Challenging Agents** | Agents generate own training tasks | Challenger role creates Code-as-Task (instruction + verification + test cases); Executor trains on self-generated tasks | Programmatic verification functions | M3ToolEval & TauBench: 2× improvement in Llama-3.1-8B-Instruct |
| **ReflecTool** | Reflection on tool selection and execution | Two-stage reflection: validate tool choice → check result adequacy → revise if needed | Retrieval-augmented tool documentation | Medical QA: +2.5-6.0% accuracy; corrects 15-20% of suboptimal tool selections |
| **EvoTest** | Evolutionary test-time learning | Mutation + crossover + selection of test cases; multi-armed bandit for exploration/exploitation | J-TTL benchmark (text-based games) | Exposes agent brittleness not captured by static benchmarks |

### Self-Improvement Patterns

#### 1. Evolution Strategies
- **Archive-based** (Darwin, ADAS): Maintain growing tree of discoveries
- **Test-time training** (SEAL): Self-generate training data from unlabeled examples
- **Self-challenging** (Self-Challenging Agents): Create own tasks with verification functions
- **Reflection loops** (ReflecTool): Iterative self-assessment and revision

#### 2. Validation Approaches
- **Empirical benchmarks** (Darwin): Coding benchmarks replace formal proofs
- **Self-consistency** (SEAL): Voting across multiple solution attempts
- **Programmatic verification** (Self-Challenging Agents): Code-as-Task with test cases
- **Reward models** (SEAL, HybridLLM): Learned functions score quality

#### 3. Meta-Learning Capabilities
- **Code modification** (Darwin): System improves its own modification capabilities
- **Agent programming** (ADAS): Meta agent invents novel agent architectures
- **Skill optimization** (SkillOpt): Text-space training with validation gates
- **Adaptive testing** (EvoTest): Tests evolve to expose agent weaknesses

---

## §3.5 Relevant Papers

### Small Language Models for Agents (2506.02153)
**Key Finding**: SLMs are "sufficiently powerful, inherently more suitable, and necessarily more economical for many invocations in agentic systems."

**Routing Implications**:
- **SLMs for specialized, repetitive agent tasks**: Lower cost, sufficient capability for narrow functions
- **LLMs for general conversation**: When broad knowledge and conversational flexibility matter
- **Heterogeneous systems**: Mix both model sizes based on task requirements
- **LLM-to-SLM conversion algorithm**: Proposed for operational and economic impact

### Knowledge Access Beats Model Size (2603.23013)
**Note**: PDF content not fully extractable; requires text-readable format for detailed analysis.

**Inferred Implications**:
- Memory-augmented routing may outperform larger models
- Knowledge retrieval can compensate for smaller model capacity
- Persistent agents benefit from external knowledge access

---

## Cross-Cutting Insights

### 1. Provider-Agnostic Design Principles
✅ **All researched systems support provider-agnostic operation**:
- Markdown-based skill definitions (no provider-specific APIs)
- Standard tool interfaces (Read, Write, Bash, WebFetch)
- Model-agnostic prompting patterns
- Multi-provider support (CheetahClaws: 8 providers; oh-my-openagent: category-based routing)

### 2. Skill System Architecture Layers
1. **Storage Layer**: Markdown files with YAML frontmatter
2. **Discovery Layer**: Semantic search, marketplace, lazy loading, intent detection
3. **Quality Layer**: Validation gates, scoring, relationship analysis, integrity checks
4. **Execution Layer**: Inline/fork, background agents, team mode, context isolation
5. **Evolution Layer**: Trajectory-driven optimization, self-generation, reflection loops

### 3. Routing Architecture Layers
1. **Decision Layer**: Win rate calculation, difficulty assessment, reward scoring, cascade logic
2. **Optimization Layer**: Threshold calibration, multi-sampling, early stopping, transfer learning
3. **Measurement Layer**: Performance metrics, cost tracking, quality gates
4. **Adaptation Layer**: Self-improvement, empirical validation, meta-learning

### 4. Integration Opportunities
- **Skills ↔ Router**: Skill complexity metadata informs routing decisions
- **Router ↔ Memory**: Cheap model + memory for repeat queries (BEST-Route + Knowledge Access)
- **Skills ↔ Self-Improvement**: SkillOpt trajectory optimization + Darwin evolution
- **Router ↔ Self-Improvement**: ADAS meta-agent invents routing strategies

---

## Recommendations for Lyra Phase 3

### Skills System (§4.4)
1. **Adopt SkillNet architecture**: Knowledge graph + semantic search + 5-dimensional scoring
2. **Implement SkillOS lazy loading**: 3-level hierarchy for 61% token reduction
3. **Use SkillOpt optimization**: Trajectory-driven evolution with validation gates
4. **Support multiple formats**: Single-file (Karpathy), multi-file bundles (academic-research), domain collections (alirezarezvani)
5. **Enable self-improvement**: Combine SkillNet creation + SkillOpt optimization + Darwin evolution

### Model Router (§4.5)
1. **Adopt RouteLLM foundation**: 4 router types with preference-based training
2. **Add BEST-Route sampling**: Dynamic best-of-n for cheap models
3. **Implement FrugalGPT cascade**: Sequential escalation with early stopping
4. **Memory-augmented routing**: Cheap model + memory for repeat queries (Knowledge Access paper)
5. **Skills-aware routing**: Use skill complexity metadata to inform model selection

### Self-Improvement (§4.6)
1. **Darwin-style evolution**: Archive-based agent discovery with empirical validation
2. **ADAS meta-programming**: Meta agent invents novel architectures
3. **SkillOpt text-space training**: Optimize skills without weight updates
4. **ReflecTool reflection**: Two-stage validation of tool/skill selection
5. **EvoTest adaptive testing**: Evolutionary test generation to expose weaknesses

---

## Next Steps

1. ✅ Research complete (20+ skills systems, 5 routing frameworks, 6 self-improvement systems)
2. ⏳ Write `03-skills-system.md` — Provider-agnostic skills architecture plan
3. ⏳ Write `04-model-router.md` — Multi-provider routing architecture plan
4. ⏳ Validate designs against provider-agnostic mandate
5. ⏳ Report completion to parent agent
