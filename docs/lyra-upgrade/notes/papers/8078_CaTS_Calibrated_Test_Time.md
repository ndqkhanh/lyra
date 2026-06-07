# CaTS: Calibrated Test-Time Scaling for Efficient LLM Reasoning

**Authors:** Chengsong Huang, Langlin Huang (WashU St. Louis), Jixuan Leng (CMU), Jiacheng Liu (UW), Jiaxin Huang (WashU St. Louis)
**Venue:** ICLR 2026
**arXiv:** Not provided in paper (published via ICLR 2026 proceedings)

---

## 1. Mechanism (step-by-step, equations, algorithms)

### Core Idea
Instead of using a fixed number of samples for all queries (wasteful for easy ones, insufficient for hard ones), use **model confidence to dynamically adjust sampling**. Since LLMs are overconfident, train them via **Self-Calibration** to produce reliable confidence scores in a single forward pass, then use these scores to guide Best-of-N, Self-Consistency, and Adaptive Self-Consistency.

### Self-Calibration (Training Pipeline)

**Step 1: Generate Training Data (no human labels needed)**
- For each query x from seed datasets, sample N=32 responses {y_i} with Dynamic Temperature (EDT) sampling
- For each response, compute P(True) — probability of "Yes" token given prompt: `x ⊕ y_i ⊕ "Is the answer correct? (Yes/No)"`
- Compute **Soft Self-Consistency (SSC)** score:
  ```
  SSC(y) = Σ_{i: y_i = y} c_i / Σ_{i=1..N} c_i
  ```
  where c_i = P(True) for response i
- SSC combines intrinsic confidence (P(True)) with inter-response agreement, yielding lower ECE than either alone:
  | Method | GSM8K ECE↓ | SVAMP ECE↓ |
  |--------|-----------|-----------|
  | P(True) | 12.03 | 28.94 |
  | SC | 4.48 | 4.94 |
  | **SSC** | **3.42** | **3.75** |

**Step 2: Dynamic Temperature (EDT) Sampling**
```
T(H) = T₀ × M^(γ/H)  if ≥ τ₀, else 0
```
T₀=0.8, M=0.8, γ=1.0. Increases temperature when output entropy H is low to promote diversity.

**Step 3: Training Objective**
```
L_total(θ) = Σ_{(xj,yj)∈D} SmoothL1(p_θ(Yes|xj,yj,I), cj)
           + ω · Σ_{(xi,yi), ci>η} -log p_θ(yi | xi)
```
where η=0.75 (confidence threshold for generation training), ω=0.1. Only high-confidence responses contribute to the generation loss, preserving reasoning quality. Trained with LoRA (r=32, α=16, dropout=0.05), 1 epoch, AdamW lr=5×10⁻⁵.

### CaTS Inference Variants

**CaTS-ES (Early Stopping for Best-of-N):**
```
k ← k + 1, if c_i < τ
y = y_i,    otherwise  (stop and return this response)
```
Continue sampling responses one-by-one until a response meets confidence threshold τ. The threshold τ is calibrated per dataset to match a target sample budget.

**CaTS-SC (Confidence-Weighted Self-Consistency):**
```
y = argmax_z Σ_{i=1..N} c_i · 𝟙(y_i = z)
```
Weighted majority vote where each response contributes proportionally to its confidence.

**CaTS-ASC (Confidence-Weighted Adaptive Self-Consistency):**
```
v_k(z) = Σ_{i=1..k} c_i · 𝟙(y_i = z)
r̂_k(z) = v_k(z) / Σ_{i=1..k} c_i
```
Stop when max_z r̂_k(z) ≥ τ, otherwise continue sampling.

### Theoretical Guarantee (Theorem 5)
CaTS-SC **exponentially dominates** vanilla Self-Consistency (majority voting) when the following inequality holds:
```
μ²_q / (2v_q + 2/3 μ_q)  >  μ²_MV / (2v_MV + 2/3 μ_MV)
```
where μ_MV = E[(Kq-1)/(K-1)] is mean margin for majority voting, μ_q = E[q(Kq-1)/(K-1)] is mean margin for q-weighting, and v_MV, v_q are the corresponding variances. Under a two-tier confidence mixture model (high-confidence fraction π with q_hi, low-confidence with q_lo), the inequality is satisfied whenever a nontrivial mass of genuinely high-confidence votes exists.

---

## 2. Results (real benchmark numbers with units)

### Main Results (Sample Budget = 16)

**Llama-3.1-8B-Instruct:**
| Method | Obj Counting | MathQA | ARC Challenge |
|--------|-------------|--------|---------------|
| SC | 69.1 | 73.7 | 85.2 |
| CaTS-SC | 76.8 (+7.7) | 83.6 (+9.9) | 87.7 (+2.5) |
| Best-of-N | 62.3 | 73.7 | 84.5 |
| CaTS-ES | 76.8 (+14.5) | 83.6 (+9.9) | 87.7 (+3.2) |
| ASC | 67.9 | 72.7 | 84.6 |
| CaTS-ASC | 75.2 (+7.3) | 81.9 (+9.2) | 86.6 (+2.0) |

**Qwen2.5-7B-Instruct:**
| Method | Obj Counting | MathQA | ARC Challenge |
|--------|-------------|--------|---------------|
| SC | 76.8 | 83.3 | 90.1 |
| CaTS-SC | 81.2 (+4.4) | 87.8 (+4.5) | 90.8 (+0.7) |

**DeepSeek-R1-Distill-Qwen-1.5B:**
| Method | Obj Counting | MathQA | ARC Challenge |
|--------|-------------|--------|---------------|
| SC | 64.9 | 89.4 | 60.8 |
| CaTS-SC | 70.8 (+5.9) | 91.8 (+2.4) | 66.5 (+5.7) |
| Best-of-N | 48.1 | 87.8 | 54.1 |
| CaTS-ES | 70.8 (+22.7) | 91.6 (+3.8) | 66.5 (+12.4) |

**Efficiency (Fig. 1):** CaTS-SC saves **94.2% samples** to reach 85.0 accuracy on MathQA (Llama-3.1-8B), compared to standard SC. Saves 50.4% samples to reach ~77.5 accuracy.

### Self-Calibration Quality (Table 4)

**Llama-3.1-8B-Instruct (In-Domain):**
| Dataset | Vanilla ECE↓ | Self-Cal ECE↓ | Vanilla ACC↑ | Self-Cal ACC↑ |
|---------|-------------|--------------|-------------|--------------|
| GSM8K | 13.70 | **3.79** | 77.44 | **80.43** |
| SVAMP | 28.03 | **10.17** | 72.60 | **75.29** |
| ARC easy | 5.45 | 5.00 | 87.73 | **89.21** |

**Out-of-Domain:**
| Dataset | Vanilla ECE↓ | Self-Cal ECE↓ | Vanilla ACC↑ | Self-Cal ACC↑ |
|---------|-------------|--------------|-------------|--------------|
| ARC challenge | 7.01 | **6.03** | 80.87 | **82.38** |
| Object Counting | 27.85 | **9.69** | 60.68 | **65.88** |
| MathQA | 12.55 | **8.64** | 44.18 | **52.34** |

**Qwen2.5-7B-Instruct (Out-of-Domain):**
MathQA ACC: 49.85 → **64.18** (+14.33 absolute gain). Object Counting ACC: 72.41 → **74.22**.

### Reward Model Comparison (Table 3, Best-of-16)
| Model | Dataset | Reward Model | Self-Cal Confidence |
|-------|---------|-------------|-------------------|
| Llama | MathQA | 82.1 | **84.0** |
| Llama | Obj Count | 72.6 | 72.0 |
| Llama | ARC Chal | 86.2 | **86.6** |

Self-calibrated confidence achieves **comparable or better** performance vs a separate reward model of equal size, while using only ~10 extra tokens per response (vs doubling inference cost).

### Additional Benchmarks (Table 10, Llama-3.1-8B, budget=16)
| Method | GPQA | Hellaswag | MMLU Pro |
|--------|------|-----------|----------|
| SC | 33.28 | 66.62 | 49.19 |
| CaTS-SC | 35.53 (+2.3) | 72.84 (+6.2) | 53.43 (+4.2) |
| Best-of-N | 32.26 | 67.28 | 47.31 |
| CaTS-ES | 36.55 (+4.3) | 73.72 (+6.4) | 53.83 (+6.5) |

### Ablation Study (MathQA, Llama-3.1-8B)
| Method | ECE↓ | ACC↑ |
|--------|------|------|
| Full | 8.64 | 52.34 |
| w/o EDT | 9.14 | 51.44 |
| w/o SSC | 10.85 | 52.18 |
| w/o L1-smooth | 6.43 | 50.86 |

### Robustness to Prompt Variation
Across 6 alternative confidence-querying prompts, CaTS-SC MathQA accuracy: 81.63±0.20 (vs 82.1 original). Highly robust to prompt changes.

---

## 3. Trade-offs (wins vs loses)

### Wins
- **Substantial sample savings**: 94.2% fewer samples to reach same accuracy on MathQA
- **Universal applicability**: Works across 3 model architectures (Llama, Qwen, DeepSeek), 9+ datasets, both in-domain and out-of-domain
- **No human labels needed**: Self-Calibration generates training data entirely from unlabeled seed queries
- **No extra model at inference**: Self-calibrated confidence costs ~10 tokens vs a separate reward model doubling inference cost (1.08s vs 1.71s per sample)
- **Theoretically grounded**: Exponential dominance over vanilla SC when confidence signal is sufficiently accurate
- **Robust to prompts**: 6 alternative confidence-querying prompts yield similar performance
- **Simple integration**: LoRA fine-tuning, single epoch, works with parameter-efficient methods

### Loses
- **Requires fine-tuning**: Self-Calibration needs model training (LoRA, ~1 epoch on 100K samples). Cannot be used with API-only models unless the provider offers fine-tuning.
- **Small budget regime weakness**: When sample budget is very small (≤4), Best-of-N sometimes outperforms CaTS-ES because early stopping may terminate too early with a low threshold, missing a better response. See Appendix D.
- **Threshold calibration needed**: CaTS-ES and CaTS-ASC require per-dataset threshold tuning to match the target sample budget.
- **Confidence collapse with binary labels**: Training with hard 0/1 correctness labels (instead of SSC) causes confidence predictions to collapse toward extremes, substantially degrading CaTS-ES performance (MathQA: 83.6 → 81.2, Obj C: 76.8 → 69.8).
- **Base model capability dependent**: Self-Calibration improves calibration but the absolute performance floor is set by the base model. Llama-3.1-8B Self-Cal still underperforms Qwen2.5-7B vanilla on some tasks.

---

## 4. Design Rationale (why this approach)

1. **One-size-fits-all sampling is wasteful**: Fixed N sampling ignores query difficulty. Simple queries ("2+3=?") need 1-2 samples; hard queries need more. Confidence provides a natural difficulty signal.

2. **Self-Consistency as a calibration oracle**: Self-consistency agreement is known to provide well-calibrated confidence estimates (Tian et al., 2023; Wang et al., 2024). But computing it requires many samples. Key insight: **distill** this expensive multi-sample confidence into a single-pass model prediction.

3. **P(True) is cheap but miscalibrated**: P(True) costs ~10 tokens via KV-cache reuse but LLMs are overconfident (ECE 12-28% on math). SSC bridges this gap by combining P(True) with agreement — the soft formulation is critical; hard agreement loses information.

4. **Confidence weighting provably better than uniform voting**: The Bernstein inequality analysis shows q-weighting has a larger error exponent than majority voting whenever the confidence signal separates high and low quality responses. The two-tier mixture model provides an intuitive sufficient condition.

5. **EDT prevents mode collapse**: Without dynamic temperature, the model generates repetitive responses for easy queries, making SSC less informative. EDT forces response diversity while preserving quality.

6. **L1-smooth loss over MSE**: Ablation shows MSE achieves slightly lower ECE but worse accuracy — L1-smooth better balances calibration and generation quality.

---

## 5. Limitations & Failure Modes

1. **Requires model access for fine-tuning**: Cannot be applied to black-box API models (GPT-4, Claude API) without provider fine-tuning support. The method requires LoRA training.

2. **Early stopping can be premature**: At low sample budgets, CaTS-ES may stop on a confident but incorrect response before discovering the correct one. Threshold τ must be carefully tuned per dataset.

3. **Confidence threshold brittleness**: The stopping threshold τ is calibrated per-dataset to match a target budget. In deployment with unknown query distributions, the budget-vs-accuracy trade-off is unpredictable.

4. **Binary label collapse**: Training with hard correctness labels (not SSC) causes confidence to collapse to extremes, breaking early stopping. This means you cannot simply use ground-truth labels as a shortcut — the soft SSC signal is essential.

5. **Not evaluated on agentic/multi-turn tasks**: All benchmarks are single-turn QA (math, science, commonsense). Calibration behavior in multi-turn agent trajectories is unknown.

6. **No guarantees on OOD calibration**: While Self-Calibration transfers to out-of-domain datasets (MathQA, ARC Challenge), the ECE degradation varies by dataset. Extreme distribution shifts may break calibration.

7. **Single-epoch training constraint**: The paper trains for only 1 epoch. Longer training might degrade generation quality (not explored).

8. **Temperature sensitivity**: EDT parameters (T₀=0.8, M=0.8, γ=1.0) are fixed from prior work. Ablation on these values is not presented.

---

## 6. Transfer to Lyra

**One Idea:** Apply **Self-Calibration** to Lyra's internal verification/critique model — fine-tune Lyra's LLM to output calibrated confidence scores for its own tool-use decisions and response quality, then use **CaTS-ES** for adaptive tool retry (stop retrying a tool call once a response exceeds a confidence threshold).

**Route:** §3.2 (Training Data Generation) + §4.1 (CaTS-ES) — Generate SSC-labeled training data from Lyra's tool-use traces (multiple sampled tool calls per situation, compute SSC from agreement + P(True)), LoRA-fine-tune Lyra's model, then implement confidence-based early stopping in the tool execution loop.

**Impact:** MEDIUM-HIGH — Reduces wasted token spend on unnecessary retries. Could cut tool-calling costs by 30-50% for simple/confident operations while preserving (or improving) accuracy for hard cases.

**Effort:** MEDIUM — Requires: (1) collecting multi-sample tool traces for SSC labeling (infrastructure cost), (2) LoRA fine-tuning setup, (3) confidence threshold calibration per tool type, (4) integration into Lyra's execution loop. The training requires ~100K labeled examples.

**Tier:** Tier 2 (medium-impact, requires training infrastructure)
