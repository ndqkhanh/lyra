# Skill authoring best practices (platform.claude.com/docs)

Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
Author/Org: Anthropic (Claude Platform Docs)
Date: No publication date visible

## Key Technical Claims

1. **Context window is a public good.** Every token in a Skill competes with conversation history and other context. Only skill metadata (name + description) is pre-loaded at startup; SKILL.md is read only when the skill becomes relevant, and additional files only as needed.

2. **Progressive disclosure is the core architecture.** SKILL.md serves as a thin table of contents. Reference files (FORMS.md, reference/*.md, examples.md) are loaded on demand via bash Read tools. No context penalty for unread files -- they sit on the filesystem consuming zero tokens until accessed.

3. **Degrees of freedom framework.** Three tiers of specificity:
   - **High freedom** (text instructions): multiple approaches valid, decisions depend on context.
   - **Medium freedom** (pseudocode/scripts with params): preferred pattern exists, some variation OK.
   - **Low freedom** (specific scripts, no/few params): fragile operations, consistency critical.

4. **Evaluation-driven development.** Create evaluations BEFORE writing documentation. Identify gaps by running Claude on representative tasks without a Skill. Three evaluation scenarios minimum. Measure baseline, write minimal instructions, iterate based on observed failures.

5. **Iterative development with Claude itself.** Use one Claude instance (Claude A) to author and refine the skill, another (Claude B) to test it in real workflows. Observe actual behavior, not assumptions.

6. **MCP tool references require fully qualified names.** Format: `ServerName:tool_name`. Without the prefix, Claude may fail to locate the tool when multiple MCP servers are available.

7. **"Solve, don't punt."** Utility scripts should handle errors explicitly (FileNotFoundError -> create default, PermissionError -> alternative path) rather than failing and asking Claude to recover.

8. **No voodoo constants.** Every configuration parameter must be justified and documented. Example: `TIMEOUT = 30  # HTTP requests typically complete within 30 seconds`.

## Architecture/Mechanism Details

**Skill directory structure:**
```
pdf/
├── SKILL.md              # Main instructions (loaded when triggered)
├── FORMS.md              # Form-filling guide (loaded as needed)
├── reference.md          # API reference (loaded as needed)
├── examples.md           # Usage examples (loaded as needed)
└── scripts/
    ├── analyze_form.py   # Utility script (executed, not loaded)
    ├── fill_form.py      # Form filling script
    └── validate.py       # Validation script
```

**Progressive disclosure flow:**
1. Startup: only `name` + `description` from YAML frontmatter loaded into system prompt.
2. When skill triggered: Claude reads SKILL.md via bash Read tool.
3. As needed: Claude reads reference files linked from SKILL.md (one level deep only).
4. Scripts: executed via bash without loading contents into context. Only output consumes tokens.

**Evaluation structure:**
```json
{
  "skills": ["pdf-processing"],
  "query": "Extract all text from this PDF file and save it to output.txt",
  "files": ["test-files/document.pdf"],
  "expected_behavior": [
    "Successfully reads the PDF file...",
    "Extracts text content from all pages...",
    "Saves the extracted text to a file named output.txt..."
  ]
}
```

**Plan-validate-execute pattern:** Create intermediate structured output (e.g., changes.json), validate with script before applying. Catches errors early, machine-verifiable, reversible planning phase.

**Runtime environment differences:**
- claude.ai: Can install packages from npm/PyPI, pull from GitHub.
- Claude API: No network access, no runtime package installation.

## Numbers & Benchmarks

- **`name` field**: Max 64 characters, lowercase letters/numbers/hyphens only, no XML tags, no reserved words ("anthropic", "claude").
- **`description` field**: Max 1024 characters, non-empty, third person, no XML tags.
- **SKILL.md body**: Under 500 lines for optimal performance.
- **Reference depth**: Keep all references exactly one level deep from SKILL.md (no deeply nested references -- Claude may use `head -100` to preview nested files, getting incomplete info).
- **Reference file TOC**: For files over 100 lines, include a table of contents for partial-read navigation.
- **Evaluation count**: At least three evaluations recommended.
- **Model testing**: Test with all target models (Haiku, Sonnet, Opus).

## Transfer to Lyra

### One transferable idea: Progressive disclosure for the plan corpus

Lyra's `docs/lyra-upgrade/` directory already resembles the skill directory structure: a top-level MASTER-PLAN.md that overviews the plan, with individual plan files (02-memory.md, 05-router.md, 07-plugins.md, etc.) acting as reference files. The problem is that there is no systematic progressive disclosure discipline.

**Apply the Agent Skills best practices to Lyra's documentation:**

1. **MASTER-PLAN.md as SKILL.md**: Keep it under 500 lines. It should be a thin table of contents pointing to individual plan files. Example from the skill docs: "**Memory System**: See [plans/02-memory.md](plans/02-memory.md) for implementation" rather than inlining everything.

2. **One level deep, always**: Every reference from MASTER-PLAN.md should point directly to plan files. Plan files should not chain-reference other plan files. This avoids the partial-read problem where Claude does `head -100` on a nested file and misses content.

3. **Table of contents in long plan files**: Any plan file over 100 lines (most of them) should have a TOC at the top so Claude can navigate it efficiently even with partial reads.

4. **Frontmatter discipline**: Each plan file should have YAML-style metadata with a clear `description` field that tells Claude when to read it: "Use this plan when implementing memory system features, context management, or tool integration for the Lyra upgrade." This is exactly the skill selection model.

5. **Evaluation-driven plan validation**: Before writing detailed plan content, create evaluation scenarios that test whether Claude (or the agent) can correctly follow the plan. Three scenarios minimum. This replaces the current "write first, verify later" pattern.

6. **Template pattern for plan output**: Use the strict template pattern for deliverable output (like plan implementations). Include a copyable checklist that can be tracked as work progresses.

### Workstream Route: Section 4.1 (Skills/Plugin System)

This directly feeds into the Skills and Plugin System workstream. The progressive disclosure architecture for agent skills is the exact pattern Lyra should use for its plugin system: a thin router SKILL.md that points to individual capability files, loaded on demand with no context penalty for unloaded content.

**Concrete recommendation:** Add a subsection to the plugin system plan (§4.1) titled "Progressive Disclosure Architecture" that specifies:
- Plugin SKILL.md must be under 500 lines
- Plugin description must be third person, include both what and when
- All reference files must be one level deep
- Each plugin gets its own directory with SKILL.md + reference files + optional scripts
- Scripts should handle errors explicitly (solve, don't punt)
- Evaluation scenarios required before plugin documentation is considered complete

**Route:** `docs/lyra-upgrade/brainstorm/07-plugins.md` (or the corresponding plan file in `plans/`) should be updated to include these patterns.
