# OpenAI — Harness Engineering (Feb 2026)

> **Source:** https://openai.com/index/harness-engineering/
> **Type:** Blog post / industry position paper
> **Deep-read:** 2026-06-07

## Key Claims

- 1 million lines of production code with zero human-written lines
- The harness IS the product — constraints, feedback loops, evaluation, context management, methodology
- "Harness engineering is the most important engineering discipline of 2026"
- Agents accelerate broken practices — fix foundations first (CI/CD, IaC, observability, security scanning)
- Context engineering: 400-line prompt → 15 lines, 12 tools → 3 primitives improved pass rate from 83% → 92%

## What Lyra Takes

This post is the canonical industry validation of Lyra's core thesis: the harness (constraints, feedback loops, evaluation, context management, methodology) matters more than the model. Every module in Lyra is a harness component — the memory tier gates what the agent remembers, the safety pipeline gates what tools it can call, the adversarial panel verifies what it produces, and the hook system enforces all of it. OpenAI's post confirms that the largest AI lab arrives at the same conclusion Lyra's architecture embodies: invest in harness quality first; model upgrades provide diminishing returns without it.

## Related Workstreams

- §4.26 Harness Engineering
- §4.3 Context Engineering
- §4.16 Reliability
- §4.17 Safety
