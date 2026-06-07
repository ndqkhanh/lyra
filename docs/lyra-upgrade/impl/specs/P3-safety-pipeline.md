# P3: Defense-in-Depth Safety Pipeline

> Plan: §4.17 | Depends on: P2

## Scope
5-layer safety architecture: lexical gate → tool-call gating → alignment check → data-flow tracking → continuous eval.

## Key Design
1. Layer 1: Fast lexical scan (regex-based, 19ms target)
2. Layer 2: Deterministic tool-call gating (P2)
3. Layer 3: Alignment check via separate LLM (sampling schedule)
4. Layer 4: Data-flow tracking for untrusted data
5. Layer 5: Self-evolving safety evaluation
