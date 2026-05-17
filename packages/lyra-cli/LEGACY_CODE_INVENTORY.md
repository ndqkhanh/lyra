# Legacy Code Inventory

**Created**: 2026-05-17  
**Purpose**: Track files scheduled for removal in v1.0.0  
**Status**: Phase 0 Complete - Awaiting Phase 5 Execution  

---

## Files Scheduled for Removal

These files will be removed after tui_v2 has been the default for 2-3 months with no critical bugs.

### 1. Legacy TUI Core
**File**: `packages/lyra-cli/src/lyra_cli/cli/tui.py`  
**Size**: 1,221 lines  
**Status**: ⚠️ DEPRECATED (v0.x.0)  
**Removal**: v1.0.0  
**Used By**: `__main__.py` (legacy entry point)  
**Dependencies**: input.py, banner.py, spinner.py, agent_integration.py  

### 2. Legacy Input System
**File**: `packages/lyra-cli/src/lyra_cli/cli/input.py`  
**Size**: 11,735 bytes  
**Status**: Active (used by tui.py only)  
**Removal**: v1.0.0  
**Used By**: `cli/tui.py` only  

### 3. Legacy Banner Renderer
**File**: `packages/lyra-cli/src/lyra_cli/cli/banner.py`  
**Size**: 6,278 bytes  
**Status**: Active (used by tui.py only)  
**Removal**: v1.0.0  
**Used By**: `cli/tui.py` only  

### 4. Legacy Spinner
**File**: `packages/lyra-cli/src/lyra_cli/cli/spinner.py`  
**Size**: 3,434 bytes  
**Status**: Active (used by tui.py only)  
**Removal**: v1.0.0  
**Used By**: `cli/tui.py` only  

### 5. Legacy Agent Integration
**File**: `packages/lyra-cli/src/lyra_cli/cli/agent_integration.py`  
**Size**: ~4,800 bytes  
**Status**: Active (used by tui.py only)  
**Removal**: v1.0.0 (pending verification)  
**Used By**: `cli/tui.py` only  
**Note**: Verify not used elsewhere before removal  

### 6. Empty UI Directory
**File**: `packages/lyra-cli/src/lyra_cli/ui/`  
**Size**: 0 bytes (empty)  
**Status**: ✅ REMOVED (2026-05-17)  
**Removal**: Complete  

---

## Summary Statistics

| Category | Count | Total Size |
|----------|-------|------------|
| Files to Remove | 5 | ~2,000 lines |
| Files Removed | 1 | 0 bytes |
| Remaining | 5 | ~2,000 lines |

---

## Removal Checklist

### Pre-Removal Requirements
- [ ] tui_v2 has been default for 2-3 months
- [ ] Zero critical bugs in tui_v2
- [ ] All 24 functional requirements implemented
- [ ] User acceptance testing complete
- [ ] Migration guide published
- [ ] Backup branch created

### Removal Order
1. ✅ Empty ui/ directory (Phase 0)
2. ⬜ Refactor shared modules (Phase 5)
3. ⬜ Remove tui.py (Phase 5)
4. ⬜ Remove input.py (Phase 5)
5. ⬜ Remove banner.py (Phase 5)
6. ⬜ Remove spinner.py (Phase 5)
7. ⬜ Remove agent_integration.py (Phase 5, if unused)
8. ⬜ Remove legacy entry point from __main__.py (Phase 5)

---

## Impact Analysis

### Code Reduction
- **Before**: 3 implementations, ~8,000 lines
- **After**: 1 implementation, ~7,600 lines
- **Net Change**: -400 lines, -2 implementations

### Maintenance Burden
- **Before**: Maintain 3 UIs (legacy, harness-tui, tui_v2)
- **After**: Maintain 1 UI (tui_v2 extending harness-tui)
- **Reduction**: 66% fewer implementations

---

## Notes

- All files marked for removal have deprecation warnings
- Legacy TUI remains functional until v1.0.0
- Users can access via `lyra --legacy-tui` flag
- See LEGACY_CODE_CLEANUP_CHECKLIST.md for detailed removal steps

---

**Last Updated**: 2026-05-17  
**Next Review**: After Phase 1 completion  
