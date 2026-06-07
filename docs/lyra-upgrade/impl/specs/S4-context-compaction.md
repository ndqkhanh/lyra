# S4: Iterative Workspace Reconstruction (Breakthrough #1)

> Plan: §4.3 (03-context-compaction.md) | Depends on: S1, S3 | Breakthrough #1
> Sources: IterResearch [2511.07327v2], Tongyi DeepResearch [2510.24701v3], COMEM [2605.30842v1]

## Scope
Implement evolving compressed workspace report M_t that replaces linear context accumulation. O(1) memory per step instead of O(t) growth.

## Key Design
1. **WorkspaceReport**: structured markdown document updated after each step
2. **Update function**: M_{t+1} = synthesize(M_t, latest_observations, action_outcome)
3. **Prompt-only variant first** (IterResearch approach, no training needed)
4. **Configurable compression**: aggressive (keep only key findings), balanced (default), verbose (keep more)
