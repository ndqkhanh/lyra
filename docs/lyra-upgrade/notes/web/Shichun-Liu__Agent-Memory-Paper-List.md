# Shichun-Liu/Agent-Memory-Paper-List -- Deep-Read

## 1. Headline Feature & Mechanism

This repository is the **companion paper list** for the survey *"Memory in the Age of AI Agents: A Survey"* (arXiv 2512.13564, Dec 2025). Its headline contribution is a **unified three-lens taxonomy** that organizes the fragmented landscape of agent memory research into a coherent framework. Unlike ad-hoc temporal taxonomies (short-term vs long-term), this survey proposes three orthogonal lenses:

- **Forms** (What Carries Memory?): Token-level (explicit, discrete text/embeddings), Parametric (implicit model weights, LoRA adapters), Latent (hidden states, KV caches, continuous vectors).
- **Functions** (Why Agents Need Memory?): Factual Memory (knowledge storage/retrieval), Experiential Memory (insights, skills, procedural learning), Working Memory (active context management during reasoning).
- **Dynamics** (How Memory Evolves?): Formation (extraction from experience), Evolution (consolidation, forgetting, merging), Retrieval (access strategies -- sparse, dense, hybrid).

The repository contains **~200 curated papers** (2022-2026) classified along the Function x Form matrix: Factual/Token-level (70+ papers), Factual/Parametric (16 papers), Factual/Latent (8 papers), Experiential/Token-level (40+ papers), Experiential/Parametric (6 papers), Experiential/Latent (1 paper), Working Memory/Token-level (14 papers), Working Memory/Parametric (2 papers), Working Memory/Latent (20+ papers). The README is the entire codebase -- there is no runnable software.

## 2. Architecture & Core Modules

This is a **pure markdown repository** with no build system, package manager, or executable code.

```
Shichun-Liu__Agent-Memory-Paper-List/
  README.md        # The full paper catalog + taxonomy explanation + citation
  LICENSE          # MIT License
  assets/
    main.png       # Taxonomy overview: Forms x Functions x Dynamics
    concept.png    # Agent Memory vs LLM Memory vs RAG vs Context Engineering
```

The data model is a flat, manually curated list organized under h3 headings (Factual Memory > Token-level, Experiential Memory > Token-level, etc.). Each entry is a bullet with format: `[YYYY/MM] Title. [[paper](arxiv_url)]`. There is no database, no API, no search -- it is a purely static reference document.

Key design pattern: Papers are assigned exclusively to one cell of the Function x Form matrix. A paper can appear in only one category, which is a deliberate simplification trade-off (many papers span multiple categories).

## 3. Performance/Benchmarks

N/A. This is a survey paper list, not an empirical research artifact. No benchmarks, no runtime measurements, no evaluation scores are present.

## 4. Trade-offs

**Wins:**
- The three-lens taxonomy is genuinely novel and solves the fragmentation problem in agent memory literature. Prior surveys used simplistic temporal splits (STM vs LTM) or one-axis functional taxonomies. The orthogonal Forms x Functions matrix captures the design space more completely.
- Excellent coverage of 2024-2026 papers (the most active period). Papers are current through January 2026.
- The conceptual distinction between Agent Memory, LLM Memory, RAG, and Context Engineering (shown in `assets/concept.png`) is valuable and rarely made explicit in the literature.
- 1k+ GitHub stars, HuggingFace Daily Paper #1, indicating strong community reception.

**Losses:**
- No executable code, no evaluation harness, no reproducible experiments. This is a bibliography, not a tool. There is no way to test or validate any of the claims made by the papers.
- Cross-cutting papers (e.g., a paper about both Factual and Working Memory) are forced into one bucket. The taxonomy has no mechanism for multi-label classification.
- No explicit coverage of the Dynamics lens (Formation/Evolution/Retrieval) in the paper list organization. The paper list is organized only by Function > Form. Dynamics are discussed in the survey paper itself but not reflected in the catalog structure.
- No annotations beyond title and link -- no tags, no summary, no key result extracted from each paper. This limits its utility for systematic literature review.
- Single author/group maintainer model (EvoAgentX). Sustainability depends on continued PR acceptance.
- No comparison or critique of papers within each category. The list is purely descriptive.

## 5. Design Rationale

The fragmented state of agent memory research motivated this taxonomy. The authors argue that prior taxonomies conflated three separate concerns (storage medium, purpose, and lifecycle) into one dimension. By separating Forms, Functions, and Dynamics as orthogonal axes, the framework enables precise positioning of any memory system along three independent dimensions.

The choice to build a flat paper list (rather than a taggable database, web app, or interactive taxonomy browser) is deliberate: a README.md is the lowest-friction, most accessible format for a research community. It requires zero infrastructure, is trivially forkable, and aligns with the convention of survey companion repositories (e.g., "Awesome X" lists).

The choice to use arXiv papers (predominantly 2024-2025) rather than peer-reviewed venues reflects the fast-moving nature of the field -- by the time a paper is published at a conference, the ideas have often been superseded.

## 6. Transfer to Lyra

**The single most transferable idea is the three-lens taxonomy (Forms x Functions x Dynamics) as a design framework for Lyra's memory subsystem.** Rather than building a monolithic memory store, Lyra could use this taxonomy to:

- **Map Lyra's existing memory mechanisms to the matrix**: What is currently token-level factual memory (RAG stores)? What could be parametric (fine-tuned persona adapters)? Where does Lyra's working memory live (context window, state machine)?
- **Identify gaps**: The Experiential/Latent cell has only 1 paper -- Lyra could innovate here by using compressed continuous representations of agent experience. The Parametric categories across all functions are thin -- Lyra could explore lightweight fine-tuning for procedural memory.
- **Design the Dynamics pipeline explicitly**: Separate Lyra's memory operations into Formation (how does info enter memory?), Evolution (how does it get consolidated, summarized, or forgotten?), and Retrieval (what triggers a memory lookup, and with what strategy?).

**Recommended workstream route**: **Section 4.3 (Memory Architecture)** -- this taxonomy serves as a direct input to Lyra's memory subsystem design. The effort is low (reading a README and its 200 references for design inspiration) with disproportionately high impact on architectural clarity.

**Impact: 7** -- High conceptual leverage. The taxonomy could prevent Lyra from making ad-hoc memory design decisions and ground them in a surveyed research landscape. However, it provides no implementation -- Lyra still needs to build the actual system.

**Effort: 3** -- Low. Reading one markdown file and selectively reading 10-20 key referenced papers.

**Tier: T1** -- Immediately actionable design insight. The taxonomy can inform Lyra's memory architecture without needing any code changes.

**License**: MIT (Copyright 2025 EvoAgentX). The paper list itself can be freely referenced and extended.
