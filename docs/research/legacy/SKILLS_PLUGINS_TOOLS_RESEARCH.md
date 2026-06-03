# Skills, Plugins, and Tools Systems Research

**Research Date:** 2026-05-29  
**Researcher:** Agent (general-purpose)  
**Mission:** Comprehensive analysis of skills, plugins, and tools systems for Lyra

---

## Executive Summary

This research analyzes 5 major skills/plugins systems and Claude Code's official architecture to inform Lyra's skills ecosystem design. Key findings:

1. **Skills are the universal abstraction** — all systems converge on markdown-based skill definitions with YAML frontmatter
2. **Plugins are containers** — they bundle skills, agents, hooks, MCP servers, and LSP servers into distributable packages
3. **Tools are primitives** — low-level operations (Read, Write, Bash, LSP) that skills compose
4. **Auto-evaluation is rare** — only SkillOS and academic-research-skills implement continuous learning loops
5. **Lyra already has 80% of the foundation** — skill loader, curator, ledger, compaction, and router exist

---

## 1. Research Targets Analysis

### 1.1 kepano/obsidian-skills (33,517⭐)

**Architecture:**
- Plugin-based distribution via `.claude-plugin/plugin.json`
- 5 skills: obsidian-markdown, obsidian-bases, json-canvas, obsidian-cli, defuddle
- Each skill is a directory with `SKILL.md` + optional reference docs
- Follows [Agent Skills specification](https://agentskills.io/specification)

**Key Patterns:**
```json
{
  "name": "obsidian",
  "version": "1.0.1",
  "description": "Create and edit Obsidian vault files...",
  "repository": "https://github.com/kepano/obsidian-skills",
  "keywords": ["obsidian", "markdown", "bases", "canvas"]
}
```

**Skill Structure:**
```markdown
---
name: obsidian-markdown
description: Create and edit Obsidian Flavored Markdown...
---

# Obsidian Flavored Markdown Skill

## Workflow: Creating an Obsidian Note
1. Add frontmatter with properties
2. Write content using standard Markdown
3. Link related notes using wikilinks
...
```

**Strengths:**
- Clean separation: plugin.json (metadata) + SKILL.md (content)
- Reference docs alongside skills (PROPERTIES.md, EMBEDS.md, CALLOUTS.md)
- Workflow-oriented structure (numbered steps)
- Marketplace-ready packaging

**Weaknesses:**
- No auto-evaluation or learning
- No skill versioning beyond plugin version
- No skill composition or dependencies

---

### 1.2 Imbad0202/academic-research-skills (23,771⭐)

**Architecture:**
- 4 top-level skills: deep-research, academic-paper, academic-reviewer, academic-pipeline
- 35+ modes across 38-agent ensemble
- v3.8 claim-faithfulness gate (L3 gap closure)
- v3.9.2 phase boundary fence (#133)
- Cross-model verification with `ARS_CROSS_MODEL=1`

**Plugin Manifest:**
```json
{
  "name": "academic-research-skills",
  "version": "3.9.4.2",
  "description": "Production-grade academic research pipeline...",
  "keywords": ["academic", "research", "writing", "review", 
               "deep-research", "literature-review", "systematic-review"]
}
```

**Key Innovation — Data Access Levels:**
```yaml
data_access_level: raw | redacted | verified_only
task_type: open-ended | outcome-gradable
```

**Integrity Gates:**
- Stage 2.5: Pre-review integrity check (15 fabricated refs + 3 statistical errors caught)
- Stage 4.5: Final integrity verification (zero regressions confirmed)
- 7-mode blocking checklist from AI research failure modes

**Strengths:**
- **Production-grade quality gates** — multi-stage verification
- **Cross-model adversarial review** — optional DA critique
- **Material Passport** — artifact reproducibility lockfile
- **Benchmark Report Schema** — honest comparison framework
- **Human-in-the-loop** — avoids full automation failure modes

**Weaknesses:**
- Monolithic skill structure (each skill is 1000+ lines)
- No skill auto-evolution (manual versioning)
- High token cost (~$4-6 per 15k-word paper)

---

### 1.3 multica-ai/andrej-karpathy-skills (161,355⭐)

**Architecture:**
- Single `CLAUDE.md` file with 4 principles
- Not a plugin — global instructions via `~/.claude/CLAUDE.md`
- Addresses LLM coding pitfalls identified by Andrej Karpathy

**The Four Principles:**

| Principle | Addresses | Implementation |
|-----------|-----------|----------------|
| **Think Before Coding** | Wrong assumptions, hidden confusion | State assumptions explicitly, present multiple interpretations |
| **Simplicity First** | Overcomplication, bloated abstractions | Minimum code, no speculative features |
| **Surgical Changes** | Orthogonal edits, touching unrelated code | Touch only what you must, match existing style |
| **Goal-Driven Execution** | Weak success criteria | Transform tasks into verifiable goals with tests |

**Strengths:**
- **Principle-based** — not prescriptive rules
- **Addresses root causes** — LLM behavioral patterns
- **Lightweight** — single file, no dependencies
- **Universal** — applies to any coding task

**Weaknesses:**
- Not a skill system — no discovery, versioning, or composition
- No enforcement mechanism — relies on LLM following instructions
- No metrics or feedback loop

---

### 1.4 MontrealAI/skillos (35⭐)

**Architecture:**
- **SkillOS loop:** Work → Trace → Learn → Skill → Test → Approve → Release → Improve
- Wealth accumulation proof: cost/job ↓, minutes/job ↓, quality ↑
- GitHub Actions automation for CI/CD
- Static HTML/CSS/JS website for demo

**Core Workflow:**
```text
1. Job execution creates trace and lesson
2. Lesson creates tested skill release
3. Skill improves future job performance
4. Metrics prove wealth accumulation
```

**Proof Report:**
```bash
python -m skillos.cli wealth-proof
# Generates docs/wealth_accumulation_proof.md
```

**Strengths:**
- **Self-improving loop** — every job teaches the network
- **Economic proof** — measurable cost/time reduction
- **CI/CD integration** — automated skill testing and release
- **Wealth accumulation** — one agent learns, all agents level up

**Weaknesses:**
- Early stage (35⭐ vs 161k for Karpathy)
- No API keys required (demo-only?)
- Limited documentation on skill format
- No marketplace or distribution mechanism

---

### 1.5 Claude Code Official Architecture

**Plugin System:**

```text
plugin/
├── .claude-plugin/
│   └── plugin.json          # Metadata, version, keywords
├── skills/                  # or commands/
│   ├── skill-name/
│   │   ├── SKILL.md
│   │   ├── reference.md     # Optional
│   │   └── scripts/         # Optional
│   └── another-skill/
│       └── SKILL.md
├── agents/                  # Subagent definitions
│   └── agent-name.md
├── hooks/
│   └── hooks.json           # Event handlers
├── .mcp.json                # MCP server config
└── lsp/                     # LSP server config
```

**Plugin Components:**

| Component | Location | Purpose |
|-----------|----------|---------|
| **Skills** | `skills/` or `commands/` | Reusable prompt-based workflows |
| **Agents** | `agents/` | Specialized subagents |
| **Hooks** | `hooks/hooks.json` | Event handlers (27+ events) |
| **MCP Servers** | `.mcp.json` | External tool/service connections |
| **LSP Servers** | `lsp/` | Code intelligence providers |
| **Monitors** | Plugin config | Background watchers |

**Tool System (40+ built-in tools):**

| Category | Tools | Permission |
|----------|-------|------------|
| **File** | Read, Write, Edit, Glob, Grep | Yes (Edit/Write) |
| **Code** | LSP, NotebookEdit | No (LSP), Yes (NotebookEdit) |
| **Shell** | Bash, PowerShell, Monitor | Yes |
| **Agent** | Agent, SendMessage, TeamCreate | No |
| **Web** | WebFetch, WebSearch | Yes |
| **Task** | TaskCreate, TaskUpdate, TaskList | No |
| **Skill** | Skill, ToolSearch | Yes (Skill) |
| **Plan** | EnterPlanMode, ExitPlanMode | No/Yes |
| **Worktree** | EnterWorktree, ExitWorktree | No |
| **Cron** | CronCreate, CronDelete, CronList | No |

**Hook Events (27+):**
- SessionStart, Setup, UserPromptSubmit, UserPromptExpansion
- PreToolUse, PermissionRequest, PermissionDenied
- PostToolUse, PostToolUseFailure, PostToolBatch
- SubagentStart, SubagentStop
- TaskCreated, TaskCompleted
- Stop, StopFailure
- TeammateIdle, InstructionsLoaded, ConfigChange
- CwdChanged, FileChanged
- WorktreeCreate, WorktreeRemove
- PreCompact, PostCompact
- Elicitation, ElicitationResult
- SessionEnd

**Strengths:**
- **Comprehensive** — skills, agents, hooks, MCP, LSP in one system
- **Event-driven** — 27+ lifecycle hooks for automation
- **Marketplace-ready** — plugin.json + npx skills installer
- **Tool composition** — skills compose 40+ built-in tools
- **Isolation** — worktree support for safe experimentation

**Weaknesses:**
- No auto-evaluation or learning loop
- No skill versioning beyond plugin version
- No skill composition or dependencies
- No metrics or performance tracking

---

## 2. Comparison Matrix

| Feature | Obsidian | Academic | Karpathy | SkillOS | Claude Code | Lyra (Current) |
|---------|----------|----------|----------|---------|-------------|----------------|
| **Skill Format** | SKILL.md | SKILL.md | CLAUDE.md | Custom | SKILL.md | SKILL.md |
| **Plugin System** | ✅ | ✅ | ❌ | ❌ | ✅ | ⚠️ (Planned) |
| **Auto-Evaluation** | ❌ | ⚠️ (Manual gates) | ❌ | ✅ | ❌ | ✅ (Curator) |
| **Self-Evolution** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ (GEPA, T2S) |
| **Skill Versioning** | Plugin-level | Plugin-level | N/A | ✅ | Plugin-level | ⚠️ (Ledger) |
| **Skill Composition** | ❌ | ⚠️ (Pipeline) | ❌ | ❌ | ❌ | ⚠️ (Router) |
| **Marketplace** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| **MCP Integration** | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Hooks** | ✅ | ❌ | ❌ | ❌ | ✅ (27+) | ✅ (HookEngine) |
| **Metrics** | ❌ | ⚠️ (Cost tracking) | ❌ | ✅ (Wealth proof) | ❌ | ✅ (Ledger, TO) |
| **Quality Gates** | ❌ | ✅ (7-mode) | ⚠️ (Principles) | ✅ (Test) | ❌ | ✅ (MAV, AS) |

**Legend:**
- ✅ Fully implemented
- ⚠️ Partially implemented or planned
- ❌ Not implemented

---

## 3. Key Insights

### 3.1 Skills Are the Universal Abstraction

All systems converge on:
- **Markdown format** with YAML frontmatter
- **Declarative metadata** (name, description, triggers)
- **Prose instructions** for LLM consumption
- **Optional reference docs** for complex domains

### 3.2 Plugins Are Distribution Containers

Successful plugins bundle:
- Multiple related skills (5-10 per plugin)
- Metadata for discovery (keywords, description)
- Version management (semantic versioning)
- Installation automation (npx, marketplace)

### 3.3 Tools Are Composable Primitives

Skills compose tools, not the reverse:
- **Tools** = low-level operations (Read, Write, Bash, LSP)
- **Skills** = high-level workflows (research, review, refactor)
- **Agents** = autonomous executors (CodeAgent, TestAgent)

### 3.4 Auto-Evaluation Is Rare But Valuable

Only 2/5 systems implement learning loops:
- **SkillOS:** Work → Trace → Learn → Skill → Test → Approve → Release
- **Lyra:** Ledger → Curator → Optimizer → Compactor

Most systems rely on manual curation and versioning.

### 3.5 Quality Gates Are Essential for Production

Academic-research-skills proves the value of:
- **Multi-stage verification** (Stage 2.5, Stage 4.5)
- **Cross-model adversarial review** (optional DA critique)
- **Claim-faithfulness audits** (L3 gap closure)
- **Human-in-the-loop** (avoids full automation failure modes)

---

## 4. Lyra's Current State

### 4.1 Existing Components

**Skills System (lyra-skills):**
- ✅ `SkillLoader` — discovers and loads SKILL.md files
- ✅ `SkillCurator` — grades skills with 5 tiers (promote/keep/watch/rewrite/retire)
- ✅ `SkillLedger` — tracks activations, successes, failures, utility scores
- ✅ `SkillRouter` — semantic matching and dispatch
- ✅ `SkillCompactor` — per-section tracking, merge, archive
- ✅ `SkillOptimizer` — auto-optimization (Phase O)
- ✅ `SkillExtractor` — Trace2Skill pipeline
- ⚠️ `SkillInstaller` — basic installation (no marketplace)

**Tools System (lyra-tools):**
- ✅ `ToolRegistry` — centralized catalog with 200+ planned tools
- ✅ `ToolCategory` — 20 toolsets (filesystem, code, security, network, git, obs)
- ✅ `ToolDisclosureLevel` — progressive disclosure (3 levels)
- ✅ 16 real implementations (file_ops, code_quality, secrets_scan, network_ops, git_ops, obs_health, memory_ops, model_routing, code_analysis, skill_ops)

**Evolution System:**
- ✅ `GEPA v2` — multi-agent prompt evolution
- ✅ `Trace2Skill` — auto-skill extraction
- ✅ `ARIS` — cross-model adversarial review
- ✅ `PRISM` — prompt reliability and auto-repair

**Safety & Quality:**
- ✅ `AgentShield` — 5 scanners, 102 rules
- ✅ `Multi-Agent Verifier` — executor→validator→critic
- ✅ `TokenObservatory` — 13 categories, 7 wastes
- ✅ `Audit Engine` — HIR replay

### 4.2 Missing Components

**Plugin System:**
- ❌ Plugin packaging (plugin.json, .claude-plugin/)
- ❌ Plugin marketplace integration
- ❌ Plugin versioning and dependencies
- ❌ Plugin installation automation

**Skill Composition:**
- ❌ Skill dependencies (skill A requires skill B)
- ❌ Skill pipelines (chain skills together)
- ❌ Skill parameters (pass data between skills)

**Hooks Integration:**
- ⚠️ HookEngine exists but not integrated with skills
- ❌ Skill-specific hooks (PreSkillUse, PostSkillUse)
- ❌ Skill lifecycle events (SkillInstalled, SkillUpdated)

**Marketplace:**
- ❌ Skill discovery UI
- ❌ Skill ratings and reviews
- ❌ Skill download statistics
- ❌ Skill update notifications

---

## 5. Recommendations

### 5.1 Adopt Claude Code Plugin Format

**Rationale:** Industry standard, marketplace-ready, well-documented.

**Action:**
1. Create `.claude-plugin/plugin.json` schema
2. Migrate existing skills to plugin structure
3. Add plugin installer (`lyra plugin install <name>`)
4. Support npx skills compatibility

### 5.2 Implement Skill Composition

**Rationale:** Enable complex workflows without monolithic skills.

**Action:**
1. Add `dependencies` field to SKILL.md frontmatter
2. Implement dependency resolution in SkillLoader
3. Add skill parameters for data passing
4. Create skill pipeline DSL (YAML or JSON)

### 5.3 Integrate Hooks with Skills

**Rationale:** Enable skill-specific automation and quality gates.

**Action:**
1. Add PreSkillUse/PostSkillUse hooks
2. Allow skills to declare their own hooks
3. Implement skill lifecycle events
4. Add skill-specific quality gates

### 5.4 Build Skill Marketplace

**Rationale:** Enable community contributions and discovery.

**Action:**
1. Create skill registry API
2. Build skill discovery UI (TUI + Web)
3. Add skill ratings and reviews
4. Implement skill update notifications

### 5.5 Enhance Auto-Evaluation

**Rationale:** Lyra already has curator and ledger — extend to full learning loop.

**Action:**
1. Implement SkillOS-style learning loop
2. Add automatic skill rewriting (curator → optimizer → test → deploy)
3. Implement wealth accumulation metrics
4. Add cross-skill performance comparison

---

## 6. Implementation Roadmap

### Phase 1: Plugin System Foundation (2 weeks)
- [ ] Define plugin.json schema
- [ ] Implement plugin loader
- [ ] Migrate 10 existing skills to plugin format
- [ ] Add `lyra plugin install/list/remove` commands

### Phase 2: Skill Composition (2 weeks)
- [ ] Add dependency resolution
- [ ] Implement skill parameters
- [ ] Create pipeline DSL
- [ ] Add 5 composite skills as examples

### Phase 3: Hooks Integration (1 week)
- [ ] Add PreSkillUse/PostSkillUse hooks
- [ ] Allow skills to declare hooks
- [ ] Implement skill lifecycle events
- [ ] Add 3 quality gate examples

### Phase 4: Marketplace MVP (3 weeks)
- [ ] Build skill registry API
- [ ] Create TUI discovery interface
- [ ] Add skill ratings/reviews
- [ ] Implement update notifications

### Phase 5: Enhanced Auto-Evaluation (2 weeks)
- [ ] Implement full learning loop
- [ ] Add automatic skill rewriting
- [ ] Implement wealth accumulation metrics
- [ ] Add cross-skill performance dashboard

**Total:** 10 weeks (2.5 months)

---

## 7. References

1. kepano/obsidian-skills: https://github.com/kepano/obsidian-skills
2. Imbad0202/academic-research-skills: https://github.com/Imbad0202/academic-research-skills
3. multica-ai/andrej-karpathy-skills: https://github.com/multica-ai/andrej-karpathy-skills
4. MontrealAI/skillos: https://github.com/MontrealAI/skillos
5. Claude Code Plugins Reference: https://code.claude.com/docs/en/plugins-reference
6. Claude Code Tools Reference: https://code.claude.com/docs/en/tools-reference
7. Agent Skills Specification: https://agentskills.io/specification

---

**Next Steps:**
1. Review this research with the team
2. Prioritize recommendations based on business value
3. Create detailed technical specs for Phase 1
4. Begin implementation with plugin system foundation
