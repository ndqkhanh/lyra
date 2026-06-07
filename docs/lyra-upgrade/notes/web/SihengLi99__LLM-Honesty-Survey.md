# SihengLi99/LLM-Honesty-Survey -- Deep-Read

## 1. Headline Feature & Mechanism

This repo is a **curated literature survey** (arXiv 2409.18786) that taxonomizes the growing body of research on making LLMs "honest." It does not contain executable code. Its core contribution is a **two-axis conceptual framework** that decomposes LLM honesty into:

- **Self-knowledge** -- the model's ability to recognize what it knows and what it does not know (known-unknown awareness, calibration, selective prediction/abstention).
- **Self-expression** -- the model's ability to faithfully express its internal knowledge without fabrication, sycophancy, or context-loss (faithful decoding, grounding, resistance to spurious prompts).

The mechanism of the repo is purely organizational: it collects ~100+ papers and arranges them into a 3-level tree (Honesty Definition / Evaluation / Improvement), with each leaf node grouping papers by method family (training-free vs training-based, prompting vs decoding-intervention vs self-supervised FT, etc.). The README is the sole deliverable; 5 schematic figures in `assets/` visualize the taxonomy.

## 2. Architecture & Core Modules

Since this is a documentation repo with zero executable code, "architecture" here refers to the **knowledge organization structure**:

```
README.md                              -- the entire corpus, one file
assets/
  main_figure.jpg                      -- honesty framework overview
  evaluation_self_knowledge.jpg        -- known-unknown / calibration / selective prediction
  evaluation_self_expression.jpg       -- identification-based / identification-free
  improvement_self_knowledge.jpg       -- training-free (prob, prompt, sample) + training-based (SFT, RL, probe)
  improvement_self_expression.jpg      -- training-free (prompt, decode, sample, revise) + training-based (self-aware FT, self-supervised FT)
```

No package.json, no setup.py, no entry-point files, no tests, no configuration. The sole dependency is a markdown renderer (any will do). The git history is a single merge commit -- the repo is a snapshot, not an active development project.

## 3. Performance/Benchmarks

This repo contains **zero empirical benchmarks**. It is a secondary survey that cites primary papers -- each cited paper may contain its own calibration scores (ECE, AUROC for selective prediction) or refusal accuracy on benchmarks like SelfAware, BeHonest, UnknownBench, but the survey itself does not re-implement or aggregate those numbers.

Key benchmarks referenced within the cited papers (not implemented here):
- **SelfAware** (Yin et al., ACL 2023) -- known/unknown QA
- **BeHonest** (GAIR-NLP, 2024) -- honesty benchmark across 6 dimensions
- **UnknownBench** (Liu et al., 2024) -- uncertainty expression toward out-of-knowledge questions
- **Semantic Entropy** (Kuhn et al., Nature 2024) -- hallucination detection via meaning-clustering

## 4. Trade-offs

**Wins:**
- The self-knowledge / self-expression decomposition is genuinely clarifying; it separates the epistemic problem ("do I know this?") from the expressive problem ("will I say what I actually know?") which often get conflated.
- The taxonomy is comprehensive and well-structured -- covers training-free (cheap, no compute) and training-based (effective, expensive) approaches on both axes.
- Excellent citation map for anyone entering the LLM honesty field.

**Losses / Gaps:**
- No executable implementations -- cannot reproduce or extend any cited result from this repo alone.
- No empirical comparison across methods -- the reader cannot tell whether prompting-based confidence elicitation outperforms probing-based approaches without reading every cited paper.
- Static snapshot (single commit, no updates). The field moves fast and the survey likely misses 2025 work.
- No license file on disk (badge claims MIT but the repo root has no LICENSE file).

## 5. Design Rationale

The taxonomizers chose the **self-knowledge + self-expression** partition because it maps onto distinct failure modes of deployed LLMs:

- A model with good self-knowledge but poor self-expression **knows it is uncertain but lies anyway** (e.g., overconfidence from RLHF pressure to be helpful).
- A model with good self-expression but poor self-knowledge **faithfully reports wrong answers** (hallucination from lack of awareness).
- Both dimensions must be strengthened for a system to be reliably honest.

This mirrors the "know-that vs know-how" distinction in epistemology. The survey is structured so that a practitioner can quickly identify which quadrant their reliability problem falls into and find the relevant method family.

## 6. Transfer to Lyra

**One transferable idea:** Use **self-knowledge-aware routing as a first-class architectural primitive** in Lyra's agent loop. Instead of treating LLM uncertainty as a post-hoc signal (e.g., thresholding log probabilities), inject a dedicated "epistemic gate" that evaluates the model's calibrated confidence before deciding whether to generate, retrieve, abstain, or escalate. This is the operational analogue of the survey's self-knowledge axis.

Specifically, Lyra could implement a lightweight **confidence calibration layer** that (a) samples multiple responses per query, (b) computes semantic entropy or consistency scores, and (c) routes the query to RAG (low confidence) or direct generation (high confidence) or abstention (near-zero confidence). The survey's "Sampling and Aggregation" and "Predictive Probability" sections provide the algorithmic primitives; the "Calibration" and "Selective Prediction" sections provide the evaluation methodology.

**Workstream route:** Section 4.x -- Router and Orchestration. The epistemic gate is a routing decision (generate vs retrieve vs abstain) that sits naturally in Lyra's router subsystem. The confidence signal itself is a lightweight side-channel.

**Impact:** 7/10 -- addresses the root cause of Lyra hallucination and overconfidence, not just the symptom. Directly improves user trust.

**Effort:** 5/10 -- requires no model retraining. Sampling-based uncertainty estimators (semantic entropy, SelfCheckGPT) are plug-in modules that wrap any LLM backend. The calibration evaluation framework (ECE, AUROC for abstention) is well-established.

**Tier:** Medium -- significant reliability gain with moderate engineering effort, no training pipeline dependency.

**License:** MIT (claimed via badge; no LICENSE file present in repo root).

**Note path:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/SihengLi99__LLM-Honesty-Survey.md`
