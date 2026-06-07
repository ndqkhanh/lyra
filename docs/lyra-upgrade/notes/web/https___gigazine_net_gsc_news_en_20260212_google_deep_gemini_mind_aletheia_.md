# Google DeepMind Aletheia -- Autonomous Mathematical Research Agent (Gigazine via Google DeepMind)

Source: https://gigazine.net/gsc_news/en/20260212-google-deep-gemini-mind-aletheia/
Date: 2026-02-12
Author: log1i_yk (Gigazine); agent developed by Google DeepMind
Related papers: arxiv:2601.23245, arxiv:2602.02450, arxiv:2601.21442

---

## Key Technical Claims

- Aletheia is a mathematical research agent built on **Gemini 3 Deep Think**, designed for "extremely difficult reasoning problems."
- It can "generate, verify, and revise answers end-to-end using natural language."
- It calculated **eigenweights, a structural constant in arithmetic geometry, without human intervention**, producing a fully autonomous research paper (arxiv:2601.23245).
- From the **Erdos Conjecture database of 700 open problems**, Aletheia autonomously solved four open problems; one was generalized into an independent paper (arxiv:2601.21442).
- Google DeepMind proposed a **"Mathematical Research Autonomy Levels"** framework (modeled on self-driving car autonomy tiers) with three contribution categories: "Human with Secondary AI Input," "Human-AI Collaboration," and "Essentially Autonomous." Mathematical significance is rated Level 0 (Negligible Novelty) to Level 4 (Landmark Breakthrough). Aletheia's own output was self-classified as **Level 2 (Publishable Research)** and submitted for peer review.

## Architecture / Mechanism Details

- **Three-subagent loop:**
  1. **Generator** -- produces candidate answers/proofs.
  2. **Verifier** -- judges correctness of each candidate.
  3. **Reviser** -- makes minor corrections based on Verifier feedback.
- **External tool integration:** Google search is used "to navigate the literature," which the authors claim significantly reduces unfounded citations and calculation errors.
- **Inference-time compute scaling:** A scaling law was validated showing accuracy improves with increased inference-time compute, extending beyond competition math into doctoral-level tasks.
- Prompts and outputs for each generated paper are published on GitHub.

## Numbers & Benchmarks

| Benchmark | Result |
|-----------|--------|
| IMO-Proof Bench Advanced | **95.1% accuracy** ("highest accuracy") |
| FutureMath Basic (doctoral-level exercises) | "Excellent performance" (no specific percentage given) |
| Erdos Conjecture database (700 open problems) | **4 autonomously solved**; 1 generalized into independent paper |
| Autonomy self-classification | Level 2 / Publishable Research |

## Limitations / Caveats

- Human involvement was not entirely absent: for one proof, the agent proposed the high-level strategy and "a human described it in detail."
- The self-classification (Level 2) comes from Google DeepMind itself and has not been independently validated (papers only "submitted for peer review").
- No failure rates, unsolved-problem counts among the 700, or boundary conditions for the scaling law are discussed.

## Transfer to Lyra

**Transferable idea:** The Generator-Verifier-Reviser three-agent loop with external-tool citation grounding.

Lyra's current design has separate planner/executor/verifier roles but lacks a dedicated **Reviser** agent that makes fine-grained corrections based on Verifier output without restarting from scratch. Adding a lightweight Reviser pass between verification failure and re-planning would reduce wasted compute on full retries.

**Workstream route:** §4.3 (Agent Architecture / Control Loop) -- specifically introduce a `Reviser` stage into the agent loop, gated behind the existing Verifier. When the Verifier scores a plan or artifact below threshold but above a "minor fix" cutoff, route to Reviser (a fast, cheap model or a targeted edit prompt) rather than restarting from the Generator/Planner. Ground Reviser edits with web search or file-system lookups to reduce hallucinated corrections, mirroring Aletheia's Google search integration.

**Impact:** Medium (reduces retry waste and improves iteration speed in the verification loop)
**Effort:** Low (adds one conditional branch and a lightweight prompt template)
**Tier:** T2 (quick structural improvement to existing loop)
