# Extend Claude with skills (code.claude.com/docs/en/skills)

Anthropic, Claude Code documentation. No explicit publication date.

## Key Technical Claims

1. **Skills extend Claude Code via SKILL.md files.** A directory-based plugin system where each skill is a folder with a SKILL.md entrypoint plus optional supporting files (templates, examples, scripts, reference docs). The directory name becomes the command name (e.g., `/deploy`).

2. **Four storage tiers with precedence rules:** Enterprise (org-wide managed settings) > Personal (~/.claude/skills/) > Project (.claude/skills/) > Plugin (<plugin>/skills/). Plugin skills use `plugin-name:skill-name` namespace to avoid conflicts. Live change detection watches all tiers; edits take effect without restart.

3. **Skills are loaded lazily, unlike CLAUDE.md:** Description text is always in context (at 1% of context window budget); full body loads only when invoked. Each invoked skill stays in context for the session duration. Survives compaction: last-invoked skills get 5,000 tokens each, 25,000 combined budget.

4. **Rich frontmatter controls all behavior:** `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context: fork` (subagent isolation), `agent` type, `disable-model-invocation`, `user-invocable`, `paths` (glob-based activation), `hooks`, `shell`, `arguments` (named positional params), `argument-hint`. This is essentially a full plugin descriptor in YAML.

5. **Preprocessing before the model sees content:** Dynamic context injection via `!`command`` syntax runs shell commands before the skill renders. Output replaces the placeholder inline. Also supports multi-line `` ```! `` fenced blocks. Can be disabled organization-wide via `disableSkillShellExecution` in managed settings.

## Architecture/Mechanism Details

- **Directory structure:** `my-skill/SKILL.md` (required, under 500 lines recommended) + optional supporting files referenced from SKILL.md. Claude reads supporting files only when instructed by the skill content.

- **Subagent execution (`context: fork` + `agent:`):** Skill content becomes the prompt for a forked subagent. The `agent` field selects the execution profile (Explore, Plan, general-purpose, or custom agents from `.claude/agents/`). Explore/Plan agents skip CLAUDE.md and git status for a small context footprint.

- **Content lifecycle:** Invoked skills stay in context across turns. After auto-compaction, the most recent invocation of each skill is re-attached (5K tokens/skill, 25K combined). Older skills dropped if budget exceeded. Re-invoke after compaction to restore full content.

- **Permissions model:** `allowed-tools` grants pre-approved tools while skill is active (does not restrict other tools). Permission rules can target specific skills: `Skill(deploy *)` for prefix matching. `Skill` tool can be globally denied to disable all skills.

- **Dynamic substitution:** `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N` (shorthand), `$name` (named from `arguments` frontmatter). Shell-style quoting for multi-word args. `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}` for context-aware skills.

- **skillOverrides in settings.json:** Control skill visibility without editing SKILL.md. States: `on`, `name-only`, `user-invocable-only`, `off`. Written automatically by `/skills` menu. Plugin skills exempt.

## Numbers & Benchmarks

- Description `+ when_to_use` truncated at **1,536 characters** combined per skill in listings.
- Skill listing budget: **1%** of context window by default, configurable via `skillListingBudgetFraction`.
- After compaction: **5,000 tokens** per skill, **25,000 tokens** combined budget for re-attached skills.
- SKILL.md recommended **under 500 lines**; move detailed reference to supporting files.
- Two-way table: Skill with `context: fork` uses subagent system prompt + SKILL.md as task; Subagent with `skills` field uses preloaded skills + delegation message.
- Bundle: `/run` and `/verify` skills require Claude Code **v2.1.145+**.

## Transfer to Lyra

**One idea:** Adopt the SKILL.md directory-based plugin architecture with frontmatter-driven invocation control and subagent isolation as Lyra's plugin/command system.

Lyra currently lacks a standardized mechanism for third-party or user-defined plugins. The skill model solves this cleanly: a plugin is a directory with `SKILL.md`, supporting files, and YAML frontmatter that declares its triggers (`paths`, `description`), tool scoping (`allowed-tools`), execution isolation (`context: fork`, `agent`), and argument protocol (`arguments`, `$ARGUMENTS`). No plugin registry, no lifecycle hooks — just a file in a known directory with structured metadata.

For Lyra specifically, `context: fork` + `agent: Explore` would map perfectly to Lyra's research/verification workflows: a plugin provides instructions, Lyra forks an isolated research agent with read-only tools, the agent executes against the codebase, and results return to the main planner. The dynamic context injection pattern (`!`command``) lets plugins inject live data (current diff, test results, file listings) before the model sees the prompt, reducing hallucination risk.

**Workstream route: §4.3 Plugin System**

The frontmatter fields `allowed-tools`, `context: fork`, `agent`, and `disable-model-invocation` directly define a plugin contract that Lyra's §4.3 Plugin System spec should codify. Lyra's plugin bus would read skill directories, parse frontmatter into a capability descriptor (triggers, tools, execution profile), and route invocations to the appropriate subagent (Explore for read-only research, general-purpose for codegen, Plan for design). The `paths` glob field already solves path-scoped activation — a plugin for "only activate when the user asks about testing in Python files."
