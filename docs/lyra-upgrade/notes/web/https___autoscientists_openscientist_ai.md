# AutoScientists: Self-Organizing Agent Teams for Long-Running Scientific Experimentation (arXiv 2605.28655 / Harvard Zitnik Lab)

## Source
- **Authors:** Shanghua Gao, Ada Fang, Marinka Zitnik (Harvard Medical School, Kempner Institute, Broad Institute)
- **Paper:** https://arxiv.org/pdf/2605.28655
- **Code:** https://github.com/mims-harvard/AutoScientists
- **Page:** https://autoscientists.openscientist.ai

## Key Technical Claims

1. **Decentralized multi-agent system** for long-running computational science experiments -- no central orchestrator. Agents self-organize into teams around research directions by reading/writing a shared experimental state `S`.

2. **BioML-Bench (24 tasks):** Mean leaderboard percentile 74.40% vs. prior best biomedical agent 66.07% (+8.33 pp). Largest domain gain in drug discovery (64.52% vs. 46.16%).

3. **GPT nanochat training optimization:** Reaches target validation bits-per-byte 1.9x faster than prior auto-research baseline (34 experiments vs. 65). When starting from AutoScientists champion (val_bpb=0.9777), discovers 7 accepted improvements reaching 0.9730 while single-agent finds zero in 100 experiments.

4. **ProteinGym (217 DMS assays):** Discovers recipe on single development assay (ACE2-Spike binding) improving Spearman rho from 0.747 to 0.840 (+12.5% relative). Frozen recipe transfers across all 217 assays: mean Spearman rho 0.657 -> 0.700 (+6.5% relative).

## Architecture/Mechanism Details

### Shared State S
Every agent follows the same heartbeat: read `S`, act, write back. `S` contains:
- Current champion `p*` (best hypothesis/checkpoint so far)
- Experiment log `L` (all historical experiments with results)
- Structured discussion forum `F` (categories: DISCUSSION, QUEUED, RUNNING, KEEP, REJECT)
- Per-team queues `Qk`
- Per-team dead-end registries `Dk` (cross-team readable -- critical for avoiding repeated dead ends)

### Agent Types
1. **Analyst agents (x3):** Read `L` and `F`, rank proposals by effect size, write to `Qk`, own hypothesis documents and dead-end registry.
2. **Experiment agents:** Claim from `Qk`, apply the diff to `p*`, train, record results to `L` and `F`. Includes "noise-gated second-seed confirmation."

### Team Formation
- Teams form dynamically via agent interaction (not user-specified decomposition).
- Two-phase alternation: Discussion (agents form teams around research directions) then Execution (teams run experiments in parallel).
- When a team stagnates, agents trigger re-discussion and may reorganize.
- Each team runs a continuous propose-execute loop on the shared state.

### Ablation Study (Four Components Removed)
| Config | TDC-hERG | Human Plasma | Cell-Cell | GPT nanochat |
|--------|----------|--------------|-----------|-------------|
| Full | 0.867 | 0.8729 | 0.924 | 0.9777 |
| no analyst | 0.738 | 0.8051 | 0.812 | 0.9815 |
| no cross-agent feedback | 0.804 | 0.7144 | 0.781 | 0.9806 |
| no self-organization | 0.821 | 0.8312 | 0.706 | 0.9833 |
| independent agents | 0.692 | 0.6810 | 0.435 | 0.9851 |

Each ablation's worst hit lands on a different task, confirming the four mechanisms address complementary failure modes.

## Numbers & Benchmarks

- **BioML-Bench:** 24 tasks across 4 domains (biomedical imaging 4, drug discovery 9, protein engineering 6, single-cell omics 5). Metric: leaderboard percentile vs. public human submissions.
- **GPT nanochat:** Single experiment = 5 min training on 1 H100 GPU. Metric: validation bits-per-byte (lower better). Baseline 0.998 -> champion 0.9777 -> 7 improvements to 0.9730.
- **ProteinGym:** 217 DMS assays. Development on single ACE2-Spike assay. Discovered recipe: three-GP ensemble combining Kermut's structure-kernel with expanded zero-shot features, greedy diversity-based feature selection, quantile-warped targets.
- **Second-seed confirmation:** Noise-gated verification prevents spurious results from a single lucky seed.

## Transfer to Lyra

### The ONE idea: Decentralized shared-state with cross-team dead-end registry

Lyra currently uses a centralized supervisor/orchestrator pattern: a main loop dispatches to sub-agents and aggregates results. The AutoScientists idea most transferable to Lyra is the **shared dead-end registry `Dk` that is cross-team readable** combined with the **discussion phase / forum `F` with structured categories (DISCUSSION, QUEUED, RUNNING, KEEP, REJECT)**.

This directly addresses a problem Lyra faces: when a research or experimentation route fails, that information is siloed in the sub-agent that ran it. Another agent may independently waste resources retrying the same dead end. A shared, structured forum with dead-end tracking would let Lyra's agents collaboratively prune the search space.

### Workstream Route: §4.2 (Research Planning & Experimental Loop)

The natural place to integrate this is §4.2 (Experimental loop and automated hypothesis testing). The forum mechanism maps onto Lyra's need to track which research directions are active, which have been exhausted, and which showed promise. The dead-end registry is a lightweight addition to Lyra's shared context/memory that could yield significant efficiency gains in multi-agent research workflows.
