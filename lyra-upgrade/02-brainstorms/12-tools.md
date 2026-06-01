# Brainstorm: Tools System (§4.6)

## Sources Reviewed

### Claude Code Tools Reference (§3.1)
- 40+ built-in tools: Agent, AskUserQuestion, Bash, Cron*, Edit, Glob, Grep, LSP, Monitor, NotebookEdit, PowerShell, PushNotification, Read, ScheduleWakeup, SendMessage, Skill, Task*, Team*, ToolSearch, WebFetch, WebSearch, Workflow, Write, EnterPlanMode/ExitPlanMode, EnterWorktree/ExitWorktree
- Permission specifier patterns: `Bash(npm run *)`, `Read(~/secrets/**)`, `Edit(/src/**)`, `Skill(deploy *)`, `Agent(Explore)`, `WebFetch(domain:example.com)`
- Read-before-edit guard, file-locking, output size limits, timeout configuration
- Background execution (`run_in_background: true`)
- Tool search for deferred-loading of 100+ MCP tools

### Hermes Agent Tools (§3.2)
- 5 core: bash, file_read, file_write, search, web_fetch
- Plus Memory Bank (persistent context tool)
- Minimal/lean approach vs Claude's expansive set

### Awesome Harness Engineering (§3.3)
- "Tools as first-class citizens" pattern
- Tool composition graphs
- Capability discovery via JSON schemas

### MCP Servers (§3.19)
- 100+ community servers cataloged
- Code-execution-with-MCP pattern: 98.7% token reduction by executing tool calls as code
- Tool capability negotiation

### Other Harnesses (§3.2, §3.11)
- Aider: repomap + git-native tools
- Goose: MCP-native, Recipes (saved workflows-as-tools)
- Crush: minimal core + extensible
- OpenHands: SOTA SWE-bench via comprehensive tool set
- Cline: parallel agents share tool pool

### Tool-Use Research (§3.5)
- HASP: Skills as executable Program Functions that actively intervene
- Tool capability matching (which model can use which tool effectively)
- Tool-call failure → recovery patterns

---

## Cross-Source Breakthrough Ideas

### Idea 1: **Tool Capability Negotiation Layer**

**Sources Combined**:
- Claude Code tools-reference (40+ tools with capability specifiers)
- MCP capability negotiation
- HASP executable Program Functions (active intervention)
- Model router (§4.5 — provider capability map)

**Mechanism**:
Every tool declares its **capability requirements** (provider features needed: tool-calling format, JSON mode, context window, vision, streaming). Tools also declare **fallback strategies** when capabilities are missing.

```yaml
tool: Monitor
capability_requirements:
  - background_execution: required
  - streaming_output: preferred
  - process_spawning: required
  - cost: low
fallback:
  - if: !background_execution
    use: synchronous_polling_with_5s_interval
  - if: !streaming_output
    use: buffered_batch_output_every_30s
```

**Tool Selection Flow**:
```
User intent → Capability requirements → Match against provider's capability matrix
            → Filter to compatible tools → Cost-rank → Select primary + fallback
```

**Why It Beats Individual Sources**:
- Claude Code: Static tools with no negotiation
- MCP: Negotiation per-server but not per-tool
- HASP: Active intervention but not capability-aware
- **Fusion**: Tools that gracefully degrade across providers + intervention safety

**Impact × Effort**: 5×4 = BREAKTHROUGH

**Failure Modes**:
- Capability matrix drift (providers change features)
- Fallback strategies could mask real failures
- Performance overhead from negotiation

---

### Idea 2: **Unified Tool Composition Graph with Auto-Discovery**

**Sources Combined**:
- Claude Code tools-reference (tool composition via Workflow)
- MCP tool search (deferred loading from 100+ servers)
- SkillNet skill graph (§3.7 — composition relationships)
- Awesome Harness Engineering tool composition patterns

**Mechanism**:
Build a **runtime tool graph** that:
1. **Auto-discovers** tools from all sources (built-in, MCP, plugin, skill-exposed)
2. **Maps relationships**: depends-on, replaces, complements, conflicts-with
3. **Auto-composes** tool sequences for complex tasks
4. **Caches** common sequences as "macro-tools"

Example macro-tool:
```yaml
macro: "deploy-feature"
composition:
  sequence:
    - WebSearch(query="latest deployment docs")
    - Read(file="package.json")
    - Bash(command="npm test", required=true)
    - Edit(file="VERSION", increment="patch")
    - Bash(command="npm run build")
    - Bash(command="npm publish")
    - PushNotification(message="Deploy complete")
  fallback_on_failure:
    - skill: rollback-deployment
```

**Auto-Discovery Mechanism**:
- Scan `~/.lyra/tools/`, `./.lyra/tools/`, MCP server manifests
- Build graph in `.lyra/tool-graph.json` (versioned)
- Update on plugin install/remove
- LLM uses graph to choose composition paths

**Why It Beats Individual Sources**:
- Claude Code Workflow: One-off compositions, not reusable
- MCP search: Discovery only, no composition
- SkillNet graph: Skills only, not tools
- **Fusion**: All tools (built-in/MCP/plugin/skill) → unified graph → automatic composition

**Impact × Effort**: 5×4 = BREAKTHROUGH

**Failure Modes**:
- Graph complexity could overwhelm the LLM
- Auto-composition could create unsafe sequences
- Cache invalidation when tools change

---

### Idea 3: **Tool Provenance & Replay**

**Sources Combined**:
- Claude Code background execution + Monitor tool
- Aider git-native automatic commits
- Goose Recipes (workflows-as-tools)
- HASP execution trace + reflection
- Memory architecture (§4.2 — episodic memory)

**Mechanism**:
Every tool execution records a **provenance record**: who called it, why, with what inputs, what outputs, side effects, and learned lessons. These records feed:
1. **Memory** — Episodic store of "what worked"
2. **Replay** — Re-run any past sequence with modifications
3. **Audit** — Full history for security review
4. **Learning** — Pattern detection across executions

```json
{
  "id": "exec-2026-05-31-abc123",
  "tool": "Bash",
  "input": "npm test",
  "output": "...",
  "exit_code": 0,
  "duration_ms": 8400,
  "called_by": "agent-test-runner",
  "called_for": "verify auth refactor",
  "session_id": "s-2026-05-31-001",
  "context_before": {"files_modified": ["src/auth.ts"], ...},
  "side_effects": ["wrote test-output.log"],
  "lessons": ["tests took >8s — consider parallelization"],
  "linked_artifacts": ["commit:abc123def"]
}
```

**Replay Use Cases**:
- "Re-run yesterday's deploy with the new env file"
- "Show me all Bash commands run by agent-X this session"
- "What sequence of tools led to this commit?"
- "Find similar past tool sequences and learn from outcomes"

**Why It Beats Individual Sources**:
- Claude Code: No provenance, just logs
- Aider: Git commits only, not tool-level
- Goose Recipes: Manual reuse, not auto-learning
- HASP: Execution trace only, no replay
- **Fusion**: Full tool-level provenance → memory + replay + audit + learning

**Impact × Effort**: 4×3 = HIGH

**Failure Modes**:
- Storage growth (need retention policy)
- Privacy concerns with sensitive command logging
- Replay across environment changes is hard

---

## Parked Ideas (Future Runs)

### Idea 4: **Tool Marketplace with Trust Scores**
Community-contributed tools with cryptographic signing, trust scores from usage data, and automated security review. Could integrate with §4.7 plugins.

### Idea 5: **Predictive Tool Suggestion**
Watch user typing patterns and suggest tool sequences before they're requested. Like GitHub Copilot but for tool orchestration.

### Idea 6: **Tool Cost Forecasting**
Before executing expensive tool sequences (LLM-heavy workflows), forecast token/compute cost and require approval if over budget.

---

## Promoted to Plan (B) Breakthrough Tier

**Primary**: Idea 2 (Unified Tool Composition Graph) — Highest impact, fundamentally new capability across all tool sources

**Secondary**: Idea 1 (Tool Capability Negotiation) — Critical for multi-provider Lyra requirement (§4.5)

These two fuse to create Lyra's flagship tool system advantage: **provider-agnostic tool composition with graceful degradation**.
