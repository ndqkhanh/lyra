# Feature Parity Matrix: Lyra vs Comparable Harnesses

**Purpose**: Compare Lyra's capabilities against 5 researched AI coding harnesses to identify gaps and transferable features.

**Legend**:
- ✅ Full support
- 🟡 Partial support
- ❌ Not supported
- 🔄 Planned/In progress

---

## Core Architecture

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **Multi-agent orchestration** | ✅ (planner/architect/executor/verifier) | 🟡 (build/plan/general) | ✅ (specialist delegation) | 🟡 (general-purpose) | ❌ | ❌ |
| **Mode switching** | 🟡 (agent invocation) | ✅ (Tab key toggle) | ✅ (Plan/Act toggle) | ❌ | ❌ | ❌ |
| **Context preservation across modes** | ✅ | ✅ | ✅ | N/A | N/A | N/A |
| **SDK-first architecture** | ❌ | ❌ | ✅ (@cline/sdk) | ✅ (API) | ❌ | ❌ |
| **Language** | TypeScript | TypeScript | TypeScript | Rust | Python | Go |
| **License** | TBD | MIT | Apache 2.0 | Apache 2.0 | Apache 2.0 | FSL-1.1-MIT |

---

## Memory & Context

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **Project memory** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Wiki system** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Episodic memory** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Semantic memory** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Working memory** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Shared memory** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Repository mapping** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Codebase-wide context** | 🟡 (via search) | 🟡 | 🟡 | 🟡 | ✅ (semantic map) | 🟡 (LSP) |
| **Session persistence** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Development Features

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **Cross-file edits** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Linter/compiler monitoring** | 🟡 | 🟡 | ✅ | 🟡 | ✅ (auto-fix) | 🟡 |
| **Git integration** | ✅ | ✅ | ✅ | ✅ | ✅ (auto-commit) | ✅ |
| **Checkpoint/rollback** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **LSP integration** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **MCP support** | ✅ | ❌ | ✅ | ✅ (70+ extensions) | ❌ | ✅ (3 transports) |
| **Hooks system** | ✅ | ❌ | ❌ | ❌ | ❌ | 🟡 (preliminary) |
| **Skills system** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ (Agent Skills) |

---

## Model & Provider Support

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **Multi-provider** | ✅ | ✅ | ✅ | ✅ (15+) | ✅ (100+) | ✅ |
| **Mid-session model switching** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Local model support** | ✅ | ✅ | ✅ (Ollama/LM Studio) | ✅ | ✅ | ✅ |
| **Model routing** | 🔄 (planned) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Cost tracking** | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | ✅ |

---

## User Interface

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **CLI** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Desktop app** | ❌ | ✅ (macOS/Win/Linux) | ❌ | ✅ (macOS/Win/Linux) | ❌ | ❌ |
| **IDE extensions** | ❌ | ❌ | ✅ (VS Code/JetBrains) | ❌ | 🟡 (watch mode) | ❌ |
| **Web UI** | ❌ | ❌ | ✅ (Kanban) | ❌ | ❌ | ❌ |
| **Voice input** | 🔄 (foundation laid) | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Desktop notifications** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Collaboration & Integration

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **Workspace sharing** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (multi-client) |
| **Messaging platforms** | ❌ | ❌ | ✅ (Slack/Discord/etc) | ❌ | ❌ | ❌ |
| **CI/CD integration** | 🟡 | 🟡 | ✅ (headless JSON) | ✅ (API) | 🟡 | 🟡 |
| **Scheduled agents** | ❌ | ❌ | ✅ (cron) | ❌ | ❌ | ❌ |
| **Embedding API** | ❌ | ❌ | ✅ (SDK) | ✅ | ❌ | ❌ |

---

## Configuration & Extensibility

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **Project config files** | ✅ (.omc/) | ✅ (.clinerules) | ✅ (.clinerules) | ✅ | ✅ | ✅ (.crush.json) |
| **Global config** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Custom distributions** | ❌ | ❌ | ❌ | ✅ (branded) | ❌ | ❌ |
| **Plugin system** | 🟡 (MCP) | ❌ | ✅ | ✅ (MCP) | ❌ | ✅ (MCP) |
| **Shell expansion in config** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ ($VAR, $(cmd)) |

---

## Advanced Features

| Feature | Lyra | OpenCode | Cline | Goose | Aider | Crush |
|---------|------|----------|-------|-------|-------|-------|
| **Research agents** | ✅ | 🟡 (general) | 🟡 | ✅ (general-purpose) | ❌ | ❌ |
| **State management** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Image/web context** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Auto-testing** | 🟡 | 🟡 | 🟡 | 🟡 | ✅ (with auto-fix) | 🟡 |
| **Community model repo** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (Catwalk) |

---

## Key Differentiators

### Lyra's Unique Strengths
1. **Advanced memory architecture** (episodic/semantic/working/shared)
2. **Wiki system** for persistent knowledge
3. **Multi-agent orchestration** (planner/architect/executor/verifier)
4. **Hooks system** for extensibility
5. **State management** for complex workflows
6. **Research-focused** capabilities

### Gaps to Address (High Priority)

#### From Cline
- **Checkpoint-based rollback** (Impact: 5, Effort: 4, Tier: BREAKTHROUGH)
- **Messaging platform integrations** (Impact: 5, Effort: 4, Tier: BREAKTHROUGH)
- **Scheduled agents** (Impact: 4, Effort: 3, Tier: HIGH)

#### From Aider
- **Repository mapping** (Impact: 5, Effort: 4, Tier: BREAKTHROUGH)
- **Watch mode for IDE integration** (Impact: 5, Effort: 4, Tier: BREAKTHROUGH)
- **Image/web page context** (Impact: 4, Effort: 3, Tier: HIGH)

#### From Crush
- **Mid-session model switching** (Impact: 5, Effort: 4, Tier: BREAKTHROUGH)
- **Workspace collaboration** (Impact: 5, Effort: 4, Tier: BREAKTHROUGH)
- **LSP integration** (Impact: 5, Effort: 4, Tier: BREAKTHROUGH)
- **Desktop notifications** (Impact: 3, Effort: 2, Tier: MEDIUM)

#### From OpenCode
- **Mode-based agent switching** (Impact: 4, Effort: 3, Tier: HIGH)
- **Desktop app** (Impact: 3, Effort: 5, Tier: MEDIUM)

#### From Goose
- **Custom distribution framework** (Impact: 3, Effort: 5, Tier: MEDIUM)
- **Embedding API** (Impact: 4, Effort: 4, Tier: HIGH)

---

## Implementation Priority

### Phase 1: Core Enhancements (Q2 2026)
1. **Repository mapping** — Aider-style codebase semantic map
2. **Mid-session model switching** — Crush-style provider switching
3. **Checkpoint-based rollback** — Cline-style state tracking
4. **LSP integration** — Crush-style language server support

### Phase 2: Collaboration (Q3 2026)
5. **Workspace collaboration** — Crush-style multi-client
6. **Messaging platform integrations** — Cline-style async notifications
7. **Desktop notifications** — Crush-style focus-aware alerts

### Phase 3: Advanced Features (Q4 2026)
8. **Watch mode** — Aider-style IDE integration
9. **Scheduled agents** — Cline-style cron automation
10. **Embedding API** — Goose-style programmatic access

### Phase 4: Distribution (2027)
11. **Custom distributions** — Goose-style branded versions
12. **Desktop app** — OpenCode-style native application

---

**Last Updated**: 2026-05-31  
**Research Coverage**: §3.2 rows 45-50 (5/6 harnesses, 1 failed/404)
