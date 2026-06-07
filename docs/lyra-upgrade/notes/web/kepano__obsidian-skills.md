# kepano/obsidian-skills -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline Feature:** A collection of Agent Skills (following the [Agent Skills specification](https://agentskills.io/specification)) that teach LLM agents (Claude Code, Codex CLI, OpenCode) how to create and edit Obsidian vault files -- Markdown, Bases, Canvas, CLI commands, and web-page-to-markdown extraction.

**Mechanism:** The repo contains zero executable code. Each skill is a `SKILL.md` file with YAML frontmatter (name, description, trigger keywords) followed by markdown reference content. When installed, the skill's content is loaded into the LLM's context, teaching the model domain-specific syntax and workflows on demand. This is entirely "cognitive" rather than "tool-based" -- the skill does not run code; it equips the LLM with authoritative knowledge so it can generate correct Obsidian-specific output directly.

Five skills ship:
- **obsidian-markdown** -- wikilinks, embeds, callouts, properties (frontmatter), tags, comments, highlight, LaTeX, Mermaid diagrams, footnotes
- **obsidian-bases** -- `.base` file schema: YAML-defined database-like views (table, cards, list, map) with filter expressions (AND/OR/NOT recursion), computed formulas (`if()`, date arithmetic, string ops), and summary aggregations
- **json-canvas** -- `.canvas` file structure per JSON Canvas Spec 1.0: nodes (text/file/link/group), edges (directional with side anchors), 16-char hex IDs, color presets
- **obsidian-cli** -- how to invoke the `obsidian` CLI to create/read/search/append notes, set properties, manage tasks, query backlinks, and run plugin development commands (reload, errors, screenshot, DOM inspect, eval)
- **defuddle** -- wraps the Defuddle CLI (`npm install -g defuddle`) to extract clean markdown from web pages, preferred over raw WebFetch for token savings

## 2. Architecture & Core Modules

**Entry points:** There is no code entry point. The entry point is the plugin manifest at `.claude-plugin/plugin.json`, which names the plugin `"obsidian"` v1.0.1 and points to the root directory. The marketplace manifest at `.claude-plugin/marketplace.json` enables `obsidian-skills` to be installed via `/plugin marketplace add kepano/obsidian-skills`.

**File layout:**

```
kepano__obsidian-skills/
  .claude-plugin/
    plugin.json          # Plugin metadata (name: "obsidian", v1.0.1, MIT)
    marketplace.json     # Marketplace registration
  LICENSE                # MIT License
  README.md              # Installation instructions for 4 platforms
  skills/
    defuddle/
      SKILL.md           # Web-to-markdown via Defuddle CLI
    json-canvas/
      SKILL.md           # JSON Canvas spec (.canvas files)
      references/
        EXAMPLES.md      # 4 full canvas examples: simple, project board, research, flowchart
    obsidian-bases/
      SKILL.md           # Obsidian Bases (.base files)
      references/
        FUNCTIONS_REFERENCE.md  # Complete formula function reference
    obsidian-cli/
      SKILL.md           # Obsidian CLI commands
    obsidian-markdown/
      SKILL.md           # Obsidian Flavored Markdown
      references/
        CALLOUTS.md      # Callout types and aliases
        EMBEDS.md        # Embed syntax for all media types
        PROPERTIES.md    # YAML frontmatter property types
```

**Data flow for an agent using a skill:**

1. Agent receives a user request (e.g., "create a project board canvas")
2. Skill trigger keywords in SKILL.md frontmatter (`description` field) match the request
3. Skill content is loaded into the agent's context
4. Agent generates output (e.g., `.canvas` JSON file) following the skill's specification and examples
5. No runtime is involved -- the output is written directly to the filesystem

**Architecture pattern:** Plugin / Library pattern within the Claude Agent Skills ecosystem. Each skill is a self-contained markdown document with YAML metadata. The SKILL.md serves as both the instruction document and the "source of truth." Reference files in `references/` provide exhaustive detail but are loaded only when the main skill deems them necessary (linked via relative markdown links).

## 3. Performance / Benchmarks

This repository contains no executable code and therefore no benchmarks. There are no numbers for latency, throughput, accuracy, or token costs. The only performance-related claim is in the defuddle skill: using Defuddle over raw WebFetch "reduces token usage" by stripping navigation, ads, and clutter from web pages. No quantitative figures are given.

## 4. Trade-offs (Wins vs Losses)

**Wins:**

- **Zero maintenance burden.** No code means no tests, no CI/CD, no dependency upgrades, no build steps. The entire repo is markdown files.
- **Platform portability.** Because the skills follow the Agent Skills specification, they work identically across Claude Code, Codex CLI, and OpenCode without modification.
- **Authoritative source.** Written by Steph Ango (@kepano), the creator of Obsidian. The knowledge is canonical -- no reverse-engineering or guessing.
- **Granular loading.** Each skill is narrowly scoped to one Obsidian subsystem. Agents can load only the skill(s) relevant to the current task, keeping context budgets manageable.
- **Community contribution path.** The open FILE structure (plain markdown) invites PRs for corrections and additions.

**Losses:**

- **No automated validation.** There are no tests to verify that SKILL.md syntax examples are correct or up-to-date with Obsidian's actual parser. An update to Obsidian could silently break a skill.
- **Cognitive-only, not tool-based.** The skills teach the LLM *what to write* but do not provide runnable tool calls. The LLM must generate output directly; there is no API-level guard against hallucinating invalid syntax.
- **Context overhead.** Each skill's full SKILL.md is loaded into the LLM's context window, consuming tokens even when only a small part of the skill is needed.
- **Single point of authority.** If the SKILL.md contains an error or omission, all agents receiving it will repeat that error consistently.
- **No version pinning.** The skills describe Obsidian features at a point in time without specifying which Obsidian version they correspond to. A future Obsidian release could change syntax without the skills being updated.

## 5. Design Rationale

The design is a direct response to a specific problem: how do you give an LLM agent domain-specific knowledge about a complex application (Obsidian) without writing custom tool code?

The author chose the Agent Skills specification because it solves this cleanly:
- **Declarative over imperative.** Skills are declarative markdown, not imperative code. This reduces the barrier to entry for contributors and eliminates the code surface area for bugs.
- **In-context over hardcoded.** Rather than baking Obsidian knowledge into a monolithic system prompt or a library of tool implementations, skills are loaded on demand into the agent's context only when needed.
- **Separation of concerns.** The skill author's job is to write clear, correct documentation of the Obsidian API/syntax. The agent's job is to apply that documentation to user requests. Neither needs to understand the other's internals.
- **Ecosystem alignment.** By using the standard Agent Skills format, the repo becomes instantly installable in any compliant agent platform without any porting work. This is a bet on the emerging standards layer for agent capabilities.

The reference subdirectories (e.g., `references/FUNCTIONS_REFERENCE.md`, `references/EXAMPLES.md`) indicate a deliberate decision to keep SKILL.md focused on the "how to use it" workflow while pushing exhaustive reference material to separate files that are loaded only when needed.

## 6. Transfer to Lyra

**Transferable idea: Skill-based agent knowledge injection.**

Lyra currently implements all agent capabilities as code (tools, adapters, commands). This repo demonstrates a complementary approach: loadable markdown "skills" that teach the agent how to perform domain-specific tasks without writing any code. Lyra could adopt a `skills/` directory where flat `.md` files describe workflows (e.g., "how to create a Lyra pipeline", "how to write a Lyra adapter for a new model", "how to configure a new transport"), and agents load them dynamically.

**Specific implementation sketch:**
- Add a `lyra skills` command that lists available skills
- Add a `skills/` directory in the Lyra project root (or user config dir)
- Each skill is a `.md` file with YAML frontmatter (name, description, triggers, version)
- Before performing a task, Lyra's agent scans skills for keyword matches and loads matching skills into context
- Community contributions become as simple as adding a markdown file

**Workstream route:** Section 4.2 (Plugin System) -- adding a skill-loading subsystem as a plugin type. Alternatively, Section 5 (Documentation & Training) if implemented purely as a user-facing knowledge system rather than a plugin architecture. Section 4.2 is the stronger fit because the mechanism (dynamic loading of behavioral modules) is a plugin concern.

**Impact:** 6 (moderate -- reduces code complexity for domain-specific agent behaviors, enables community contributions without code changes)
**Effort:** 5 (moderate -- requires designing the skill schema, a loader mechanism, keyword matching, and context injection; the skill content itself can be developed incrementally)
**Tier:** Silver (high-value, moderate effort, aligns with the plugin system roadmap)

**License:** MIT (fully compatible with Lyra's license -- copy, modify, sublicense freely)
