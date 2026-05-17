# Legacy Code Cleanup Checklist

**Version**: 1.0.0  
**Created**: 2026-05-17  
**Status**: Ready for Execution  
**Total Lines to Remove**: ~2,000 lines  
**Total Files to Remove**: 6 files + 1 directory  

---

## Overview

This checklist identifies all legacy UI code that should be removed after tui_v2 becomes the default TUI. The cleanup is organized by risk level and dependency order.

---

## Phase 1: Safe Immediate Cleanup (Zero Risk)

### ✅ Empty Directories

#### Item 1.1: Remove Empty ui/ Directory
**Path**: `packages/lyra-cli/src/lyra_cli/ui/`  
**Size**: 0 bytes (empty)  
**Risk**: None  
**Dependencies**: None  
**Used By**: Nothing  

**Command**:
```bash
rm -rf packages/lyra-cli/src/lyra_cli/ui/
```

**Verification**:
```bash
# Should return "No such file or directory"
ls packages/lyra-cli/src/lyra_cli/ui/
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

## Phase 2: Documentation & Warnings (Low Risk)

### ✅ Deprecation Warnings

#### Item 2.1: Add Deprecation Warning to Legacy TUI
**Path**: `packages/lyra-cli/src/lyra_cli/cli/tui.py`  
**Lines**: 1-10 (docstring)  
**Risk**: Low  
**Impact**: User-facing warning  

**Change**:
```python
"""
DEPRECATED: Legacy prompt_toolkit TUI (v0.x.0)
==============================================

This TUI implementation is deprecated and will be removed in v1.0.0.

Use the new Textual-based TUI instead:
  - Default: lyra
  - Explicit: lyra tui
  - Legacy: lyra --legacy-tui

Migration Guide: /docs/tui-migration.md
New TUI Docs: /projects/lyra/ui-specs/

Reason for deprecation:
- Not aligned with Claude Code parity spec
- Difficult to extend and maintain
- Replaced by modern Textual-based implementation
"""
```

**Verification**:
```bash
# Should show deprecation warning
lyra --legacy-tui
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 2.2: Create Legacy Code Inventory Document
**Path**: `packages/lyra-cli/LEGACY_CODE_INVENTORY.md`  
**Risk**: None  
**Purpose**: Track what will be removed  

**Content**:
```markdown
# Legacy Code Inventory

Files scheduled for removal in v1.0.0:

1. lyra_cli/cli/tui.py (1,221 lines)
2. lyra_cli/cli/input.py (11,735 bytes)
3. lyra_cli/cli/banner.py (6,278 bytes)
4. lyra_cli/cli/spinner.py (3,434 bytes)
5. lyra_cli/cli/agent_integration.py (TBD - check usage)
6. lyra_cli/ui/ (empty directory)

Total: ~2,000 lines
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

## Phase 3: Refactor Shared Code (Medium Risk)

### ✅ Extract Shared Modules from cli/

These modules are used by both legacy TUI and new interactive/session.py. They must be moved to a shared location before legacy TUI removal.

#### Item 3.1: Move skill_manager.py
**Current Path**: `packages/lyra-cli/src/lyra_cli/cli/skill_manager.py`  
**New Path**: `packages/lyra-cli/src/lyra_cli/core/skill_manager.py`  
**Size**: ~8,500 bytes  
**Risk**: Medium  
**Used By**:
- `lyra_cli/cli/tui.py` (line 613)
- `lyra_cli/interactive/session.py` (lines 595, 726, 9394+)

**Steps**:
1. Create `lyra_cli/core/` directory
2. Move file: `git mv lyra_cli/cli/skill_manager.py lyra_cli/core/`
3. Update imports in `cli/tui.py`:
   ```python
   # OLD
   from .skill_manager import SkillManager
   
   # NEW
   from lyra_cli.core.skill_manager import SkillManager
   ```
4. Update imports in `interactive/session.py`:
   ```python
   # OLD
   from lyra_cli.cli.skill_manager import SkillManager
   
   # NEW
   from lyra_cli.core.skill_manager import SkillManager
   ```

**Verification**:
```bash
# All tests should pass
pytest packages/lyra-cli/tests/ -v

# No imports from old location
grep -r "from.*cli.skill_manager" packages/lyra-cli/src/
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 3.2: Move memory_manager.py
**Current Path**: `packages/lyra-cli/src/lyra_cli/cli/memory_manager.py`  
**New Path**: `packages/lyra-cli/src/lyra_cli/core/memory_manager.py`  
**Size**: ~6,200 bytes  
**Risk**: Medium  
**Used By**:
- `lyra_cli/cli/tui.py` (lines 509, 603)
- `lyra_cli/interactive/session.py` (multiple locations)

**Steps**: Same as 3.1

**Verification**: Same as 3.1

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 3.3: Audit agent_integration.py
**Path**: `packages/lyra-cli/src/lyra_cli/cli/agent_integration.py`  
**Size**: ~4,800 bytes  
**Risk**: Medium  
**Used By**: Only `lyra_cli/cli/tui.py` (line 878)

**Action**: Determine if this is legacy-specific or should be refactored

**Steps**:
1. Search for all imports:
   ```bash
   grep -r "TUIAgentIntegration" packages/lyra-cli/
   ```
2. If only used by `cli/tui.py`: Mark for removal with legacy TUI
3. If used elsewhere: Refactor to `lyra_cli/core/agent_integration.py`

**Decision**: ⬜ Remove with legacy TUI | ⬜ Refactor to core/

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

## Phase 4: Legacy TUI Removal (High Risk)

**⚠️ ONLY execute after 2-3 months of tui_v2 as default with no critical bugs**

### ✅ Remove Legacy TUI Files

#### Item 4.1: Remove cli/tui.py
**Path**: `packages/lyra-cli/src/lyra_cli/cli/tui.py`  
**Size**: 1,221 lines  
**Risk**: High  
**Dependencies**: Items 4.2-4.5 must be removed together  

**Command**:
```bash
git rm packages/lyra-cli/src/lyra_cli/cli/tui.py
```

**Verification**:
```bash
# Should fail (file removed)
python -c "from lyra_cli.cli.tui import launch_tui"

# No imports reference this file
grep -r "from.*cli.tui import" packages/lyra-cli/src/
grep -r "cli.tui.launch_tui" packages/lyra-cli/src/
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 4.2: Remove cli/input.py
**Path**: `packages/lyra-cli/src/lyra_cli/cli/input.py`  
**Size**: 11,735 bytes  
**Risk**: High  
**Used By**: Only `cli/tui.py` (lines 44-46)  

**Command**:
```bash
git rm packages/lyra-cli/src/lyra_cli/cli/input.py
```

**Verification**:
```bash
# No imports reference this file
grep -r "from.*cli.input import" packages/lyra-cli/src/
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 4.3: Remove cli/banner.py
**Path**: `packages/lyra-cli/src/lyra_cli/cli/banner.py`  
**Size**: 6,278 bytes  
**Risk**: High  
**Used By**: Only `cli/tui.py` (line 44)  

**Command**:
```bash
git rm packages/lyra-cli/src/lyra_cli/cli/banner.py
```

**Verification**:
```bash
# No imports reference this file
grep -r "from.*cli.banner import" packages/lyra-cli/src/
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 4.4: Remove cli/spinner.py
**Path**: `packages/lyra-cli/src/lyra_cli/cli/spinner.py`  
**Size**: 3,434 bytes  
**Risk**: High  
**Used By**: Only `cli/tui.py` (line 46)  

**Command**:
```bash
git rm packages/lyra-cli/src/lyra_cli/cli/spinner.py
```

**Verification**:
```bash
# No imports reference this file
grep -r "from.*cli.spinner import" packages/lyra-cli/src/
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 4.5: Remove cli/agent_integration.py (if unused)
**Path**: `packages/lyra-cli/src/lyra_cli/cli/agent_integration.py`  
**Size**: ~4,800 bytes  
**Risk**: High  
**Condition**: Only if Item 3.3 determined it's legacy-specific  

**Command**:
```bash
git rm packages/lyra-cli/src/lyra_cli/cli/agent_integration.py
```

**Verification**:
```bash
# No imports reference this file
grep -r "TUIAgentIntegration" packages/lyra-cli/src/
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

#### Item 4.6: Remove Legacy Entry Point from __main__.py
**Path**: `packages/lyra-cli/src/lyra_cli/__main__.py`  
**Lines**: Remove `--legacy-tui` flag and all legacy code paths  
**Risk**: High  

**Changes**:
```python
# REMOVE these lines:
if use_legacy_tui:
    from .cli.tui import launch_tui
    raise typer.Exit(launch_tui(...))

# REMOVE this parameter:
legacy_tui: bool = typer.Option(
    False,
    "--legacy-tui",
    help="Use deprecated prompt_toolkit TUI",
),
```

**Verification**:
```bash
# Should fail (flag removed)
lyra --legacy-tui

# Should succeed (only tui_v2 remains)
lyra
```

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete

---

## Phase 5: Consolidate Duplicate Code (Low Priority)

### ✅ Slash Command Registry

#### Item 5.1: Consolidate Command Definitions
**Issue**: Slash commands defined in both legacy TUI and tui_v2  
**Risk**: Low  
**Priority**: P2 (optional)  

**Current State**:
- Legacy: `cli/tui.py` lines 398-480 (inline dispatch)
- tui_v2: `tui_v2/commands/` (modular)

**Recommendation**: After legacy removal, this is automatically resolved

**Status**: ⬜ Not Started | ⬜ In Progress | ⬜ Complete | ✅ N/A (resolved by Phase 4)

---

## Summary Statistics

### Files to Remove
- **Total Files**: 6
- **Total Lines**: ~2,000
- **Total Size**: ~30 KB

### Breakdown by Phase
| Phase | Files | Lines | Risk |
|-------|-------|-------|------|
| Phase 1 | 1 | 0 | None |
| Phase 2 | 0 | 0 | Low |
| Phase 3 | 0 | 0 | Medium |
| Phase 4 | 5-6 | ~2,000 | High |
| Phase 5 | 0 | 0 | Low |

### Risk Assessment
- **Zero Risk**: 1 item (empty directory)
- **Low Risk**: 2 items (documentation)
- **Medium Risk**: 3 items (refactoring)
- **High Risk**: 6 items (removal)

---

## Pre-Removal Checklist

Before executing Phase 4, verify:

- [ ] tui_v2 has been default for 2-3 months
- [ ] Zero critical bugs reported in tui_v2
- [ ] All 24 functional requirements implemented in tui_v2
- [ ] 100% test coverage for tui_v2
- [ ] User acceptance testing complete
- [ ] Migration guide published
- [ ] Deprecation warnings in place for 2+ months
- [ ] No active users on `--legacy-tui` flag (check telemetry)
- [ ] Backup branch created: `git branch legacy-tui-backup`

---

## Rollback Plan

If issues are discovered after removal:

1. **Immediate**: Revert the removal commit
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Within 24h**: Restore `--legacy-tui` flag as default
3. **Within 48h**: Fix tui_v2 issues or extend legacy support
4. **Post-mortem**: Document what went wrong

---

## Verification Commands

### After Phase 1
```bash
# Empty directory removed
! test -d packages/lyra-cli/src/lyra_cli/ui/
```

### After Phase 3
```bash
# Shared modules moved
test -f packages/lyra-cli/src/lyra_cli/core/skill_manager.py
test -f packages/lyra-cli/src/lyra_cli/core/memory_manager.py

# Old locations removed
! test -f packages/lyra-cli/src/lyra_cli/cli/skill_manager.py
! test -f packages/lyra-cli/src/lyra_cli/cli/memory_manager.py

# All tests pass
pytest packages/lyra-cli/tests/ -v
```

### After Phase 4
```bash
# Legacy files removed
! test -f packages/lyra-cli/src/lyra_cli/cli/tui.py
! test -f packages/lyra-cli/src/lyra_cli/cli/input.py
! test -f packages/lyra-cli/src/lyra_cli/cli/banner.py
! test -f packages/lyra-cli/src/lyra_cli/cli/spinner.py

# No imports reference legacy code
! grep -r "from.*cli.tui import" packages/lyra-cli/src/
! grep -r "cli.tui.launch_tui" packages/lyra-cli/src/

# All tests pass
pytest packages/lyra-cli/tests/ -v

# Git diff shows ~2,000 lines removed
git diff --stat HEAD~1 | grep "deletions"
```

---

## Progress Tracking

### Overall Progress
- **Phase 1**: ⬜⬜⬜⬜⬜ 0/1 (0%)
- **Phase 2**: ⬜⬜⬜⬜⬜ 0/2 (0%)
- **Phase 3**: ⬜⬜⬜⬜⬜ 0/3 (0%)
- **Phase 4**: ⬜⬜⬜⬜⬜⬜ 0/6 (0%)
- **Phase 5**: ⬜ 0/1 (0%)

**Total**: 0/13 items complete (0%)

### Timeline
- **Phase 1**: Week 1, Day 1 (15 minutes)
- **Phase 2**: Week 1, Day 1 (1 hour)
- **Phase 3**: Week 7, Days 1-2 (8 hours)
- **Phase 4**: Week 7, Days 3-5 (after 2-3 months of tui_v2 as default)
- **Phase 5**: Optional (resolved by Phase 4)

---

## Sign-off

### Phase 1 Approval
- [ ] Reviewed by: _______________
- [ ] Approved by: _______________
- [ ] Date: _______________

### Phase 3 Approval (Refactoring)
- [ ] Reviewed by: _______________
- [ ] Approved by: _______________
- [ ] Date: _______________

### Phase 4 Approval (Removal)
- [ ] All pre-removal checklist items verified
- [ ] Reviewed by: _______________
- [ ] Approved by: _______________
- [ ] Date: _______________

---

**End of Cleanup Checklist**
