# Deep Research (Concept)

> **What & Why:** Lyra researches autonomously. A Librarian agent browses and synthesizes into a knowledge base. An Author agent writes the final report from that knowledge base alone. The separation ensures citations are grounded in collected evidence, not hallucinated.

## Mental Model

Think of it as a research assistant with two roles: one person gathers sources, takes notes, and organizes a shared folder. Another person writes the paper using only what's in that folder — no internet access, no memory of things they might have read elsewhere. The result is a paper where every claim traces to a collected source.

## Key Concepts

- **Dual-agent separation:** Librarian (browse + synthesize) ≠ Author (write from KB only). -10.35 RACE drop without this separation [FS-Researcher, 2602.01566v2].
- **Evidence DAG:** Claims → evidence nodes → support/contradict arcs. Navigator finds gaps, dispatches verification.
- **Citation verification:** 4-index cross-check (Semantic Scholar + OpenAlex + Crossref + arXiv) as mandatory pipeline gate.

## → Dive Deeper

- [Innovation Doc](../innovations/deep-research.md)
- [Plan](../lyra-upgrade/plans/15-deep-research.md)
