# Documentation Plan — README & Docs

**Per §6 + §9 of master prompt** — this is a PLAN describing the visual, sourced, builder-friendly documentation to write. Implementation happens in a future run.

---

## Goal

Update all Lyra docs + `README.md` to match the current + planned state with:
- **Visual** — Mermaid diagrams, charts, data models, flow diagrams
- **Interactive** — scannable, attractive to builders
- **Sourced** — every novel technique cites paper/repo inspiration

---

## Documentation Inventory (to update)

### Top-level
- `README.md` — Main project entry point (likely outdated)
- `CONTRIBUTING.md` — How to contribute
- `CHANGELOG.md` — Release history (may not exist)

### Packages (`packages/lyra-*/README.md`)
Scan each package for outdated docs:
- `lyra-cli/`
- `lyra-core/`
- `lyra-harness-core/`
- `lyra-memory/`
- `lyra-pentest/`
- `lyra-research/`
- Other packages

### docs/ directory
- `docs/research/` — Research notes (many in lyra-upgrade)
- `docs/operations/` — Ops guides (US-012, US-031 implementations)
- `docs/performance/` — Performance docs
- `docs/design/` — Design docs

---

## README.md Structure (Proposed)

```markdown
# Lyra

> The Omni-Agent. Multi-agent AI harness for deep research, coding, solution architecture,
> design, SRE, PM/BA, and brainstorming. Terminal-native. Provider-agnostic. MIT licensed.

[Hero diagram: Mermaid showing the 4 layers — Memory / Skills / Router / Tools]

## What Makes Lyra Different

[3-column visual comparison]
| Lyra | Single-Provider Harnesses | Multi-Provider Harnesses |
| Voice mode flagship | Text-only | Text-only |
| Provider-agnostic memory | Provider-locked | Provider-agnostic |
| Self-evolving skills | Static prompts | Static skills |
| Memory-augmented routing | Single model | Cost-routing only |

## Quick Start
[3 commands max]

## Architecture
[Master Mermaid diagram showing all major subsystems]

## Capabilities
### 🎙️ Voice Mode (Flagship)
[Brief + link to docs/voice-mode.md]

### 🧠 Breakthrough Memory
[Brief + link to memory-architecture.md]

### 🎯 Skills System (Self-Evolving)
[Brief + link to docs/skills.md]

### 🧭 Intelligent Router
[Brief + link to docs/router.md]

### 👥 Multi-Agent Swarm
[Brief + link to docs/swarm.md]

### 🔬 Deep Research
[Brief + link to docs/deep-research.md]

## Inspirations

> Lyra synthesizes ideas from 280+ sources. See [findings.md](./lyra-upgrade/findings.md) for full attribution.

Notable influences:
- Anthropic Claude Code (skills system, hooks)
- ICLR 2026 MemAgent Workshop (memory architecture)
- Moshi / Pipecat / LiveKit (voice mode)
- Darwin Gödel Machine (self-evolving skills)
- AutoScientists (research swarm)
- ...

## Documentation

- [Quick Start](./docs/quickstart.md)
- [Architecture](./docs/architecture.md)
- [Memory Architecture](./lyra-upgrade/memory-architecture.md)
- [Voice Mode](./lyra-upgrade/voice-mode.md)
- [Test Plan](./lyra-upgrade/test-plan.md)
- [Roadmap](./lyra-upgrade/MASTER-PLAN.md)

## Contributing

[Link to CONTRIBUTING.md]

## License

MIT
```

---

## Visual Asset Catalog (to create)

### Master Mermaid Diagrams (one per major subsystem)

1. **Lyra Master Architecture** (4-layer model)
   ```
   Memory ← Router ← Skills ← Tools
   ```

2. **Voice Mode Pipeline** (already exists in voice-mode.md)
   ```
   Mic → VAD → STT → Router → LLM → TTS → Speaker
   ```

3. **Memory Architecture** (already exists in memory-architecture.md)
   ```
   STM → LTM (Episodic/Semantic) → Archive
   ```

4. **Skills Lifecycle**
   ```
   Discover → Load → Execute → Learn → Evolve
   ```

5. **Multi-Agent Swarm**
   ```
   Coordinator → [Parallel Agents] → Adversarial Critique → Convergence
   ```

6. **Tool Composition Graph**
   ```
   [Tools] ← Capability Negotiation ← User Intent
   ```

7. **Provider Abstraction Layer**
   ```
   Lyra Core → Provider Interface → {Claude, DeepSeek, Qwen, GPT, Local}
   ```

8. **Hook Lifecycle**
   ```
   PreTool → Tool → PostTool → Stop
   ```

### Charts to Add

1. **Cost Reduction by Workstream** (bar chart)
   - Memory-augmented router: 52%
   - Skills graph: 30%
   - Tool capability: 25%
   - Voice mode on-device: 95%

2. **Latency by Component** (stacked bar)
   - VAD: 1ms
   - STT: 100ms
   - LLM: 200-500ms
   - TTS: 50ms

3. **Workstream Maturity Matrix** (heat map)
   - Workstream × (Research, Plan, Brainstorm, Implementation)

4. **Source Coverage by Section** (donut chart)
   - §3.1: 38 sources
   - §3.4: 22 sources
   - §3.5: 63 sources
   - etc.

### Data Models (Mermaid classDiagram)

1. **Memory Schemas** (already in memory-architecture.md)
2. **Skill Manifest** (SKILL.md frontmatter + body)
3. **Tool Definition** (capability requirements)
4. **Profile Schema** (multi-tenancy)
5. **Hook Configuration**

---

## Per-Workstream Doc Pages (`docs/<workstream>.md`)

For each §4/§5 workstream, create a builder-friendly doc that:
1. **Hooks the reader** in 2 sentences
2. **Shows visual** (Mermaid) of how it works
3. **Explains breakthrough** (what's unique vs existing tools)
4. **Cites sources** (links to papers/repos)
5. **Quick-starts** with example code
6. **Links to plan** in lyra-upgrade/plans/

Template:
```markdown
# [Capability Name]

> [Hook: 2 sentences explaining why this matters]

## How It Works
[Mermaid diagram]

## The Breakthrough
[1-2 paragraphs on what's unique]

## Inspirations
- [Paper Name](link) — [what we took]
- [Repo Name](link) — [what we adapted]

## Quick Start
[Code example]

## Configuration
[Settings options]

## Learn More
- [Detailed plan](../lyra-upgrade/plans/NN-name.md)
- [Brainstorm](../lyra-upgrade/brainstorm/NN-name.md)
```

---

## Source Attribution Pattern

Every novel technique in Lyra docs must cite inspiration:

```markdown
**Memory-Augmented Router** (52% cost reduction)
> Combining [Cost-Sensitive Store Routing](https://openreview.net/pdf?id=iGRGjdhl9r) (ICLR 2026)
> with [Knowledge Access Beats Model Size](https://arxiv.org/pdf/2603.23013) (2026) and Lyra's
> §4.5 router design. See [memory-architecture.md](./memory-architecture.md) for full design.
```

This makes Lyra **traceable** — any builder can dig into the source to understand the inspiration.

---

## Migration Path

### Phase 1: Audit (week 1)
- Scan all existing docs for outdated content
- Identify docs that describe novel techniques without attribution
- List docs that need Mermaid diagrams

### Phase 2: README (week 2)
- Rewrite top-level README using structure above
- Add hero Mermaid diagram
- Link to all major docs

### Phase 3: Per-Workstream Docs (weeks 3-4)
- Create `docs/voice-mode.md`, `docs/memory.md`, `docs/skills.md`, etc.
- One doc per major capability
- Mermaid + sources + quick-start for each

### Phase 4: Package READMEs (week 5)
- Update each `packages/lyra-*/README.md`
- Add Mermaid showing package's role in system

### Phase 5: Polish (week 6)
- Cross-link all docs
- Add navigation breadcrumbs
- Verify all source attributions

---

## Tooling

### Mermaid Rendering
- All docs use GitHub-native Mermaid (renders inline)
- For complex diagrams, also export PNG to `docs/diagrams/`
- Color palette: consistent across all diagrams

### Source Attribution Linter
- Custom script `scripts/check-attribution.js`
- Scans for capability claims without citations
- Reports unsourced novel techniques
- Run in CI on doc changes

### Doc Testing
- All code examples in docs are tested via doc-testing framework
- Outdated examples fail CI

---

## Success Criteria

✅ **Visual** — Every capability page has ≥1 Mermaid diagram
✅ **Sourced** — Every novel technique cites ≥1 paper/repo
✅ **Scannable** — Reader can grok any page in <60s
✅ **Builder-attractive** — Quick-start example in <10 lines
✅ **Linked** — No orphan docs; all reachable from README

---

## What This Plan Does NOT Do

- ❌ Modify any Lyra source code
- ❌ Modify any existing user-facing docs (yet — that's the implementation pass)
- ❌ Generate the actual documentation

This is a **plan describing what to write**, per master prompt §6 + §9 requirement. Implementation is a separate future task.

---

## References

- Master Prompt §6: Documentation Deliverable
- Master Prompt §9: Final Reminder — Documentation
- `lyra-upgrade/MASTER-PLAN.md` — Overall roadmap
- `lyra-upgrade/findings.md` — 140+ research rows for source attribution
- All `lyra-upgrade/plans/NN-*.md` — Per-workstream details to summarize
