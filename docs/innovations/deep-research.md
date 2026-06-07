# Deep Research: Dual-Agent Architecture with Structured Evidence DAG
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/15-deep-research.md) | [Code](../../src/lyra/research/)

## Abstract
Lyra's deep research system separates research into two agents operating on a shared filesystem workspace: Context Builder (Librarian) browses, synthesizes, and writes to knowledge_base/; Report Writer (Author) has web tools removed and treats the knowledge base as sole fact source. An Evidence DAG (Navigator-Searcher, from Argus) identifies gaps and dispatches targeted verification queries with 1200:1 context compression. Log-linear accuracy scaling to K=64 agents. Deterministic multi-index citation verification (Semantic Scholar + OpenAlex + Crossref + arXiv) runs as a mandatory pipeline gate.

## Method
```mermaid
flowchart LR
    QUERY[Research Question] --> LIB[Context Builder / Librarian]
    LIB --> KB[Knowledge Base (filesystem)]
    KB --> DAG[Evidence DAG]
    DAG --> GAPS{Gaps Found?}
    GAPS -->|Yes| VERIFY[Targeted Verification]
    GAPS -->|No| AUTHOR[Report Writer / Author]
    VERIFY --> KB
    AUTHOR --> CITE[Citation Verification (4-index)]
    CITE --> REPORT[Final Report]
```

## Conclusion
Implemented: dual-agent separation with shared workspace. Future: GRPO-trained search strategies, AutoScientists-style self-organizing teams.
