# Brainstorm — Skills System (§4.4)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Source Techniques Gathered

| Technique | Source | Core Idea | Key Numbers |
|-----------|--------|-----------|-------------|
| Agent Skills Open Standard | Claude Code/Anthropic | SKILL.md with YAML frontmatter, progressive disclosure, subagent execution | ~100 tokens/skill at load time |
| SkillNet "npm for skills" | ZJU-NLP | End-to-end: search/install/create/evaluate/organize; auto-generates from GitHub repos/PDFs/conversations; 5 quality dimensions; skill graph | — |
| GEPA Reflective Evolution | GEPA (ICLR 2026 Oral) | Gradient-free reflective prompt evolution: generate variants → evaluate → keep winners → mutate → repeat | Matches GRPO, gradient-free |
| Feedback Descent | Uw5G3H26ps | Pairwise textual-rationale feedback at inference time | Matches GEPA, beats GRPO |
| MemGrad Textual Gradients | TCS (GeaPE7iw1V) | Textual gradients → memory + prompt updates without fine-tuning | No FT needed |
| TF-TTCL Training-Free | SCUT/Pazhou (2604.13552) | Explore-Reflect-Steer loop; contrastive distillation of superior-vs-inferior trajectories; training-free | Works on ANY provider |
| MAGEO Experience→Skill | (2604.19516) | Validated edit patterns distilled into reusable engine-specific SKILLS | — |
| DGM Self-Rewriting | UBC/Sakana (2505.22954) | Agents rewrite own harness code | SWE-bench 20%→50% |
| MetaAgent-X | Meta (2605.14212) | Designer+Executor co-evolution via GRPO | Qwen3 8B 38.33% avg |
| SERM Self-Evolving | NEU/ByteDance (2601.09515) | Sample miner + annotator with two-level agreement framework | Billion-request scale |
| EvoTest Evolutionary | He et al. (2510.13220) | Gradient-free evolutionary test-time learning; evolves whole agentic system after each episode | — |
| ADAS Meta Agent Search | UBC (2408.08435) | Meta agent searches over agent designs | ICLR 2025 |
| ReflecTool | Liao et al. (2410.17657) | Saves successful solving processes + tool-wise experience into long-term memory | — |
| Anthropic Context Cookbook | Anthropic (Mar 2026) | "Less is more": 400-line→15-line prompt, 12 tools→3 primitives | Pass rate 83%→92% |
| claude-skills Library | alirezarezvani | 330+ skills across engineering/research/PM/etc. | Multi-platform |

---

## Breakthrough Idea #1: Self-Evolving Skill Genome with GEPA-Style Gradient-Free Optimization

**Sources Fused:** GEPA (ICLR 2026 Oral) + SkillNet graph + MAGEO experience→skill + TF-TTCL training-free + MemGrad textual gradients

**Core Mechanism:**
1. **Skill Genome Representation:** Each skill is a structured genome (not flat markdown): name, trigger patterns, instructions, examples, tool bindings, dependencies, quality scores
2. **GEPA-Style Evolution Loop:**
   a. Generate N variants of a skill (vary instructions, examples, trigger patterns)
   b. Evaluate each variant on a task suite (held-out test tasks)
   c. Keep top-K variants, mutate (crossover between variants, add/remove examples, rephrase instructions)
   d. Repeat until convergence or budget exhausted
   e. Promote winner to production
3. **Training-Free for Closed Providers (TF-TTCL):**
   - Explore: multi-agent role-play diversifies trajectories using the skill
   - Reflect: Contrastive distillation of superior vs inferior trajectories into explicit textual rules
   - Steer: Update skill content with extracted rules, contextual retrieval at inference
4. **MemGrad Integration:** When batched feedback is available, compute textual gradients (what worked, what didn't, why) and update skill genome retroactively
5. **Skill Graph (SkillNet):** Skills linked in similarity/composition/dependency graph. Evolution of one skill triggers re-evaluation of dependent skills.

**Why It Beats Individual Sources:**
- GEPA alone works on prompts, not structured skills with trigger patterns + tool bindings
- SkillNet's graph is static — no evolution
- TF-TTCL is generic — not applied to skill optimization
- MAGEO distills edits but doesn't have the evolutionary loop

**Why It Beats Baseline:**
- Lyra's skills are static Markdown files with manual creation
- Self-evolving skills improve over time without human intervention
- The skill graph enables dependency-aware evolution

**Failure Modes:**
- Evolution may overfit to eval tasks (mitigation: held-out validation, diversity constraints)
- GEPA requires an evaluator — quality depends on eval quality (mitigation: multi-dimensional eval rubric from SkillNet)
- Training-free approach may converge slower than gradient-based (mitigation: hybrid — TF-TTCL for closed providers, MemGrad for open)

**Impact:** 5 | **Effort:** 5 | **Risk:** Medium-High

---

## Breakthrough Idea #2: Harness-Level Skill Loader with Provider-Aware Degradation

**Sources Fused:** Claude Code Skills (progressive disclosure) + Anthropic Context Cookbook ("less is more") + SkillNet search/install + claude-skills library (330+ skills)

**Core Mechanism:**
1. **Progressive Disclosure (3 levels):**
   - Level 0 (always loaded): Skill name + one-line description + trigger keywords (~10 tokens/skill)
   - Level 1 (loaded on trigger match): Full SKILL.md body (instructions, constraints, examples)
   - Level 2 (loaded on task-relevant access): Referenced files, scripts, assets
2. **Harness-Level (Never Provider-API-Level):**
   - Skill loader reads SKILL.md from filesystem
   - Injects into outgoing `messages` array as a system/user message
   - Never depends on a provider-specific "skills" endpoint (no Claude/DeepSeek/GPT skills API exists)
3. **Provider-Aware Degradation:**
   - Per-provider compatibility matrix (see below)
   - Claude-only frontmatter (`model:`, subagent extensions) stripped/translated for non-Claude providers
   - Fallback trigger strategy: deterministic (keyword/embedding/rules) when model auto-trigger is unreliable (e.g., DeepSeek-V4-Flash triggers far less reliably than Claude Opus)
4. **"Less is More" Curation:**
   - Default: load top-10 skills by relevance (not all 330+)
   - Tool clearing: removed unused skill tools from context after N turns
   - Skill compaction: summarize skill content when near context limit

**Provider × Trigger Strategy:**
| Provider | Auto-Trigger Reliability | Recommended Strategy |
|----------|-------------------------|---------------------|
| Claude Opus/Sonnet | High (90%+) | Model-auto-trigger primary, keyword fallback |
| DeepSeek V4-Pro | Medium (70-80%) | Hybrid: keyword pre-filter + model selection |
| DeepSeek V4-Flash | Low (50-60%) | Deterministic (keyword + embedding) primary |
| GPT-5.x | High (85%+) | Model-auto-trigger primary |
| Open-weights (Llama) | Low-Medium (50-70%) | Deterministic primary |

**Why It Beats Baseline:**
- Lyra's current skill loading is all-or-nothing: all skills loaded, all content injected
- Progressive disclosure saves 80%+ of context tokens at startup
- Provider-aware degradation ensures skills work across all backends

**Impact:** 5 | **Effort:** 3 | **Risk:** Low

---

## Breakthrough Idea #3: Skill Creator from Execution Trajectories

**Sources Fused:** SkillNet auto-generation + MAGEO experience→skill + ReflecTool experience accumulation + DGM self-rewriting

**Core Mechanism:**
1. **Trajectory Capture:** Every agent execution is logged as a trajectory (task → actions → tool calls → results → success/failure)
2. **Pattern Extraction:**
   - Cluster successful trajectories by task type
   - Extract recurring action sequences, tool combinations, and heuristics
   - Identify the "critical path" — the minimal sequence that leads to success
3. **Skill Template Generation:**
   - LLM (cheap model via §4.5) generates SKILL.md from extracted patterns
   - Template: name, description, trigger patterns, step-by-step instructions, example trajectories, tool requirements
4. **Quality Evaluation (SkillNet rubric):**
   - 5 dimensions: Correctness, Completeness, Clarity, Reusability, Efficiency
   - Auto-evaluated on held-out tasks from same cluster
   - Score ≥ threshold → promote to candidate skill
5. **Human-in-the-Loop Gate:**
   - Candidate skills queued for human review
   - Preview: generated SKILL.md + eval scores + example trajectory
   - Accept → register in SkillRegistry; Reject → log feedback for improvement
6. **DGM-Style Harness Rewriting (advanced):**
   - When a skill repeatedly succeeds at a task type, the agent can propose code changes to the harness itself (e.g., add a new tool, optimize a hook, create a new agent type)
   - Human approval required for harness changes

**Why It Beats Baseline:**
- Lyra currently has NO skill creation — all skills must be manually written
- Auto-creation from trajectories means skills emerge from actual use
- Human-in-the-loop ensures quality without blocking progress

**Failure Modes:**
- Trajectory patterns may encode bad habits (mitigation: only use successful trajectories, quality eval)
- Generated skills may overfit to specific task instances (mitigation: generalization test on held-out tasks)
- Harness rewriting is dangerous without strong safety bounds (mitigation: sandbox + human approval)

**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

---

## Expert Check (Skills Personas)

**Senior AI Researcher:** "GEPA-style evolution is promising but the computational cost is high — N variants × K generations × evaluation budget. For a system with 330+ skills, full evolution is infeasible. Focus evolution on the top-10 most-used skills; for the long tail, use the cheaper TF-TTCL approach."

**Senior Backend Engineer:** "Idea #2 (harness-level loader) is the most important and lowest risk. It's the foundation everything else builds on. The progressive disclosure alone saves enormous context. Ship this first."

**Senior Safety Engineer:** "Idea #3 (skill creator from trajectories) raises the 'misevolution' risk from Shao et al. (2509.26354). Skills created from execution data may encode unsafe patterns. The human-in-the-loop gate is essential but must be genuinely reviewable — no auto-accept. Harness rewriting (DGM-style) should be behind a separate, stricter permission gate."

**Adversarial Skeptic:** "All three ideas add significant complexity. The simplest approach: just use claude-skills' 330+ pre-written skills and a basic keyword-based loader. That gets Lyra to parity with Claude Code's skill coverage at 10% of the effort. Why evolve skills when you can just write more of them?"

**Resolution:** Idea #2 (harness-level loader with progressive disclosure) is the immediate (A) parity tier — it's foundational and low-risk. Idea #1 (self-evolving via GEPA) is the (B) breakthrough tier — gated behind the loader shipping. Idea #3 (skill creator) is a Phase 2 feature — depends on both the loader and sufficient trajectory data. The Skeptic's "just use pre-written skills" is what the (A) tier ships — the (B) tier is what makes Lyra self-improving.
