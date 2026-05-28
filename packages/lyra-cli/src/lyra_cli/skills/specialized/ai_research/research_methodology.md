---
name: "ai-researcher"
description: AI/ML research expertise covering paper analysis, experiment design, model evaluation, and research methodology. Use when analyzing papers, designing experiments, or evaluating ML models.
tags: ["ai", "research", "machine-learning", "deep-learning", "experiments"]
triggers: ["ai research", "ml research", "paper analysis", "experiment design", "model evaluation"]
model: "opus"
tools: ["Read", "Write", "Edit", "Bash"]
---

# AI Researcher

Research methodology for AI/ML experimentation and paper analysis.

## Core Competencies

### 1. Paper Analysis
- Literature review and synthesis
- Methodology evaluation
- Results interpretation
- Reproducibility assessment
- Citation tracking

### 2. Experiment Design
- Hypothesis formulation
- Baseline selection
- Ablation studies
- Statistical significance testing
- Hyperparameter tuning

### 3. Model Evaluation
- Metrics selection (accuracy, F1, BLEU, etc.)
- Cross-validation strategies
- Error analysis
- Bias and fairness assessment
- Computational efficiency

### 4. Research Communication
- Paper writing (ICLR, NeurIPS, ICML format)
- Visualization and plots
- Reproducibility documentation
- Code and data release

## Paper Analysis Framework

### 1. Quick Scan (5 minutes)
```
- Title and abstract
- Introduction (problem statement)
- Figures and tables
- Conclusion
- Decision: Read in depth or skip?
```

### 2. Deep Read (30-60 minutes)
```
- Problem: What problem does it solve?
- Motivation: Why is this important?
- Method: How does it work?
- Experiments: What did they test?
- Results: What did they find?
- Limitations: What are the weaknesses?
```

### 3. Critical Analysis
```
Questions to ask:
- Is the problem well-motivated?
- Is the method novel or incremental?
- Are baselines appropriate?
- Are results statistically significant?
- Is the evaluation comprehensive?
- Can I reproduce this?
- What are the failure cases?
```

### 4. Synthesis
```
- Key contributions (1-3 bullet points)
- Relation to prior work
- Potential applications
- Future research directions
- Personal notes and ideas
```

## Experiment Design

### Scientific Method
```
1. Observation: Identify a problem or gap
2. Question: Formulate research question
3. Hypothesis: Propose a solution
4. Experiment: Design tests to validate
5. Analysis: Interpret results
6. Conclusion: Accept or reject hypothesis
```

### Hypothesis Example
```
Observation:
  Transformer models struggle with long sequences

Question:
  Can we improve long-range attention efficiency?

Hypothesis:
  Sparse attention patterns reduce complexity
  while maintaining performance

Experiment:
  - Baseline: Full attention O(n²)
  - Proposed: Sparse attention O(n√n)
  - Tasks: Language modeling, document classification
  - Metrics: Perplexity, accuracy, speed, memory

Expected outcome:
  Similar accuracy with 10x speedup
```

### Ablation Studies
```
Purpose: Understand which components matter

Example: Transformer ablations
1. Full model (baseline)
2. Remove positional encoding
3. Remove layer normalization
4. Remove residual connections
5. Reduce number of heads
6. Reduce hidden dimension

Measure impact of each component on performance
```

### Baseline Selection
```
Strong baselines:
- State-of-the-art from recent papers
- Well-tuned standard models
- Simple but effective methods

Weak baselines (avoid):
- Outdated methods
- Poorly tuned models
- Strawman comparisons
```

## Model Evaluation

### Metrics by Task

**Classification**
```
- Accuracy: Correct predictions / Total
- Precision: TP / (TP + FP)
- Recall: TP / (TP + FN)
- F1 Score: 2 * (Precision * Recall) / (Precision + Recall)
- AUC-ROC: Area under ROC curve
```

**Regression**
```
- MSE: Mean Squared Error
- RMSE: Root Mean Squared Error
- MAE: Mean Absolute Error
- R²: Coefficient of determination
```

**Language Generation**
```
- BLEU: N-gram overlap with reference
- ROUGE: Recall-oriented overlap
- METEOR: Semantic similarity
- BERTScore: Contextual embeddings similarity
- Human evaluation: Fluency, coherence, relevance
```

**Image Generation**
```
- FID: Fréchet Inception Distance
- IS: Inception Score
- LPIPS: Learned Perceptual Image Patch Similarity
- Human evaluation: Quality, diversity
```

### Statistical Significance

**T-Test**
```python
from scipy import stats

# Compare two models
model_a_scores = [0.85, 0.87, 0.86, 0.88, 0.84]
model_b_scores = [0.82, 0.83, 0.81, 0.84, 0.82]

t_stat, p_value = stats.ttest_ind(model_a_scores, model_b_scores)

if p_value < 0.05:
    print("Statistically significant difference")
else:
    print("No significant difference")
```

**Bootstrap Confidence Intervals**
```python
import numpy as np

def bootstrap_ci(scores, n_bootstrap=1000, ci=0.95):
    bootstrapped = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(scores, size=len(scores), replace=True)
        bootstrapped.append(np.mean(sample))
    
    lower = np.percentile(bootstrapped, (1 - ci) / 2 * 100)
    upper = np.percentile(bootstrapped, (1 + ci) / 2 * 100)
    return lower, upper

scores = [0.85, 0.87, 0.86, 0.88, 0.84]
lower, upper = bootstrap_ci(scores)
print(f"95% CI: [{lower:.3f}, {upper:.3f}]")
```

### Cross-Validation
```
K-Fold Cross-Validation:
  Split data into K folds
  Train on K-1 folds, test on 1 fold
  Repeat K times
  Average results

Stratified K-Fold:
  Maintain class distribution in each fold

Leave-One-Out:
  K = number of samples
  Expensive but unbiased
```

## Research Workflow

### 1. Literature Review
```
1. Search: Google Scholar, arXiv, Papers with Code
2. Filter: Read abstracts, check citations
3. Organize: Zotero, Mendeley, Notion
4. Synthesize: Identify gaps and opportunities
```

### 2. Idea Generation
```
Sources of ideas:
- Limitations in existing work
- Combining techniques from different domains
- Applying methods to new tasks
- Improving efficiency or scalability
- Addressing fairness or robustness
```

### 3. Prototyping
```
1. Implement baseline (use existing code if possible)
2. Implement proposed method
3. Run small-scale experiments
4. Debug and iterate
5. Scale up if promising
```

### 4. Experimentation
```
1. Define metrics and evaluation protocol
2. Run baseline experiments
3. Run proposed method experiments
4. Ablation studies
5. Error analysis
6. Statistical significance testing
```

### 5. Writing
```
1. Introduction: Problem, motivation, contributions
2. Related Work: Prior work, differences
3. Method: Detailed description, diagrams
4. Experiments: Setup, results, analysis
5. Conclusion: Summary, limitations, future work
```

## Reproducibility Checklist

```
Code:
- [ ] Code released (GitHub)
- [ ] Dependencies listed (requirements.txt)
- [ ] Random seeds fixed
- [ ] Training scripts provided
- [ ] Evaluation scripts provided

Data:
- [ ] Dataset described
- [ ] Data splits specified
- [ ] Preprocessing steps documented
- [ ] Data released (if possible)

Model:
- [ ] Architecture details
- [ ] Hyperparameters listed
- [ ] Training procedure described
- [ ] Pretrained models released

Experiments:
- [ ] Hardware specifications
- [ ] Training time reported
- [ ] Number of runs specified
- [ ] Confidence intervals provided
```

## Common Pitfalls

### Data Leakage
```
Problem: Test data influences training
Examples:
- Normalizing before train/test split
- Using future information in time series
- Duplicate samples across splits

Solution:
- Split data first, then preprocess
- Use proper cross-validation
- Check for duplicates
```

### Cherry-Picking Results
```
Problem: Reporting only favorable results
Examples:
- Running many experiments, reporting best
- Tuning on test set
- Selective metric reporting

Solution:
- Preregister experiments
- Report all results
- Use validation set for tuning
```

### Weak Baselines
```
Problem: Comparing against poorly tuned baselines
Examples:
- Using default hyperparameters
- Outdated methods
- Unfair comparison (different data, compute)

Solution:
- Tune baselines properly
- Use recent strong baselines
- Ensure fair comparison
```

## Tools & Resources

### Paper Discovery
- **arXiv**: Preprints (cs.AI, cs.LG, cs.CL)
- **Papers with Code**: Papers + code + benchmarks
- **Google Scholar**: Citation tracking
- **Semantic Scholar**: AI-powered search

### Experiment Tracking
- **Weights & Biases**: Experiment tracking, visualization
- **MLflow**: Model tracking, registry
- **TensorBoard**: Training visualization
- **Neptune**: Experiment management

### Visualization
```python
import matplotlib.pyplot as plt
import seaborn as sns

# Training curves
plt.plot(epochs, train_loss, label='Train')
plt.plot(epochs, val_loss, label='Validation')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.savefig('training_curve.png', dpi=300)

# Confusion matrix
sns.heatmap(confusion_matrix, annot=True, fmt='d')
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.savefig('confusion_matrix.png', dpi=300)
```

## Quick Commands

```bash
# Search papers
arxiv-search "attention mechanism"

# Download paper
arxiv-download 2106.09685

# Track experiments
wandb login
wandb init
wandb log {"loss": 0.5, "accuracy": 0.85}

# Hyperparameter tuning
python train.py --lr 0.001 --batch_size 32
python train.py --lr 0.0001 --batch_size 64

# Evaluate model
python evaluate.py --model checkpoint.pt --data test.json
```

## When to Escalate

- Large-scale experiments → Use distributed training (DeepSpeed, FSDP)
- Hyperparameter optimization → Use Optuna or Ray Tune
- Model interpretability → Use SHAP or LIME
- Fairness evaluation → Use Fairlearn or AI Fairness 360
- Deployment → Consider model compression, quantization, distillation
