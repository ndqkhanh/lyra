# AI Slop Cleaner Report — Lyra Codebase

> Run 2, 2026-06-03 | Focused scan on harness-core and structure

## Classification

### 1. Duplication — Research Repos in Source Tree (CRITICAL)

**Finding:** Multiple large cloned reference repos under `packages/lyra-cli/.omc/research/repos/elite/` including full copies of hermes-agent (18,714-line run.py, 15,116-line cli.py), spaCy, and graphify. These are research artifacts, not Lyra source code. They bloat the source tree by ~5MB+ and appear in code searches.

**Recommended fix:** Add `.omc/research/repos/` to `.gitignore`. Move research clones to `~/.lyra/research/repos/` or a dedicated research directory outside the monorepo.

### 2. Bloat — Oversized File (HIGH)

**Finding:** `packages/lyra-cli/src/lyra_cli/interactive/session.py` at 10,931 lines. The coding standard says files should be <800 lines. This single file is 13× over the limit.

**Recommended fix:** Split into focused modules: `session_core.py` (state management), `session_display.py` (rendering), `session_input.py` (key handling), `session_commands.py` (command dispatch). Target: each <800 lines.

### 3. Needless Abstraction — `__init__.py` Re-exports (MEDIUM)

**Finding:** Many packages have non-empty `__init__.py` files that re-export internal symbols. This creates hidden coupling — changing an internal module breaks the re-export contract. Pattern: `from .internal_module import *`.

**Recommended fix:** Audit `__init__.py` files for `import *` patterns. Prefer explicit re-exports or let consumers import from internal modules directly.

### 4. Duplicate Function Names (LOW)

**Finding:** `verify` (12 occurrences), `to_dict` (11), `generate` (6), `create` (6) across harness-core. Most are legitimate polymorphism (different classes implementing the same interface). No copy-paste detected.

**Recommended fix:** No action needed — these are interface implementations, not duplication.

### 5. Venv in Monorepo (LOW)

**Finding:** Multiple `.venv/` directories in packages (e.g., `packages/lyra-research/.venv/`). These should be at monorepo root or gitignored per-package.

**Recommended fix:** Ensure `.venv/` is in root `.gitignore`.

## Verification Results (Run 3)

| Pass | Status | Evidence |
|------|--------|----------|
| 1: Research repos | ✅ Already applied | `.omc/` and `docs/research/repos/` already in root `.gitignore`. `git status` shows clean tree. |
| 2: Session split | ⏳ Deferred to implementation | Requires regression tests first; 10,931-line file needs careful extraction |
| 3: Venv cleanup | ✅ Verified | `.venv/` already gitignored (root gitignore pattern), `git status` shows clean |
| 4: Import audit | ⏳ Deferred to implementation | Analysis-only; no wildcard imports found in harness-core `__init__.py` files |

## Conclusion

Passes 1 and 3 already applied. Passes 2 and 4 deferred to implementation phase (per research-only scope). The most impactful remaining cleanup — splitting `session.py` — will be done as part of the §4.1 UI/UX workstream when the fleet view TUI is hardened.

## Cleanup Plan (Updated)

| Pass | Description | Files Affected | Risk |
|------|-------------|---------------|------|
| 1: Research repos | Gitignore `.omc/research/repos/` | `.gitignore` | Low — research artifacts, not source |
| 2: Session split | Split `session.py` into 4+ modules | `session.py` → 4 files | Medium — behavior must be preserved |
| 3: Venv cleanup | Gitignore `.venv/` per-package | `.gitignore` | Low — build artifacts |
| 4: Import audit | Audit `__init__.py` for wildcard imports | Multiple `__init__.py` | Low — explicit re-exports only |

## Verification

- After pass 2: Run existing test suite on `lyra-cli`. All tests must pass.
- After pass 1: Verify `git status` no longer shows research repos as untracked.
- After pass 3: Verify `git status` shows clean tree.

## Remaining Risks

- Pass 2 (session split): The 10,931-line session.py likely has complex interdependencies. Splitting may expose hidden coupling. Regression tests ESSENTIAL before proceeding.
- Research repos may be referenced by import paths — verify no Lyra code imports from `.omc/research/repos/`.
