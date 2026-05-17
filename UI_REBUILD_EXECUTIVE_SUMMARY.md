# Lyra UI Rebuild: Executive Summary

**Version**: 1.0.0  
**Created**: 2026-05-17  
**Status**: Ready for Execution  
**Owner**: Khanh  

---

## TL;DR

**Problem**: Lyra has 3 competing UI implementations (legacy TUI, harness-tui, tui_v2), creating maintenance burden and incomplete spec compliance.

**Solution**: Complete tui_v2 (4 missing widgets), make it default, remove 2,000 lines of legacy code.

**Timeline**: 6-8 weeks

**Impact**: 100% spec compliance, -1,550 net lines of code, single unified UI

---

## Documents Created

This research produced 4 comprehensive planning documents:

### 1. **LYRA_UI_REBUILD_ULTRA_PLAN.md** (Main Plan)
- 7 phases over 6-8 weeks
- 70+ tasks with priorities and estimates
- Risk mitigation strategies
- Success metrics and rollback plan
- **Start here** for project execution

### 2. **LEGACY_CODE_CLEANUP_CHECKLIST.md** (Cleanup Guide)
- 13 items across 5 phases
- File-by-file removal instructions
- Verification commands
- Pre-removal checklist
- **Use this** for Phase 5 (legacy removal)

### 3. **UI_ARCHITECTURE_DIAGRAM.md** (Technical Reference)
- Current vs. target state diagrams
- Component hierarchy
- Data flow architecture
- Dependency graphs
- **Reference this** for understanding system design

### 4. **QUICK_START_IMPLEMENTATION.md** (Developer Guide)
- Step-by-step widget implementation
- Code templates with examples
- Testing strategies
- Common issues & solutions
- **Use this** for Phase 1 (implementing widgets)

---

## Current State Analysis

### Three Competing Implementations

| Implementation | Status | Lines | Spec Compliance | Maintainability |
|----------------|--------|-------|-----------------|-----------------|
| **Legacy TUI** (prompt_toolkit) | ✅ Complete | 1,221 | ❌ 0% | ❌ Hard to extend |
| **harness-tui** (shared lib) | ✅ Production | 4,946 | ⚠️ 83% (generic) | ✅ Modular |
| **tui_v2** (Lyra-specific) | ⚠️ Partial | 2,207 | ⚠️ 83% (20/24 FRs) | ✅ Extensible |

### Missing Features (Gap Analysis)

From the architect agent's analysis:

| Feature | Legacy | harness-tui | tui_v2 | Priority |
|---------|--------|-------------|--------|----------|
| Welcome Card (FR-001) | ❌ | ❌ | ❌ | **P0** |
| Compaction Banner (FR-010) | ❌ | ❌ | ❌ | **P0** |
| Background Switcher (FR-012) | ❌ | ❌ | ❌ | **P0** |
| To-Do Panel (FR-015) | ❌ | ❌ | ❌ | **P0** |

**All other 20 requirements are implemented.**

### Legacy Code to Remove

From the code reviewer agent's analysis:

```
Files to Remove (Phase 5, after 2-3 months):
├── cli/tui.py                    1,221 lines
├── cli/input.py                 11,735 bytes
├── cli/banner.py                 6,278 bytes
├── cli/spinner.py                3,434 bytes
├── cli/agent_integration.py     ~4,800 bytes
└── ui/ (empty directory)              0 bytes
────────────────────────────────────────────
Total:                           ~2,000 lines
```

---

## Recommended Approach

### Phase 0-1: Foundation (Weeks 1-3)
**Goal**: Implement 4 missing widgets

**Tasks**:
1. Remove empty `ui/` directory (5 min)
2. Add deprecation warnings to legacy TUI (30 min)
3. Implement WelcomeCard widget (8 hours)
4. Implement CompactionBanner widget (6 hours)
5. Implement BackgroundSwitcher modal (6 hours)
6. Implement TodoPanel widget (4 hours)

**Deliverable**: 24/24 functional requirements implemented

---

### Phase 2-3: Transition (Weeks 4-5)
**Goal**: Make tui_v2 the default

**Tasks**:
1. Wire new widgets into app (8 hours)
2. Connect to event bus (4 hours)
3. Reverse default entry point logic (1 hour)
4. Add `--legacy-tui` fallback flag (30 min)
5. Update documentation (2 hours)

**Deliverable**: tui_v2 is default, legacy is opt-in

---

### Phase 4: Verification (Week 6)
**Goal**: Ensure quality and performance

**Tasks**:
1. Complete test suite (8 hours)
2. Constitution compliance audit (4 hours)
3. Performance benchmarking (4 hours)
4. User acceptance testing (ongoing)

**Deliverable**: 100% test coverage, all metrics met

---

### Phase 5: Cleanup (Week 7+, after 2-3 months)
**Goal**: Remove legacy code

**⚠️ ONLY after 2-3 months of tui_v2 as default with no critical bugs**

**Tasks**:
1. Refactor shared modules to `core/` (4 hours)
2. Remove legacy TUI files (1 hour)
3. Remove legacy entry point (30 min)
4. Verify all tests pass (1 hour)

**Deliverable**: -2,000 lines of code removed

---

## Key Decisions

### Decision 1: Complete tui_v2 First (Not Deprecate Immediately)

**Rationale**:
- Ensures no feature regression
- Allows gradual migration
- Reduces risk of breaking existing workflows

**Trade-off**: Maintains two codebases temporarily

---

### Decision 2: Keep harness-tui Generic

**Rationale**:
- Used by 12+ projects
- Stable, well-tested foundation
- Lyra-specific features belong in tui_v2

**Trade-off**: Some duplication between harness-tui and tui_v2

---

### Decision 3: 2-3 Month Deprecation Window

**Rationale**:
- Gives users time to adapt
- Allows discovery of edge cases
- Reduces rollback risk

**Trade-off**: Longer maintenance of legacy code

---

## Success Metrics

### Quantitative
- ✅ 24/24 functional requirements (100%)
- ✅ 100% test coverage for new widgets
- ✅ 0 legacy code in production path (after Phase 5)
- ✅ ≥30 fps, <200 MB RSS
- ✅ <200 ms cancellation latency

### Qualitative
- ✅ New contributor can complete quickstart unaided
- ✅ Zero critical bugs in first 2 weeks
- ✅ Positive user feedback
- ✅ 7/7 constitution principles compliant

---

## Risk Assessment

### High-Risk Items

#### Risk 1: Breaking Changes for Existing Users
**Likelihood**: Medium  
**Impact**: High  
**Mitigation**:
- Keep `--legacy-tui` flag for 2-3 months
- Add deprecation warnings
- Provide migration guide

---

#### Risk 2: Performance Regression
**Likelihood**: Low  
**Impact**: High  
**Mitigation**:
- Benchmark before/after
- Profile with `py-spy` if issues found
- Add performance tests to CI

---

#### Risk 3: Incomplete Feature Parity
**Likelihood**: Low  
**Impact**: Medium  
**Mitigation**:
- Audit all legacy TUI commands
- Create feature parity checklist
- User acceptance testing before removal

---

## Resource Requirements

### Developer Time
- **Phase 0-1**: 24 hours (1 developer, 3 days)
- **Phase 2-3**: 16 hours (1 developer, 2 days)
- **Phase 4**: 16 hours (1 developer, 2 days)
- **Phase 5**: 8 hours (1 developer, 1 day)
- **Total**: 64 hours (8 developer-days)

### Infrastructure
- No additional infrastructure required
- Existing CI/CD pipeline sufficient
- Textual ≥0.86 already in dependencies

---

## Timeline

```
Week 1: Audit & Cleanup + Start Widgets
├── Day 1: Remove empty dirs, add warnings
├── Day 2-3: Implement WelcomeCard
└── Day 4-5: Implement CompactionBanner

Week 2-3: Complete Widgets
├── Day 1-2: Implement BackgroundSwitcher
├── Day 3: Implement TodoPanel
└── Day 4-5: Integration & wiring

Week 4: Make Default
├── Day 1-2: Wire widgets into app
├── Day 3: Reverse entry point logic
└── Day 4-5: Documentation & testing

Week 5-6: Testing & Verification
├── Week 5: Complete test suite
└── Week 6: Performance benchmarking + UAT

Week 7+ (after 2-3 months): Legacy Removal
├── Day 1: Refactor shared modules
├── Day 2: Remove legacy files
└── Day 3: Final verification
```

---

## Next Steps

### Immediate (This Week)
1. **Review this plan** with team
2. **Create GitHub project** with all tasks
3. **Assign owner** for Phase 0-1
4. **Start Phase 0**: Remove empty directory, add warnings

### Short-Term (Next 2 Weeks)
1. **Implement 4 missing widgets** (Phase 1)
2. **Write tests** for each widget
3. **Weekly check-ins** to track progress

### Medium-Term (Weeks 3-6)
1. **Wire widgets** into app (Phase 2)
2. **Make tui_v2 default** (Phase 3)
3. **Complete testing** (Phase 4)
4. **User acceptance testing**

### Long-Term (After 2-3 Months)
1. **Monitor for critical bugs**
2. **Collect user feedback**
3. **Remove legacy code** (Phase 5)
4. **Tag v1.0.0 release**

---

## Key Contacts

### Stakeholders
- **Owner**: Khanh (primary author, decision maker)
- **Reviewers**: TBD (code review for Phase 1-4)
- **Testers**: TBD (user acceptance testing)

### Resources
- **Spec**: `/projects/lyra/ui-specs/`
- **Code**: `/projects/lyra/packages/lyra-cli/src/lyra_cli/tui_v2/`
- **Tests**: `/projects/lyra/packages/lyra-cli/tests/test_tui_v2_*.py`
- **Docs**: `/projects/lyra/docs/`

---

## Appendix: Agent Research Summary

### Architect Agent Findings
- **Current State**: 3 competing implementations
- **Gaps**: 4 missing widgets (FR-001, FR-010, FR-012, FR-015)
- **Recommendation**: Complete tui_v2, make default, deprecate legacy
- **Estimated Effort**: 4-6 weeks to full spec compliance

### Code Reviewer Agent Findings
- **Legacy Code**: ~2,000 lines to remove
- **High-Priority Issues**: 3 (legacy TUI default, empty directory, duplicate modules)
- **Medium-Priority Issues**: 8 (shared modules, inconsistent entry points)
- **Recommendation**: REQUEST CHANGES — 3 HIGH severity issues must be addressed

### Key Insights
1. **tui_v2 is 83% complete** — only 4 widgets missing
2. **Legacy TUI is fully functional** — no feature gaps, just not spec-aligned
3. **harness-tui is production-ready** — solid foundation, used by 12+ projects
4. **Clean separation possible** — no shared code between legacy and tui_v2

---

## Conclusion

The path forward is clear and achievable:

1. **Complete tui_v2** (4 widgets, 24 hours)
2. **Make it default** (reverse logic, 2 hours)
3. **Test thoroughly** (16 hours)
4. **Remove legacy** (after 2-3 months, 8 hours)

**Total effort**: 64 hours (8 developer-days) over 6-8 weeks.

**Result**: Single, spec-compliant, production-ready TUI with -1,550 net lines of code.

---

**Ready to execute. Start with Phase 0, Task T001: Remove empty ui/ directory.**

---

**End of Executive Summary**
