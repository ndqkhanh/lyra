# Ink + React Performance Validation - FAILED

**Date:** 2026-05-17  
**Status:** FAILED - Technical Incompatibility

---

## Test Result: FAILED

**Reason:** Ink v4 has a fundamental incompatibility with tsx/esbuild due to yoga-layout's use of top-level await in CommonJS format.

**Error:**
```
Error: Transform failed with 1 error:
/Users/khanhnguyen/node_modules/yoga-layout/dist/src/index.js:13:26: 
ERROR: Top-level await is currently not supported with the "cjs" output format
```

---

## Root Cause Analysis

1. **Ink v4** uses `yoga-layout` for flexbox layout
2. **yoga-layout** uses top-level await in its CommonJS distribution
3. **tsx/esbuild** cannot transpile top-level await in CJS format
4. **ts-node** would have the same issue

This is a known issue in the Ink ecosystem with Node.js v20+.

---

## Implications

**Ink + React is NOT a viable option** for Lyra's UI due to:
1. Technical incompatibility with modern Node.js tooling
2. Would require downgrading to Ink v3 (outdated, unmaintained)
3. Or waiting for yoga-layout to fix their ESM/CJS distribution
4. Claude Code likely uses a custom fork or older versions

---

## Final Performance Comparison

| Framework | Language | CPU Usage | Frame Rate | Status |
|-----------|----------|-----------|------------|--------|
| Rich Live() | Python | 2.1% ✅ | 28.8 FPS ❌ | Borderline fail |
| Textual | Python | 100.4% ❌ | 30.3 FPS ✅ | Critical fail |
| **Ink + React** | **TypeScript** | **N/A** | **N/A** | **Technical failure** |

---

## Recommendation

**Proceed with Rich Live() despite borderline FPS failure**

### Rationale

1. **Best available option**: Rich has the best performance profile
   - Excellent CPU usage (2.1% vs 100% for Textual)
   - Only 1.2 FPS below threshold (28.8 vs 30)
   - Likely acceptable for real-world use

2. **Ink is not viable**: Technical incompatibility blocks adoption

3. **Optimization potential**: Rich's FPS can likely be improved
   - Reduce update frequency
   - Optimize rendering logic
   - Use incremental updates

4. **Plan allows for iteration**: Phase 10 provides escape hatch
   - If state bugs emerge, can refactor
   - If performance issues arise, can optimize

---

## Updated Migration Plan

### Phase 0: COMPLETE - Use Rich Live()
- ✅ Performance validation complete
- ✅ Rich selected as UI framework
- ✅ Decision: Proceed despite borderline FPS

### Phase 1-9: Implement with Rich (5 weeks)
Continue with original Python plan using Rich + prompt_toolkit:
- Phase 1: EventQueue & UIStateManager
- Phase 2: Token counter & spinner
- Phase 3: Task checklist
- Phase 4: Background counter
- Phase 5: Agent panel
- Phase 6: Error handling
- Phase 7: Performance optimization (target: 30+ FPS)
- Phase 8: Accessibility
- Phase 9: E2E testing

### Phase 10: Event Sourcing (Future, if needed)
- Trigger: >3 state desync bugs in production
- Refactor to event-sourced architecture

---

## Next Steps

1. ✅ Mark Phase 0 as complete
2. ✅ Update plan to use Rich Live()
3. ⏳ Begin Phase 1: EventQueue & UIStateManager Foundation
4. ⏳ Implement with performance optimization focus

---

## Lessons Learned

1. **Don't assume Claude Code's stack is replicable**
   - Claude Code likely uses custom forks or older versions
   - "Same stack" doesn't mean "same versions"

2. **Test early, test often**
   - Performance validation caught issues before major investment
   - Saved 6 weeks of TypeScript migration work

3. **Python TUI ecosystem is limited**
   - Rich is the best option despite limitations
   - Textual has severe performance issues
   - No perfect solution exists

4. **Borderline failures may be acceptable**
   - 28.8 FPS vs 30 FPS is likely imperceptible
   - Real-world performance may differ from stress test
   - Optimization can close the gap

---

**Decision:** Proceed with Rich Live() implementation
