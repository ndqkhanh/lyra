# Skills System: Harness-Level Loader with Progressive Disclosure & Skill Graph
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/04-skills.md) | [Code](../../src/lyra/skills/)

## Abstract
Lyra's skills system is a harness-level (not provider-API-level) skill loader with progressive disclosure, deterministic matching, and a SkillGraph for dependency-based topological execution. Unlike provider-specific implementations (Claude Code skills endpoint, OpenAI function calling), Lyra reads SKILL.md from the filesystem and injects it into the outgoing messages array — working identically across Anthropic, DeepSeek, GPT, and open-weights. Progressive disclosure loads only frontmatter by default, the full skill body on selection, and referenced files only when reached. A deterministic keyword/embedding matching path provides a fallback when model auto-triggering is unreliable (critical for smaller/faster models like deepseek-v4-flash). The SkillGraph (from SkillNet, ZJU-NLP) enables composition: skills declare dependencies, and the executor topologically orders them.

## Introduction
**Intuition.** Skills are "on-demand instruction manuals" — not always-loaded system prompts. Lyra keeps a catalog of skill names and descriptions (~50 tokens) in context. When a task matches a skill's trigger patterns, the full skill body is loaded (~500-2000 tokens). When referenced files are needed, they load on demand. This keeps the base context small while making deep expertise available when relevant.

**Contributions:** (1) Harness-level loader working across all providers, (2) progressive disclosure minimizing context bloat, (3) deterministic matching fallback for unreliable auto-triggers, (4) SkillGraph with cycle detection and topological execution ordering, (5) provider × skill compatibility matrix.

## Related Work
| System | Loading | Matching | Composition | Provider-Agnostic |
|--------|---------|----------|-------------|-------------------|
| **Lyra** | Progressive disclosure (3 levels) | Keyword + embedding + model trigger | SkillGraph (topological) | Yes |
| Claude Code Skills | Filesystem injection | Model auto-trigger only | No | No (Claude-only extensions) |
| SkillNet (ZJU-NLP) | npm-style install | Search + graph | Similarity + composition + dependency | Yes (MCP) |
| OpenClaw Skills | Modular TypeScript | Pattern-based | No | Plugin-based |
| agent-skills (Addy Osmani) | Plugin marketplace | Auto-activation by task type | Lifecycle slash commands | Markdown-based |

## Method
**Loader pipeline** (`src/lyra/skills/`): registry → parser → executor → importer. Skills are YAML-frontmatter markdown files. Progressive disclosure: Level 1 (frontmatter: name, description, triggers) → Level 2 (full SKILL.md body on trigger match) → Level 3 (referenced files on demand).

| Level | Loaded | Context Cost | When |
|-------|--------|-------------|------|
| 1 | Frontmatter only | ~50 tokens | Always (catalog) |
| 2 | Full SKILL.md body | ~500-2000 tokens | On trigger match |
| 3 | Referenced files | Variable | On first use |

```mermaid
flowchart LR
    CATALOG[Skill Catalog (L1)] --> MATCH{Trigger Match?}
    MATCH -->|Yes| LOAD[Load Full Body (L2)]
    MATCH -->|No| CATALOG
    LOAD --> EXEC[Execute Skill]
    EXEC --> REFS{References?}
    REFS -->|Yes| LOADREF[Load Referenced Files (L3)]
    REFS -->|No| DONE[Done]
    LOADREF --> EXEC
```

## Working Flow

Skills work like pop-up instruction manuals. You keep a catalog of titles in your pocket (~50 tokens each) and pull out the full manual only when you need one.

**Example:** You type "review the current diff" or run the /code-review command:

1. Lyra checks its **skill catalog** (frontmatter only, ~50 tokens per skill). It matches "code-review" against your request.
2. The **loader** reads the full `src/lyra/skills/code-review.md` (~800 tokens) and injects it into the next LLM call. The catalog stub is replaced with the full body.
3. If the skill references other files, those load **on demand** -- not until you actually need them. This keeps context lean.
4. If the skill has dependencies (e.g., code-review depends on a git-diff skill), the **SkillGraph** resolves them in order, with cycle detection preventing infinite loops.

## Debate
**Skeptic:** "Progressive disclosure adds latency — each level load is a separate filesystem read."
**Resolution:** Filesystem reads are sub-millisecond. The alternative (always loading all skills) costs 50K+ context tokens. The trade-off is worth it for all but the smallest sessions.

## Use Cases

**Scenario 1: Onboarding new team members with standardized skills.** A team lead maintains a repository of 20 skills: how to write migration scripts, how to deploy to staging, how to run the integration test suite, how to format commit messages. A new engineer clones the repo and opens Lyra. Every skill is immediately available as a slash command or auto-triggered by keywords. The engineer runs "/deploy-to-staging" on day one and follows the skill's step-by-step instructions without asking for help. No documentation wiki needed.

**Scenario 2: Domain-specific agent customization.** A data science team works with Lyra on pandas pipelines, but the general-purpose agent doesn't know their internal column naming conventions or preferred plotting library. They write a single "data-science-team" skill that captures these conventions: use snake_case columns, always call df.pipe() not chained mutations, use seaborn for exploration and plotly for dashboards. When any team member asks Lyra to "visualize the distribution," the skill triggers, loads the conventions, and the generated code matches the team's standards exactly.

**Scenario 3: Multi-skill workflows that compose complex tasks.** A developer wants to "create a new microservice." This involves generating boilerplate, setting up CI, writing the Dockerfile, and creating a database migration. Instead of one monolithic skill, four individual skills declare dependencies: "create-microservice" depends on "boilerplate-gen" and "docker-setup," which in turn depends on "ci-config." Lyra's SkillGraph resolves the dependency order, loads each skill sequentially, and executes them as a pipeline. The developer gets a fully scaffolded service from a single command.

## Conclusion
Implemented: registry, parser, executor, importer, SkillGraph with CycleError detection. Provider × skill compatibility matrix. Core module: `src/lyra/skills/`. Future: SkillNet-style auto-creation from execution trajectories.
