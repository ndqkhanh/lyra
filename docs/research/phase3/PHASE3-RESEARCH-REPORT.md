# Phase 3 Research Report: Skills, Routing, and Self-Improvement

**Research Date:** 2026-05-31  
**Focus Areas:** §3.7 Skills Systems, §3.14 Model Routing, §3.18 Self-Improving Agents  
**Target:** Lyra Ultra Upgrade

---

## Executive Summary

This report synthesizes research across 23 systems in three critical domains for Lyra's Phase 3 upgrade:
- **12 Skills Systems** for agent capability management
- **5 Model Routing Systems** for cost-optimized inference
- **6 Self-Improving Agent Systems** for autonomous evolution

Key findings indicate that **SkillNet + SkillOpt** provide the strongest foundation for skills management, **RouteLLM + BEST-Route** offer production-ready routing, and **Darwin Gödel Machine** represents the state-of-the-art in self-improvement.

---

## §3.7 SKILLS SYSTEMS

### 1. SkillNet (ZJU-NLP)

**Source:** [zjunlp/SkillNet](https://github.com/zjunlp/SkillNet) | [arXiv:2603.04448](https://arxiv.org/abs/2603.04448)

**Design Pattern:**
- Unified ontology for structuring skills from heterogeneous sources
- Multi-dimensional evaluation: Safety, Completeness, Executability, Maintainability, Cost-awareness
- Rich relational modeling: similarity, composition, dependency between skills
- Large-scale "skill graph" knowledge base

**Benchmark Results:**
- Outperforms native skill provisioning and skill-free baselines
- Enables retrieval, composition, and reuse of procedural knowledge
- Scales to ecosystem-level skill organization

**Lyra Relevance:** ⭐⭐⭐⭐⭐
- Directly addresses skill discovery, evaluation, and composition
- Provides systematic framework for organizing Lyra's growing skill library
- Multi-dimensional evaluation aligns with Lyra's quality gates

**Adoption Strategy:**
1. Implement skill graph data structure in `lyra-core`
2. Add 5-dimension evaluation pipeline for skill validation
3. Build skill relation engine (similarity, composition, dependency)
4. Create skill discovery API for runtime loading

**Multi-Provider Notes:**
- Evaluation dimensions are provider-agnostic
- Skill graph structure works across DeepSeek, Anthropic, OpenAI
- Cost-awareness dimension needs provider-specific pricing data

**Impact × Effort:** HIGH × MEDIUM
- High impact: Transforms skill management from ad-hoc to systematic
- Medium effort: Requires new data structures but leverages existing skill format

**References:**
- [SkillNet Paper](https://arxiv.org/abs/2603.04448)
- [HuggingFace Blog](https://huggingface.co/blog/xzwnlp/skillnet)

---

### 2. SkillOpt (Microsoft Research)

**Source:** [arXiv:2605.23904](https://huggingface.co/papers/2605.23904) | Microsoft Research

**Design Pattern:**
- Text-space optimizer for agent skills (not model weights)
- Frozen agent + optimizer model proposing edits (additions, deletions, replacements)
- Validation-gated acceptance: edits only accepted if they improve held-out validation set
- Produces compact, human-readable SKILL.md files

**Benchmark Results:**
- +23.5 points average improvement for GPT-5.5 across QA, spreadsheet, embodied tasks
- 52/52 wins in comparative evaluations
- Zero deployment inference overhead

**Lyra Relevance:** ⭐⭐⭐⭐⭐
- "Gradient descent for SKILL.md" - systematic skill improvement
- Validation gates prevent skill degradation
- Human-readable output maintains transparency
- No runtime overhead (skills optimized offline)

**Adoption Strategy:**
1. Implement skill evaluation harness with validation splits
2. Build optimizer agent that proposes skill edits
3. Create acceptance gate based on validation performance
4. Add skill versioning to track optimization history

**Multi-Provider Notes:**
- Optimizer model can be any capable LLM (DeepSeek-V3, Claude Opus, GPT-5)
- Frozen agent can be different provider than optimizer
- Validation tasks should cover provider-specific strengths

**Impact × Effort:** VERY HIGH × MEDIUM
- Very high impact: Enables systematic, reproducible skill improvement
- Medium effort: Requires eval harness + optimizer loop

**References:**
- [SkillOpt Paper](https://huggingface.co/papers/2605.23904)
- [Blog: Your Skill File Now Has a Backward Pass](https://www.ikangai.com/your-skill-file-now-has-a-backward-pass/)

---

### 3. obra/superpowers

**Source:** [obra/superpowers](https://github.com/obra/superpowers)

**Design Pattern:**
- Agentic skills framework + software development methodology
- Community-editable skills repository
- Experimental skills lab for testing
- Integration with Claude Code's native skill system

**Benchmark Results:**
- Production-proven in Claude Code ecosystem
- Active community contributions
- Experimental lab validates new patterns before promotion

**Lyra Relevance:** ⭐⭐⭐⭐
- Demonstrates successful community-driven skill development
- Lab → production promotion pattern is valuable
- Methodology documentation provides best practices

**Adoption Strategy:**
1. Study superpowers methodology for skill authoring guidelines
2. Implement skill promotion pipeline (experimental → stable)
3. Create community contribution templates
4. Build skill testing framework

**Multi-Provider Notes:**
- Methodology is provider-agnostic
- Skill format compatible with Agent Skills standard
- Community patterns transferable across providers

**Impact × Effort:** MEDIUM × LOW
- Medium impact: Improves skill development process
- Low effort: Mostly process and documentation

**References:**
- [Main Repository](https://github.com/obra/superpowers)
- [Superpowers Lab](https://github.com/obra/superpowers-lab)

---

### 4. obsidian-skills (kepano)

**Source:** [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)

**Design Pattern:**
- Domain-specific skills for Obsidian: Markdown, Databases, JSON Canvas, CLI
- Teaches agents to use specific software capabilities
- Modular skill organization by feature area

**Benchmark Results:**
- Production-proven for Obsidian plugin development
- Demonstrates effective domain-specific skill packaging

**Lyra Relevance:** ⭐⭐⭐
- Pattern for domain-specific skill libraries
- Shows how to teach agents complex software APIs
- Modular organization is reusable

**Adoption Strategy:**
1. Create domain-specific skill packages for Lyra's core domains
2. Use similar structure for teaching Lyra-specific APIs
3. Build skill templates for common patterns

**Multi-Provider Notes:**
- Domain knowledge is provider-agnostic
- API teaching patterns work across all LLMs
- Syntax examples may need provider-specific adjustments

**Impact × Effort:** MEDIUM × LOW
- Medium impact: Improves domain-specific capabilities
- Low effort: Template-based approach

---

### 5. CLI-Anything (HKUDS)

**Source:** [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) | [CLI-Hub](https://clianything.cc/)

**Design Pattern:**
- Transforms any software into agent-controllable CLI with one command
- Generates complete CLI harnesses for GUI software
- No manual coding or brittle GUI automation required
- Produces CLIs with tests, docs, and REPL

**Benchmark Results:**
- Works with Claude Code, Cursor, any agent framework
- Can be applied to any software, codebase, or Web API
- Eliminates need for custom integration code

**Lyra Relevance:** ⭐⭐⭐⭐
- Enables Lyra to control arbitrary software without custom integrations
- Reduces integration effort for new tools
- Generated CLIs are testable and documented

**Adoption Strategy:**
1. Integrate CLI-Anything as tool generation capability
2. Build catalog of generated CLIs for common tools
3. Add runtime CLI generation for user-requested tools
4. Cache generated CLIs for reuse

**Multi-Provider Notes:**
- Generated CLIs are provider-agnostic
- Works with any agent that can call CLI commands
- Tool descriptions compatible with all function-calling formats

**Impact × Effort:** HIGH × MEDIUM
- High impact: Dramatically expands tool ecosystem
- Medium effort: Integration + catalog management

**References:**
- [GitHub Repository](https://github.com/HKUDS/CLI-Anything)
- [CLI-Hub](https://clianything.cc/)

---

### 6. academic-research-skills

**Source:** [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | [zechenzhangAGI/AI-research-SKILLs](https://github.com/zechenzhangAGI/AI-research-SKILLs)

**Design Pattern:**
- Workflow-based skills: research → write → review → revise → finalize
- Comprehensive library of AI research and engineering skills
- Evidence-based education skills (152 skills)
- PhD-level research infrastructure

**Benchmark Results:**
- Production-proven in academic workflows
- Maintained by Orchestra Research
- Compatible with Claude Code, Codex, Gemini

**Lyra Relevance:** ⭐⭐⭐⭐
- Lyra-research package can leverage these patterns
- Workflow structure applicable to other domains
- Shows how to package domain expertise

**Adoption Strategy:**
1. Import academic research skills into lyra-research
2. Adapt workflow pattern for other domains (engineering, design)
3. Build skill composition for multi-step workflows
4. Add domain-specific evaluation criteria

**Multi-Provider Notes:**
- Workflow patterns are provider-agnostic
- Research methodologies work across all LLMs
- Citation formats may need provider-specific handling

**Impact × Effort:** HIGH × LOW
- High impact: Dramatically improves research capabilities
- Low effort: Skills are ready to import

**References:**
- [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills)
- [AI Research SKILLs](https://github.com/zechenzhangAGI/AI-research-SKILLs)

---

### 7. CheetahClaws (SafeRL-Lab)

**Source:** [SafeRL-Lab/cheetahclaws](https://github.com/SafeRL-Lab/cheetahclaws)

**Design Pattern:**
- Python-native personal AI assistant for any model
- Autonomous 24/7 operation
- 9 specialized agents for multi-day research
- Sandboxed Python experiments + citation verification

**Benchmark Results:**
- Production-proven for autonomous research
- Multi-day task completion
- Safety through sandboxing

**Lyra Relevance:** ⭐⭐⭐
- Autonomous operation patterns applicable to Lyra
- Multi-agent coordination architecture
- Sandboxing approach for safe execution

**Adoption Strategy:**
1. Study autonomous operation patterns
2. Implement multi-day task persistence
3. Add sandboxed execution environments
4. Build agent coordination protocols

**Multi-Provider Notes:**
- Python-native design works with any LLM API
- Agent coordination is provider-agnostic
- Sandboxing is universal safety pattern

**Impact × Effort:** MEDIUM × MEDIUM
- Medium impact: Improves autonomous capabilities
- Medium effort: Requires infrastructure changes

---

### 8. Agent Skills Standard (agentskills/agentskills)

**Source:** [agentskills/agentskills](https://github.com/agentskills/agentskills) | [anthropics/skills](https://github.com/anthropics/skills)

**Design Pattern:**
- Open format for agent capabilities: folders of instructions, scripts, resources
- Simple, discoverable structure
- Compatible with multiple agent frameworks
- 40,000+ skills in SkillsMP marketplace

**Benchmark Results:**
- Industry standard adopted by Anthropic, Microsoft, Vercel
- Compatible with Claude Code, Cursor, GitHub Copilot, Codex, Antigravity
- Large ecosystem of community skills

**Lyra Relevance:** ⭐⭐⭐⭐⭐
- Lyra should adopt this standard for interoperability
- Access to 40,000+ existing skills
- Community contributions become possible

**Adoption Strategy:**
1. Migrate Lyra skills to Agent Skills format
2. Implement skill discovery from SkillsMP
3. Build skill validation for imported skills
4. Contribute Lyra-specific skills back to community

**Multi-Provider Notes:**
- Standard is explicitly multi-provider
- Skills work across all major agent frameworks
- Format supports provider-specific sections

**Impact × Effort:** VERY HIGH × LOW
- Very high impact: Unlocks entire skill ecosystem
- Low effort: Format is simple and well-documented

**References:**
- [Agent Skills Specification](https://github.com/agentskills/agentskills)
- [Anthropic Skills](https://github.com/anthropics/skills)
- [SkillsMP Marketplace](https://github.com/Karanjot786/agent-skills-cli)

---

### 9. Andrej Karpathy Skills (CLAUDE.md)

**Source:** [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)

**Design Pattern:**
- Single CLAUDE.md file with behavioral rules
- Four core principles derived from real-world LLM coding pain points
- Turns "overconfident juniors into disciplined engineers"
- 220,000+ combined GitHub stars across forks

**Benchmark Results:**
- Viral adoption across Claude Code community
- Documented reduction in common coding errors
- Simple, effective configuration approach

**Lyra Relevance:** ⭐⭐⭐⭐
- Demonstrates power of simple, focused rules
- Behavioral patterns applicable to Lyra
- Community validation of effectiveness

**Adoption Strategy:**
1. Extract core behavioral principles
2. Adapt for Lyra's multi-provider context
3. Add to Lyra's default system prompts
4. Test impact on error rates

**Multi-Provider Notes:**
- Principles are provider-agnostic
- May need different phrasing for different models
- Core behaviors (immutability, error handling) universal

**Impact × Effort:** HIGH × VERY LOW
- High impact: Reduces common errors
- Very low effort: Just configuration changes

**References:**
- [Karpathy Skills](https://github.com/multica-ai/andrej-karpathy-skills)
- [Blog Post](https://antigravity.codes/blog/karpathy-claude-code-skills-guide)

---

### 10. oh-my-openagent

**Source:** [code-yeongyu/oh-my-openagent](https://github.com/code-yeongyu/oh-my-opencode)

**Design Pattern:**
- Agent orchestration harness
- Multi-agent coordination
- Standards-aware agent teams
- Portable across Antigravity, Claude Code, Codex, OpenCode

**Benchmark Results:**
- Production-proven orchestration
- Active development and community

**Lyra Relevance:** ⭐⭐⭐
- Orchestration patterns applicable to Lyra
- Multi-agent coordination architecture
- Portability lessons for multi-provider support

**Adoption Strategy:**
1. Study orchestration patterns
2. Adapt coordination protocols for Lyra
3. Implement portable agent interfaces
4. Build team composition strategies

**Multi-Provider Notes:**
- Explicitly designed for multi-framework portability
- Coordination protocols are provider-agnostic
- Interface abstraction enables provider swapping

**Impact × Effort:** MEDIUM × MEDIUM
- Medium impact: Improves orchestration
- Medium effort: Requires architecture changes

---

### 11. alirezarezvani/claude-skills

**Source:** [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | [Claude Code Skill Factory](https://github.com/alirezarezvani/claude-code-skill-factory)

**Design Pattern:**
- Comprehensive skill collection for Claude Code
- Skill Factory toolkit for building production-ready skills
- 26+ domain packages (Tresor ready-to-use collection)
- Structured skill templates + workflow integration

**Benchmark Results:**
- Large community collection
- Production-ready templates
- Accelerates skill development

**Lyra Relevance:** ⭐⭐⭐⭐
- Skill Factory pattern accelerates Lyra skill development
- Domain packages provide starting points
- Templates ensure consistency

**Adoption Strategy:**
1. Import relevant domain packages
2. Adapt Skill Factory for Lyra's needs
3. Build Lyra-specific templates
4. Create skill generation workflows

**Multi-Provider Notes:**
- Skills are Claude-focused but adaptable
- Factory patterns are provider-agnostic
- Templates need multi-provider sections

**Impact × Effort:** HIGH × LOW
- High impact: Accelerates skill development
- Low effort: Templates and patterns ready to use

---

### 12. AgentSkillOS (Research)

**Source:** [arXiv:2603.02176](https://arxiv.org/abs/2603.02176)

**Design Pattern:**
- Ecosystem-scale skill organization and orchestration
- Benchmarking framework for agent skills
- Outperforms native skill provisioning and skill-free baselines

**Benchmark Results:**
- Systematic evaluation across multiple domains
- Demonstrates value of structured skill management
- Provides benchmarking methodology

**Lyra Relevance:** ⭐⭐⭐⭐
- Benchmarking framework for evaluating Lyra skills
- Ecosystem-scale organization principles
- Validation methodology

**Adoption Strategy:**
1. Implement AgentSkillOS benchmarking framework
2. Add skill performance tracking
3. Build comparative evaluation pipeline
4. Create skill quality metrics

**Multi-Provider Notes:**
- Benchmarking methodology is provider-agnostic
- Evaluation metrics work across all models
- Comparative analysis requires provider-specific baselines

**Impact × Effort:** HIGH × MEDIUM
- High impact: Enables systematic skill evaluation
- Medium effort: Requires benchmark infrastructure

---

## §3.7 SKILLS SYSTEMS: SYNTHESIS

**Top 3 Recommendations for Lyra:**

1. **SkillNet + SkillOpt** (CRITICAL PATH)
   - SkillNet provides systematic organization and evaluation
   - SkillOpt enables reproducible skill improvement
   - Combined: systematic discovery, composition, and optimization

2. **Agent Skills Standard** (FOUNDATION)
   - Adopt standard format for interoperability
   - Access 40,000+ existing skills
   - Enable community contributions

3. **CLI-Anything** (FORCE MULTIPLIER)
   - Dramatically expands tool ecosystem
   - Reduces integration effort
   - Enables user-requested tool support

**Implementation Priority:**
1. Phase 1: Adopt Agent Skills Standard (1 week)
2. Phase 2: Implement SkillNet graph structure (2 weeks)
3. Phase 3: Build SkillOpt evaluation harness (2 weeks)
4. Phase 4: Integrate CLI-Anything (1 week)

---
