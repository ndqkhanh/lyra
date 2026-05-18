# Lyra Cleanup & Reorganization Plan

**Goal:** Clean up messy file structure and update all documentation to match current Lyra (946 tests, 5 plans complete)

---

## Current Problems

### 1. Too Many Root-Level Files (80+ markdown files)
- Multiple completion reports (PHASE_1_COMPLETE.md, PHASE_2_COMPLETE.md, etc.)
- Session summaries scattered everywhere
- Outdated plan files
- Test output files in root

### 2. Duplicate Documentation
- `docs/` and `site/` have overlapping content
- Multiple README files
- Duplicate architecture docs

### 3. Outdated Content
- References to incomplete features
- Old test results
- Superseded plans
- Legacy implementation reports

### 4. Poor Organization
- No clear structure
- Files not grouped by purpose
- Hard to find current documentation

---

## Cleanup Strategy

### Phase 1: Archive Obsolete Files (Move to archive/)

**Create archive structure:**
```
archive/
├── completion-reports/     # All PHASE_X_COMPLETE.md files
├── session-summaries/      # All SESSION_SUMMARY_*.md files
├── old-plans/             # Superseded plan files
├── test-outputs/          # test_output/ and test_output_deepseek/
└── legacy-docs/           # Outdated documentation
```

**Files to archive:**
- All `PHASE_*_COMPLETE.md` files (12 files)
- All `SESSION_SUMMARY_*.md` files (5 files)
- All `*_ULTRA_PLAN.md` files (10+ files)
- All `*_IMPLEMENTATION_*.md` files (15+ files)
- All `*_VERIFICATION_*.md` files (5 files)
- `test_output/` and `test_output_deepseek/` directories
- Duplicate completion reports

### Phase 2: Consolidate Documentation

**New docs/ structure:**
```
docs/
├── README.md                    # Main documentation index
├── getting-started/
│   ├── installation.md
│   ├── quick-start.md
│   └── first-session.md
├── architecture/
│   ├── overview.md              # System overview
│   ├── diagrams.md              # All architecture diagrams
│   ├── context-optimization.md
│   ├── process-transparency.md
│   ├── deep-research.md
│   ├── self-evolution.md
│   └── cli-migration.md
├── guides/
│   ├── configuration.md
│   ├── mcp-integration.md
│   ├── skills.md
│   ├── memory-system.md
│   └── hooks.md
├── reference/
│   ├── commands.md
│   ├── tools.md
│   ├── env-vars.md
│   └── api.md
├── development/
│   ├── contributing.md
│   ├── testing.md
│   ├── building.md
│   └── releasing.md
└── research/
    ├── papers.md
    ├── benchmarks.md
    └── comparisons.md
```

**Remove:**
- `site/` directory (duplicate of docs/)
- Outdated docs in `docs/research/`
- Legacy implementation guides

### Phase 3: Update Core Documentation

**Files to update:**
1. **README.md** - Main project README
   - Current status (946 tests, 5 plans complete)
   - Quick start guide
   - Link to full documentation

2. **ARCHITECTURE_DIAGRAMS.md** - Already updated ✅

3. **CONTRIBUTING.md** - Update with current workflow

4. **CHANGELOG.md** - Add recent changes

5. **Package READMEs** - Update each package README:
   - `packages/lyra-cli/README.md`
   - `packages/lyra-core/README.md`
   - `packages/lyra-research/README.md`
   - `packages/lyra-evolution/README.md`
   - `packages/lyra-memory/README.md`
   - `packages/lyra-skills/README.md`
   - `packages/lyra-mcp/README.md`
   - `packages/lyra-evals/README.md`

### Phase 4: Clean Up Root Directory

**Keep in root (essential files only):**
```
/
├── .github/
├── .omc/
├── docs/
├── packages/
├── tests/
├── scripts/
├── examples/
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── pyproject.toml
└── uv.lock
```

**Move to archive/:**
- All completion reports
- All session summaries
- All ultra plans
- All implementation reports
- All verification reports
- Test output directories

### Phase 5: Update .gitignore

Add to `.gitignore`:
```
# Test outputs
test_output/
test_output_*/

# Session data
.lyra/
.omc/state/
.frg/

# Build artifacts
*.pyc
__pycache__/
.pytest_cache/
.ruff_cache/
.coverage

# Virtual environments
.venv/
venv/

# IDE
.vscode/
.idea/

# OS
.DS_Store
```

---

## Implementation Steps

### Step 1: Create Archive Structure
```bash
mkdir -p archive/{completion-reports,session-summaries,old-plans,test-outputs,legacy-docs}
```

### Step 2: Move Obsolete Files
```bash
# Move completion reports
mv PHASE_*_COMPLETE.md archive/completion-reports/
mv *_IMPLEMENTATION_*.md archive/completion-reports/
mv *_VERIFICATION_*.md archive/completion-reports/

# Move session summaries
mv SESSION_SUMMARY_*.md archive/session-summaries/
mv LYRA_SESSION_*.md archive/session-summaries/

# Move old plans
mv *_ULTRA_PLAN.md archive/old-plans/
mv LYRA_*_PLAN.md archive/old-plans/

# Move test outputs
mv test_output/ archive/test-outputs/
mv test_output_deepseek/ archive/test-outputs/
```

### Step 3: Remove Duplicate Directories
```bash
# Remove site/ (duplicate of docs/)
rm -rf site/

# Remove builder-specs/ (obsolete)
rm -rf builder-specs/

# Remove ui-specs/ (obsolete)
rm -rf ui-specs/
```

### Step 4: Update Documentation
- Update README.md with current status
- Update CONTRIBUTING.md
- Update CHANGELOG.md
- Update all package READMEs
- Consolidate docs/ structure

### Step 5: Update .gitignore
- Add test output patterns
- Add session data patterns
- Add build artifacts

---

## Expected Results

### Before Cleanup
- **200+ markdown files** in root and subdirectories
- **Duplicate docs/** and **site/** directories
- **Confusing structure** with no clear organization
- **Outdated content** everywhere

### After Cleanup
- **~15 essential files** in root
- **Single docs/** directory with clear structure
- **All obsolete files** archived
- **Updated documentation** matching current Lyra
- **Clean, professional structure**

---

## Files to Keep (Essential)

### Root Directory
- README.md (updated)
- CONTRIBUTING.md (updated)
- CHANGELOG.md (updated)
- LICENSE
- .gitignore (updated)
- .pre-commit-config.yaml
- pyproject.toml
- uv.lock

### Documentation
- docs/ (reorganized and updated)
- packages/*/README.md (updated)

### Code
- packages/ (all packages)
- tests/ (all tests)
- scripts/ (utility scripts)
- examples/ (example projects)

---

## Timeline

1. **Create archive structure** - 5 minutes
2. **Move obsolete files** - 10 minutes
3. **Remove duplicates** - 5 minutes
4. **Update documentation** - 30 minutes
5. **Update .gitignore** - 5 minutes
6. **Commit and push** - 5 minutes

**Total:** ~1 hour

---

## Success Criteria

- ✅ Root directory has <20 files
- ✅ All obsolete files archived
- ✅ No duplicate directories
- ✅ Documentation matches current Lyra
- ✅ Clear, professional structure
- ✅ Easy to navigate
- ✅ Updated .gitignore

---

**Ready to execute?** This will make Lyra much cleaner and more professional! 🚀
