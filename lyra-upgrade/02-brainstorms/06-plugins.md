# Brainstorm: Plugins System (§4.7)

## Sources Reviewed

### Claude Code Plugins
- Plugin architecture with lifecycle hooks
- Plugin discovery and loading
- Plugin configuration and settings
- Plugin permissions and sandboxing

### Comparable Harnesses
- Kilo Marketplace: curated plugins/MCP servers/modes
- OpenClaw: modular TypeScript skill system
- Goose: MCP-native plugin architecture

### Skills Systems (§3.7)
- SkillNet: npm-like package manager for AI skills
- oh-my-claude: plugin ecosystem
- claude-skills: 330+ skills across domains

---

## Cross-Source Breakthrough Ideas

### Idea 1: Self-Evolving Plugin Ecosystem
**Sources Combined**:
- SkillNet (auto-generates skill packages from repos/PDFs/trajectories)
- Darwin Gödel Machine (self-rewriting coding agent)
- MemGrad (textual gradients from feedback)
- Claude Code plugins (lifecycle hooks)

**Mechanism**:
Plugins that **learn and evolve from usage**:
- Track plugin invocations, success/failure rates, user feedback
- Generate textual gradients from feedback batches
- Auto-update plugin prompts/logic based on gradients
- Create new plugin variants via trajectory analysis
- Maintain plugin genealogy (parent → evolved children)

**Plugin evolution cycle**:
1. User uses plugin, provides feedback (explicit or implicit via success/failure)
2. System batches feedback across multiple uses
3. MemGrad-style textual gradient extraction
4. Plugin prompt/logic updated
5. New version tested in shadow mode
6. If better, promote to active; if not, keep as variant

**Why It Beats Individual Sources**:
- SkillNet generates skills but doesn't evolve them; this adds **continuous improvement**
- Darwin self-rewrites code; this applies it to **plugin ecosystem**
- MemGrad works on agents; this applies it to **plugins**
- Claude Code plugins are static; this makes them **adaptive**

**Impact × Effort**: 5×5 = BREAKTHROUGH impact, HIGH effort

**Failure Modes**:
- Evolution could break working plugins
- Feedback quality determines evolution quality
- Version management complexity
- Risk of plugins drifting from original intent

---

### Idea 2: Cross-Plugin Composition Graph
**Sources Combined**:
- SkillNet (skill graph with similarity/composition/dependency)
- Pipecat (pipeline-as-agent composition)
- Dynamic Workflows (code-driven workflow specs)
- Claude Code plugins (plugin system)

**Mechanism**:
Plugins as **composable graph nodes** with automatic composition discovery:
- Each plugin declares inputs/outputs as typed schemas
- System builds composition graph showing which plugins can chain
- Auto-suggest plugin sequences for complex tasks
- Visual graph editor for creating plugin workflows
- Save workflows as new meta-plugins

**Example**:
```
User: "Research topic X, summarize findings, create presentation"

System detects composition:
[web-search plugin] → [summarizer plugin] → [presentation-builder plugin]

Auto-chains them with intermediate data passing
```

**Why It Beats Individual Sources**:
- SkillNet has skill graph but no auto-composition; this adds **automatic chaining**
- Pipecat composes pipelines; this composes **plugins**
- Dynamic Workflows are code-driven; this is **graph-driven**
- Claude Code plugins are isolated; this enables **composition**

**Impact × Effort**: 5×4 = BREAKTHROUGH impact, HIGH effort

**Failure Modes**:
- Type system complexity
- Graph could become too dense
- Auto-composition might chain incorrectly
- Debugging composed workflows is hard

---

### Idea 3: Plugin Capability Negotiation
**Sources Combined**:
- Multi-provider router (§4.5 - DeepSeek vs Anthropic behavior)
- Claude Code plugins (plugin permissions)
- Progent (programmable least-privilege tool control)
- Skills system (provider-agnostic requirements)

**Mechanism**:
Plugins **negotiate capabilities** with the runtime based on available providers:
- Plugin declares required capabilities (tool-use, vision, long-context, etc.)
- Runtime checks active provider's capabilities
- Plugin adapts behavior or gracefully degrades
- User gets clear message about what's available vs unavailable

**Example**:
```
Plugin: "code-reviewer"
Required: tool-use (file reading), long-context (>100K)
Optional: vision (screenshot analysis)

On DeepSeek:
✓ tool-use available
✓ long-context available (128K)
✗ vision unavailable → skip screenshot analysis

On Anthropic:
✓ tool-use available
✓ long-context available (200K)
✓ vision available → full functionality
```

**Why It Beats Individual Sources**:
- Multi-provider router handles model selection; this handles **plugin adaptation**
- Claude Code plugins assume capabilities; this makes them **provider-aware**
- Progent controls permissions; this controls **capabilities**
- Skills system is provider-agnostic; this makes **plugins** provider-agnostic

**Impact × Effort**: 4×3 = HIGH impact, MEDIUM effort

**Failure Modes**:
- Capability detection might be inaccurate
- Degraded behavior might confuse users
- Plugin authors need to handle multiple code paths
- Capability matrix maintenance burden

---

## Parked Ideas

### Idea 4: Plugin Marketplace with Reputation System
Community-driven plugin marketplace with ratings, reviews, download counts, and reputation scores for plugin authors.

**Why Parked**: Requires infrastructure (hosting, auth, payments); focus on core plugin system first.

### Idea 5: Plugin Sandboxing with WASM
Run untrusted plugins in WebAssembly sandbox for security isolation.

**Why Parked**: WASM adds complexity; start with permission-based sandboxing.

### Idea 6: Plugin Hot-Reloading
Reload plugins without restarting Lyra session.

**Why Parked**: Nice-to-have but not critical for initial plugin system.
