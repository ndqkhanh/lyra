# Changelog

All notable changes to the Lyra project.

## [5.0.0] — 2026-05-24

### Added
- **135+ composable packages** across three tiers: Foundation, Breakthrough, AGI Ascent
- **Multi-agent orchestration** with PrimaryAgent + specialist agents (Code, Test, Review, Research)
- **Hierarchical 8-level memory system** with STM/LTM, hybrid BM25+vector retrieval, and consolidation
- **Hook system** for PreToolUse, PostToolUse, SessionStart, SessionEnd, and Stop events
- **Rule engine** across 10 categories (coding style, security, testing, patterns, etc.)
- **Skill registry** with 150+ trigger patterns and cross-source (ECC) import
- **AgentShield** security scanner: secrets, command injection, path traversal, SQLi, XSS
- **TokenObservatory** with 13 activity categories and 7 waste pattern detectors
- **TokenOptimizer** with model selection, context compression, and prompt caching
- **Cross-platform adapter layer** (Claude Code, Cursor, VS Code, JetBrains)
- **Task coordination**: allocator, load balancer, dependency manager, conflict resolver
- **ECC agent/skill import** with YAML frontmatter parsing
- **Unified agent registry** with multi-index dispatch
- **Deep reasoning engine** (CoT, tree search, multi-agent debate, hypothesis generation)
- **10-step research pipeline** with 7+ academic sources and citation traversal
- **Self-evolution** via GEPA prompt optimization and continuous learning
- Root-level `ARCHITECTURE.md` with Mermaid diagrams

### Changed
- Migrated from Textual TUI to Typer CLI + prompt_toolkit REPL (93% code reduction)
- Migrated from single-package to monorepo architecture
- Split kernel (`lyra-core`) from application (`lyra-cli`)
- TypeScript UI repackaged as separate workspace modules (`ui-core`, `ui-terminal`, `ui-transport`)

### Removed
- Textual-based TUI v1 (~18.5K lines removed)
- Legacy single-package structure

## [4.0.0] — 2026-05-18

### Added
- Multi-agent coordination (TaskAllocator, LoadBalancer, DependencyManager, ConflictResolver)
- Memory consolidation pipeline (STM → LTM with pattern extraction)
- Hook engine with priority-based async execution
- Rule engine with multi-category evaluation
- ECC agent integration framework

## [3.0.0] — 2026-05-12

### Added
- Agent base class with communication, memory, and execution tracking
- PrimaryAgent orchestrator with specialist delegation
- Short-term and long-term memory stores with JSON persistence
- Core task/result data models with validation
- Initial skill registry and parser

## [2.0.0] — 2026-04-27

### Added
- Multi-provider LLM support (Anthropic, OpenAI, DeepSeek, Gemini, xAI, Mistral)
- Streaming SSE responses
- Interactive CLI with slash commands
- Model picker UI with keyboard navigation
- Provider-agnostic AliasRegistry

## [1.0.0] — 2026-04-15

### Added
- Initial release with Anthropic Claude integration
- Basic CLI with Typer
- Task-based model routing
- Configuration persistence (`~/.lyra/`)
