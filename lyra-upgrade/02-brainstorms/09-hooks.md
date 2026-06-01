# Brainstorm: Hooks & Automation (§4.10)

## Sources Reviewed

### Claude Code Hooks
- PreToolUse, PostToolUse, Stop hooks
- Hook configuration in settings.json
- Auto-accept permissions
- TodoWrite best practices

### Comparable Harnesses
- Kilo Code: --auto flag for full autonomy
- Dynamic Workflows: code-driven automation
- Goose: Recipes for recurring workflows

### Sound Effects via Hooks
- Warcraft peon notifications
- Hook-based audio playback

---

## Cross-Source Breakthrough Ideas

### Idea 1: Declarative Hook Composition Language
**Sources Combined**:
- Claude Code hooks (PreToolUse, PostToolUse, Stop)
- Dynamic Workflows (code-driven specs)
- NeMo Guardrails (Colang DSL for programmable rails)
- Progent (programmable least-privilege control)

**Mechanism**:
**DSL for composing hooks** without writing shell scripts:

```yaml
hooks:
  - name: auto-format-on-write
    trigger: PostToolUse
    when:
      tool: Write
      file_pattern: "*.{ts,js,py}"
    actions:
      - run: prettier --write {file}
        if: file.endsWith('.ts') || file.endsWith('.js')
      - run: black {file}
        if: file.endsWith('.py')
      - notify: "Formatted {file}"
    
  - name: auto-test-on-code-change
    trigger: PostToolUse
    when:
      tool: [Write, Edit]
      file_pattern: "src/**/*.ts"
    actions:
      - run: npm test -- {file}.test.ts
        async: true
      - if_fails:
          notify: "Tests failed for {file}"
          suggest: "/debug {file}"
    
  - name: cost-guard
    trigger: PreToolUse
    when:
      tool: Agent
      model: opus
    actions:
      - check: session.cost < 10.00
        else:
          block: true
          message: "Session cost limit reached ($10)"
          suggest: "Switch to sonnet or haiku"
```

**Features**:
- **Declarative**: No shell scripting required
- **Composable**: Combine multiple hooks
- **Conditional**: Run based on context
- **Async**: Background execution
- **Type-safe**: Validate at load time

**Why It Beats Individual Sources**:
- Claude Code hooks are shell scripts; this is **declarative**
- Dynamic Workflows are code-driven; this is **config-driven**
- NeMo Guardrails is for safety; this is for **automation**
- Progent controls tools; this **automates around tools**

**Impact × Effort**: 5×4 = BREAKTHROUGH impact, HIGH effort

**Failure Modes**:
- DSL complexity could rival shell scripts
- Limited expressiveness vs full programming
- Debugging declarative hooks is harder
- Performance overhead from interpretation

---

### Idea 2: Hook Marketplace with Community Recipes
**Sources Combined**:
- Claude Code hooks (hook system)
- Goose Recipes (recurring workflows)
- SkillNet (npm-like package manager)
- Kilo Marketplace (curated content)

**Mechanism**:
**Community-driven hook library** with discovery and installation:

```bash
# Search for hooks
lyra hooks search "auto-format"

# Install hook
lyra hooks install @community/auto-format-on-write

# List installed hooks
lyra hooks list

# Update hooks
lyra hooks update

# Publish your hook
lyra hooks publish my-custom-hook
```

**Hook packages**:
```
@community/auto-format-on-write
@community/auto-test-on-change
@community/cost-guard
@community/security-scan-on-commit
@community/voice-notifications
@community/slack-notifications
@community/git-auto-commit
```

**Hook composition**:
```yaml
# Install multiple related hooks as a bundle
lyra hooks install @bundles/tdd-workflow
# Includes: auto-test, auto-format, coverage-check, commit-guard
```

**Why It Beats Individual Sources**:
- Claude Code hooks are manual; this adds **discovery**
- Goose Recipes are built-in; this is **community-driven**
- SkillNet is for skills; this is for **hooks**
- Kilo Marketplace is centralized; this is **decentralized**

**Impact × Effort**: 4×4 = HIGH impact, HIGH effort

**Failure Modes**:
- Quality control for community hooks
- Security concerns with untrusted hooks
- Version compatibility issues
- Marketplace infrastructure costs

---

### Idea 3: Adaptive Hook Scheduling
**Sources Combined**:
- Claude Code hooks (fixed trigger points)
- CronCreate (scheduled tasks)
- Dynamic Workflows (state-driven execution)
- A-MAC (adaptive memory admission control)

**Mechanism**:
**Hooks that adapt their behavior** based on context and history:

**Frequency adaptation**:
```yaml
hook: auto-save-session
trigger: every 5 minutes
adaptive:
  - if: user.activity == "high"
    frequency: every 2 minutes
  - if: user.activity == "low"
    frequency: every 10 minutes
  - if: session.cost > $5
    frequency: every 1 minute  # Save more often when expensive
```

**Conditional execution**:
```yaml
hook: auto-test
trigger: PostToolUse(Write)
adaptive:
  - if: file.size < 100 lines
    run: immediately
  - if: file.size > 100 lines
    run: debounced(5 seconds)  # Wait for more edits
  - if: tests.last_run < 1 minute ago
    skip: true  # Don't run too frequently
```

**Learning from outcomes**:
```yaml
hook: auto-format
trigger: PostToolUse(Write)
adaptive:
  - track: format_success_rate
  - if: format_success_rate < 0.8
    disable: true
    notify: "Auto-format disabled due to low success rate"
```

**Why It Beats Individual Sources**:
- Claude Code hooks are static; this makes them **adaptive**
- CronCreate is time-based; this is **context-based**
- Dynamic Workflows adapt workflows; this adapts **hooks**
- A-MAC adapts memory; this adapts **automation**

**Impact × Effort**: 4×3 = HIGH impact, MEDIUM effort

**Failure Modes**:
- Adaptation logic could be wrong
- Tracking state adds complexity
- Debugging adaptive behavior is hard
- Performance overhead from condition checking

---

## Parked Ideas

### Idea 4: Visual Hook Debugger
Interactive debugger showing hook execution flow, timing, and outputs.

**Why Parked**: Nice-to-have but not critical for initial hook system.

### Idea 5: Hook Performance Profiler
Measure hook execution time and identify slow hooks.

**Why Parked**: Optimization concern; focus on functionality first.

### Idea 6: Hook Rollback
Undo the effects of a hook that ran incorrectly.

**Why Parked**: Complex to implement safely; many hooks aren't reversible.
