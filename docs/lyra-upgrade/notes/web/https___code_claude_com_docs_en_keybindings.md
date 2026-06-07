# Customize Keyboard Shortcuts (Claude Code Docs)

**Source:** https://code.claude.com/docs/en/keybindings
**Author/Org:** Anthropic / Claude Code Team
**Date:** Not explicitly dated; references Claude Code v2.1.18+ as minimum version.

## Key Technical Claims

1. **Fully customizable keyboard shortcuts** via `~/.claude/keybindings.json` -- no restart required; file changes auto-detected and live-applied.
2. **Context-scoped binding blocks** -- each binding block targets a specific UI context (Global, Chat, Autocomplete, Confirmation, Tabs, Transcript, DiffDialog, etc.), and only the actions valid within that context can be bound.
3. **Rich action namespace** -- actions follow `namespace:action` format (e.g., `chat:submit`, `app:toggleTodos`, `diff:nextFile`), spanning 17+ namespaces covering the entire app surface.
4. **Chord (multi-key sequence) support** -- keystrokes can be chained: `ctrl+x ctrl+k` means press Ctrl+X, release, then Ctrl+K.
5. **Unbinding support** -- any default can be removed by setting the action to `null`, and unbinding all chords on a shared prefix frees that prefix for single-key use.
6. **Validation** -- `/doctor` reports warnings for parse errors, invalid contexts, reserved shortcut conflicts, terminal multiplexer conflicts, and duplicate bindings.
7. **Reserved shortcuts** -- Ctrl+C (interrupt), Ctrl+D (exit), Ctrl+M (identical to Enter in terminals), and Caps Lock (not delivered to terminal apps) cannot be rebound.
8. **Documented terminal conflicts** -- Ctrl+B (tmux prefix), Ctrl+A (GNU screen), Ctrl+Z (SIGTSTP).

## Architecture / Mechanism Details

- **Configuration format:** JSON with `$schema`, `$docs`, and a `bindings` array. Each binding block has a `context` string and a `bindings` map from keystroke string to action string (or `null` for unbind).
- **Keystroke syntax:** modifier keys joined with `+` (`ctrl`, `shift`, `alt`/`meta`, `cmd`/`super`). Uppercase letters without modifiers imply Shift. Chords use space separation.
- **Context system (19 contexts):** Global, Chat, Autocomplete, Settings, Confirmation, Tabs, Help, Transcript, HistorySearch, Task, ThemePicker, Attachments, Footer, MessageSelector, DiffDialog, ModelPicker, Select, Plugin, Doctor. Each with a curated action set.
- **Vim mode independence:** keybindings operate at the component level while vim mode handles text-input-level cursor/motion/mode -- they coexist without conflict. Escape in vim mode goes to NORMAL, not `chat:cancel`.
- **Platform awareness:** `cmd` modifier only detected in terminals with Kitty keyboard protocol or xterm modifyOtherKeys; otherwise use `ctrl` or `meta` for cross-platform bindings.

## Numbers & Benchmarks

No performance numbers or benchmarks provided. Documentation is purely config-level reference.

## Transfer to Lyra

**One Idea:** Context-scoped command routing with live-reload configuration.

Lyra's modular command/plugin system (brainstorm docs `05-router.md` and `07-plugins.md`) could adopt the same pattern: instead of flat keybindings, define binding blocks scoped to Lyra-specific "contexts" (e.g., `Chat`, `Session`, `Pipeline`, `DiffViewer`, `PluginBrowser`). Each plugin registers its context and available commands; the router layer merges them into a composite keybinding map. Configuration lives in a YAML/JSON file (e.g., `~/.lyra/keybindings.yaml`) that is watched for changes with `fs.watch` and hot-reloaded without restart.

The chord mechanism is particularly useful for Lyra's multi-step workflows: a chord like `ctrl+p ctrl+r` could trigger "pipeline run" without conflicts. The null-unbinding pattern also solves a pain point where conflicting terminal defaults (tmux/screen) cause user frustration.

**Workstream Route:** §4.x: **Command Router & Plugin Architecture** (cross-cutting both `05-router` and `07-plugins`). Specifically:
- The router (05) should support context-scoped action registrations, not flat keymaps.
- The plugin system (07) should allow plugins to declare their own contexts and actions, merged by the router.
- The configuration layer should support JSON Schema validation (like Claude Code's `$schema`) for editor autocompletion and error checking.
