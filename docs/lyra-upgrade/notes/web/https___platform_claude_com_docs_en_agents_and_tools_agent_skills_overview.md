# Agent Skills (platform.claude.com -- Anthropic Official Docs)

## Source
- **URL**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- **Author/Org**: Anthropic (official platform docs)
- **Date**: No explicit date on page; references beta headers with dates (skills-2025-10-02, code-execution-2025-08-25) suggesting late-2025 / early-2026
- **Related engineering blog**: "Equipping agents for the real world with Agent Skills" (https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

## Key Technical Claims

1. **Agent Skills are the canonical Anthropic mechanism for modular agent capability extension.** They package instructions, metadata, and optional resources (scripts, templates) into filesystem directories that Claude loads on demand.

2. **Three-level progressive disclosure architecture:**
   - **Level 1 -- Metadata (always loaded)**: YAML frontmatter with `name` + `description` (~100 tokens per Skill). Loaded at startup in the system prompt. Describes *what* the skill does and *when* to activate it.
   - **Level 2 -- Instructions (loaded when triggered)**: The `SKILL.md` body -- procedural knowledge, workflows, best practices (<5k tokens). Loaded via bash `read` when the description matches the user's request.
   - **Level 3+ -- Resources and code (loaded as needed)**: Bundled markdown files, executable scripts, reference materials. Scripts execute via bash with *output only* entering context (script code itself never loads). Effectively unlimited token cost because files sit on filesystem until accessed.

3. **Filesystem-based model enables "no practical limit on bundled content"** -- a skill can include dozens of reference files, comprehensive API docs, large datasets. Context penalty is zero for unused content.

4. **Skills are distinct from prompts** -- prompts are conversation-level, one-off instructions. Skills persist on filesystem, auto-discovered, and load on demand. "Create once, use automatically."

5. **Skill definition format**:
   ```yaml
   ---
   name: your-skill-name        # max 64 chars, lowercase+hyphens
   description: ...             # max 1024 chars, no XML tags
   ---
   ```

6. **Sharing and surface model is fragmented** -- Custom skills do NOT sync across surfaces (claude.ai / API / Claude Code are independent). API skills are workspace-wide; claude.ai skills are per-user; Claude Code skills are filesystem-based per project or per user.

7. **Runtime constraints differ by surface:**
   - Claude API: **No network access**, no runtime package installation, only pre-installed packages.
   - claude.ai: Varying network access depending on user/admin settings.
   - Claude Code: Full network access, but global package installation discouraged.

8. **Security warnings** -- Only use skills from trusted sources. Malicious skills could direct tool invocation, data exfiltration, unauthorized system access. Treat like installing software. External URL fetching in skills poses particular risk (fetched content may carry malicious instructions).

## Architecture/Mechanism Details

- **Trigger mechanism**: Claude reads skill metadata (YAML frontmatter) at startup. When a user message matches a skill's `description`, Claude invokes `bash: read <skill-dir>/SKILL.md` to load the instructions. This is not a regex/tool-call match -- Claude itself decides relevance based on the description string.

- **Token cost model**:
  | Level | When Loaded | Token Cost |
  |-------|------------|------------|
  | Level 1: Metadata | Always (startup) | ~100 tokens per Skill |
  | Level 2: Instructions | On trigger | Under 5k tokens |
  | Level 3+: Resources | As needed | Effectively unlimited |

- **Script execution efficiency**: When Claude runs a script (e.g., `validate_form.py`), the script's code never enters context -- only stdout/stderr output does. This makes deterministic operations far more efficient than having Claude generate equivalent code on the fly.

- **Pre-built skills available**: pptx, xlsx, docx, pdf. Open-source skill: claude-api skill (API reference for 8 languages). Published at github.com/anthropics/skills.

- **Required beta headers for API usage**: `code-execution-2025-08-25`, `skills-2025-10-02`, `files-api-2025-04-14`.

## Numbers & Benchmarks

- ~100 tokens per Skill for metadata (Level 1) -- negligible context overhead
- Under 5k tokens for SKILL.md body (Level 2)
- No hard benchmark numbers; the value proposition is qualitative (context efficiency)
- Max name length: 64 characters
- Max description length: 1024 characters
- Three beta header versions cited

## Transfer to Lyra

### One Idea: Three-Level Progressive Disclosure for Lyra's Plugin/Skill System

Lyra's current plugin architecture (brainstorm/07-plugins.md) lacks a formal loading strategy. It does not distinguish between metadata, instructions, and resources in terms of when they enter the context window. The consequence: every loaded plugin competes for the same context budget, limiting how many plugins Lyra can support simultaneously.

**The transfer**: Lyra should adopt the exact three-level loading model:

- **Level 1 (always loaded)**: Each plugin exposes only a `name` + `description` + `trigger_patterns` in a lightweight registration manifest. These are compiled into Lyra's system prompt at startup. Total overhead < 50 tokens per plugin -- Lyra can register 50+ plugins without noticeable context bloat.

- **Level 2 (loaded on trigger)**: When Lyra's router (or the user) activates a plugin, Lyra reads the plugin's full `INSTRUCTIONS.md` into context. This contains procedural knowledge, workflow steps, guardrails. Target < 3k tokens per activation.

- **Level 3 (loaded on demand)**: Plugin resources (reference data, templates, example files, DB schemas) remain on disk. Lyra reads only the specific files referenced by the current instruction step. Scripts execute via bash with output-only context cost.

**Key difference from Lyra's current design**: Lyra's brainstorm currently describes plugins as "modules activated on demand" but does not specify the *token cost layering*. This three-level model gives Lyra a principled way to scale to dozens of plugins without running out of context window.

### Adaptation for Lyra's constraints

Lyra does not have a VM/code execution container like Claude API. However, Lyra runs on the user's machine with full filesystem access -- making it more like Claude Code's skill environment. The bash-read pattern is directly applicable: Lyra can `cat` or `read` plugin files when triggered. Lyra's subagent spawning capability could also parallel the "script execution with output-only context cost" pattern by delegating deterministic work to subagents.

### Workstream Route: §4.7 Plugins (extend with progressive disclosure sub-section)

This should become a subsection under §4.7 Plugins (or a new §4.8 Skills if the architecture splits plugins from skills):

- **§4.7.1 Plugin Registration (metadata-only)**: Manifest format with name, description, trigger patterns
- **§4.7.2 Plugin Activation (instruction loading)**: When and how Lyra reads plugin INSTRUCTIONS.md
- **§4.7.3 Plugin Resources (on-demand loading)**: File access patterns, reference data, templates
- **§4.7.4 Plugin Scripts (output-only execution)**: Subagent delegation for deterministic tasks

If redesigning, consider renaming §4 from "Plugins" to "Skills & Plugins" to align with wider industry terminology (Anthropic Agent Skills, Kilo Skills, OMC Skills).
