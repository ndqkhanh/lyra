---
id: trade-off-analysis
name: Trade-off Analysis
description: Systematic comparison of architectural options with explicit criteria and weights.
keywords:
  - trade-off
  - comparison
  - decision
  - options
  - criteria
  - analysis
---

1. List all viable options (including "do nothing" and "simplest thing that works").
2. Define evaluation criteria: cost, latency, complexity, maintainability, scalability, risk.
3. Weight each criterion by importance (must sum to 1.0).
4. Score each option on each criterion (1-5 scale, be consistent).
5. Calculate weighted scores. The highest score is the recommendation — but the analysis matters more than the number.
6. Identify the decisive trade-off: what is the ONE thing that would change the decision?
7. Document the steelman of the rejected options: what's the strongest case for each, and why it lost?
