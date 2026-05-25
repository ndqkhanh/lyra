---
name: model-evaluation
description: Systematic evaluation methodology for machine learning models including benchmarks and fairness
origin: "Plan 13"
tags: [ML, evaluation, benchmark, metrics, fairness]
triggers: [evaluate, benchmark, metric, accuracy, fairness, ablation]
---

# Model Evaluation

## Benchmark Design Principles

- **Representativeness**: Dataset covers real-world distribution and edge cases
- **Contamination prevention**: Hold out test data from all training pipelines; monitor for leakage
- **Standardization**: Fixed train/val/test splits, evaluation harness, and scoring protocol

## Metric Selection

- **Classification**: Precision, recall, F1, ROC-AUC, PR-AUC, Matthews correlation coefficient
- **Generation**: BLEU (n-gram overlap), ROUGE (recall-oriented summary quality), BERTScore (semantic similarity)
- **Human evaluation**: Likert-scale ratings, pairwise preference, Best-Worst Scaling

## Ablation Study Design

Remove or disable one component at a time while holding everything else fixed. Report delta on primary metrics. Document cumulative vs. isolated effects when components interact.

## Fairness Auditing

- **Demographic parity**: Equal positive prediction rate across groups
- **Equal opportunity**: Equal true positive rate across groups
- **Disparate impact**: Ratio of favorable outcomes between groups (< 0.8 flags concern)
- Audit across multiple thresholds, not just the decision boundary

## Statistical Significance for Model Comparison

- **Bootstrap**: Resample with replacement from test set; compute confidence intervals on metric differences
- **Permutation test**: Shuffle model labels; compare observed score difference to null distribution
- Report both point estimates and uncertainty intervals for all comparisons

## Evaluation-Driven Development Loop

1. Establish baseline metric on fixed test set
2. Train candidate model variant
3. Evaluate on held-out validation set
4. Compare to baseline with statistical test
5. Promote only if improvement exceeds significance threshold and practical significance bar
