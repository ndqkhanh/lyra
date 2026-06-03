# Skills Systems, UI/UX, Voice Notifications & Developer Experience Research

> Research completed: 2026-05-25 | Sources: 10+ repos/docs analyzed

## 1. Skills Management Architecture

### 1.1 Skill Curation

**Academic Research Skills (ARS)** provides the most advanced curation model:
- Skills decomposed into discrete agents (7-13 per skill), each owning specific pipeline phases
- YAML frontmatter with enforced vocabularies: `data_access_level`, `task_type`, `status`, `related_skills`
- `MODE_REGISTRY.md` serves as canonical mode-to-skill mapping (~25 modes)

**Karpathy-style skills**: Principle-to-symptom mapping — each principle traces to a specific LLM pitfall. Imperative-to-declarative rewrite pattern operationalizes insights.

**ECC**: Hierarchical rules architecture: `common/` (language-agnostic) + language-specific directories.

**Key takeaway for Lyra**: YAML frontmatter with enforced vocabularies. Mode registry as single source of truth. Skills organized by domain with `common/` + language-specific hierarchy.

### 1.2 Loading Mechanism

**ARS**: Dual-track installation (plugin marketplace + symlink). SessionStart hook injects context with graduated verbosity (full on start/clear, minimal on resume/compact).

**ECC**: Install profiles (`--profile minimal|core|full`). Consult/advisory system for component discovery.

**CLI-Anything**: Auto-generates SKILL.md during pipeline phase 6.5. Files at canonical + packaged locations.

**Key takeaway**: Dual-track installation. Graduated verbosity context injection. Install profiles. Auto-generated SKILL.md from structured metadata.

### 1.3 Skill Creation and Evolution

**ARS Lifecycle**:
- `PATTERN PROTECTION (v3.6.7)` blocks hardened against 13/18 documented hallucination/drift patterns
- Skill size actively managed (142KB → 85KB, -40% by extracting to `references/`)
- CI enforces schema and protocol conformance (6+ scripts, GitHub Actions)

**ECC Instinct Learning**:
- `/instinct-status`, `/instinct-import`, `/instinct-export`
- `/evolve` clusters related instincts into skills
- `/prune` deletes expired pending instincts (30d TTL)
- `/learn-eval` extracts and evaluates patterns before saving

**Key takeaway**: Pattern protection blocks, version-tracked. Skill size budgets with auto-extraction. CI pipeline for schema conformance. Instinct learning with confidence scoring and TTL pruning.

### 1.4 Evaluation Pipeline

**ARS Multi-Layered Evaluation**:
1. **Integrity Gates** (Stage 2.5, 4.5): 7-mode blocking checklist
2. **Compliance Agent** (v3.4.0): PRISMA-trAIce + RAISE with tier-based blocking
3. **Claim-Faithfulness Audit** (v3.8.0): Judges citations against retrieved excerpts
4. **Temporal Verification** (v3.9.4): 5 temporal failure modes
5. **Cross-Index Triangulation** (v3.9.0): 3-index contamination detection
6. **Cross-Model Verification**: Sample checks on second model
7. **Reviewer Calibration**: FNR/FPR/balanced-accuracy against gold set
8. **Collaboration Depth Observer** (v3.5.0): 4-dimension rubric

**Key takeaway**: Multi-layered evaluation with integrity gates, compliance agents, claim audits, temporal verification, cross-index triangulation, cross-model verification.

---

## 2. UI/UX Innovations

### 2.1 CLI-Anything: Gold Standard CLI UI

- **Dual-Mode Operation**: REPL + one-shot subcommands
- **Stateful Context in Prompt**: Live project name, modified-state indicator
- **ReplSkin Framework**: Branded banners, styled prompts, command history, progress indicators
- **Structured JSON Output**: `--json` flag on every command universally
- **Undo/Redo**: Persistent project state with rollback
- **Preview Stack**: `preview`, `preview live`, `trajectory.json`
- **Trajectory Recording**: Complete command-to-preview history

### 2.2 Color Themes and Visual Design

- **ECC**: YAML frontmatter for visual configuration. Cursor rules with extended metadata. Adapter pattern for cross-platform hooks.
- **Status Line**: Full JSON stdin pipeline (`model.display_name`, context window stats, cost, workspace). Guided setup via `/statusline` slash command.

### 2.3 Keybindings and Interactions

- Status line customization via JSON stdin pipeline
- `/model`, `/context`, `/usage`, `/extra-usage`, `/config` for inner loop
- Command-Agent-Skill orchestration pattern

**Key takeaway**: Dual-mode operation with stateful context. `--json` flag everywhere. Undo/redo. Trajectory recording. Guided setup via slash commands. Full status line customization.

---

## 3. Voice/Audio Notification Systems

### 3.1 PeonPing: Complete Architecture

**Hook Events** (8 events): SessionStart, SessionEnd, SubagentStart, Stop, Notification, PermissionRequest, PostToolUseFailure, PreCompact, Rapid prompts (3+ in 10s)

**Five-Phase Pipeline**:
1. Event Mapping → CESP sound category
2. Sound Selection → Random from active pack manifest with no-repeat logic
3. Audio Playback → Platform-specific async chain
4. Notifications → Tab title update + desktop notification
5. Remote Routing → HTTP relay for SSH/containers

**Cross-Platform Audio**:
- macOS: `afplay` (built-in)
- Linux: `pw-play` → `paplay` → `ffplay` → `mpv` → `play` → `aplay`
- WSL: PowerShell MediaPlayer/SoundPlayer
- Windows: PowerShell MediaPlayer + WinForms overlay

**Desktop Notifications**: JXA Cocoa overlay (glassmorphism themes), notify-send (Linux), Toast (Windows)

**Pack Selection Hierarchy** (6 layers): session_override → path_rules → ide_rules → pack_rotation → default_pack → hardcoded

**Config**: `enabled`, `desktop_notifications`, `mobile_notify.enabled`, path rules, rotation modes, suppression settings

**Mobile Push**: ntfy.sh, Pushover, Telegram

**SSH Relay**: Relay server on local machine (port 19998), category-based endpoints

### 3.2 Alexop Sound Effects: Minimal Approach

4 hooks: SessionStart (`afplay horn.mp3 &`), UserPromptSubmit, Stop, PreCompact. Backgrounded with `&`.

**Key takeaway for Lyra**: Both levels — simple 4-event model + full PeonPing 5-phase pipeline. Pack selection hierarchy essential for production. MCP server for agent-controlled sound playback.

---

## 4. Developer Experience Patterns

### 4.1 Context Management

- Context rot onset: ~300-400K tokens (on 1M model)
- "Dumb zone": keep under 30% for experienced users, 40% for beginners
- Manual compact beats auto-compact
- Subagents as context isolation layers
- `"summarize from here"` before rewinding

### 4.2 Hook Patterns (5 Strategies)

1. On-demand hooks in skills (`/careful`, `/freeze`)
2. Skill usage measurement via PreToolUse
3. PostToolUse auto-formatting
4. Permission routing through Opus
5. Stop hooks for verification nudges

### 4.3 Skill Design Principles (9 Rules)

1. Structure as folders (references/, scripts/, examples/)
2. Build a Gotchas section
3. Description as trigger, not summary
4. Don't state the obvious — push out of default behavior
5. Goals and constraints, not prescriptive steps
6. Scripts and libraries for composition
7. Embed `!command` for dynamic shell output
8. Use `context: fork` for isolated subagent execution
9. Monorepo: organize skills in subfolders

### 4.4 Config-Driven Architecture

spaCy pattern: Pipeline composition, model selection, and parameters in config (YAML/TOML), not code:
```yaml
pipeline:
  - skill: intent_classifier
    model: bert-base
    threshold: 0.7
  - skill: tool_selector
    tools: [search, calculator, database]
```

---

## 5. Plugin/Extension Architectures

### 5.1 Cross-Platform Support

**CLI-Anything**: 7 platforms, all driving same generation pipeline via HARNESS.md

**ECC**: Per-platform adapter directories (9+ platforms). Translator pattern (Cursor adapter.js normalizes event formats).

### 5.2 Hook Configuration Hierarchy (7 Levels)

1. `~/.claude/settings.json` (all projects, local)
2. `.claude/settings.json` (single project, shareable)
3. `.claude/settings.local.json` (single project, gitignored)
4. Managed policy settings (organization-wide)
5. Plugin `hooks/hooks.json` (when enabled)
6. Skill/Agent YAML frontmatter (while active)

### 5.3 OpenHuman Integration Fabric

118+ third-party integrations via one-click OAuth. Each exposed as typed tools to the agent. Composio connector layer handles OAuth and tool calls.

### 5.4 PeonPing Adapter Architecture

Each IDE adapter translates platform-specific events to CESP v1.0 standard. Adapter types: Shell/PowerShell scripts, TypeScript plugins, filesystem watchers.

---

## 6. Novel Approaches Worth Adopting

| Approach | Description | Source |
|----------|-------------|--------|
| TokenJuice Compression | Rule-based overlay, up to 80% cost reduction | OpenHuman |
| Anti-Context-Rot Design | 29 Anti-Patterns, 22 IRON RULEs, read-only constraints | ARS |
| Material Passport | Append-only cross-session ledger | ARS |
| Sprint Contract Hard Gate | Two-call gate, pre-committed scoring plans | ARS |
| Memory as Editable Artifact | Obsidian vault, cross-agent shared memory | OpenHuman |
| Continuous Background Awareness | Auto-fetch every 20min per connection | OpenHuman |
| Honest Framing | Fence only what actually needs fencing | ARS |
| Merge-Designed Architecture | Skills layer onto project conventions | Karpathy |
| Calibrated Tradeoff | Explicit permission to bypass for trivial tasks | Karpathy |
| Adversarial Security | Red-team/blue-team/auditor pipeline | ECC |
| Output Verification | Beyond exit codes (magic bytes, structure, pixel/RMS) | CLI-Anything |
| HARNESS.md Decoupling | Platform-agnostic methodology document | CLI-Anything |

---

## 7. Summary: What Lyra Should Adopt

| Area | Highest Impact | Source |
|------|---------------|--------|
| Skill metadata | YAML frontmatter with enforced vocabularies, mode registry | ARS, ECC |
| Skill loading | Dual-track (plugin + symlink), graduated context injection | ARS |
| Skill lifecycle | Pattern protection blocks, CI enforcement, instinct learning | ARS, ECC |
| Evaluation gates | Multi-layered (integrity, compliance, claim, temporal, cross-model) | ARS |
| CLI UI | Dual-mode (REPL + one-shot), --json everywhere, ReplSkin, undo/redo, trajectory | CLI-Anything |
| Audio/voice | 8-event hook model, 5-phase pipeline, pack hierarchy, cross-platform, SSH relay, MCP control | PeonPing |
| Context management | ~30% threshold, manual compact, subagent isolation | Best Practices |
| Cross-platform | Per-platform adapter directories, CESP standard, translator pattern | ECC, PeonPing |
| Plugin architecture | Uniform contract, config-driven pipeline, versioned packages | spaCy, ECC |
| Cost optimization | TokenJuice compression, config-driven pipeline | OpenHuman, spaCy |
| Memory | Editable vault, cross-agent shared memory, continuous auto-fetch | OpenHuman |
| Anti-degradation | IRON RULE markers, Anti-Pattern tables, read-only constraints | ARS |
| Verification | Beyond exit codes (magic bytes, structure, pixel/RMS analysis) | CLI-Anything |
| Security | Red-team/blue-team/auditor adversarial pipeline | ECC |

Sources:
- [CLI-Anything](https://github.com/HKUDS/CLI-Anything)
- [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills)
- [Andrej Karpathy Skills](https://github.com/forrestchang/andrej-karpathy-skills)
- [Claude Code Best Practice](https://github.com/shanraisshan/claude-code-best-practice)
- [ECC](https://github.com/affaan-m/ECC)
- [OpenHuman](https://github.com/tinyhumansai/openhuman)
- [spaCy](https://github.com/explosion/spaCy)
- [PeonPing](https://github.com/PeonPing/peon-ping)
