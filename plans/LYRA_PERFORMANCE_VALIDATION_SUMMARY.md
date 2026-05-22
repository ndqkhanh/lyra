# Lyra UI Performance Validation Summary

**Date:** 2026-05-17  
**Status:** Phase 0 - Performance Testing in Progress

---

## Test Results

### Test 1: Rich Live() (Python)
- **CPU Usage:** 2.1% avg, 5.2% max ✅ **PASS** (< 10% threshold)
- **Frame Rate:** 28.8 FPS ❌ **FAIL** (< 30 FPS threshold by 1.2 FPS)
- **Flicker:** Manual inspection required
- **Verdict:** **BORDERLINE FAIL** - Excellent CPU but slightly low FPS

### Test 2: Textual (Python)
- **CPU Usage:** 100.4% avg, 100.5% max ❌ **CRITICAL FAIL** (10x over threshold)
- **Frame Rate:** 30.3 FPS ✅ **PASS** (≥ 30 FPS threshold)
- **Flicker:** Manual inspection required
- **Verdict:** **CRITICAL FAIL** - Unacceptable CPU usage

### Test 3: Ink + React (TypeScript)
- **Status:** ⏳ **RUNNING** (60-second test in progress)
- **Expected completion:** ~1 minute
- **Gate criteria:** CPU < 10%, FPS ≥ 30

---

## Key Findings

### Python TUI Frameworks Are Inadequate

Both Python TUI frameworks failed the performance gate:

1. **Rich Live()**: Great CPU efficiency (2.1%) but can't maintain 30 FPS
   - Only 1.2 FPS below threshold (borderline)
   - Likely due to Python's GIL limiting concurrent rendering
   - Could potentially be optimized, but uncertain

2. **Textual**: Catastrophic CPU usage (100%)
   - Completely unacceptable for a UI framework
   - Would drain batteries and make system unresponsive
   - Likely due to excessive reactive updates and timer intervals

### Why Ink + React?

**Claude Code uses Ink + React**, not Python TUI frameworks:
- Ink is a React-based renderer for terminals (TypeScript/JavaScript)
- Proven to handle high-frequency streaming LLM output
- React's virtual DOM efficiently batches updates
- Yoga flexbox layout engine (pure TypeScript port)
- No Python GIL limitations

---

## Architectural Decision

**Pivot from Python to TypeScript with Ink + React**

### Rationale

1. **Performance**: Python TUI frameworks can't meet requirements
2. **Proven**: Claude Code successfully uses Ink + React
3. **Ecosystem**: Better tooling and npm package ecosystem
4. **Maintainability**: TypeScript is more common than Python TUI expertise

### Architecture

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
  └── IPC bridge to Python core
```

### Integration Strategy

- **Python core** (lyra-core): Agent orchestration, LLM calls, observability
- **TypeScript UI** (lyra-cli): Terminal rendering with Ink + React
- **IPC**: JSON-RPC over stdin/stdout for communication

---

## Migration Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 0 | 2 days | Performance validation (current) |
| Phase 1 | 1 week | TypeScript foundation + IPC bridge |
| Phase 2-5 | 3 weeks | Port UI components to Ink |
| Phase 6-9 | 2 weeks | Quality, testing, accessibility |
| **Total** | **6 weeks** | Full TypeScript migration |

---

## Next Steps

### If Ink Passes (CPU < 10%, FPS ≥ 30)
1. ✅ Approve Ink + React as UI framework
2. Begin Phase 1: TypeScript foundation
3. Implement IPC bridge (Python ↔ TypeScript)
4. Port UI components incrementally

### If Ink Fails
1. Analyze failure reasons
2. Escalate to user for decision
3. Options:
   - Optimize Ink implementation
   - Proceed with Rich despite borderline FPS
   - Explore alternative frameworks
   - Simplify UI requirements

---

## Risk Assessment

### Low Risk
- ✅ Ink is proven (Claude Code uses it)
- ✅ TypeScript ecosystem is mature
- ✅ IPC over stdin/stdout is battle-tested

### Medium Risk
- ⚠️ Team TypeScript experience (mitigated: TypeScript is common)
- ⚠️ Python-TypeScript integration complexity (mitigated: simple IPC)

### High Risk
- ❌ Ink performance unknown (testing now)

---

## Success Criteria

### Phase 0 Gate (Ink Stress Test)
- [ ] CPU usage < 10%
- [ ] Frame rate ≥ 30 FPS
- [ ] No visible flicker
- [ ] All 3 scenarios pass (tokens, progress bars, tree)

### Final Acceptance
- [ ] All UI patterns from UI.md implemented
- [ ] Performance benchmarks met (CPU < 5%, 30 FPS)
- [ ] Keyboard navigation works
- [ ] Background task management functional
- [ ] Agent panel with live updates
- [ ] Token/time tracking accurate

---

## References

- **Decision Document:** `.omc/plans/LYRA_INK_PIVOT_DECISION.md`
- **Original Plan:** `.omc/plans/LYRA_PROCESS_TRANSPARENCY_PLAN_REVISED.md`
- **UI Requirements:** `projects/lyra/UI.md`

---

**Status:** Awaiting Ink + React stress test results...
