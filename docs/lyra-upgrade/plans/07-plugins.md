# Plugins — Plan (§4.7)

> Run 3, 2026-06-03

## Plain-Language Summary

Lyra's plugin system loads Python packages that extend agent capabilities — adding custom tools, hook handlers, MCP servers, and UI components. Plugins are discovered from project-local and user-global directories, versioned, and hot-reloaded. A marketplace enables community sharing.

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Plugins docs (§3.1) | Plugin directory structure, manifest format, lifecycle hooks, hot-reload |
| Kilo Marketplace (§3.2) | Curated skills/MCP servers/modes packaged as installable plugins |
| Lyra's plugins/manifest.py (359L) | Existing manifest system, needs marketplace + discovery |

## Proposed Design

1. **Plugin structure:** `lyra-plugin-<name>/` with `manifest.json` (metadata, version, dependencies, tools, hooks) + `__init__.py` (entry point)
2. **Discovery:** Project-local (`.lyra/plugins/`), user-global (`~/.lyra/plugins/`), system (`/usr/share/lyra/plugins/`)
3. **Lifecycle:** Install → validate → activate → deactivate → uninstall. Hot-reload on manifest change.
4. **Marketplace:** Registry at `plugins.lyra.dev` — search, install, publish. Namespaced (`@user/plugin-name`).
5. **Sandboxing:** Plugins run in restricted Python subprocess with allowlisted imports.

## Build Outline

1. Plugin loader + manifest parser (week 1)
2. Lifecycle management (install/activate/deactivate/uninstall) (week 1)
3. Hot-reload on file change detection (week 2)
4. Marketplace registry + CLI (`lyra plugin search/install/publish`) (week 3-4)
5. Plugin sandboxing (restricted subprocess) (week 4)

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| plugins/manifest.py (359L) | EXTEND: lifecycle, discovery, marketplace | Medium |

**Impact:** 3 | **Effort:** 3 | **Tier:** (A) Parity

## Expert Review

**Mini-Debate Participants:** Senior UX Designer, Senior Backend Engineer, Adversarial Skeptic

**Skeptic's challenge:** "Port Claude Code's implementation directly — don't invent something new unless the evidence proves it's better."

**Resolution:** Parity port is the (A) tier baseline. Breakthrough enhancements must beat Claude Code's implementation on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence. Otherwise ship parity.

**Sign-off:** Plan is feasible. Parity implementation is well-documented in Claude Code docs (§3.1). Breakthrough tier gated on evidence from batch research findings.

## Changelog

- Run 4 (2026-06-03): Added Expert Review section, Changelog
