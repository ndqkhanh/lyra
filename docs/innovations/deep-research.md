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

## Working Flow

You ask Lyra, "How does federated learning compare to centralized for healthcare?" Lyra runs a two-agent pipeline on a shared filesystem workspace.

First, the Context Builder (Librarian) browses the web, reads papers, and writes summaries into `knowledge_base/`. It builds an Evidence DAG — a graph of claims and their sources. The DAG spots gaps: unsupported claims, weak citations. Targeted verification queries go out to fill those gaps (with 1200:1 compression — only relevant snippets are sent). Once the knowledge base is solid, the Report Writer (Author) takes over. The Author has no web access — it can only cite what was actually collected. Before delivery, every citation is cross-checked against Semantic Scholar, OpenAlex, Crossref, and arXiv.

**Example:** You ask about federated vs. centralized learning.
1. Librarian writes 15 source summaries to `knowledge_base/`.
2. Evidence DAG flags "differential privacy cost" as unsupported.
3. Verification finds three papers with real numbers — added to the base.
4. Author writes the report using only those 18 sources.
5. Every citation checked against 4 academic indexes.
6. You receive a cited, verified report.

## Use Cases

**Scenario 1: Market research for a startup.** A founder asks Lyra, "What are the top five competitors in the AI code assistant space and what unique features does each offer?" The research pipeline launches a Context Builder agent that scours Crunchbase, G2 reviews, product docs, and recent funding announcements. It builds a knowledge base with 30 sources, the Evidence DAG flags two claims about "real-time collaboration" that have only one weak source each, and the verification agent fills those gaps. The founder gets a 10-page report where every claim has citations verified across four academic indexes.

**Scenario 2: Academic literature review for a paper.** A PhD student needs to understand the landscape of "differential privacy in federated learning over the last three years." The deep research system reads 80 papers, builds a citation graph, and the Evidence DAG automatically surfaces a contradiction: three papers claim DP costs 5% accuracy, two newer papers claim it costs only 2%. The verification agent tracks down the discrepancy — different epsilon budgets. The student gets a literature review with the debate captured clearly, not just a summary.

**Scenario 3: Competitive technical analysis for an engineering team.** An engineering lead asks, "What database engine should we pick for our new analytics platform — ClickHouse, DuckDB, or StarRocks?" The research system fetches benchmarks, reads release notes, scrapes Hacker News discussions, and builds a comparison table with trade-offs per use case. Each benchmark number is cross-checked against at least two independent sources. The final report includes a decision matrix the team can use in their next sprint planning meeting.

## Conclusion
Implemented: dual-agent separation with shared workspace. Future: GRPO-trained search strategies, AutoScientists-style self-organizing teams.
