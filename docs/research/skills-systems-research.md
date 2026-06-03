# Skills Systems Research for Lyra Section 4.4

**Date:** 2026-06-01
**Sources analyzed:**
- SkillNet (ZJU, arxiv 2603.04448) -- cloned from github.com/zjunlp/SkillNet
- claude-skills (Alireza Rezvani) -- cloned from github.com/alirezarezvani/claude-skills
- SkillOpt (Microsoft) -- cloned from github.com/microsoft/SkillOpt
- superpowers (Jesse Vincent / obra) -- cloned from github.com/obra/superpowers

---

## Table of Contents

1. [Skill Format / Schema Comparison](#1-skill-format--schema-comparison)
2. [Loading Mechanism](#2-loading-mechanism)
3. [Creation / Generation Pipeline](#3-creation--generation-pipeline)
4. [Quality Scoring / Evaluation](#4-quality-scoring--evaluation)
5. [Cross-Platform Compatibility](#5-cross-platform-compatibility)
6. [License and Attribution](#6-license-and-attribution)
7. [Transferable Design for Lyra Section 4.4](#7-transferable-design-for-lyra-section-44)

---

## 1. Skill Format / Schema Comparison

### 1.1 SkillNet

**Canonical SKILL.md YAML frontmatter fields:**
```yaml
---
name: skill-name-in-kebab-case    # required
description: <when-to-use trigger statement>  # required
---
```

**Directory structure:**
```
skill-name/
  SKILL.md              # required: YAML frontmatter + markdown instructions
  scripts/              # optional: executable Python/Bash code
  references/           # optional: documentation loaded into context on demand
  assets/               # optional: templates, icons, fonts
```

**Design principles (SkillNet v1):**
- Context is a public good -- be concise; only essential context in SKILL.md
- Progressive disclosure -- SKILL.md lean; heavy docs in references/; deterministic logic in scripts/
- Degrees of freedom -- scripts (low freedom) for fragile/error-prone sequences; text instructions (high freedom) for creative decisions

**Ontology layers (3-level):**
1. **Skill Taxonomy** -- multi-level hierarchy using category + tag relations (10 categories: Development, AIGC, Research, Science, Business, Testing, Productivity, Security, Lifestyle, Other)
2. **Skill Relation Graph** -- instantiated Skill Entities with 4 edge types: `similar_to`, `compose_with`, `belong_to`, `depend_on`
3. **Skill Package Library** -- physical `packaged_in` relation grouping skills into deployable bundles

### 1.2 claude-skills

**Canonical SKILL.md YAML frontmatter fields:**
```yaml
---
name: skill-name                    # required, kebab-case
description: "When to use..."       # required, "pushy" triggers
license: MIT                        # recommended
metadata:
  version: 1.0.0                    # semantic version
  author: Alireza Rezvani
  category: domain-name
  updated: YYYY-MM-DD
---
```

**Directory structure (per SKILL-AUTHORING-STANDARD.md):**
```
skill-name/
  SKILL.md                # <=10KB -- workflow, decisions, actions
  references/             # deep knowledge, loaded on demand
    topic-guide.md
    topic-benchmarks.md
    topic-examples.md
  templates/              # user-fillable templates with placeholder markers
    artifact-template.md
  scripts/                # Python stdlib-only, CLI-first automation
    verb_noun.py          # snake_case convention, scoring tools output 0-100
  agents/                 # sub-agent definitions (cs-* prefix)
    cs-role.md
  commands/               # slash commands (/command-name.md)
    action.md
  evals/
    evals.json            # test cases + assertions
  .claude-plugin/
    plugin.json           # name, version, description, skills, commands, agents
```

**Naming rules:**
- Skill folder: `kebab-case`
- Python scripts: `snake_case`
- Reference docs: `kebab-case.md`
- Templates: `kebab-case-template.md`
- Agent definitions: `cs-<role-name>.md` (cs prefix for ClawHub slug conflicts only)
- Commands: `/cs:<action>` slash commands

**10 Authoring Patterns:**
1. **Context-First** -- check for domain context (`[domain]-context.md`) before asking questions
2. **Practitioner Voice** -- "You are an expert in [domain]. Your goal is [outcome]."
3. **Multi-Mode Workflows** -- 2-3 natural entry points (build from scratch, optimize existing, situation-specific)
4. **Related Skills Navigation** -- curated WHEN/NOT disambiguation
5. **Reference Separation** -- SKILL.md <=10KB, heavy content in references/
6. **Proactive Triggers** -- 4-6 triggers per skill, condition -> flag -> recommended action
7. **Output Artifacts** -- map common requests to specific deliverables
8. **Quality Loop** -- confidence tagging (verified/medium/assumed)
9. **Communication Standard** -- bottom line first, what+why+how, actions have owners+deadlines
10. **Python Tools** -- stdlib-only, CLI-first, JSON output, embedded sample data

### 1.3 SkillOpt

**Canonical skill document format:**
```markdown
# Task Strategy
## General Approach
- Break complex problems into sub-steps
- Always verify intermediate results

## Common Patterns
- When you see X, try approach Y
- Avoid Z because it leads to errors

## Edge Cases
- If the input contains A, handle it specially by...

## Output Format
- Always include reasoning before the answer
```

**SkillOpt treats the entire markdown document as "prompt weights"** -- no frontmatter required, no structured YAML. The document is simply a task strategy encoded in natural language. Skills are typically 300-2000 tokens.

**Edit operations on skill documents (dataclass):**
```python
EditOp = Literal["append", "insert_after", "replace", "delete"]

@dataclass
class Edit:
    op: EditOp
    content: str = ""
    target: str = ""
    support_count: int | None = None
    source_type: Literal["failure", "success"] | None = None
    merge_level: int | None = None
    update_origin: str = ""
    update_target: str = ""

@dataclass
class Patch:
    edits: list[Edit] = field(default_factory=list)
    reasoning: str = ""
```

### 1.4 superpowers

**Canonical SKILL.md YAML frontmatter:**
```yaml
---
name: Skill-Name-With-Hyphens        # required, letters/numbers/hyphens only
description: Use when [specific triggering conditions and symptoms]  # required
---
```

**Directory structure (minimal):**
```
skills/
  skill-name/
    SKILL.md              # main reference (required)
    supporting-file.*     # only if needed
```

**Flat namespace** -- all skills in one searchable namespace.

**Design principles:**
- Description = When to Use, NOT What the Skill Does (Claude Search Optimization -- prevents workflow shortcutting)
- Start description with "Use when..." to focus on triggering conditions
- Max 1024 characters total for frontmatter
- Third-person only (injected into system prompt)
- Token efficiency target: getting-started <150 words, frequently-loaded <200 words, others <500 words
- Skill creation = TDD applied to process documentation (RED-GREEN-REFACTOR)
- Skills are NOT narratives about how you solved a problem once

**Skill types:**
1. **Technique** -- concrete method with steps (condition-based-waiting, root-cause-tracing)
2. **Pattern** -- way of thinking about problems (flatten-with-flags, test-invariants)
3. **Reference** -- API docs, syntax guides, tool documentation

---

## 2. Loading Mechanism

### 2.1 SkillNet (3-step progressive)

1. **Discovery** -- agents initially load only minimal metadata (name + description) to identify potentially relevant skills
2. **Activation** -- when a task matches a skill's description, the agent reads the full SKILL.md and prepares associated resources
3. **Execution** -- the agent follows instructions and optionally executes bundled code

Key: **Progressive disclosure** -- agents do not pre-load all skill content. Only metadata is indexed; full content is demand-loaded based on trigger match.

### 2.2 claude-skills

**Multiple loading mechanisms coexist:**
- **Claude Code plugin system** -- `.claude-plugin/plugin.json` registers skills; Claude Code auto-loads on session start based on plugin manifest
- **Trigger-based activation** -- description field contains pushy trigger phrases; Claude Code's system prompts activate matching skills during conversation
- **Domain context files** -- loaded on demand: `if [domain]-context.md exists, read it before asking questions`
- **Reference separation** -- SKILL.md links to references inline (`See references/frameworks.md`); references are loaded on demand, zero startup cost
- **Indexing via skills-index.json** -- `.codex/skills-index.json`, `.gemini/skills-index.json`, `.hermes/skills-index.json` for cross-platform loading

**Marketplace installation:**
```bash
/plugin marketplace add alirezarezvani/claude-skills
/plugin install skill-name@claude-code-skills
```

### 2.3 SkillOpt

**Training-time only** -- there is no runtime loading mechanism. SkillOpt produces a single `best_skill.md` file that is prepended as system prompt for the target model. The skill is loaded into the prompt at the start of every episode/rollout.

No progressive disclosure, no activation trigger -- the skill is always active when the agent runs.

### 2.4 superpowers

**Bootstrapped via SessionStart hooks:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "async": false
          }
        ]
      }
    ]
  }
}
```

The `using-superpowers` bootstrap loads at session start. This is what causes skills to auto-trigger at the right moments. Without the bootstrap, skills are dead weight -- present on disk but never invoked.

**Claude Search Optimization (CSO)** is a critical design element:
- The description field determines loading: Claude reads description to decide which skills to load
- Description = Should I read this skill right now?
- Keywords throughout for search (errors, symptoms, tools)
- Active voice, verb-first naming for better search alignment

**Iron Law:** No prerequisite or dependency between skills -- each is self-contained. Cross-references use skill name only, not `@` file paths (which force-loads and burns context).

---

## 3. Creation / Generation Pipeline

### 3.1 SkillNet

**4 creation modes, all LLM-driven:**

1. **From execution trajectory** (`create_from_trajectory`):
   - Step 1: LLM analyzes trajectory to identify candidate skills (name + description)
   - Step 2: For each candidate, LLM generates full SKILL.md content + optional scripts/references
   - Step 3: Parse `## FILE: path` blocks from LLM output and write files to disk
   - Output is wrapped in XML tags (`<Skill_Candidate_Metadata>`)

2. **From GitHub repository** (`create_from_github`):
   - Fetches repo metadata (stars, topics, license, description) via GitHub REST API
   - Fetches README, file tree, language breakdown
   - Analyzes code files (Python AST parsing, regex-based for JS/TS/Java/Go/C/C++/Rust)
   - LLM generates skill package from: repo metadata + README + file tree + code analysis summary
   - Generates scripts with actual library API usage, references with function signatures
   - Retry mechanism with content validation (checks for SKILL.md, frontmatter, minimum length)

3. **From office documents** (`create_from_office`):
   - Supports PDF, DOCX, PPTX via PyPDF2, python-docx, python-pptx
   - Extracts text, then LLM converts to skill package

4. **From direct prompt** (`create_from_prompt`):
   - User provides natural language description
   - LLM generates complete skill package

**Filtering/curation pipeline (post-creation):**
- Deduplication via directory structure comparison + MD5 hashes of markdown files
- Filtering via rule-based validation + model-based checking
- Categorization into 10 functional categories + fine-grained semantic tags
- Multi-dimensional evaluation (5 dimensions)
- Selective consolidation into structured skill package library

**Scale:** 200,000+ total, 150,000+ curated skills.

### 3.2 claude-skills

**9-phase production pipeline (MANDATORY):**

```
Intent -> Research -> Draft -> Eval -> Iterate -> Compliance -> Package -> Deploy -> Verify -> Rollback-Ready
```

- **Phase 1 (Intent & Research)** -- capture intent, interview, research competing skills, define POWERFUL tier
- **Phase 2 (Draft SKILL.md)** -- Anthropic Skill Creator workflow; YAML frontmatter, pushy description, <500 lines
- **Phase 3 (Eval & Benchmark)** -- 2-3 test cases in `evals/evals.json`; spawn with-skill AND baseline runs in parallel; grade via `agents/grader.md`; quality gate: pass rate >=85%, delta vs baseline >=+30%, variance <20%
- **Phase 4 (Iterate)** -- generalize from feedback, keep prompt lean, max 5 iterations, max 3 hours per skill
- **Phase 5 (Description Optimization)** -- generate 20 trigger eval queries (10 should-trigger, 10 should-not); optimization loop via `scripts/run_loop.py`; apply `best_description` to frontmatter
- **Phase 6 (Compliance)** -- Claude Code 8-point inspection; Tessl quality check (minimum score 85%)
- **Phase 7 (Package)** -- package for all platforms (Claude Code plugin.json, Codex AGENTS.md, OpenClaw, Gemini CLI)
- **Phase 8 (Deploy)** -- marketplace, Gemini CLI setup, GitHub release, ClawHub, Codex CLI Registry
- **Phase 9 (Real-World Verification)** -- marketplace install test, trigger test (3 should + 2 should-not), functional test, cross-platform verify

**Quality tiers:**
| Tier | Score | Criteria |
|------|-------|----------|
| POWERFUL | 85%+ | Expert-level, scripts, refs, evals pass, real-world utility |
| SOLID | 70-84% | Good knowledge, some automation |
| GENERIC | 55-69% | Too general, needs domain depth |
| WEAK | <55% | Reject or rewrite |

**Only POWERFUL ships.** Everything else goes back to iteration.

### 3.3 SkillOpt

**ReflACT training pipeline (6 stages per step, 2 epoch-level):**

Per-step pipeline:
1. **Rollout** -- target model executes tasks using current skill document; produces trajectories + scores
2. **Reflect** -- optimizer model analyzes failed/success trajectories; produces edit patches
   - Two-level priority: custom prompt (adapter-specific) or generic default
   - Minibatch mode: groups trajectories of size M and analyzes together (analogous to minibatch SGD)
3. **Aggregate** -- hierarchical LLM-based merging of independently-generated patches; failure-driven patches take priority over success-driven
   - Uses ThreadPoolExecutor for parallel same-level batch merging
4. **Select** -- rank edits by relevance; learning_rate caps how many edits applied per step (like gradient clipping)
   - Supports autonomous LR decisions via `decide_autonomous_learning_rate()`
5. **Update** -- apply selected edits to skill document (append, insert_after, replace, delete)
   - Protected slow-update region (`<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->`)
6. **Gate** -- validate updated skill on selection split; only accept if performance improves

Epoch-level:
- **Slow Update** -- longitudinal comparison (previous epoch vs current) on same samples; categorizes as improved/regressed/persistent_fail/stable_success; generates guidance injected into skill document
- **Meta Skill** -- optimizer-side memory distilled from adjacent-epoch comparisons; compact guidance for future optimizer behavior (proposing, merging, ranking edits)

**Output:** single `best_skill.md` file (300-2000 tokens).

**Hyperparameter mapping:**
| DL Concept | SkillOpt |
|---|---|
| Learning rate | `edit_budget` (max edits per step) |
| LR scheduler | `lr_scheduler` (cosine/linear/constant) |
| Batch size | `batch_size` (tasks per rollout) |
| Minibatch | `minibatch_size` (trajectories per reflect group) |
| Momentum | Slow update (longitudinal comparison) |
| Meta-learning | Meta skill (cross-epoch strategy memory) |
| Early stopping | Gate patience |
| Gradient clipping | Edit selection |
| Validation set | Selection split |

### 3.4 superpowers

**Skill creation = TDD applied to process documentation:**

RED phase:
1. Create pressure scenarios (3+ combined pressures for discipline skills)
2. Run scenarios WITHOUT skill -- document baseline behavior verbatim
3. Identify patterns in rationalizations/failures

GREEN phase:
4. Write minimal skill addressing those specific violations
5. Run scenarios WITH skill -- verify compliance

REFACTOR phase:
6. Find new rationalizations -> add explicit counters -> re-test -> repeat until bulletproof

**Testing methodology:**
- Pressure types: time pressure, sunk cost, authority, exhaustion
- Discipline-enforcing skills tested with academic questions + pressure scenarios + multiple pressures combined
- Technique skills tested with application scenarios + variation scenarios + missing information tests
- Pattern skills tested with recognition scenarios + counter-examples
- Reference skills tested with retrieval scenarios + gap testing

**Iron Law:** "NO SKILL WITHOUT A FAILING TEST FIRST" -- applies to new skills AND edits to existing skills.

---

## 4. Quality Scoring / Evaluation

### 4.1 SkillNet (5-Dimensional)

**Dimensions (3 levels: Good / Average / Poor):**
1. **Safety** -- potential harm, unauthorized file deletion, prompt injection, adversarial manipulation
2. **Completeness** -- all critical procedural steps, prerequisites, dependencies, execution constraints
3. **Executability** -- can agent successfully implement in sandboxed environments; hallucinated tool calls vs ambiguous instructions
4. **Maintainability** -- modularity, composability, local update capability without breaking dependencies
5. **Cost-awareness** -- time latency, computational resource consumption, API usage costs

**Evaluation mechanism:**
- Automated LLM-based evaluator (GPT-5o-mini) with fine-grained rubrics
- JSON structured output with `level` + `reason` per dimension
- For Executability: LLM judgment + empirical validation (scripts executed in controlled sandbox environments)
- Human validation: 3 PhD-level annotators on 200 random samples showed MAE <0.03, QWK near-perfect (1.000)

**Detailed rubric examples in prompts.py:**
- "If allowed_tools grants broader permissions than what the Skill clearly needs, reduce safety by at least one level"
- "For health/medical-related Skills without explicit disclaimer, safety MUST NOT be Good"
- "If core formula contains language-level errors (e.g., `^` for exponentiation in Python), executability MUST be Poor"
- "If scripts only print/echo input without implementing promised behavior, executability at most Average"
- "Instruction-only skills: absence of runnable scripts is acceptable if instructions are clear and actionable"

### 4.2 claude-skills (Tessl + Multi-Metric)

**8-point compliance checklist:**
1. No malware, exploit code, or security risks
2. No hardcoded secrets or credentials
3. Description is accurate (no surprise behavior)
4. Scripts are stdlib-only (no undeclared dependencies)
5. YAML frontmatter valid (name + description)
6. File references all resolve correctly
7. Under 500 lines SKILL.md (or justified)
8. Assets include sample data + expected output

**Quality gates:**
- Tessl quality check: minimum score 85%
- Eval pass rate >=85% with-skill
- Delta vs baseline >=+30% on key assertions
- No flaky evals (variance <20%)

**Plugin audit (8 phases):**
- Structure scoring (0-100)
- Quality scoring (0-100)
- Scripts count/quality
- Security audit (0 critical, 0 high required)

### 4.3 SkillOpt (Gate-based)

**Gate mechanism (held-out validation):**
- Updated skill evaluated on selection split (analogous to validation set)
- Update accepted ONLY if performance strictly improves
- Gate patience prevents accepting non-improving updates

**Metrics:**
- `hard` score: primary (0.0-1.0, can be continuous for smoothed reward)
- `soft` score: secondary (0.0-1.0)
- Rollout_hard and rollout_soft tracked per step
- Edit acceptance rate: fraction of proposed edits that pass gating
- Skill length in tokens tracked over training

### 4.4 superpowers (Adversarial Testing)

**No automated scoring -- testing is purely adversarial/human:**
- Pressure scenarios with subagents prove skill effectiveness
- Baseline (without skill) vs with-skill comparison
- Rationalization capture: agents will find loopholes; each identified rationalization gets an explicit counter in the skill
- Red flags list for agents to self-check when rationalizing

---

## 5. Cross-Platform Compatibility

### 5.1 SkillNet

- **Claude Code**: SKILL.md directory format, YAML frontmatter triggers
- **Codex CLI**: Same SKILL.md format
- **OpenClaw**: Same SKILL.md format
- **Platform-neutral**: Uses `<skills-dir>` placeholder; supports `SKILLNET_SKILLS_DIR` env var or agent convention (`~/.claude/skills`, `~/.codex/skills`, `~/.openclaw/workspace/skills`)

### 5.2 claude-skills

**Most comprehensive cross-platform support (8 platforms):**

| Platform | Format | Index File |
|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | Marketplace install |
| Codex CLI | `AGENTS.md` in skill dir | `.codex/skills-index.json` |
| Gemini CLI | Same SKILL.md | `.gemini/skills-index.json` + `GEMINI.md` |
| Hermes Agent | Same SKILL.md | `.hermes/skills/claude-skills/skills-index.json` |
| OpenClaw | Same SKILL.md + `openclaw.json` | ClawHub publish |
| Cursor | Via `.cursor-plugin/` | -- |
| OpenCode | Via `.opencode/plugins/` | -- |
| Mistral Vibe | Via `scripts/sync-vibe-skills.py` | `~/.vibe/skills/claude-skills/` |

**Sync scripts:**
- `scripts/sync-codex-skills.py` -- scans all domains for SKILL.md, creates symlinks + skills-index.json
- `scripts/sync-gemini-skills.py` -- sync-to-Gemini CLI index
- `scripts/sync-hermes-skills.py` -- sync-to-Hermes agent index
- `scripts/sync-vibe-skills.py` -- sync-to-Mistral Vibe
- `scripts/sync_skill_bundles.py` -- bundle multi-skill packages
- `scripts/audit_skills.py` -- repo-wide skill audit

### 5.3 SkillOpt

**Agent/harness agnostic -- output is pure markdown:**
- `best_skill.md` can be prepended to any LLM system prompt
- Supports 3 execution harnesses: direct chat, Codex CLI, Claude Code CLI
- Skills transfer across model scales (GPT-5.5, DeepSeek V3, Gemini 2.5 Pro)
- Skills transfer between Codex and Claude Code harnesses
- Skills transfer to nearby benchmarks without further optimization

**Backend support:** Azure OpenAI, OpenAI-compatible, Claude Chat, Codex CLI, Qwen Chat, MiniMax Chat

### 5.4 superpowers

**Claude Code native** -- uses hook system for session-start bootstrap. Cross-harness support is architecture-level:
- `.claude-plugin/plugin.json` for Claude Code
- `gemini-extension.json` for Gemini CLI
- `.cursor-plugin/plugin.json` for Cursor
- `.codex-plugin/plugin.json` for Codex CLI
- `.opencode/plugins/superpowers.js` for OpenCode

**Acceptance test for new harness support:**
> "Let's make a react todo list"
- A working integration auto-triggers the `brainstorming` skill before any code is written
- Session transcript proof required

---

## 6. License and Attribution

| Project | License | Notes |
|---|---|---|
| **SkillNet** | MIT | Full grant: "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND" |
| **claude-skills** | MIT | 338 skills, 62 marketplace plugins across 16 domains; commercial bundles sold on Gumroad/Stan Store ($39-$99) alongside free MIT GitHub distribution |
| **SkillOpt** | MIT | Microsoft open source; full patent and rights grants |
| **superpowers** | MIT | 0-dependency design principle; PRs requiring third-party dependencies rejected |

**claude-skills attribution conventions:**
- External MIT-licensed derivations require `attribution` field in plugin.json
- Repo conventions: preserve upstream voice verbatim in SKILL.md + add wrapper (validators + references + agent + command)
- Dual-published: standalone marketplace plugin AND bundled in domain plugin
- Source provenance tracked for megaprompt-to-skill conversions via `source` field in plugin.json

---

## 7. Transferable Design for Lyra Section 4.4

### 7.1 Skill Format Recommendation

Adopt a hybrid of claude-skills and superpowers:
```
skill-name/
  SKILL.md              # required: YAML frontmatter (name, description, version, license, author, category, updated)
  references/           # optional: loaded on demand for deep knowledge
  scripts/              # optional: executable code, stdlib-preferred
  templates/            # optional: user-facing templates
  evals/
    evals.json          # optional: test cases + assertions
```

**Required SKILL.md frontmatter:**
```yaml
---
name: skill-name
description: Use when [triggering conditions] -- NOT [disambiguation]
version: 1.0.0
author: <author>
category: <domain>
license: MIT
---
```

### 7.2 Progressive Loading (Critical for Lyra)

Implement **3-level progressive disclosure** from SkillNet:
1. **Discovery** -- agent indexes skill by name + description only (no full content loaded)
2. **Activation** -- when task matches trigger, load SKILL.md body
3. **Execution** -- when task reaches relevant section, load references/ + scripts/

**Skill graph for discovery:**
- Index skills by `similar_to`, `belong_to`, `compose_with`, `depend_on` relations
- LLM-inferred relation graph (SkillNet approach)
- Store as `relationships.json` in skill directory

### 7.3 Creation Pipeline

Adopt SkillNet's multi-source creation but add claude-skills' rigor:

1. **Source acquisition** -- trajectory, GitHub repo, document, direct prompt
2. **LLM generation** -- 2-stage (candidate metadata -> content generation)
3. **Structural validation** -- check SKILL.md present, frontmatter valid, file references resolve
4. **Multi-dimensional evaluation** -- Safety, Completeness, Executability, Maintainability, Cost-awareness
5. **Deduplication** -- MD5 hash + directory structure comparison
6. **Categorization + tagging** -- into Lyra's domain taxonomy
7. **Relation graph construction** -- LLM-inferred edges

### 7.4 Skill Optimization Loop

Integrate SkillOpt's ReflACT pipeline for continuous improvement:

1. **Rollout** -- agent executes task with current skill
2. **Reflect** -- optimizer analyzes trajectories, proposes edits (append/insert_after/replace/delete)
3. **Aggregate** -- merge similar edits hierarchically
4. **Select** -- apply learning rate (max edits per step)
5. **Update** -- apply edits to skill document (respecting slow-update protected regions)
6. **Gate** -- validate on held-out tasks before accepting

**Key parameters for Lyra:**
- `edit_budget`: 4-16 (learning rate)
- `lr_scheduler`: cosine (start aggressive, taper)
- `minibatch_size`: 8 (trajectories per reflect group)
- `use_slow_update`: true (prevent catastrophic forgetting)
- `use_meta_skill`: true (cross-epoch optimizer memory)

### 7.5 Evaluation System

Adopt SkillNet's 5-D rubric with the concrete level definitions:

| Dimension | Good | Average | Poor |
|---|---|---|---|
| Safety | Avoids destructive actions; includes safeguards; scope limits | Benign domain but no safeguards mentioned | Dangerous actions without safeguards; over-broad tool permissions |
| Completeness | Clear goal + steps + inputs/outputs + prerequisites + edge cases | Clear goal but underspecified steps/prereqs | Too vague to act on; missing core steps |
| Executability | Concrete actions/artifacts; minimal ambiguity | Generally executable but ambiguous steps | Non-actionable; depends on unspecified systems |
| Maintainability | Narrow scope; clear I/O; low coupling; configurable | Some reusable parts but unclear boundaries | Overly broad; tightly coupled; conflicts with other workflows |
| Cost-awareness | Explicit batching/limits/caching/scope control | No explicit controls but not wasteful | Encourages wasteful workflows without cost acknowledgment |

### 7.6 Skill Graph for Lyra

Implement SkillNet's 4-edge relation graph:

1. **similar_to** -- functionally equivalent skills (for dedup/replacement)
2. **compose_with** -- independent but often co-used (pipeline composition)
3. **belong_to** -- sub-component of larger workflow (hierarchical organization)
4. **depend_on** -- prerequisite requirement (execution ordering)

LLM-inferred from skill names + descriptions, stored as `relationships.json`.

### 7.7 Quality Gates (claude-skills style)

Blocking for merge:
- [ ] SKILL.md drafted with frontmatter (name + description + version)
- [ ] Evaluated on 5 dimensions (no "Poor" on Safety, minimum "Average" on Completeness)
- [ ] No hardcoded secrets or credentials
- [ ] Scripts verifyable (at minimum `--help` passes)
- [ ] Cross-references resolve correctly
- [ ] Test cases exist for primary workflow

### 7.8 Key Differences from Existing Systems

| Feature | SkillNet | claude-skills | SkillOpt | superpowers | Lyra Recommendation |
|---|---|---|---|---|---|
| Skill format | YAML frontmatter + markdown | YAML + scripts + refs + agents + commands | Pure markdown (no YAML) | YAML frontmatter + markdown | Hybrid: YAML + optional scripts/refs/agents |
| Loading | 3-step progressive | Plugin system + trigger activation | Always-active in prompt | SessionStart hook bootstrap | 3-step progressive + trigger-based |
| Creation | LLM from 4 source types | Manual with 9-phase pipeline | ReflACT training loop | TDD with adversarial testing | LLM-based + training loop |
| Evaluation | 5-D LLM + sandbox | Tessl + multi-metric | Gate-based (validation split) | Adversarial subagent testing | 5-D LLM + gate-based validation |
| Cross-platform | Claude Code / Codex / OpenClaw | 8 platforms | 3 harnesses + model-agnostic | 6 platforms via plugins | All 4 approaches combined |
| Skill graph | 4-edge ontology | Related Skills (manual curation) | None | None | 4-edge LLM-inferred graph |

### 7.9 Implementation Priority for Lyra Section 4.4

1. **Skill format** -- adopt the hybrid SKILL.md with YAML frontmatter (immediate)
2. **Progressive loading** -- metadata-only index, demand-load on trigger match (P0)
3. **Skill graph** -- `relationships.json` with 4 edge types, LLM-inferred (P0)
4. **5-D evaluation** -- LLM-based with structured JSON output (P0)
5. **Multi-source creation** -- trajectory, GitHub, document, prompt (P1)
6. **ReflACT optimization loop** -- SkillOpt pipeline for continuous improvement (P1)
7. **Cross-platform sync** -- index generators for multiple agent systems (P2)
8. **Eval-driven quality gates** -- blocking checks before merge (P2)
