---
id: experiment-design
name: Experiment Design
description: Design rigorous ML experiments with proper controls, ablations, and statistical validity.
keywords:
  - experiment
  - ablation
  - baseline
  - hypothesis
  - control
  - statistical
---

1. State the hypothesis clearly and what would falsify it.
2. Establish baselines: simplest reasonable approach, current SOTA, human performance if applicable.
3. Design ablations: remove one component at a time to measure its contribution. This is more important than beating SOTA.
4. Control for confounding variables: same hardware, same random seeds, same data splits.
5. Report variance: run multiple seeds, report mean ± std, use statistical tests (not just "ours is 0.1 better").
6. Document failure modes: when does your method FAIL? This is as important as when it succeeds.
7. Release code, data splits, and hyperparameters for reproducibility.
