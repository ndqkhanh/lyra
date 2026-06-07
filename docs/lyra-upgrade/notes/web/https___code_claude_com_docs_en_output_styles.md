# Output Styles (Claude Code Docs)

## Source

- **URL**: https://code.claude.com/docs/en/output-styles
- **Source**: Claude Code official documentation (Anthropic)
- **Date**: Undated (current as of Claude Code v2.1.x era)

## Key Technical Claims

1. **Output styles modify the system prompt, not the knowledge base.** They change *how* Claude responds (role, tone, output format) without changing *what* Claude knows. This is a clean separation of concerns: knowledge goes in CLAUDE.md, behaviour goes in output styles.

2. **Three built-in styles:**
   - *Proactive*: Executes immediately, makes reasonable assumptions instead of pausing for routine decisions, prefers action over planning. Stronger autonomous-execution guidance than auto mode; still shows permission prompts.
   - *Explanatory*: Provides educational "Insights" in between completing SE tasks. Helps the user understand implementation choices and codebase patterns.
   - *Learning*: Collaborative, learn-by-doing mode. Adds "Insights" while coding AND asks the user to contribute small, strategic pieces of code via `TODO(human)` markers.

3. **Custom output styles are Markdown files** with YAML frontmatter saved at user level (`~/.claude/output-styles/`), project level (`.claude/output-styles/`), or managed policy level.

4. **`keep-coding-instructions` flag**: When `true`, Claude Code's built-in software engineering instructions are preserved and the custom style is appended. When `false` (default), the SE instructions are stripped entirely -- useful when Claude is not doing software engineering (e.g., writing assistant, data analyst).

5. **Plugins can ship output styles** and use `force-for-plugin: true` to automatically apply a style whenever the plugin is enabled, overriding the user's `outputStyle` setting.

6. **Output styles are read once at session start** and cached. Changes take effect after `/clear` or a new session. Prompt caching reduces the input token cost after the first request.

## Architecture / Mechanism Details

- Output styles directly modify the system prompt. Custom instructions are appended to the end. All styles trigger periodic reminders for Claude to adhere to them.
- `keep-coding-instructions: true` is the key toggle: it separates the communication layer from the capability layer.
- Settings precedence: managed policy > project-level settings > user-level settings. The `outputStyle` field lives in `.claude/settings.local.json` (local project level) or `.claude/settings.json`.
- Set via `/config` menu or by editing `outputStyle` field directly in settings JSON.
- Plugins can force an output style automatically via `force-for-plugin: true` in the style's frontmatter, without user selection.
- Custom styles can be distributed as part of plugins (in an `output-styles/` directory).

## Numbers & Benchmarks

- No explicit benchmarks. Token impact described qualitatively:
  - Adding instructions increases input tokens (mitigated by prompt caching after first request).
  - Explanatory and Learning styles produce longer responses by design (increased output tokens).
  - Custom style token cost depends entirely on the instructions provided.
- The standalone `/output-style` command was deprecated in v2.1.73 and removed in v2.1.91.

## Transfer to Lyra

**One idea**: Adopt an "output profile" system for Lyra sub-agents. Just as Claude Code output styles cleanly separate *how to respond* (role/tone) from *what to know* (CLAUDE.md), Lyra agents could carry a lightweight "persona profile" (a YAML/Markdown snippet injected into the agent's system prompt) that defines tone, verbosity, and decision-making style independently of domain knowledge stored in a shared vector store or memory layer.

**Concrete application**: A Lyra "debugging agent" could ship with a persona profile that sets terse, evidence-first output, while a "mentor agent" profile sets explanatory, Socratic-style output -- both drawing from the same knowledge store. The `force-for-plugin` pattern is especially relevant: if Lyra supports plugins, a plugin could force a compatible persona profile automatically without user configuration.

**Workstream route**: $4.1 (Agent Architecture) -- persona/profile management is a system prompt construction concern. Alternatively, a dedicated $4.x subsection on "Agent Persona & Tone Profiles" could be created if the architecture grows complex enough.

**Impact**: 7/10 -- directly applicable, cleanly transferable, requires minimal new infrastructure.
**Effort**: 3/10 -- light implementation overhead. The Markdown-file-with-frontmatter pattern is simple and mirrors existing patterns.
**Tier**: Quick Win -- can be prototyped as a design doc and small PoC in one sprint.
