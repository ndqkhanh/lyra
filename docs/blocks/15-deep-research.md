# Deep Research — Block Spec

> Dual-agent research architecture: Librarian browses + synthesizes into knowledge base; Author writes from knowledge base only. Evidence DAG with gap detection and 4-index citation verification.

## Architecture

```
Research Question
      │
      ▼
┌──────────────┐     ┌──────────────────┐
│ Librarian    │────→│ Knowledge Base   │
│ (browse +    │     │ (filesystem)     │
│  synthesize) │←────│                  │
└──────────────┘     └────────┬─────────┘
                              │
                        ┌─────▼─────────┐
                        │ Evidence DAG  │
                        │ (Navigator)   │
                        └─────┬─────────┘
                              │ gaps found?
                        ┌─────▼─────────┐
                        │ Verification  │
                        │ (targeted)    │
                        └─────┬─────────┘
                              │
                        ┌─────▼─────────┐
                        │ Author        │
                        │ (write from   │
                        │  KB only)     │
                        └─────┬─────────┘
                              │
                        ┌─────▼─────────┐
                        │ Citation      │
                        │ Verification  │
                        │ (4-index)     │
                        └─────┬─────────┘
                              │
                        ┌─────▼─────────┐
                        │ Final Report  │
                        └───────────────┘
```

## Key Modules

| Module | File | Role |
|--------|------|------|
| Research Pipeline | `src/lyra/research/pipeline.py` | Orchestrates Librarian→Author flow |
| Evidence DAG | `src/lyra/verification/` | Gap detection, targeted verification |
| Citation Verify | `src/lyra/verification/` | 4-index cross-check |

## → Dive Deeper

- [Deep Research Concept](../concepts/18-deep-research.md)
- [Innovation Doc](../innovations/deep-research.md)
- [Plan](../lyra-upgrade/plans/15-deep-research.md)
