# Gap Analysis: Current Lyra vs AGI Target State

> Generated 2026-05-26 from comprehensive codebase survey (40 modules, src/lyra/) and 7-domain synthesis.

## Executive Summary

Lyra is **far more mature** than initially assumed. The codebase already implements 80-95% of synthesis targets across Memory, Skills, Tools, Orchestration, Autonomy, and UI/UX. The primary gap is **Safety & Alignment** (est. ~60% of target), followed by integration hardening and benchmarking infrastructure.

## Domain-by-Domain Assessment

### 1. Memory Architecture

| Target (Synthesis) | Current State | Gap |
|---|---|---|
| L0 Working Memory | `lyra-cli/memory/` — L1 atom store, RRF search, BM25+Vector fusion | **DONE** |
| L1 Session Memory | `lyra-harness-core/memory_store/` — Working memory, session store | **DONE** |
| L2 Episodic Memory | `lyra-memory` — Dream 4-phase consolidator, agentic Zettelkasten | **DONE** |
| L3 Semantic Memory | `lyra-knowledge-graph`, `lyra-memory` cognitive stack (beliefs/valence/thalamic) | **DONE** |
| Active Retrieval (multi-hop) | Active reconstruction engine, LP-RAG routing | **DONE** |
| Hybrid Storage (Verbatim+Symbolic+Graph) | All present — KV-cache, modular compression, KG fact | **DONE** |
| CoMem Async Pipeline | `lyra-memory` CoMem async pipeline | **DONE** |
| MemGrad Optimization | Feedback descent, MemGrad optimization | **DONE** |
| Memory Transplant | `lyra-memory` memory transplant module | **DONE** |
| Cue-Tag-Episode/Semantic (MRAgent) | Routing fabric, heuristic pool | **PARTIAL** |

**Gap: MRAgent-style Cue-Tag retrieval** — The routing fabric exists but doesn't fully implement MRAgent's cue-tag-episode + cue-tag-semantic dual encoding. Estimated effort: ~500 lines.

**Score: 90% complete**

### 2. Skills System

| Target (Synthesis) | Current State | Gap |
|---|---|---|
| 40+ built-in skills | `lyra-cli/skills/` — 40+ SKILL.md files (API, architecture, debug, security, TDD, etc.) | **DONE** |
| Skill loader/manager | `skill_loader.py`, `skill_manager.py`, `builtin_skills.py` | **DONE** |
| Self-evolving skills | `lyra-skill-evolution` — SkillOpt text optimization, AEvo meta-editing | **DONE** |
| Skill curation | `lyra-skill-curator` — Full lifecycle curation | **DONE** |
| Skill weaving/composition | `lyra-skill-weaver` — Composition patterns | **DONE** |
| Auto-extraction (Trace2Skill) | `lyra-harness-core/skill_auto/` — Trace2Skill pattern | **DONE** |
| Skill drift monitoring | `lyra-harness-core/skill_drift/` — Performance drift detection | **DONE** |
| Skills packs (atomic/heavy/safety) | `lyra-skills` — Organized packs | **DONE** |
| Skill validation gates | Not fully implemented | **GAP** |
| Cross-skill knowledge transfer | Not present | **GAP** |

**Gaps:**
1. **Skill validation gates** — SkillOpt-style automated validation before skill promotion. ~400 lines
2. **Cross-skill knowledge transfer** — Sharing learned patterns between skill domains. ~600 lines

**Score: 85% complete**

### 3. Tools / Plugins / MCP

| Target (Synthesis) | Current State | Gap |
|---|---|---|
| MCP protocol support | `lyra-cli/mcp/` — MCP manager, server registry, ECC integration | **DONE** |
| MCP client | `lyra-mcp`, `mcp_integration/` | **DONE** |
| Tool execution engine | `lyra-harness-core/tool_runtime/` — Execution, retry, types | **DONE** |
| Eager tools | `lyra-cli/eager_tools/` — Eager execution engine (526 lines) | **DONE** |
| Plugin system | `lyra-core/plugins/` | **DONE** |
| Tool search | `lyra-core/tools/tool_search.py` (622 lines) | **DONE** |
| Viper protocol | `lyra-viper-mcp` — Viper adapter | **DONE** |
| Plugin ecosystem (40+ tools) | Core tool infrastructure present, count varies | **PARTIAL** |
| Plugin hot-reload | Not confirmed | **GAP** |
| Tool composition/pipe | Not confirmed | **GAP** |

**Gaps:**
1. **Plugin hot-reload** — Dynamic plugin loading without restart. ~300 lines
2. **Tool composition pipelines** — Chaining multiple tools declaratively. ~400 lines

**Score: 85% complete**

### 4. Agent Orchestration

| Target (Synthesis) | Current State | Gap |
|---|---|---|
| 3-layer hierarchy (Orchestrator→Team Lead→Worker) | `lyra-core/orchestration/` — Workflow orchestrator, agent models, phase executors | **DONE** |
| SOP-based teams (MetaGPT) | `lyra-core/teams/agent_teams.py` (550 lines) — SOP role-based teams | **DONE** |
| Subagent management | `lyra-core/subagent/`, `lyra-cli/agents/` | **DONE** |
| Swarm patterns | `lyra-agent-swarm`, `lyra-colony` | **DONE** |
| Agent lifecycle | `lyra-agent-lifecycle` | **DONE** |
| Ralph agent mode | `lyra-core/ralph/` | **DONE** |
| Auto-research agent | `lyra-autoresearch` | **DONE** |
| Compound AI coordination | Not present | **GAP** |
| Latent-space collaboration | Not present | **GAP** |
| Hash-anchored editing | Not present | **GAP** |

**Gaps:**
1. **Compound AI Coordination Protocol** — 5-slot model architecture (Normal/Thinking/Compact/Critique/VLM). ~800 lines
2. **Latent-space collaboration** — RecursiveMAS-style 34-75% token reduction. ~1,200 lines
3. **Hash-anchored edits** — 10x improvement over raw edits (6.7%→68.3%). ~500 lines

**Score: 80% complete**

### 5. Autonomy / Continuous Operation

| Target (Synthesis) | Current State | Gap |
|---|---|---|
| Autonomous mode | `lyra-core/auto_mode.py` (919 lines) — Triple-budget governance, stall detection, relay-race | **DONE** |
| Idempotent iterations | Multiple loop implementations (`loops/`, `loop/`) | **DONE** |
| Pivot/Refine self-recovery | `lyra-core/loop/pivot_refine.py` (583 lines) | **DONE** |
| Continual learning | `lyra-continual` | **DONE** |
| Goal-driven execution | Goal infrastructure present in core | **PARTIAL** |
| Checkpointing/resume | `lyra-cli/interactive/checkpoints.py` (709 lines) | **DONE** |
| 12-week autonomy roadmap | Not explicitly tracked | **GAP** |

**Gaps:**
1. **Explicit goal decomposition** — Breaking high-level goals into executable sub-goals with dependency tracking. ~600 lines
2. **Progress tracking dashboard** — Real-time visibility into long-running autonomous tasks. ~400 lines

**Score: 85% complete**

### 6. UI/UX

| Target (Synthesis) | Current State | Gap |
|---|---|---|
| 15 color themes | `lyra-cli/src/theme_engine.py` (514 lines), 15 themes cataloged | **DONE** |
| Theme hot-reload | `interactive/themes.py` (739 lines) | **DONE** |
| Vim/Emacs/Readline keybindings | `interactive/keybinds.py` (502 lines) | **DONE** |
| TUI (Ink-based) | `ui-terminal/` — Ink-based terminal TUI | **DONE** |
| WebSocket gateway | `tui_gateway/server.py` (2,169 lines) | **DONE** |
| HUD display | `lyra-cli/src/hud/` | **DONE** |
| Sound effects / audio feedback | Not present | **GAP** |
| Voice I/O | `lyra-core` TTS module exists | **PARTIAL** |
| Cockpit UI | `lyra-cockpit` | **DONE** |
| cmux-style UI patterns | Not present (GPL-3.0 compliance needed) | **GAP** |

**Gaps:**
1. **Sound effects system** — Event-driven audio feedback. ~500 lines
2. **Voice input pipeline** — Speech-to-text with model routing. ~700 lines
3. **cmux UI patterns** — Vertical tabs, notification rings (GPL-3.0 compliance). ~800 lines

**Score: 80% complete**

### 7. Safety & Alignment (CRITICAL GAP)

| Target (Synthesis) | Current State | Gap |
|---|---|---|
| 10-layer safety framework | `lyra-safety-governance` — Parallax cognitive-executive separation (98.9% block rate) | **PARTIAL** |
| 4-level approval gates | `lyra-core/permissions/` — Permission engine exists | **PARTIAL** |
| Reasoning monitor | Not confirmed as separate module | **GAP** |
| ARIS 3-stage adversarial review | `lyra-core/verifier/adversarial.py` (622 lines) | **DONE** |
| Constitutional verification | `lyra-harness-core/verifier/` — Constitutional gates | **DONE** |
| Sandbox execution | `lyra-sandbox`, `lyra-cli/sandbox/` | **DONE** |
| Intent monitoring | `lyra-core/safety/` — Intent monitoring | **DONE** |
| Dual-use detection | `lyra-harness-core/verifier/` — Dual-use gate | **DONE** |
| Chain-of-note verification | `lyra-harness-core/verifier/` — Chain-of-note gate | **DONE** |
| Retraction gates | `lyra-harness-core/verifier/` — Retraction gate | **DONE** |
| Audit trail | Not explicit | **GAP** |
| Alignment drift monitoring | Not present | **GAP** |
| Cross-model adversarial validation | Not present | **GAP** |

**Gaps:**
1. **4-level Approval Gate Router** — Structured escalation: AUTO→NOTIFY→CONFIRM→BLOCK. ~600 lines
2. **Reasoning Monitor** — 5-pattern detection (deception, self-deception, reward hacking, goal misgeneralization, power-seeking). ~800 lines
3. **Audit Engine** — Immutable audit trail with cryptographic verification. ~500 lines
4. **Alignment Drift Monitor** — Continuous measurement of value alignment. ~700 lines
5. **Cross-Model Adversarial Validation** — Multi-model claim verification (90%+ accuracy target). ~600 lines

**Score: 60% complete**

## Priority Matrix

| Priority | Domain | Current | Target | Effort | Impact |
|---|---|---|---|---|---|
| **P1** | Safety & Alignment | 60% | 95% | ~3,200 lines | Critical — AGI safety floor |
| **P2** | Agent Orchestration | 80% | 95% | ~2,500 lines | High — Multi-agent capability |
| **P2** | Skills System | 85% | 95% | ~1,000 lines | High — Self-improvement |
| **P3** | UI/UX | 80% | 90% | ~2,000 lines | Medium — User experience |
| **P3** | Autonomy | 85% | 95% | ~1,000 lines | Medium — Continuous operation |
| **P3** | Tools/Plugins | 85% | 95% | ~700 lines | Medium — Extensibility |
| **P4** | Memory | 90% | 98% | ~500 lines | Low — Already excellent |

## Total Estimated Effort

- **New code**: ~10,900 lines across all domains
- **Modified code**: ~2,000 lines (integration, hardening)
- **Tests**: ~5,000 lines (80%+ coverage target)
- **Documentation**: ~3,000 lines
- **Total**: ~20,900 lines
- **Timeline**: 16 weeks (4 phases of 4 weeks each)

## Key Findings

1. **Memory is the strongest domain** — 27 subpackages, 14K+ lines in lyra-memory alone. The 3-tier architecture with active retrieval is already implemented.
2. **Safety needs the most work** — Despite solid foundation (Parallax, 98.9% block rate), the approval gate routing, reasoning monitoring, and audit trail are incomplete.
3. **Skills system is surprisingly mature** — Full lifecycle (curation, evolution, weaving, drift detection) already exists. SkillOpt and AEvo are integrated.
4. **Compound AI coordination is the biggest orchestration gap** — No multi-model coordination protocol yet.
5. **UI is feature-rich** — 15 themes, 3 keybinding modes, TUI, and cockpit exist. Sound/voice are the missing pieces.
