# AlphaEvolve Quick Reference for Lyra

**Last Updated**: 2026-05-26

## Core Concept

**Evolve search algorithms, not solutions directly.**

Instead of evolving constructions → Evolve programs that search for constructions.

## Key Innovations

1. **Heuristic Search Program Evolution** - Meta-level optimization
2. **LLM-Guided Mutations** - Intelligent code variations using Gemini
3. **Full-Codebase Evolution** - Multiple files, multiple languages
4. **Multi-Objective Optimization** - Balance competing objectives
5. **Meta-Prompt Evolution** - Automatically improve prompts
6. **Production Deployment** - Real-world impact at Google scale

## Impact Metrics

- **23% speedup** - Gemini kernel operations
- **0.7% recovery** - Google fleet-wide compute resources
- **32% speedup** - XLA-generated IR optimization
- **SOTA results** - 52+ mathematical construction problems

## Critical Components (from Ablations)

1. ✅ **Evolutionary approach** - Most critical, massive drop without it
2. ✅ **Context in prompts** - Highly important, significant degradation
3. ✅ **Meta prompts** - Important for complex tasks
4. ✅ **Full-file evolution** - Enables system-level optimization
5. ✅ **Model mixture** - Critical for diversity

## Lyra Applications (Priority Order)

### Priority 1: Agent Prompt Evolution
Evolve agent system prompts for better performance.

```python
from lyra_cli.evolution import PromptEvolutionEngine

engine = PromptEvolutionEngine(base_prompt, evaluation_tasks)
best_prompt = engine.evolve(num_generations=10)
```

### Priority 2: Workflow Heuristic Evolution
Evolve task allocation and coordination strategies.

```python
from lyra_cli.evolution import WorkflowHeuristicEvolution

workflow_evolver = WorkflowHeuristicEvolution()
best_allocator = workflow_evolver.evolve_task_allocator(historical_data)
```

### Priority 3: Multi-Objective Agent Optimization
Optimize for quality, speed, cost, reliability simultaneously.

```python
from lyra_cli.evolution import MultiObjectiveAgentOptimizer

optimizer = MultiObjectiveAgentOptimizer()
score, breakdown = optimizer.evaluate_agent_config(config, test_tasks)
```

## Implementation Roadmap

**Phase 1: Offline Evolution (Weeks 1-2)**
- Collect historical task data
- Run prompt evolution experiments
- Validate on held-out test set
- A/B test evolved vs. baseline

**Phase 2: Workflow Evolution (Weeks 3-4)**
- Evolve task allocation heuristics
- Evolve coordination strategies
- Deploy best performers

**Phase 3: Continuous Evolution (Ongoing)**
- Automated evolution pipeline
- Periodic re-evolution
- Performance monitoring

## Key Lessons

1. **Evolution > Single-Shot** - Iterative refinement beats one-shot generation
2. **Context Matters** - Rich problem descriptions improve results significantly
3. **Diversity is Strength** - Mix small + large models for best results
4. **Verify Everything** - Automated testing prevents hallucinations
5. **Meta-Level Wins** - Evolve strategies, not just solutions

## Quick Wins for Lyra

1. **Evolve agent prompts** - Immediate impact, low risk
2. **Evolve context compression** - Reduce token usage
3. **Evolve task allocation** - Better agent utilization
4. **Evolve error recovery** - Improved reliability
5. **Evolve coordination** - Better multi-agent workflows

## Comparison with Alternatives

| Approach | Scope | Optimization | Deployment |
|----------|-------|--------------|------------|
| **AlphaEvolve** | Full codebase | Multi-objective | Production-ready |
| FunSearch | Single function | Single objective | Research |
| Traditional GP | Limited | Predefined ops | Difficult |
| Manual tuning | Ad-hoc | Trial-and-error | Slow |

## Success Metrics

Track these to measure evolution effectiveness:

- **Quality**: Task completion accuracy
- **Speed**: Time to completion
- **Cost**: Token usage per task
- **Reliability**: Success rate across tasks
- **Generalization**: Performance on unseen tasks

## Anti-Patterns to Avoid

❌ **Don't**: Evolve without verification  
✅ **Do**: Automated testing for every variant

❌ **Don't**: Use only large models  
✅ **Do**: Mix small (diversity) + large (quality)

❌ **Don't**: Ignore context  
✅ **Do**: Provide rich problem descriptions

❌ **Don't**: Single-objective optimization  
✅ **Do**: Balance multiple objectives

❌ **Don't**: Evolve solutions directly  
✅ **Do**: Evolve search algorithms

## Next Steps

1. Read full analysis: `alphaevolve-analysis.md`
2. Implement prompt evolution prototype
3. Collect baseline performance data
4. Run evolution experiments
5. Measure improvement vs. baseline
6. Deploy best-performing variants

---

**See Also**: 
- Full analysis: `alphaevolve-analysis.md`
- Original paper: DeepMind AlphaEvolve (2025)
- Related: FunSearch, genetic programming literature
