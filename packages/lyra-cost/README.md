# Lyra Cost Tracking & Optimization

Phase 0 of the Lyra AGI V4 Ultra Plan. Implements the Economics layer (Section 16) — cost tracking and optimization infrastructure.

## Architecture

### 4-Tier Model Hierarchy
| Tier   | Models                           | Cost/M tokens       | Use Case                    |
|--------|----------------------------------|---------------------|-----------------------------|
| Tier 0 | Local SLM                        | $0                  | Classification, routing     |
| Tier 1 | Haiku/Flash/DeepSeek             | $0.28-$5            | Simple tasks, high-volume   |
| Tier 2 | Sonnet 4/GPT-4o                  | $3-$15              | Daily coding, analysis      |
| Tier 3 | Opus 4/DeepSeek-V4-Pro           | $5-$25              | Architecture, hard reasoning |

### Cost Reduction Stack
- Prompt caching: 90% discount on cache reads
- Semantic caching: 30-70% savings on similar queries
- Prompt compression: 50-70% token reduction
- Combined target: 80% lower cost per task

### Safety Controls
- $5/session circuit breaker
- Per-task call limits
- Loop detection (3 consecutive 1/5 quality scores blocks task)
- Budget-aware degradation (downgrade model tier as spend increases)

## Usage

```python
from lyra_cost import CostTracker, PromptCache, CircuitBreaker, CostOptimizer

tracker = CostTracker(session_id="session-1")
tracker.record_call(model="sonnet-4", input_tokens=500, output_tokens=200)
tracker.record_success(task_id="task-1")
cost_per_task = tracker.cost_per_successful_task
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
