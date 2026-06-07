# S6: Worktree Isolation Layer

> Plan: §4.13 | Depends on: S5

## Scope
Git worktree isolation for parallel agent sessions. Each session gets its own worktree/branch. Auto-cleanup on completion. Configurable base-ref policy.

## Key Design
1. WorktreeManager: create(session_id, base_ref), switch(session_id), cleanup(session_id)
2. Base-ref policy: FRESH (from origin/main), HEAD (carry local changes)
3. .worktreeinclude for env files
4. Auto-remove clean worktrees, prompt for dirty ones
