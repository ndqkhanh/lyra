# Lyra UI Architecture Pivot: Ink + React (TypeScript)

**Date:** 2026-05-17  
**Status:** APPROVED - Architectural Decision  
**Previous Approach:** Rich + prompt_toolkit (Python)  
**New Approach:** Ink + React (TypeScript)

---

## Decision Summary

After Phase 0 performance validation, we're pivoting Lyra's UI from Python (Rich/Textual) to **TypeScript with Ink + React** to match Claude Code's proven architecture.

## Performance Test Results

| Framework | Language | CPU Usage | Frame Rate | Verdict |
|-----------|----------|-----------|------------|---------|
| Rich Live() | Python | 2.1% ✅ | 28.8 FPS ❌ | Borderline fail |
| Textual | Python | 100.4% ❌ | 30.3 FPS ✅ | Critical fail |
| **Ink + React** | **TypeScript** | **Unknown** | **Unknown** | **To be tested** |

## Why Ink + React?

### 1. **Claude Code Uses It**
- Claude Code is built on Ink + React (TypeScript)
- Proven to handle:
  - Streaming responses at high token rates
  - Real-time tool call visualizations
  - Background task management (Ctrl+B)
  - Complex interactive UI (Vim mode, slash commands)
  - Hierarchical expandable views

### 2. **Performance Characteristics**
- React's virtual DOM efficiently batches updates
- Ink's reconciler optimizes terminal rendering
- Yoga flexbox layout engine (pure TypeScript port)
- Designed specifically for streaming LLM use cases

### 3. **Ecosystem Alignment**
- Node.js/TypeScript is standard for modern CLI tools
- Rich npm ecosystem for terminal UIs
- Better tooling (TypeScript, ESLint, Prettier)
- Easier integration with web-based tools

### 4. **Python Limitations Exposed**
- Rich: Good CPU but borderline FPS (28.8 vs 30)
- Textual: Catastrophic CPU usage (100%)
- Python's GIL may limit concurrent rendering performance
- No proven Python TUI framework for high-frequency updates

## Architectural Impact

### What Changes

**Before (Python):**
```
lyra-cli (Python)
  ├── Rich (rendering)
  ├── prompt_toolkit (interactivity)
  └── EventBus (Python)
```

**After (TypeScript):**
```
lyra-cli (TypeScript)
  ├── Ink (React renderer for terminal)
  ├── React (component model)
  ├── Yoga (flexbox layout)
  └── EventBus (TypeScript port or IPC bridge)
```

### What Stays the Same

- **lyra-core** (Python) - Agent orchestration, LLM calls, observability
- **EventBus architecture** - Events still flow from Python core to UI
- **Process transparency goals** - All UI patterns from UI.md still apply
- **Feature flags** - Same incremental rollout strategy

### Integration Strategy

**Option A: Full TypeScript Rewrite**
- Rewrite lyra-cli in TypeScript with Ink
- Python core communicates via IPC (stdin/stdout or sockets)
- Clean separation: Python = backend, TypeScript = frontend

**Option B: Hybrid Approach**
- Keep Python CLI as orchestrator
- Spawn TypeScript Ink process for UI rendering
- Python → TypeScript via JSON-RPC or message passing

**Recommendation:** Option A (Full TypeScript Rewrite)
- Cleaner architecture
- Matches Claude Code's design
- Better long-term maintainability
- Easier to hire TypeScript developers than Python TUI experts

## Migration Path

### Phase 0: Ink Performance Validation (2 days)
Create Ink + React stress test with same 3 scenarios:
1. Token streaming at 50 tokens/sec
2. 5 concurrent progress bars
3. 100-node tree with expansion

**Gate criteria:** CPU < 10%, FPS ≥ 30

### Phase 1: TypeScript Foundation (1 week)
- Set up TypeScript project structure
- Implement EventBus client (connects to Python core)
- Create basic Ink components (Spinner, TokenCounter, StatusBar)
- IPC bridge between Python core and TypeScript UI

### Phase 2-5: Port UI Components (3 weeks)
- Phase 2: Token counter + spinner (Ink components)
- Phase 3: Task checklist widget
- Phase 4: Background task counter
- Phase 5: Agent panel with navigation

### Phase 6-9: Quality & Testing (2 weeks)
- Phase 6: Error handling
- Phase 7: Performance optimization
- Phase 8: Accessibility (keyboard nav, screen readers)
- Phase 9: E2E testing

**Total Timeline:** 6 weeks (vs 5 weeks for Python approach)

## Technical Decisions

### 1. IPC Protocol: JSON-RPC over stdin/stdout

**Python Core → TypeScript UI:**
```typescript
interface UIEvent {
  type: "token_received" | "task_added" | "agent_started" | ...;
  payload: any;
  timestamp: number;
}
```

**TypeScript UI → Python Core:**
```typescript
interface UICommand {
  type: "interrupt" | "background" | "expand_node" | ...;
  payload: any;
}
```

### 2. Component Architecture

```typescript
// Main App
<App>
  <Header>
    <Spinner verb={verb} />
    <TokenCounter tokens={tokens} />
  </Header>
  
  <Body>
    <TaskChecklist tasks={tasks} />
    <AgentPanel agents={agents} />
  </Body>
  
  <Footer>
    <BackgroundCounter count={bgTasks} />
    <StatusBar />
  </Footer>
</App>
```

### 3. State Management: Zustand or Jotai

Use lightweight React state management:
- Zustand for global UI state
- React hooks for local component state
- EventBus events update Zustand store

### 4. Testing Strategy

- **Unit tests:** Jest + React Testing Library
- **Integration tests:** Test IPC bridge with mock Python core
- **E2E tests:** Spawn real Python core + TypeScript UI
- **Performance tests:** Same stress test scenarios

## Risks & Mitigations

### Risk 1: Ink Performance Unknown
**Mitigation:** Phase 0 stress test validates before committing

### Risk 2: IPC Complexity
**Mitigation:** Use proven JSON-RPC libraries (vscode-jsonrpc)

### Risk 3: Team TypeScript Experience
**Mitigation:** TypeScript is more common than Python TUI expertise

### Risk 4: Python-TypeScript Integration
**Mitigation:** stdin/stdout IPC is simple and battle-tested

## Success Criteria

### Phase 0 Gate (Ink Stress Test)
- [ ] CPU usage < 10%
- [ ] Frame rate ≥ 30 FPS
- [ ] No visible flicker
- [ ] All 3 scenarios pass

### Final Acceptance
- [ ] All UI patterns from UI.md implemented
- [ ] Performance benchmarks met (CPU < 5%, 30 FPS)
- [ ] Keyboard navigation works
- [ ] Background task management functional
- [ ] Agent panel with live updates
- [ ] Token/time tracking accurate

## Rollback Plan

If Ink stress test fails Phase 0:
1. Document why Ink failed
2. Escalate to user for decision
3. Options:
   - Proceed with Rich despite borderline FPS
   - Investigate alternative frameworks (blessed, blessed-contrib)
   - Simplify UI requirements

## Next Steps

1. ✅ Document architectural decision (this file)
2. ⏳ Create Ink + React stress test (Phase 0)
3. ⏳ Run stress test and validate performance
4. ⏳ If pass: proceed with TypeScript migration
5. ⏳ If fail: escalate to user

---

## Appendix: Claude Code Architecture Reference

Claude Code's TUI stack:
- **Ink** - React renderer for terminal
- **React** - Component model and reconciler
- **Yoga** - Flexbox layout engine (TypeScript port)
- **ANSI/CSI parser** - Full terminal control sequence handling
- **Custom reconciler** - Optimized for streaming LLM output

Key features we want to replicate:
- Hierarchical expandable views (Ctrl+O)
- Background task management (Ctrl+B)
- Live status indicators (⏺ ◯ ✳ ✶ ✻ ✽)
- Token/time tracking per operation
- Smooth streaming without flicker
- Keyboard-first navigation

---

**Decision Status:** APPROVED  
**Next Action:** Create Ink stress test (Phase 0)
