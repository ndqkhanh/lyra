# Agent Skills in the SDK (Anthropic -- code.claude.com/docs)

> Fetched 2026-06-07 | Source: https://code.claude.com/docs/en/agent-sdk/skills

---

## Key Technical Claims

1. **Skills are exclusively filesystem artifacts.** There is no programmatic API for registering skills in the SDK. Every skill must be a `SKILL.md` file inside a directory under `.claude/skills/`. This is a first-class architectural constraint: skills are file-system-defined, not code-defined.

2. **Four-stage lifecycle:** (a) Discovery at startup from filesystem directories (metadata only), (b) Lazy loading of full SKILL.md content when the skill is triggered, (c) Autonomous invocation by the model based on description-to-context matching, (d) Execution with the session's allowed tool set.

3. **Skills are context filters, not sandboxes.** The `skills` option hides unlisted skills from the model and rejects them from the Skill tool, but their files remain on disk and are reachable through Read and Bash. This is an explicit design choice -- skill filtering controls model visibility, not filesystem access.

4. **`allowed-tools` frontmatter in SKILL.md does NOT work in the SDK.** Tool access must be controlled at the `allowedTools` level in the query configuration, not per-skill. This only works in the Claude Code CLI, making SDK skill tool restrictions strictly global.

5. **Skill namespacing uses `plugin:skill` convention** for plugin-provided skills, enabling clean disambiguation when multiple sources provide skills with the same short name.

## Architecture/Mechanism Details

### Discovery Sources (governed by `settingSources` / `setting_sources`)

- **`"user"` source:** `~/.claude/skills/` -- personal skills across all projects
- **`"project"` source:** `.claude/skills/` in `cwd` and every parent directory up to repo root -- team-shared via git
- **Plugin skills:** Bundled with installed Claude Code plugins

Default `query()` without explicit `settingSources` loads both user and project sources. If you set `settingSources` explicitly and omit `"user"` or `"project"`, skills are NOT loaded.

### Loading Strategy

```
Session Start
  --> Scan filesystem for .claude/skills/*/SKILL.md
  --> Collect metadata (name, description, frontmatter)
  --> Register skill metadata with Skill tool
  --> Model triggers skill via description match
  --> Load full SKILL.md content lazily
```

This is the critical architectural pattern: **metadata-first discovery, lazy content loading.** It avoids loading all skill content into context at startup.

### Skill Filtering

```python
# Enable every discovered skill
options = ClaudeAgentOptions(skills="all")

# Enable only specific skills by name
options = ClaudeAgentOptions(skills=["pdf", "docx"])

# Disable all skills
options = ClaudeAgentOptions(skills=[])
```

The `skills` option is additive with `allowedTools`. When `skills` is set, the SDK automatically adds the Skill tool to `allowedTools`. If an explicit `tools` list is also passed, `"Skill"` must be included in that list.

### Tool Restriction in SDK vs CLI

| Feature | Claude Code CLI | Agent SDK |
|---|---|---|
| `allowed-tools` in SKILL.md frontmatter | Supported | **Not supported** |
| `allowedTools` in query options | N/A | Controls tool access |
| `canUseTool` callback | N/A | Fine-grained per-tool decisions |

### Directory Structure

```bash
.claude/skills/processing-pdfs/
└── SKILL.md
```

Skills are single files or directories with supporting resources. The SKILL.md has YAML frontmatter (name, description, trigger patterns, etc.) followed by Markdown body content.

## Numbers & Benchmarks

None. This is a documentation/reference page, not a benchmarks paper. Key non-numeric items:

- Skill names match the `name` field in SKILL.md or the directory name (fallback)
- Plugin skills use `plugin:skill` naming (e.g., `oh-my-claudecode:verify`)
- Skills are discovered from every `.claude/skills/` directory in the path chain up to repo root
- Maximum practical discoverable skills limited by filesystem scanning (no hard cap documented)

## Transfer to Lyra

### One Idea: Filesystem-Defined Skills with Lazy Discovery

**Idea:** Adopt the same filesystem-first skill architecture for Lyra's 330+ skill inventory. Instead of loading all skills into context (or managing them through a code-level registry), Lyra should scan `~/.lyra/skills/` and `.lyra/skills/` at startup, collect only metadata (name, description, trigger keywords), and defer full skill content loading until the model triggers a skill by name or description match.

This solves a concrete scaling problem for Lyra: 330+ skills cannot all reside in active context. The Claude Agent SDK pattern of "metadata-upfront, content-on-demand" is a directly transferable mechanism.

**Lyra-specific adaptation:**
- Lyra's SkillNet graph (from §4.4 Skills Plane) can serve as the metadata index -- skills are discovered, registered in SkillNet, and lazily loaded from disk when the graph traversal reaches them
- Plugin skills (`plugin:skill` convention) map naturally to Lyra's §4.7 Plugin system
- The "context filter, not sandbox" principle means Lyra can safely list all 330+ skills without worrying about context overflow -- only triggered skills consume content space
- The `plugin:skill` namespacing solves the plugin naming collision problem Lyra would face when multiple plugins define a "code-review" or "deploy" skill

### Workstream Route: §4.4 Skills Plane -- subsection on Skill Loading Architecture

This maps most directly to **§4.4 Skills Plane** (Skills/Self-Evolution workstream) in Lyra's architecture. The SkillNet graph (already planned for §4.4) becomes the metadata registry; the lazy-loading filesystem pattern becomes the storage backend. There is secondary crossover to **§4.7 Plugins** for the `plugin:skill` namespacing convention.

Within the MASTER-PLAN, this reinforces the "safe evolution only" decision (SkillNet + GEPA, no self-modification) by grounding skill storage in the filesystem rather than in-memory registries that could be corrupted or overflowed.

### Impact-assessment

| Dimension | Rating | Rationale |
|-----------|--------|-----------|
| Impact    | 5/10   | Improves scalability and context management for the existing 330+ skill inventory; not a new capability but a critical architectural refinement |
| Effort    | 2/10   | Relatively low -- implement a directory scanner, metadata index (SkillNet integration), and lazy content loader. Existing SKILL.md files can be reused with frontmatter added. |
| Tier      | Quick Win | Pure architectural infra; no model changes, no new skills, no safety validation needed. Can be done alongside §4.4 implementation. |
