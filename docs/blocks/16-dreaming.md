# Memory Consolidation / Dreaming — Block Spec

> Idle-time memory consolidation: Scan→Dedup→Resolve→Trim→Discover→Produce. Reviewable memory bank, never modifies originals. Field-theoretic PDE-governed semantic diffusion.

## Consolidation Pipeline

```
Idle Trigger (no activity for N minutes)
      │
      ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ SCAN     │───→│ DEDUP    │───→│ RESOLVE  │
│ recent   │    │ MD5 hash │    │ negations│
│ memories │    │ cosine   │    │ conflicts│
└──────────┘    └──────────┘    └────┬─────┘
                                     │
┌──────────┐    ┌──────────┐         │
│ PRODUCE  │←───│ DISCOVER │←───┐    │
│ reviewable│   │ cross-   │    │    │
│ bank     │   │ session  │    │    │
└────┬─────┘    │ patterns │    │    │
     │          └──────────┘    │    │
     ▼                         ▼    ▼
┌──────────┐              ┌──────────┐
│ ACCEPT/  │              │ TRIM     │
│ REJECT   │              │ outdated │
└──────────┘              │ excess   │
                          └──────────┘
```

## Key Modules

| Module | File | Role |
|--------|------|------|
| DreamEngine | `src/lyra/memory/dream_engine.py` | Full consolidation loop |
| FieldMemory | `src/lyra/memory/field_theoretic.py` | PDE-governed fields |
| PopulationBroadcast | `src/lyra/memory/population_broadcast.py` | FORGE propagation |
| LatentMemory | `src/lyra/memory/latent_tokens.py` | MemGen tokens |
| MemoryConsolidation | `src/lyra/memory/memory_consolidation.py` | STM→LTM bridge |

## → Dive Deeper

- [Dreaming Concept](../concepts/19-dreaming-consolidation.md)
- [Memory Innovation Doc](../innovations/memory.md)
- [Dreaming Innovation Doc](../innovations/dreaming.md)
- [Plan](../lyra-upgrade/plans/24-dreaming.md)
