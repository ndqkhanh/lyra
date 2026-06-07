# Run parallel sessions with worktrees (code.claude.com/docs)

Official Claude Code documentation on git worktree isolation for parallel sessions. Covers the `--worktree` flag, subagent isolation via `isolation: worktree`, `.worktreeinclude` for copying gitignored files, automatic cleanup policies, and non-git VCS hook support.

## Key Technical Claims

1. **Worktree isolation removes file-collision risk in parallel sessions** -- each Claude Code session gets its own working directory, branch, and files, sharing only the repository history and remote. Edits in one session never touch files in another.
2. **Automatic lifecycle management** -- worktrees created by `--worktree` are cleaned up automatically on exit (no changes = silent removal; changes present = user prompt). Subagent worktrees are cleaned by a periodic sweep based on `cleanupPeriodDays`, provided they have no uncommitted changes, untracked files, or unpushed commits.
3. **`.worktreeinclude` file** -- a `.gitignore`-syntax file in the project root copies gitignored files (e.g., `.env`, `.env.local`) into each new worktree automatically. Only files matching a pattern AND already gitignored are copied.
4. **Subagent isolation as a frontmatter toggle** -- setting `isolation: worktree` on a custom subagent gives each subagent its own temporary worktree, removed when the subagent finishes without changes.
5. **Non-git VCS support via hooks** -- `WorktreeCreate` and `WorktreeRemove` hooks replace default git logic for SVN, Perforce, Mercurial, etc. When hooks are configured, `.worktreeinclude` is not processed.
6. **Base branch configurable** -- `worktree.baseRef` setting accepts `"fresh"` (branch from `origin/HEAD`, default) or `"head"` (branch from local HEAD, useful for carrying unpushed work). Does not accept arbitrary git refs.
7. **PR-specific worktrees** -- pass `#1234` or a full PR URL to `--worktree` to create a worktree on `pull/<number>/head` from origin.

## Architecture/Mechanism Details

- **Default location**: `.claude/worktrees/<name>/` at repository root.
- **Branch naming**: New branch `worktree-<value>`; random name (e.g., `bright-running-fox`) if name omitted.
- **Cleanup rules**:
  - No uncommitted changes + no untracked files + no new commits: automatic silent removal on exit.
  - Named sessions: prompt to keep instead of silent removal.
  - Uncommitted changes / untracked files / new commits exist: prompt to keep or remove.
  - Non-interactive (`--worktree` + `-p`): no auto-cleanup; user must `git worktree remove`.
  - Background session worktrees: removed when older than `cleanupPeriodDays` with no dirty state.
  - `--worktree`-created worktrees: **never** removed by the periodic sweep.
- **First-use trust**: `--worktree` requires accepting workspace trust by running `claude` in the directory once. Without trust, `--worktree` exits with an error.
- **Manual management**: Users can create worktrees with `git worktree add` directly, then `cd` into them and run `claude`.
- **Desktop app**: Creates a worktree for every new session automatically.
- **Two layers of parallelism**: Worktrees isolate file edits; subagents and agent teams coordinate the work itself. These are complementary.

## Numbers & Benchmarks

- **`cleanupPeriodDays`**: configurable setting in [settings](https://code.claude.com/docs/en/settings). Used for background session worktree sweep. No default value given.
- **`worktree.baseRef`**: only two valid values -- `"fresh"` (default) and `"head"`. No arbitrary refs.
- **`.worktreeinclude`**: uses `.gitignore` syntax only. Tracked files are never duplicated.
- **`.gitignore` recommendation**: Add `.claude/worktrees/` to `.gitignore` to avoid untracked file noise in main checkout.

## Transfer to Lyra

**Idea**: Adopt a worktree-per-subagent isolation model for Lyra's parallel research/deep-read subagents, gated by a simple flag in the subagent registry (analogous to `isolation: worktree` in frontmatter). Lyra currently runs subagents in the same working tree, meaning concurrent file writes from the deep-read pipeline, verification agents, and plan writers can collide silently. Adding a `worktree_isolation: bool` field to each subagent definition in the Lyra workflow config would let the orchestrator spawn each subagent in its own `git worktree add` checkout, with automatic cleanup on completion.

- **Workstream route**: Section 4.3 (Orchestration/Execution Layer) -- this is a structural change to how the Lyra orchestrator provisions execution environments for subagents, not a change to any individual workstream's logic.
- **Impact/Effort**: Medium impact (eliminates a whole class of silent file-collision bugs), low effort (thin wrapper around `git worktree add` + cleanup logic, already prototyped by Claude Code).
- **Tier**: Tier 2 (near-term, single-sprint addition to the execution harness).
