# shanraisshan/claude-code-best-practice — Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline**: The definitive community reference repository for Claude Code best practices. It is a living encyclopedia of Claude Code's extension mechanisms (agents, commands, skills, hooks, memory, settings) with a working end-to-end demo of the "Command -> Agent -> Skill" orchestration pattern.

**How it works**: This repo is not a library or framework — it is a **live Claude Code project configuration** that you clone and point Claude at. It contains:

1. **A working weather orchestration demo** (`.claude/commands/weather-orchestrator.md` -> `weather-agent` -> `weather-fetcher` skill -> `weather-svg-creator` skill) that demonstrates two distinct skill patterns: agent-preloaded skills vs directly-invoked skills. The user runs `/weather-orchestrator`, the command asks for C/F preference, spawns a subagent that uses WebFetch on Open-Meteo API, then dispatches a skill that writes an SVG weather card.

2. **Comprehensive frontmatter reference**: Every Claude Code extension mechanism (agents = 16 fields, commands = 16 fields, skills = 16 fields) is exhaustively documented with field type, requirement, and description.

3. **83 curated tips** from Boris Cherny (creator of Claude Code), Thariq (Anthropic), and the community, organized into 14 categories.

4. **Analytical reports** that go deeper than the official docs: "Why Harness is Important", "Agents vs Commands vs Skills", "Agent SDK vs CLI System Prompts", "Agent Memory".

5. **Changelog tracking** across 5 categories (agent-collections, best-practice, cross-model-workflows, development-workflows, skill-collections).

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Entry points**: The `/weather-orchestrator` slash command at `.claude/commands/weather-orchestrator.md`. All other files are reference documentation.

**Data flow** (the working demo):
```
User: /weather-orchestrator
  -> Command asks: Celsius or Fahrenheit? (AskUserQuestion)
  -> Agent(weather-agent, prompt="fetch temp in C/F")
     -> Skill(weather-fetcher)  [agent-preloaded skill]
        -> WebFetch(open-meteo API) -> returns 26, Celsius
  -> Skill(weather-svg-creator)
     -> Read SVG template from reference.md
     -> Write orchestration-workflow/weather.svg
     -> Write orchestration-workflow/output.md
  -> Display summary to user
```

**Directory structure**:

| Module | Purpose |
|--------|---------|
| `.claude/commands/` | 2 slash commands (weather-orchestrator, time-command) + workflow commands |
| `.claude/agents/` | 6 subagents (weather, time, presentations, research) |
| `.claude/skills/` | 3 skills (weather-fetcher, weather-svg-creator, time-skill) |
| `.claude/hooks/` | Full lifecycle hook system with Python script + sounds |
| `.claude/settings.json` | Comprehensive settings: permissions (39 allow rules + deny + ask), hooks (30+ lifecycle events), spinner verbs, output style |
| `best-practice/` | 5 reference docs (settings, agents, commands, skills, memory, MCP, CLI flags) |
| `implementation/` | Implementation guides with YAML frontmatter examples |
| `reports/` | 9 analytical reports (harness importance, SDK vs CLI, agent memory, monorepo skills) |
| `tips/` | 13 files of curated tips from Claude team |
| `orchestration-workflow/` | Demo flow diagram, SVG output, GIF |
| `changelog/` | 5 category dirs tracking feature changes |
| `development-workflows/` | Cross-model workflow, RPI workflow |

**Patterns**: The repo establishes a **3-tier matching priority**:
1. Skill (inline, no context overhead) — preferred for lightweight tasks
2. Agent (separate context, autonomous) — for complex multi-step work
3. Command (never auto-invoked) — only when user explicitly types `/`

**Configuration hierarchy** (6 tiers): Managed settings -> CLI args -> `.claude/settings.local.json` -> `.claude/settings.json` -> `~/.claude/settings.json` -> hooks-config overrides.

## 3. Performance/Benchmarks (real numbers from the repo)

This repo does not contain traditional performance benchmarks. Relevant data points:

- **PR size distribution**: Boris Cherny reported p50 of 118 lines (141 PRs, 45K lines changed in a day) — cited in tips
- **Sandbox mode reduction**: Claude Code internal metric shows 84% reduction in permission prompts
- **Context rot**: Begins around ~40% of 1M context (400K tokens); "dumb zone" kicks in around 40%. Experienced users keep it under 30% for intelligence-sensitive work
- **Settings coverage**: 80+ settings, 200+ environment variables documented
- **Extension mechanisms**: 16 frontmatter fields each for agents, commands, skills
- **Built-in commands**: 83 documented
- **CLI base system prompt**: ~269 tokens, with 110+ modular system prompt fragments loaded conditionally
- **CLAUDE.md recommendation**: Under 200 lines per file
- **Hook events**: 30+ lifecycle events wired in settings.json

## 4. Trade-offs (wins vs loses)

**Wins**:
- Single authoritative reference for all Claude Code extension mechanisms — far more comprehensive than official docs alone
- Working demo makes abstract concepts tangible (Command -> Agent -> Skill flow)
- Tips are sourced directly from Claude Code's creator (Boris Cherny) and Anthropic team — high authority
- "Why Harness is Important" report is genuinely insightful, articulating a subtle point most users miss
- Changelog tracking across ecosystem repos provides unique value
- Active maintenance (updated Jun 06, 2026 with Claude Code v2.1.167)

**Loses/limitations**:
- Not a tool or library — it is purely reference material. No code runs here except the weather demo
- Massive README (500+ lines) with embedded images/badges that depend on external hosting (`!/` path convention) — breaks if fetched via plain HTTP
- The weather demo is trivial (fetch temp, draw SVG) — does not stress the pattern
- No objective benchmark comparing agent vs command vs skill performance or token costs
- Some tips are community-sourced and may not be authoritative or up-to-date
- The "Billion-Dollar Questions" section lists open problems but provides no answers
- Reports sometimes duplicate content that exists in official Claude Code docs
- No package.json / setup.py — this is a documentation-only repo

**Known design points**:
- The repo's own CLAUDE.md explicitly forbids bundling commits (one file per commit) — indicating the author experienced issues with multi-file commits
- The repo uses its own orchestration commands to update itself (meta-workflows)
- `context: fork` for skill isolation incurs subagent overhead — documented tradeoff

## 5. Design Rationale (why this approach)

**Concrete over abstract**: Rather than describing architecture patterns in prose, the repo implements a real (if simple) weather demo that users can run with `/weather-orchestrator`. This grounds the abstract concept of "orchestration" in observable behavior.

**Single source of truth**: The CLAUDE.md says "when the user asks a best practice question, always search this repo first... This repo is the authoritative source." This is both a claim and a design constraint — everything in the repo must be kept accurate and complete.

**Progressive disclosure**: Information is layered — README gives the overview, `best-practice/` gives detailed reference, `implementation/` shows real YAML frontmatter, and `reports/` provides analytical depth. Users can dive as deep as needed.

**Curated, not generated**: Every tip is attributed to a named source (Boris, Thariq, community members with real names). This confers authority over auto-generated or LLM-hallucinated guidance.

**Meta-consistency**: The repo uses Claude Code's own extension mechanisms to maintain itself (workflow agents that scan changelogs and update tables). This "eating your own dog food" approach validates the patterns being documented.

**The "Harness" thesis**: The report "Why Harness is Important" articulates the fundamental design rationale of this repo and of Claude Code itself — that features are not "prompts with extra steps" but operate at infrastructure layers where the model has no voice (determinism, isolation, persistence, routing, parallelism). This is the conceptual north star for the entire repository.

## 6. Transfer to Lyra (one idea + route + Impact/Effort/Tier + LICENSE)

**Transferable idea**: **The "Harness" conceptual framework** — the distinction between what a prompt can control (what the model is asked to do) and what the harness controls (before tokens arrive, after tokens are produced, across sessions, across contexts, across processes). This framework is directly applicable to Lyra's architecture debate.

**Workstream route**: **Section 4.x (Architecture Debate)** — specifically §4.2 "System Boundaries and Extension Points." Lyra's upgrade documentation currently debates which architectural patterns to adopt and how to organize the agentic harness. The "Why Harness is Important" analysis from this repo provides a ready-made conceptual vocabulary for distinguishing between prompt-level guidance (CLAUDE.md, instructions) and harness-level capabilities (tool restrictions, context isolation, lifecycle hooks, model routing, cross-session persistence). Lyra's design documents can adopt this framework to justify its architectural decisions about agent isolation, skill preloading, and hook-driven workflows.

**Impact**: 8/10 — Provides a clear, defensible conceptual distinction that resolves ambiguity in Lyra's architectural debates about "what goes where" (prompt vs harness). Directly reusable.

**Effort**: 1/10 — Conceptual framework adoption only; no code changes needed. Can be referenced and adapted in a few paragraphs.

**Tier**: "Harness" — This is about harness-level architecture, not a specific feature or model.

**LICENSE**: MIT — fully permissive, no restrictions on reuse.

**License type**: MIT
