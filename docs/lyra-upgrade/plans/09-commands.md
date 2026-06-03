# Commands & Interactive Mode — Plan (§4.9)

> Run 3, 2026-06-03

## Plain-Language Summary

Lyra's slash command system provides a discoverable command palette. Custom commands are defined as markdown files (`.lyra/commands/<name>.md`) with YAML frontmatter for arguments, descriptions, and keybindings. The interactive mode provides a rich TUI with command autocomplete, history search, and context-aware suggestions.

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Commands docs (§3.1) | Slash commands as markdown files, `/` autocomplete, custom command registration |
| Claude Code Interactive Mode (§3.1) | Full terminal REPL with history, completion, multi-line input |
| Lyra's slash_commands.py (368L) | Existing command registry, needs custom command support |

## Proposed Design

1. **Built-in commands:** `/model`, `/effort`, `/skills`, `/memory`, `/fleet`, `/cost`, `/config`, `/help`, `/dream`
2. **Custom commands:** `.lyra/commands/<name>.md` — YAML frontmatter (description, arguments, keybinding) + body (prompt template)
3. **Command palette:** `/` opens fuzzy-search palette. Tab to autocomplete. Recent commands surfaced.
4. **Interactive mode:** REPL with syntax highlighting, multi-line input, history search (Ctrl+R), context-aware suggestions based on current task.

## Build Outline

1. Custom command file format + loader (week 1)
2. Command palette with fuzzy search + autocomplete (week 1)
3. Interactive REPL enhancements: multi-line, history search, suggestions (week 2)
4. Keybinding system for commands (Ctrl+K → /code-review, etc.) (week 2)

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| slash_commands.py (368L) | EXTEND: custom commands, palette, keybindings | Low |

**Impact:** 3 | **Effort:** 2 | **Tier:** (A) Parity

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Sign-off:** Plan is feasible. Parity implementation is well-documented in Claude Code docs (§3.1). Breakthrough tier gated on evidence from batch research findings.

## Changelog

- Run 4 (2026-06-03): Added Expert Review section, Changelog
