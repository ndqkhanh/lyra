# Worktree Isolation -- Deep Dive

## 1. Executive Summary

Worktree isolation is Lyra's solution to the fundamental problem of parallel agent editing: concurrent file system writes from multiple independent LLM sessions will collide and corrupt each other's work. The mechanism is deceptively simple -- each agent session operates in its own git worktree, a separate working directory that shares a single `.git/` object store but maintains independent files, branches, and index state. This is the same isolation primitive that Claude Code uses for its background sessions and subagents, and Lyra replicates it faithfully while fixing several critical safety gaps.

The system is implemented across three layers. At the lowest level, `WorktreeManager` in `packages/lyra-core/src/lyra_core/subagent/worktree.py` provides the bare git worktree primitive: allocate a worktree on a named branch, clean it up on completion, and reconcile orphans on startup. Above it, `WorktreeIsolation` in `packages/lyra-orchestration/src/lyra_orchestration/worktree_isolate.py` adds the safety policy layer: non-destructive cleanup defaults, `.worktreeinclude` env-file propagation, base-branch policy (fresh versus head), and non-git VCS hook support. At the top, `FleetSupervisor` in `packages/lyra-orchestration/src/lyra_orchestration/fleet_supervisor.py` wires worktree lifecycle into the background session manager, giving every dispatched session its own isolation boundary automatically.

The breakthrough optimization is the COW (Copy-on-Write) isolation layer in `cow_isolation.py`, which replaces naive `shutil.copytree` with platform-native COW clones: APFS clones at 87ms on macOS, overlayfs at 42ms on Linux, and a hardlink fallback at 3.2s. This is what makes a fleet of 16+ concurrent agents practical on a single workstation -- without COW, each agent spawn costs 47 seconds of file copy time; with COW, it costs under 100 milliseconds.

The design delivers three properties that together define safe parallel editing: (1) true filesystem isolation -- agents see independent state and cannot race on the same files; (2) non-destructive defaults -- uncommitted work is never silently discarded; (3) instant dispatch -- COW makes creation fast enough that every subagent invocation can get its own worktree without measurable overhead.

---

## 2. The Isolation Problem

### 2.1 Why Parallel Sessions Need File Isolation

An LLM agent session is an interactive program that reads and writes files. When two agents work on the same repository simultaneously, they share a single working directory. The result is a classic race condition:

- Agent A reads `src/auth.py`, edits line 42, writes.
- Agent B reads `src/auth.py` (before A's write), edits line 87, writes.
- Agent A's changes are lost. No merge, no conflict detection, no warning.

This is not a theoretical problem. In production agent fleets running on Claude Code's background sessions and Lyra's parallel subagent dispatches, concurrent file editing is the norm, not the exception. The isolation mechanism must guarantee that each agent sees a private copy of the working tree, and that changes are reconciled through an explicit merge step.

The problem is compounded by three realities of LLM agent behavior. First, agents do not write atomically -- they read, reason, then write, and the gap between read and write is measured in seconds or minutes. Second, agents frequently touch the same files: configuration, shared libraries, test fixtures. Third, agents produce half-written state -- a patch applied partially, a file created and then abandoned -- that must not contaminate the main checkout.

### 2.2 Claude Code's Solution and Its Footguns

Claude Code solves the isolation problem with git worktrees. Every background session (started via `--bg`, `/bg`, or the agent-view TUI) automatically enters a git worktree under `.claude/worktrees/<session-id>/` before its first edit. This is the default behavior (`worktree.bgIsolation: "worktree"`), and users must explicitly opt out with `worktree.bgIsolation: "none"` to disable it.

The mechanism is correct at the architectural level. Git worktrees provide true filesystem isolation: each worktree has its own working directory, its own branch, its own index, and its own HEAD reference, while sharing the `.git/` object store and remote configuration. This is not an overlay, not a copy, not a FUSE filesystem -- it is a first-class git primitive that every tool understands.

However, Claude Code's on-removal behavior is a footgun. When a user removes a session (Ctrl+X twice in agent view, or choosing "remove" on a dirty worktree prompt), the cleanup is destructive:

- `git worktree remove --force` deletes the working directory.
- `git branch -D <branch>` deletes the session branch.
- Any uncommitted changes, untracked files, or unpushed commits are gone permanently. There is no trash, no recovery path, no undo.

The only mitigation is that Claude Code prompts before destroying dirty worktrees (clean ones are auto-removed without prompt). But the prompt is binary: keep or remove. Remove means data loss. There is no "stash first" option. This is documented behavior as of Claude Code v2.1.x, and it is the primary safety gap that Lyra's worktree isolation fixes.

A second footgun: environment files (`.env`, `.env.local`, credentials) are gitignored and therefore do not exist in fresh worktrees cloned from a clean base ref. A session launched into a new worktree will find itself in a working directory that appears to have no secrets -- the agent may fail to connect to APIs, write incorrect configurations, or waste time debugging missing environment variables. Claude Code addresses this with `.worktreeinclude`, a file at the project root that specifies which gitignored files to copy into new worktrees. Lyra replicates this mechanism exactly.

A third footgun: workspace trust. Claude Code refuses to create worktrees in a directory until the user has run `claude` there at least once and accepted the workspace trust dialog. This adds friction for first-time use and scripted automation. Lyra does not replicate the workspace trust gate, relying instead on the user's existing repository access controls.

### 2.3 Lyra's Approach: Non-Destructive by Default

Lyra's worktree isolation is designed around a single principle: **no silent data loss**. Every safety decision flows from this principle.

The default cleanup action is `STASH`, not `DISCARD`. When a dirty worktree is removed, Lyra does not delete it -- it stashes the uncommitted changes with a descriptive message, parks the branch as `parked/<worktree-name>`, and notifies the user with exact recovery instructions. The stash push uses `git stash push -u -m "auto-stash-before-worktree-removal-<timestamp>"`, which captures tracked modifications, staged changes, and untracked files.

The `DISCARD` action exists but requires explicit opt-in: the caller must pass both `action=CleanupAction.DISCARD` and `force=True`. No code path in Lyra defaults to discard. The only way to lose work is to deliberately choose it.

An `ARCHIVE` action is also provided: instead of stashing, the dirty worktree is moved to `~/.lyra/archived-worktrees/<name>/`, preserving the full directory state including any build artifacts, caches, or partial patches that git stash would not capture.

The cleanup decision tree is formalized as a state machine with three dirty states:

| State | Meaning | Default Action |
|-------|---------|----------------|
| `CLEAN` | No uncommitted changes, no unpushed commits | Auto-remove (or prompt if named) |
| `DIRTY_UNCOMMITTED` | Modified/untracked files exist | STASH + notify |
| `DIRTY_NEW_COMMITS` | New commits not pushed | STASH + notify |

This state machine is implemented in `WorktreeIsolation._check_worktree_state()` (line 377 of `worktree_isolate.py`), which runs `git status --porcelain` and `git rev-list` to determine dirty status algorithmically rather than by heuristic.

---

## 3. Git Worktree Mechanism

### 3.1 How Worktrees Work: Shared `.git`, Separate Working Directory

A git worktree is a linked checkout of the same repository. The canonical repository (the "main" worktree, created by `git clone`) lives in the directory that contains `.git/`. Additional worktrees are created with `git worktree add`, which:

1. Creates a new directory at the specified path.
2. Checks out the specified branch (or creates a new one) into that directory.
3. Adds a `.git` file in the new worktree directory pointing back to the shared `.git/` via a `.git/worktrees/<id>/` administrative directory.

The shared `.git/` stores all objects, refs, and configuration. Each worktree gets its own:
- **Working directory**: independent files on disk.
- **HEAD**: independent of other worktrees (but cannot share a branch that any other worktree has checked out).
- **Index**: independent staging area.
- **Per-worktree refs**: stored in `.git/worktrees/<id>/refs/`.
- **Per-worktree configuration**: stored in `.git/worktrees/<id>/config.worktree`.

Branches are a shared namespace. A branch checked out in one worktree is locked -- no other worktree can check it out (git enforces this at the ref level). This is enforced by writing the branch's ref into `.git/worktrees/<id>/gitdir`, and checking it on every `git checkout`.

This architecture gives worktrees a critical property: they are **not copies**. Creating a worktree is a metadata operation that takes tens of milliseconds regardless of repository size. The objects are already in `.git/objects/`. The worktree just links to them.

### 3.2 Creation: Branch from origin/HEAD or Local HEAD

Lyra's `WorktreeIsolation.create()` (line 135 of `worktree_isolate.py`) supports two base-branch policies, matching Claude Code's `worktree.baseRef` setting:

**Fresh (default)**: Branch from `origin/HEAD`. This gives the agent a clean starting point that matches the remote's default branch, regardless of any local uncommitted changes or experimental branches in the parent worktree.

```
git fetch origin
BASE=$(git symbolic-ref refs/remotes/origin/HEAD)
git worktree add -b worktree-<session-id> .lyra/worktrees/<session-id> <BASE>
```

**Head**: Branch from local `HEAD`. This carries the parent's current state, including any uncommitted changes and unpushed commits, into the new worktree. This is used when a subagent needs the parent's in-progress work as its starting point.

```
git worktree add -b worktree-<session-id> .lyra/worktrees/<session-id> HEAD
```

**PR**: A third mode handles pull request worktrees. When the session name starts with `#` or is a PR URL, Lyra fetches the PR branch from the remote and creates the worktree from it:

```
git fetch origin pull/<number>/head:pr-<number>
git worktree add -b worktree-pr-<session-id> .lyra/worktrees/pr-<session-id> pr-<number>
```

The policy is configured in `WorktreeConfig.base_branch_policy` (line 66 of `worktree_isolate.py`), an enum with `FRESH`, `HEAD`, and `PR` values. The actual git invocation is in `_create_git_worktree()` (line 313), which resolves the base ref, runs `git worktree add`, and returns a `WorktreeStatus` with the branch name and state.

The `WorktreeManager` in `packages/lyra-core/src/lyra_core/subagent/worktree.py` uses a simpler variant that does not support the `FRESH` vs `HEAD` distinction -- it always branches from the current HEAD, which is the correct behavior for subagents that inherit the parent session's working state.

### 3.3 `.worktreeinclude`: Propagating Gitignored Files (env/secrets)

The `.worktreeinclude` file lives at the repository root and uses `.gitignore` syntax. When a new worktree is created, Lyra reads this file, resolves each pattern against the repository file list, and copies matched files that are also gitignored into the new worktree.

The implementation in `WorktreeIsolation._propagate_includes()` (line 420 of `worktree_isolate.py`) follows this algorithm:

```
FOR each pattern in .worktreeinclude (or config.include_patterns):
    FOR each file matching pattern in the repo root:
        IF file is gitignored (git check-ignore -q <file>):
            copy file into worktree at same relative path
            preserve permissions via shutil.copy2
        ELSE (tracked file):
            SKIP -- never duplicate tracked files
```

The gitignored check uses `git check-ignore -q <path>` (via `_is_gitignored()` on line 451), which exits 0 if the path is ignored, 1 if it is tracked. This ensures that only gitignored files are propagated -- tracked files are already in the worktree because git checked them out.

If no `.worktreeinclude` file exists, Lyra falls back to a default pattern set defined in `WorktreeConfig.include_patterns` (line 69):

```python
include_patterns: list[str] = field(default_factory=lambda: [
    ".env", ".env.local", ".envrc",
    "*.secret", "*.key", "credentials.*",
])
```

Security validations from the design spec (path traversal detection, tracked-file detection) are present in the architecture plan but are not yet implemented in the production code -- the current implementation trusts that `.worktreeinclude` patterns are authored by the repository owner.

When a `WorktreeCreate` hook is configured, `.worktreeinclude` is **not processed**. The hook is responsible for environment setup, and the auto-copy step is skipped to avoid conflicts with whatever the hook does.

---

## 4. Non-Destructive Cleanup

### 4.1 Claude Code's Silent Discard

Claude Code's cleanup behavior, as documented in the agent-view worktree mechanisms research (source: `docs/research/agent-view-worktree-mechanisms.md`), is:

- Clean exit + unnamed session: auto-remove worktree + branch (no prompt).
- Clean exit + named session: prompt keep or remove.
- Dirty exit: prompt keep or remove. If remove, **silently discards** all uncommitted changes, untracked files, and unpushed local commits.
- Non-interactive (`-p` flag): keep everything, no cleanup.
- Periodic sweep: removes clean worktrees older than `cleanupPeriodDays` (default 30).

The dirty-removal path is the footgun. A user who has been working in a worktree for hours may have uncommitted changes, new files, and local commits. Choosing "remove" on the prompt is a permanent loss with zero recovery options. There is no trash, no `git stash`, no archive. The removal is executed as:

```
git worktree remove --force .claude/worktrees/<session-id>
git branch -D worktree-<session-id>
```

Both operations are irreversible.

### 4.2 Lyra's Auto-Stash and Three-Way Cleanup

Lyra replaces the destructive single-path removal with a three-way cleanup decision that defaults to the safe path.

**Stash path** (default for dirty worktrees):

```
1. git -C <worktree-path> stash push -u -m "auto-stash-<timestamp>"
   # Captures tracked, staged, and untracked files
2. git branch -m <worktree-branch> parked/<worktree-name>
   # Renames the branch so the worktree cannot be re-created with the same ref
3. git worktree remove --force <worktree-path>
   # Deletes the working directory
4. NOTIFY user with recovery instructions
```

The stash is created with `-u` (include untracked) and a descriptive message that includes the timestamp, making it findable via `git stash list`. The branch is renamed to `parked/<name>` so that recovery is straightforward: check out the parked branch, pop the stash, and continue.

The notification shown to the user includes exact recovery commands:

```
Worktree '<name>' had uncommitted changes. Auto-stashed for safety.

Recovery:
  git worktree add .lyra/worktrees/<name> parked/<name>
  cd .lyra/worktrees/<name>
  git stash pop

Stash ref: refs/stash/worktree-<name>
Parked branch: parked/<name>
```

**Archive path** (alternative for dirty worktrees):

```
1. shutil.move(<worktree-path>, ~/.lyra/archived-worktrees/<name>/)
2. # Full directory state preserved
```

This preserves not just git-tracked state but also build artifacts, `node_modules/`, `.venv/`, and any other files that git ignores. It is the safest path but also the most expensive in terms of disk usage.

**Discard path** (requires explicit `force=True`):

```
1. git worktree remove --force <worktree-path>
2. git branch -D <worktree-branch>
3. # No recovery possible
```

This path is never taken by default. It exists only for callers who explicitly request it and pass `force=True`. No Lyra internal code path uses discard as the default or fallback.

### 4.3 Park Branch Mechanism

When a dirty worktree is stashed, its branch is renamed to `parked/<name>` before the worktree is removed. This serves two purposes.

First, it prevents accidental re-creation of the worktree on the same branch. If the branch were left as `worktree-<session-id>`, a new worktree creation with the same name would fail because git would refuse to check out an existing branch.

Second, it creates a clear recovery path. The parked branch contains all the commits that existed in the worktree, even if they were not pushed. The user can recover with:

```
git worktree add .lyra/worktrees/<name> parked/<name>
```

This re-creates the worktree on the parked branch, complete with all local commits. The stash pop then restores the uncommitted changes.

### 4.4 Periodic Sweep

Lyra's `WorktreeIsolation.cleanup_sweep()` (line 273 of `worktree_isolate.py`) runs a periodic sweep that removes old, clean worktrees. The default TTL is 7 days (Claude Code uses 30). The sweep:

- Only removes worktrees older than `max_age_days` (default 7).
- Skips dirty worktrees by default (configurable via `clean_only` flag).
- Uses the configured `cleanup_action` for removal (STASH by default, which is safe even for clean worktrees).
- Returns a list of removed worktree names for logging.

Unlike Claude Code, Lyra's sweep does not distinguish between CLI-created worktrees (`--worktree` flag) and auto-created ones -- all worktrees are subject to the sweep. Named worktrees survive only if they are clean and below the age threshold.

---

## 5. COW Optimization

### 5.1 APFS Clones: 87ms (540x Faster Than Full Copy)

On macOS 10.13+ with APFS, `cp -c` creates a clone -- a metadata-only copy that shares blocks with the original. No data is duplicated until a write occurs. For a 10GB repository with 50,000 files, an APFS clone takes approximately 87 milliseconds. The equivalent `shutil.copytree` takes 47 seconds. The speedup is 540x.

The clone is implemented in `CoWCloner._apfs_clone()` (line 162 of `cow_isolation.py`):

```python
subprocess.run(
    ["cp", "-c", "-R", str(src), str(dst)],
    check=True, capture_output=True, timeout=60,
)
```

Error handling covers two cases: cross-device clone attempts (the source and destination must be on the same APFS volume) and permission failures. On error, the cloner falls through to the next method in the chain.

Disk overhead is zero bytes initially -- the clone shares every block. The first write to a cloned file triggers a COW page at the APFS block level: the modified block is copied to a new physical location, and the clone's file extent reference is updated. Subsequent writes to the same block proceed at native speed. Typical write amplification for code editing is 5-10%.

Cleanup is instant: `rm -rf` on a clone removes only the directory metadata. The shared blocks are freed only when all references (original and clones) are deleted.

### 5.2 Overlayfs: 42ms

On Linux 3.18+, overlayfs provides a layered union mount. The original repository is mounted as a read-only lower layer, and a writable upper layer captures all modifications. The agent sees the merged view.

Creation is the fastest of all COW methods: approximately 42 milliseconds for a 10GB repository. The mount command in `CoWCloner._overlayfs_mount()` (line 175 of `cow_isolation.py`):

```bash
mount -t overlay overlay \
  -o lowerdir=<repo>,upperdir=<upper>,workdir=<work> \
  <merged>
```

The `upper` directory starts empty; no data is copied. Only files that the agent modifies are written to the upper layer. This makes overlayfs the most space-efficient option -- disk usage equals exactly the size of the modifications, plus metadata.

Cleanup requires unmounting the overlay and removing the upper/work directories:

```bash
umount <merged>
rm -rf <upper> <work>
```

On modern Linux (Ubuntu 22.04+, Debian 12+, RHEL 9+), overlayfs is available by default. The `CoWDetector._has_overlayfs()` check (line 87) reads `/proc/filesystems` for the `overlay` entry. If overlayfs is not available (no kernel module, no root privileges), the cloner falls back.

Root privileges are required for the standard `mount` command. Lyra supports `fuse-overlayfs` as a userspace alternative, which requires no root but must be installed separately.

### 5.3 Automatic Fallback Chain

The `CoWCloner.clone()` method (line 118 of `cow_isolation.py`) implements a fallback chain that tries each method in priority order and drops to the next on failure:

1. **APFS clone** (macOS): ~87ms. Falls through on cross-device error or non-APFS filesystem.
2. **overlayfs** (Linux): ~42ms. Falls through on missing kernel support or permission denied.
3. **btrfs snapshot** (Linux): ~95ms. Falls through on non-btrfs filesystem.
4. **Hardlinks** (universal): ~3.2s. Falls through on cross-filesystem error.
5. **Full copy** (last resort): ~47s. Always succeeds.

The fallback is transparent to the caller. The `CoWResult` returned by `clone()` includes the method that was actually used, so callers can log performance metrics and detect when the system is running on a suboptimal path.

The detection is handled by `CoWDetector.detect()` (line 56), which checks `platform.system()` and then tests for filesystem-specific features:

```python
system = platform.system()
if system == "Darwin":
    if CoWDetector._is_apfs(path):
        return CoWMethod.APFS_CLONE
    return CoWMethod.HARDLINK
if system == "Linux":
    if CoWDetector._has_overlayfs():
        return CoWMethod.OVERLAYFS
    if CoWDetector._is_btrfs(path):
        return CoWMethod.BTRFS_SNAPSHOT
    return CoWMethod.HARDLINK
return CoWMethod.HARDLINK  # Default for Windows, BSD, etc.
```

### 5.4 Realistic Per-Session Benchmarks

The benchmarks below are from the COW deep-dive research document (`docs/research/COW-FILESYSTEM-DEEP-DIVE.md`), measured on real hardware (M2 Pro MacBook, 10GB repository with 50,000 files):

| Method | Creation Time | Initial Disk Overhead | Write Amplification | Cleanup Time | Platform |
|--------|--------------|----------------------|---------------------|-------------|----------|
| **APFS clone** | 87ms | 0% | 1.05-1.10x | 120ms | macOS 10.13+ |
| **Overlayfs** | 42ms | 0% | 0-1x | 180ms | Linux 3.18+ |
| **btrfs snapshot** | 95ms | 0% | 1.02-1.05x | 110ms | Linux (btrfs) |
| **Hardlinks** | 3.2s | 0% | 1x (per modified file) | 2.1s | Universal |
| **Full copy** | 47s | 100% | 1x | 2.3s | Universal |

The practical impact on fleet dispatch: spawning 16 parallel agents without COW requires 16 x 47s = 752 seconds (12.5 minutes) just for file system setup. With COW, the same dispatch takes 16 x 87ms = 1.4 seconds. This is the difference between "impractical" and "instant."

---

## 6. Non-Git Fallback

### 6.1 Hook-Based Delegation

For repositories that do not use git (SVN, Mercurial, Perforce, or custom VCS), Lyra supports a `create_hook` and `remove_hook` mechanism. These are callables injected at `WorktreeIsolation` construction time (line 119 of `worktree_isolate.py`):

```python
def __init__(
    self,
    create_hook: Callable[[str, Path], Path] | None = None,
    remove_hook: Callable[[Path], bool] | None = None,
) -> None:
```

When `create_hook` is set and the repository is not a git repo, `WorktreeIsolation.create()` delegates entirely to the hook. The hook receives the worktree name and target path, and must return the path to the created isolation directory. The hook is responsible for:

1. Creating the isolated working directory (via Docker, overlay, SVN checkout, etc.).
2. Setting up any environment variables or secrets.
3. Installing dependencies if needed.

The `remove_hook` is the inverse: it receives the path and cleans up. It returns `True` on success.

This matches Claude Code's `WorktreeCreate`/`WorktreeRemove` hook system exactly. The hook receives a JSON payload on stdin with the session context:

```json
{
  "session_id": "<id>",
  "cwd": "<working-directory>",
  "hook_event_name": "WorktreeCreate",
  "name": "<worktree-name>"
}
```

And must print the created worktree path to stdout. Any non-zero exit code signals failure.

### 6.2 Hardlink-Based Shallow Copy

When no hook is configured and the repository is not git, Lyra's `WorktreeIsolation` falls back to a shallow copy (line 352 of `worktree_isolate.py`). This is the same `_create_overlay_worktree()` method that predates the COW optimization and serves as the universal fallback.

The shallow copy walks the repository root and copies files using `shutil.copy2` (preserving metadata). It skips `.git/`, `.claude/`, `__pycache__/`, `node_modules/`, and `.venv/` directories for performance. This is not a true COW operation -- every file is physically duplicated on disk.

For a more efficient non-git fallback, the COW cloner provides a hardlink-based clone via `CoWCloner._hardlink_clone()` (line 210 of `cow_isolation.py`):

```python
subprocess.run(
    ["cp", "-al", str(src), str(dst)],
    check=True, capture_output=True, timeout=120,
)
```

The `-al` flag creates hardlinks instead of copies: every file in the clone is a hardlink to the corresponding file in the original. Initial disk overhead is zero bytes. However, this is NOT true COW -- a write to a hardlinked file modifies the original unless the hardlink is explicitly broken first.

The design plan (worktree-isolation.md, Section 8) includes a `safe_write_hardlink` helper that breaks the hardlink before the first write by copying the file to a temp location and atomically replacing it:

```python
def safe_write_hardlink(path: Path, content: str) -> None:
    if path.stat().st_nlink > 1:
        temp = path.with_suffix(path.suffix + ".tmp")
        shutil.copy2(path, temp)
        temp.replace(path)
    path.write_text(content)
```

This pattern converts a hardlink-based clone into a lazy COW system: files are duplicated only on first write, matching the performance characteristics of true COW for code-editing workloads where most files are read but not modified.

---

## 7. Architecture Diagram

```
                                 +---------------------+
                                 |   FleetSupervisor   |
                                 |  (background session|
                                 |   lifecycle mgmt)   |
                                 +----------+----------+
                                            |
                          dispatches worktree ops
                                            |
                     +----------------------v----------------------+
                     |           WorktreeIsolation                 |
                     |  (orchestration layer, safety policy)       |
                     |                                              |
                     |  create()  remove()  status()  sweep()       |
                     |  .worktreeinclude propagation                |
                     |  base-branch policy (fresh/head/PR)          |
                     |  cleanup state machine                       |
                     +----------------------+-----------------------+
                                            |
                            +---------------+---------------+
                            |                               |
                    +-------v--------+           +----------v---------+
                    | WorktreeManager |          |  CoWCloner         |
                    | (core layer,    |          | (COW optimization, |
                    |  git primitive) |          |  fallback chain)   |
                    +-------+--------+          +----------+----------+
                            |                               |
                    +-------v--------+           +----------v---------+
                    |  git worktree  |           | APFS / overlayfs / |
                    |  add / remove  |           | btrfs / hardlinks  |
                    +----------------+           +--------------------+
                            |
                    +-------v--------+
                    |  Non-Git Hook  |
                    |  (SVN, Docker, |
                    |   custom VCS)  |
                    +----------------+


Session Lifecycle (timeline):

  Session Start
       |
       v
  EnterWorktree(name?, path?)   ────  Agent tool, no permission required
       |
       v
  WorktreeIsolation.create()    ────  Determine policy, pick COW method
       |
       +--> git worktree add     ────  Fast path (ms)
       +--> create_hook()        ────  Non-git VCS
       +--> overlay / hardlinks  ────  Last resort fallback
       |
       v
  .worktreeinclude propagation  ────  Copy env/secrets
       |
       v
  Agent edits files in worktree
       |
       v
  ExitWorktree(action, discard_changes?)
       |
       +--> action=keep   → worktree stays on disk
       +--> action=remove → three-way cleanup:
              |
              +--> CLEAN  → git worktree remove (safe)
              +--> DIRTY  → STASH + park branch (default, safe)
                           → ARCHIVE (full state, ~/.lyra/archived/)
                           → DISCARD (only with force=True, dangerous)
```

---

## 8. Trade-Off Analysis

### What the Worktree Architecture Costs

| Cost | Detail | Mitigation |
|------|--------|------------|
| **Disk space per worktree** | Each worktree is a full working checkout. A 500MB repository produces 500MB per worktree. | Git's hardlink optimization (for repos on the same filesystem), COW clones (zero overhead until writes), and `sparsePaths` (partial checkout). |
| **Dependency duplication** | `node_modules/`, `.venv/`, `target/` are duplicated per worktree. | `worktree.symlinkDirectories` setting to symlink large dependency directories from the main repo. |
| **Setup overhead** | Each new worktree must install dependencies. | Post-create hooks can auto-detect project type and install. Symlinked dependency directories skip this entirely. |
| **Branch namespace pollution** | Each worktree creates a branch. Many worktrees = many branches. | Auto-removed branches on cleanup. Parked branches are prefixed `parked/` so they are visually grouped. |
| **Non-git VCS requires hooks** | SVN, Perforce, Mercurial users must write WorktreeCreate/Remove hooks. | Hook API is simple (stdin JSON, stdout path). Lyra provides reference implementations. |
| **Git-only optimization** | COW optimization only applies to git repos. | Hook system and hardlink fallback cover non-git cases. |

### What the Worktree Architecture Gains

| Gain | Detail |
|------|--------|
| **True filesystem isolation** | No overlays, no FUSE tricks, no copying. Standard git worktrees. Every tool works (LSP, indexers, editors, build tools). |
| **Branch-per-task isolation** | Each session has its own branch. Can push independently. No merge conflicts between parallel sessions. |
| **Zero-cost creation** | Git worktrees are metadata operations. Even without COW, creation takes milliseconds. |
| **Standard cleanup** | `git worktree remove` is a first-class git operation. No custom cleanup scripts needed. |
| **Environment propagation** | `.worktreeinclude` solves the "missing .env files" problem with familiar gitignore syntax. |
| **Hook extensibility** | WorktreeCreate/Remove hooks support any VCS, not just git. |
| **Subagent auto-isolation** | Every subagent invocation gets its own worktree, auto-created and auto-cleaned. |
| **COW instant dispatch** | 87ms worktree creation enables true parallel fleet dispatch. |
| **Non-destructive by default** | No silent data loss. STASH/ARCHIVE paths preserve all work. |
| **Survives supervisor restart** | Worktrees are on-disk directories; supervisor restart does not affect them. |

### Design Decisions and Rationale

**Why worktrees over Docker containers?** Docker containers provide stronger isolation (filesystem + network + process), but they add significant overhead: image management, volume mounts that introduce permission issues, container startup time (seconds, not milliseconds), and incompatibility with code-indexing tools that expect native directory structure. Git worktrees are the lightest-weight isolation that achieves the goal: file-level separation with shared history.

**Why worktrees over branch-per-feature without worktrees?** Switching branches in a single checkout is not isolation. Git requires a clean working tree to switch branches, which means stashing or committing mid-task. Multiple agents sharing one checkout cannot work on different branches simultaneously. Worktrees give each agent its own branch checkout with zero interference.

**Why STASH default over ARCHIVE default?** Git stash captures only what git tracks (modified tracked files, staged changes, untracked files). It does not capture build artifacts, caches, or dependency directories. ARCHIVE preserves everything on disk. However, ARCHIVE is expensive: a 2GB worktree (including `node_modules/`) creates a 2GB archive directory. STASH is the right default because it captures the semantically important state (the changes) at minimal cost. ARCHIVE is available as an explicit alternative.

**Why no workspace-trust gate?** Claude Code's workspace-trust gate requires the user to accept a dialog before `--worktree` works. This prevents automated scripts from creating worktrees in untrusted directories. Lyra does not replicate this gate, choosing instead to trust the user's existing access controls. This is a valid choice for a development tool in a trusted environment but should be reconsidered if Lyra is deployed in multi-tenant or CI contexts.

---

## 9. (B) Breakthrough: Lazy Worktree Creation

### 9.1 The Challenge

Standard worktree creation via `git worktree add` is already fast -- it is a metadata operation that takes tens of milliseconds. But it still requires:

1. Resolving the base ref (origin/HEAD or local HEAD).
2. Creating the worktree directory.
3. Checking out files into the working directory.
4. Running `.worktreeinclude` propagation.
5. Optionally running post-create hooks (dependency installation).

Steps 3-5 can take seconds to minutes for large repositories with many files and heavy dependencies. For a fleet dispatching 16 subagents in parallel, even with COW, the checkout time dominates: 87ms for the COW clone, but potentially 30+ seconds for `npm install` or `pip install` in each worktree.

### 9.2 The Breakthrough: Lazy + Symlink

The breakthrough insight is that most subagents do not need their own dependency directories. A subagent that edits two files does not need its own `node_modules/` -- it just needs the filesystem to look like the files are there for the LSP and build tools. The solution combines two strategies:

**SymlinkDirectories** (from Claude Code's `worktree.symlinkDirectories` setting): directories listed in this setting are symlinked from the main repo into the worktree, rather than copied. Typical use cases:

- `node_modules/`: never changes between worktrees at the point of creation.
- `.cache/`: build tool caches that are read-heavy, write-light.
- `.venv/`: Python virtual environments that can be shared read-only.

Symlinks are created in a post-worktree-create hook, or by Lyra's worktree creation logic:

```python
def _apply_symlinks(worktree_path: Path, symlink_dirs: list[str]) -> None:
    repo_root = Path.cwd()
    for dir_name in symlink_dirs:
        src = repo_root / dir_name
        dst = worktree_path / dir_name
        if src.exists() and not dst.exists():
            dst.symlink_to(src, target_is_directory=True)
```

**COW overlay for the rest**: The worktree's working files use the platform-native COW mechanism (APFS clone, overlayfs, or hardlinks) so that reading files costs zero, and writing files allocates new blocks only at the page/extent level.

**Combined effect**: For a repository with 50,000 source files and 30,000 `node_modules/` files, the effective creation time drops from 47 seconds (full copy) to under 100 milliseconds (COW clone + symlink).

### 9.3 Sparse Checkout Integration

For monorepos where only a subset of packages is relevant to a given subagent, `worktree.sparsePaths` limits checkout to specific directories. This is configured per-worktree or per-session:

```json
{
  "worktree": {
    "sparsePaths": ["packages/my-app", "shared/utils"]
  }
}
```

Implementation uses git sparse-checkout:

```
git sparse-checkout init --cone
git sparse-checkout set packages/my-app shared/utils
```

The effect: instead of checking out the full repository (possibly 100,000+ files), git checks out only the specified directories and their ancestor paths. For a monorepo with a deep package tree, this reduces checkout time from minutes to seconds.

### 9.4 Channel Fabric Integration

The (B) Breakthrough also includes a vision for cross-worktree coordination via shared memory channels. Currently, each worktree is fully isolated -- agents cannot see each other's file changes until merge time. The channel fabric, proposed in the design plan (worktree-isolation.md, Section 10.3), would allow worktrees to coordinate:

```python
class WorktreeChannel:
    def __init__(self, session_id: str):
        self.channel = SharedMemory(f"lyra-wt-{session_id}")

    def broadcast(self, event: WorktreeEvent):
        """Notify other worktrees of state changes."""
        self.channel.write(event.to_json())

    def subscribe(self) -> Iterator[WorktreeEvent]:
        """Listen for events from other worktrees."""
        for msg in self.channel.read_stream():
            yield WorktreeEvent.from_json(msg)
```

Use cases include distributed file locking ("I am editing `src/auth.py`"), merge conflict early warning ("Agent B just modified a file you read"), and shared resource coordination. This is not yet implemented; it is noted as a v2 enhancement.

### 9.5 Impact Summary

| Metric | Without Breakthrough | With Breakthrough | Improvement |
|--------|---------------------|-------------------|-------------|
| Worktree creation (10GB repo) | 47s | 87ms | **540x faster** |
| Initial disk overhead | 100% (full copy) | 0% (COW) | **100% savings** |
| Dependency duplication | Full per worktree | Symlinked | **Near-zero** |
| Parallel dispatch (16 agents) | 12.5 min file copy | 1.4s COW setup | **535x faster fleet** |
| Checkout time (monorepo) | Full tree | Sparse subset | **10-100x faster** |
| Safety (dirty removal) | Silent discard | STASH + notify | **Zero data loss** |

---

## 10. Key Sources

### Lyra Source Code

- **`packages/lyra-orchestration/src/lyra_orchestration/worktree_isolate.py`**: The main worktree isolation substrate. Contains `WorktreeIsolation`, `WorktreeConfig`, `WorktreeStatus`, `CleanupAction`, `BaseBranchPolicy`, `WorktreeState` -- the full safety policy layer. 506 lines.
- **`packages/lyra-orchestration/src/lyra_orchestration/cow_isolation.py`**: COW filesystem optimization. `CoWDetector` for platform detection and `CoWCloner` with automatic fallback chain. 219 lines.
- **`packages/lyra-orchestration/src/lyra_orchestration/fleet_supervisor.py`**: Fleet supervisor that wires worktree lifecycle into background session management. 466 lines.
- **`packages/lyra-core/src/lyra_core/subagent/worktree.py`**: Low-level git worktree primitive used by the subagent orchestrator. `WorktreeManager` with allocate/cleanup/reconcile. 94 lines.

### Tests

- **`packages/lyra-core/tests/test_worktree_lifecycle.py`**: Tests for worktree allocate/cleanup/reconcile lifecycle. 6 tests covering allocation, idempotent cleanup, orphan reconciliation, and non-repo rejection.
- **`packages/lyra-core/tests/test_task_tool_worktree_isolation.py`**: Contract tests verifying that the `task` tool delegates worktree management correctly (allocate-before-work, cleanup-on-success, cleanup-on-failure).
- **`packages/lyra-core/tests/test_isolation.py`**: Context isolation tests (30+) covering context boundaries, merge strategies, and isolation policies. Complements the filesystem isolation with logical context isolation.

### Research Documents

- **`docs/research/COW-FILESYSTEM-DEEP-DIVE.md`**: Comprehensive benchmarks and implementation for APFS clones, overlayfs, btrfs reflinks, and hardlink fallbacks. 616 lines.
- **`lyra-upgrade/04-research/agent-view-worktree-mechanisms.md`**: Exact transferable design from Claude Code's agent-view and worktree system. Covers supervisor lifecycle, state model, cleanup decision tree, hooks, settings. 913 lines.
- **`lyra-upgrade/01-plans/worktree-isolation.md`**: Original design document with full architecture, COW benchmarks, cleanup rules table, and (B) breakthrough spec. 750 lines.
- **`docs/blocks/10-subagent-worktree.md`**: Lyra Block 10 specification -- subagent orchestrator with worktree isolation, merge strategy, failure modes, and metrics. 228 lines.

### Design Commitments

- **Commit `75c2def6`** ("feat(orchestration): add worktree isolation substrate for safe parallel editing"): Introduced `worktree_isolate.py` (506 lines) and updated `fleet_supervisor.py` (31 lines changed). The foundational commit.
- **Commit `3d7740ac`** ("feat(isolation): add COW filesystem optimization for instant worktree creation"): Introduced `cow_isolation.py` (219 lines) with the COW fallback chain. The breakthrough optimization.
- **Commit `7ce129f9`** ("feat(orchestration): add fleet supervisor with Agent View background sessions"): Introduced `fleet_supervisor.py` (466 lines) with the background session lifecycle and worktree delegation.
