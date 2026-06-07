# alirezarezvani/claude-skills -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline:** The largest open-source library of Claude Code skills, agent plugins, and persona definitions -- 343 skills across 17 domains, distributed via a plugin marketplace pattern and cross-compiled to 13 different AI coding tools.

**Mechanism:** Each skill is a **self-contained directory** following a rigid convention:

```
skill-name/
  SKILL.md         # YAML-frontmatter + markdown instructions (under 500 lines)
  scripts/         # Python CLI tools (stdlib only, 593 total, zero pip installs)
  references/      # Expert knowledge bases loaded on demand
  assets/          # Templates, sample data, expected outputs
  agents/          # Sub-agent definitions (cs-* agent files)
  commands/        # Slash command definitions
```

The core insight is **algorithm over AI**: every Python tool uses the standard library exclusively and implements deterministic logic (regex, state machines, closed-form formulas) rather than LLM calls. Skills are loaded by the Claude Code plugin system from a `marketplace.json` registry that maps 64 plugins to 17 domain folders. A `scripts/convert.sh` script cross-compiles the same SKILL.md content into 13 tool-native formats (Cursor `.mdc` rules, Aider `CONVENTIONS.md`, Gemini CLI skills, etc.).

Knowledge flows: `references/` resources inform `SKILL.md` workflows, which are executed by `scripts/` tools, applied through `assets/` templates. The system has no runtime -- it is entirely a content + configuration library activated by the host coding agent.

## 2. Architecture & Core Modules

**Entry points (no main.py/index.ts -- this is a content library):**

| Layer | Location | Function |
|-------|----------|----------|
| Plugin registry | `.claude-plugin/marketplace.json` | 64 plugin entries, each referencing a domain folder with metadata, versioning, and keywords |
| Cross-tool install | `scripts/convert.sh`, `scripts/install.sh` | Converts SKILL.md to 13 tool-native formats |
| Skill pipeline | `SKILL_PIPELINE.md` | 9-phase production pipeline (Intent -> Research -> Draft -> Eval -> Iterate -> Compliance -> Package -> Deploy -> Verify) |
| Meta-skills | `engineering/write-a-skill/`, `SKILL-AUTHORING-STANDARD.md` | 10 patterns for writing new skills |
| Audit infra | `scripts/audit_skills.py`, `scripts/check_plugin_json.py` | Lints all 343 skills for structure, descriptions, plugin.json validity |

**17 domain folders (each a bundled top-level directory):**

| Domain | Skills | Key Example |
|--------|--------|-------------|
| `engineering/` (POWERFUL) | 78 | RAG architect, agent-designer, MCP server builder, SLO architect, chaos engineering |
| `engineering-team/` (Core) | 51 | Senior architect, code-reviewer, Playwright Pro, security suite, a11y audit |
| `c-level-advisor/` | 66 | Full C-suite persona agents + boardroom/debate/orchestration |
| `marketing-skill/` | 46 | AEO (Answer Engine Optimization), content pods, SEO, CRO |
| `product-team/` | 17 | PM toolkit, apple-hig-expert, landing-page generator |
| `ra-qm-team/` | 18 | ISO 13485, MDR, FDA, ISO 27001, GDPR |
| `compliance-os/` | 9 | Controls, evidence, audit-readiness |
| `project-management/` | 9 | Jira/Confluence MCP, scrum master |
| `business-operations/` | 7 | Process mapper, vendor management, capacity planner |
| `commercial/` | 8 | Pricing strategist, deal desk, RFP-responder |
| `business-growth/` | 5 | Customer success, sales engineering |
| `finance/` | 4 | Financial analyst, SaaS metrics coach |
| `productivity/` | 6 | Capture, email pair, handoff, andreessen-mode |
| `marketing/` (top-level) | 1 | Landing-page generator |
| `research/` | 8 | Hybrid router + 7 specialists (litreview, grants, dossier, patent, etc.) |
| `research-ops/` | 5 | Clinical research, research finance, market research |
| `markdown-html/` | 5 | md-document, md-review, md-slides -- single-file HTML converters |
| `standards/` | 5 | Git, security, documentation standards |

**Architecture pattern:** Plugin-based modular library with cross-tool compilation. The design is entirely declarative/configuration-driven with no runtime framework. Skills are discovered by the host agent's plugin system, not by a custom engine. This is a **content-platform pattern** that happens to be expressed as a git repo.

**Key constraints enforced in code:**
- `scripts/check_plugin_json.py` validates plugin.json paths require `./` prefix post-CC-2.1.144
- All 593 Python tools verified stdlib-only (no pip installs)
- `SKILL.md` files under 500 lines per pipeline rules
- Hard rules enforced in SKILL.md (not code): "never auto-approve deals", "never silently chain converters", "clinical outputs are estimates with named owner"

## 3. Performance/Benchmarks

**Empirical footprint benchmarks from CLAUDE.md:**

| Artifact | Input | Output Size | Comparison |
|----------|-------|-------------|------------|
| md-document (long-form) | ~150 lines markdown | 11 KB HTML / 15 KB with JS | Notion/Confluence exports: 200 KB+ |
| md-document (long-form) | ~470 lines markdown | 17 KB / 23 KB with JS | Notion/Confluence exports: 200 KB+ |
| md-review (code review) | 2-hunk sample | 11.3 KB single-file HTML | Google Slides/Keynote: 200 KB+ |
| md-slides (slide deck) | 5-slide deck, 3 with notes | 12.2 KB single-file HTML | reveal.js multi-file: 200 KB+ |

**Tooling scope:**
- 343 skills, 593 Python tools, 691+ reference docs, 51+ agents, 90+ slash commands, 64 plugins
- All Python tools are stdlib-only -- zero pip installs required
- Audit: `scripts/audit_skills.py` runs in ~30s on all 343 skills
- Cross-tool conversion: `scripts/convert.sh --tool all` takes ~15 seconds
- Caveman mode token compression: 20-50% typical, 75% upper bound

**Quality metrics from SKILL_PIPELINE pipeline:**
- Tessl quality gate: minimum 85% score for POWERFUL tier
- Evals: pass rate >= 85% with-skill, delta vs baseline >= +30%
- Audit scores for new plugins: structure scores typically 79-91/100, security always PASS with 0 critical/high findings

## 4. Trade-offs (wins vs loses)

**Wins:**
- Zero-dependency Python ecosystem: all 593 tools use stdlib only, maximally portable
- Cross-tool compilation to 13 platforms from a single source of truth
- Extremely low entry cost for users: `/plugin marketplace add alirezarezvani/claude-skills` then `/plugin install <bundle>@claude-code-skills`
- Rigorous skill production pipeline with eval gates, Tessl quality scoring, and compliance checks
- Commercial viability: $9/single skill, $39-49/bundles, $99/complete collection on Gumroad/Stan Store
- Deterministic tools over LLM calls avoids cost and latency of AI-in-the-loop for analysis tasks
- Forcing-question discipline (Matt Pocock-derived) prevents skills from running on fuzzy inputs

**Loses:**
- No package manager or version resolver: the repo ships every skill bundled; there is no way to install individual skills with dependency resolution
- Massive surface area creates maintenance burden: 593 Python scripts, 343 SKILL.md files, 64 plugin.json manifests all need updating
- No formal test suite in CI: `tests/` is gitignored and run locally only; `requirements-dev.txt` has only pytest
- Skill quality is uneven: the same repo has 8-phase plugin-audit'd skills (score 91/100) alongside legacy skills from v1.0.x batch imports (some had placeholder descriptions like `description: "Migration Architect"`)
- No runtime enforcement of hard rules: constraints like "never auto-approve" live in SKILL.md prose, not in any importable schema
- Monorepo scales poorly: `CLAUDE.md` is 66,832 bytes and 515 lines; `CHANGELOG.md` is 130,621 bytes and 1,460 lines
- No MCP server for skill discovery: users must browse the README or filesystem; there is no interactive registry
- ClawHub rate limit (5 skills/hour) constrains batch publishes

## 5. Design Rationale (why this approach)

The repo's design choices are grounded in explicit principles documented in `CLAUDE.md` and `SKILL-AUTHORING-STANDARD.md`:

1. **Skills are products, not scripts.** Each skill is a standalone, deployable package with its own instructions, tools, references, and templates. This enables marketplace distribution and composition across tools.

2. **Algorithm over AI.** Deterministic analysis tools (regex, state machines, closed-form math) are faster, cheaper, more predictable, and more portable than LLM calls. The repo treats LLM reasoning as the scarce resource and offloads what it can to stdlib Python.

3. **Documentation-driven development.** The entire repo is documentation that happens to be expressed as code. `SKILL.md` files are the product; Python scripts are supporting actors. Knowledge flows from references into SKILL.md workflows.

4. **Matt Pocock discipline.** MIT-licensed derivations of Matt Pocock's skill patterns (write-a-skill, caveman, grill-me, handoff) established the template for all skills: preserve upstream voice verbatim, add wrappers (validators + references + agent), attributions in every file. The "forcing-question library" pattern (one question per turn with recommended answer and canon citation) prevents skills from operating on vague input.

5. **Commercial sustainability.** The repo generates revenue via Gumroad/Stan Store bundles. This explains the polish of marketplace.json, the CLAUDE.md navigation map, and the rigorous pipeline -- these are product management artifacts as much as engineering artifacts.

6. **Cross-tool portability over framework lock-in.** Rather than building a custom runtime, the repo converts SKILL.md to each tool's native format. This sacrifices deep integration for maximum reach (13 platforms).

7. **Karpathy-lite code discipline.** Every new PR is verified against `engineering/karpathy-coder`'s 4 principles: surface assumptions, simplify, make surgical changes, define verifiable goals.

## 6. Transfer to Lyra (one idea)

**Transferable idea: Skill pipeline with eval gates and behavioral hooks.**

The Lyra upgrade needs a skill authoring workflow that includes pre-tool-use security hooks, post-execution quality gates, and deterministic validation scripts that run without LLM overhead. Borrow the **SKILL_PIPELINE.md** 9-phase production model: convert the Lyra plugin system from ad-hoc skill loading to a structured pipeline with Intent -> Draft -> Eval -> Gate -> Ship. Each Lyra skill should ship with its own validation scripts (stdlib Python) that verify inputs before execution and outputs after.

Additionally, adopt the **forcing-question library** pattern: every Lyra skill/command starts by asking 1-2 clarifying questions with recommended answers, preventing the agent from running on vague user prompts. This is especially useful for Lyra's memory and context subsystems where ambiguity can cascade.

**Route:** §4.x -- Plugin Infrastructure & Skill Pipeline. The pipeline model maps directly to Lyra's plugin system re-architecture.

**Impact:** 8/10. A skill gateway with pre-flight validation catches hallucinations before execution. Deterministic validation scripts reduce LLM waste. The forcing-question pattern improves reliability of every agent interaction.

**Effort:** 5/10. Implementing a plugin pipeline requires designing the skill manifest schema, validation script conventions, and evaluation harness. Direct port of stdlib Python validation tools is low-effort; the cultural shift to forced intake questions requires retraining agent prompts.

**Tier:** Tier 2 (Medium-term, this release cycle).

**LICENSE:** MIT (Copyright (c) 2025 Alireza Rezvani)
