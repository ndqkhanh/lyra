---
name: experiment-design
description: Rigorous experimental design for hypothesis testing and causal inference
origin: "Plan 13"
tags: [experiment, hypothesis, ab-testing, statistics]
triggers: [experiment, hypothesis, A/B test, statistical, clinical trial]
---

# Experiment Design

## Hypothesis Formulation

- **Null (H0)**: No effect or difference exists between conditions
- **Alternative (H1)**: A specific effect or difference is present (directional or non-directional)
- **Success criteria**: Pre-specified minimum detectable effect size and primary endpoint

## Experiment Types

- **A/B test**: Two-condition randomized comparison
- **Factorial design**: Multiple independent variables crossed to detect interactions
- **Interrupted time-series**: Multiple pre/post measurements around a treatment onset

## Sample Size Calculation

- **Power analysis**: Compute N given desired power (typically 0.80), alpha (0.05), and expected effect size
- **Minimum Detectable Effect (MDE)**: Smallest effect the design can reliably detect at given N
- Adjust for multiple arms, clustering, and expected attrition rate

## Randomization Strategies

- Simple random assignment, blocked randomization, stratified randomization
- Cluster randomization when individual-level assignment is infeasible
- Minimization for small-sample balance across known covariates

## Statistical Tests

- **t-test**: Two-group continuous outcome comparison
- **Chi-square**: Categorical outcome association test
- **ANOVA**: Multi-group mean comparison (with post-hoc Tukey HSD)
- **Mann-Whitney**: Non-parametric alternative for skewed distributions

## Multiple Comparisons Correction

- **Bonferroni**: Most conservative; divide alpha by number of comparisons
- **FDR (Benjamini-Hochberg)**: Controls false discovery rate; less conservative
- Pre-register primary vs. secondary endpoints to minimize correction burden

## Result Interpretation Guide

- Report effect size with confidence intervals, not p-values alone
- Distinguish statistical significance from practical significance
- Perform sensitivity analysis for robustness to analytic choices
