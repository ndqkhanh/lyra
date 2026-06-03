> ⚠️ **Redirect:** The canonical model-router architecture document is [09-model-router.md](09-model-router.md). This file is kept for reference.

# Model Router V3: RL-Optimized Intelligent Routing

**Version:** 3.0.0
**Date:** 2026-05-30
**Status:** Implementation Design - Ready
**Based on:** NeuralUCB, 15+ contextual bandit papers, Phase 3 Research

---

## Executive Summary

Model Router V3 uses NeuralUCB contextual bandit algorithms to achieve 84% cost reduction while maintaining or improving quality. It learns task-specific model preferences through online reinforcement learning and optimizes the cost-quality Pareto frontier.

### Key Performance Targets

| Metric | V2 (Current) | V3 (Target) | Improvement |
|--------|-------------|-------------|-------------|
| Cost Reduction | Baseline | 70-84% | 84% savings |
| Quality | Baseline | +10-15% | 10-15% better |
| Routing Latency | ~50ms | <10ms | 5x faster |
| Routing Accuracy | ~80% | 95%+ | +15pp |
| Cold Start | Manual config | Auto-learned | Zero-config |

---

## I. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      MODEL ROUTER V3                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. CONTEXT EXTRACTOR                                      │   │
│  │ Task type | Complexity | History | User preferences        │   │
│  │ Token budget | Latency req | Domain | Language             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. NeuralUCB ROUTER                                       │   │
│  │ Neural network predicts reward for each (context, model)   │   │
│  │ UCB exploration bonus: σ(x) * sqrt(log(t)/n)              │   │
│  │ Pareto optimization over cost, quality, latency             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. MODEL REGISTRY                                         │   │
│  │ Capability profiles | Cost tables | Latency stats          │   │
│  │ Health status | Rate limits | Provider availability        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. FEEDBACK COLLECTOR                                     │   │
│  │ Quality scores | Task success | Latency | Token usage      │   │
│  │ User ratings | Error rates | Regret calculation            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 5. ONLINE LEARNER                                         │   │
│  │ Update neural network weights from feedback               │   │
│  │ Adapt to distribution shift                               │   │
│  │ Periodic retraining from replay buffer                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## II. Core Components

### 2.1 NeuralUCB Contextual Bandit

```python
class NeuralUCB:
    """Neural network + UCB exploration for model routing."""
    
    def __init__(self, input_dim: int, hidden_dim: int = 128):
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        self.optimizer = torch.optim.Adam(self.network.parameters())
        self.model_counts: dict[str, int] = defaultdict(int)
        self.total_rounds: int = 0
    
    def select_model(
        self, context: ContextVector, candidates: list[str]
    ) -> tuple[str, float, dict]:
        """Select best model using NeuralUCB."""
        scores = {}
        for model_id in candidates:
            # Neural network prediction
            x = torch.cat([context.tensor, self._model_embedding(model_id)])
            predicted_reward = self.network(x).item()
            
            # UCB exploration bonus
            n = self.model_counts[model_id] + 1
            exploration_bonus = 0.1 * np.sqrt(np.log(self.total_rounds + 1) / n)
            
            scores[model_id] = predicted_reward + exploration_bonus
        
        best_model = max(scores, key=scores.get)
        self.model_counts[best_model] += 1
        self.total_rounds += 1
        
        return best_model, scores[best_model], {
            'predicted_rewards': {
                m: self.network(
                    torch.cat([context.tensor, self._model_embedding(m)])
                ).item()
                for m in candidates
            },
            'exploration_bonuses': {
                m: 0.1 * np.sqrt(
                    np.log(self.total_rounds) / (self.model_counts[m] + 1)
                )
                for m in candidates
            },
            'confidence': self._confidence_interval(scores)
        }
    
    def update(self, context: ContextVector, model_id: str, reward: float):
        """Online update from feedback."""
        x = torch.cat([context.tensor, self._model_embedding(model_id)])
        predicted = self.network(x)
        loss = nn.MSELoss()(predicted, torch.tensor([[reward]]))
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
```

### 2.2 Task-Specific Model Selection

```python
class TaskSpecificRouter:
    """Pre-configured model preferences per task type with online override."""
    
    TASK_DEFAULTS = {
        TaskType.CODE_GENERATION: [
            ModelPreference('sonnet', weight=0.40, reason='Best quality/cost for code'),
            ModelPreference('haiku', weight=0.35, reason='Fast for simple code'),
            ModelPreference('opus', weight=0.25, reason='Complex algorithms'),
        ],
        TaskType.RESEARCH: [
            ModelPreference('opus', weight=0.55, reason='Deep reasoning needed'),
            ModelPreference('sonnet', weight=0.35, reason='Balanced analysis'),
            ModelPreference('haiku', weight=0.10, reason='Quick lookups'),
        ],
        TaskType.ANALYSIS: [
            ModelPreference('sonnet', weight=0.50, reason='Balanced analysis'),
            ModelPreference('opus', weight=0.30, reason='Deep analysis'),
            ModelPreference('haiku', weight=0.20, reason='Simple analysis'),
        ],
        TaskType.PLANNING: [
            ModelPreference('opus', weight=0.60, reason='Strategic thinking'),
            ModelPreference('sonnet', weight=0.40, reason='Tactical planning'),
        ],
        TaskType.REVIEW: [
            ModelPreference('haiku', weight=0.50, reason='Fast feedback'),
            ModelPreference('sonnet', weight=0.50, reason='Thorough review'),
        ],
    }
    
    def get_candidates(
        self, task_type: TaskType, context: ContextVector
    ) -> list[str]:
        """Get ranked model candidates for task type."""
        defaults = self.TASK_DEFAULTS.get(task_type, [])
        
        # Filter by context constraints
        available = [
            m for m in defaults
            if self._meets_constraints(m.model_id, context)
        ]
        
        return [m.model_id for m in available]
```

### 2.3 Cost-Quality Pareto Optimizer

```python
class ParetoOptimizer:
    """Multi-objective optimization over cost, quality, and latency."""
    
    def __init__(self):
        self.model_profiles = ModelProfileRegistry()
    
    def optimize(
        self, candidates: list[str], preferences: UserPreferences
    ) -> list[str]:
        """Find Pareto-optimal models given user preferences."""
        profiles = [self.model_profiles.get(m) for m in candidates]
        
        pareto_front = []
        for i, p1 in enumerate(profiles):
            dominated = False
            for j, p2 in enumerate(profiles):
                if i == j:
                    continue
                if self._dominates(p2, p1):  # p2 is better in ALL dimensions
                    dominated = True
                    break
            if not dominated:
                pareto_front.append(p1.model_id)
        
        # Score Pareto front by user preferences
        scored = [
            (m, self._weighted_score(m, preferences))
            for m in pareto_front
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [m for m, _ in scored]
    
    def _dominates(self, a: ModelProfile, b: ModelProfile) -> bool:
        """Check if model A dominates model B (better in all objectives)."""
        return (
            a.quality_score >= b.quality_score and
            a.cost_per_token <= b.cost_per_token and
            a.avg_latency <= b.avg_latency
        ) and (
            a.quality_score > b.quality_score or
            a.cost_per_token < b.cost_per_token or
            a.avg_latency < b.avg_latency
        )
```

### 2.4 Online Learning & Feedback Loop

```python
class OnlineLearner:
    """Continuous learning from routing decisions."""
    
    def __init__(self):
        self.neural_ucb = NeuralUCB(input_dim=256)
        self.replay_buffer = ReplayBuffer(capacity=10000)
        self.drift_detector = DistributionShiftDetector()
    
    async def learn_from_feedback(
        self, decision: RoutingDecision, outcome: TaskOutcome
    ):
        """Learn from routing outcome."""
        reward = self._calculate_reward(outcome)
        
        # Store in replay buffer
        self.replay_buffer.push(
            context=decision.context,
            model_id=decision.selected_model,
            reward=reward,
            timestamp=datetime.now()
        )
        
        # Online update
        self.neural_ucb.update(decision.context, decision.selected_model, reward)
        
        # Check for distribution shift
        if self.drift_detector.detect(self.replay_buffer.recent(1000)):
            await self._retrain_from_buffer()
    
    def _calculate_reward(self, outcome: TaskOutcome) -> float:
        """Multi-objective reward combining quality, cost, and latency."""
        quality_score = outcome.quality_score  # 0-1
        cost_normalized = 1.0 - (outcome.cost / outcome.max_budget)
        latency_score = max(0, 1.0 - (outcome.latency_ms / 30000))
        
        # User-configurable weights
        return (
            0.5 * quality_score +
            0.3 * cost_normalized +
            0.2 * latency_score
        )
```

### 2.5 A/B Testing Framework

```python
class RoutingABTester:
    """Bayesian A/B testing for routing strategies."""
    
    def __init__(self):
        self.active_tests: dict[str, ABTest] = {}
    
    def create_test(
        self, strategy_a: RoutingStrategy, strategy_b: RoutingStrategy
    ) -> str:
        """Create A/B test between two routing strategies."""
        test_id = f"ab_{uuid4().hex[:8]}"
        
        self.active_tests[test_id] = ABTest(
            id=test_id,
            variant_a=Variant(strategy_a, traffic_split=0.5),
            variant_b=Variant(strategy_b, traffic_split=0.5),
            started_at=datetime.now(),
            min_sample_size=1000,
            metrics=['quality', 'cost', 'latency', 'success_rate']
        )
        return test_id
    
    def route(self, test_id: str, context: ContextVector) -> str:
        """Route to variant with traffic splitting."""
        test = self.active_tests[test_id]
        if random.random() < test.variant_a.traffic_split:
            return test.variant_a.strategy.select(context)
        return test.variant_b.strategy.select(context)
    
    def analyze(self, test_id: str) -> ABTestResult:
        """Bayesian analysis of test results."""
        test = self.active_tests[test_id]
        
        # Bayesian hypothesis testing
        a_samples = test.variant_a.outcomes
        b_samples = test.variant_b.outcomes
        
        # Probability B > A
        prob_b_better = np.mean(
            np.random.choice(b_samples, 10000) > 
            np.random.choice(a_samples, 10000)
        )
        
        return ABTestResult(
            test_id=test_id,
            variant_a_stats=VariantStats.from_samples(a_samples),
            variant_b_stats=VariantStats.from_samples(b_samples),
            prob_b_better=prob_b_better,
            recommendation=(
                'deploy_b' if prob_b_better > 0.95
                else 'deploy_a' if prob_b_better < 0.05
                else 'continue_test'
            ),
            samples_needed=(
                None if prob_b_better > 0.95 or prob_b_better < 0.05
                else self._estimate_remaining_samples(test)
            )
        )
```

---

## III. Implementation Phases

### Phase 1: Foundation (Weeks 1-4)
- NeuralUCB algorithm implementation
- Context feature extraction (task type, complexity, history)
- Model registry with capability profiles
- Basic routing decision engine
- **Tests:** 40 unit tests, 90%+ coverage

### Phase 2: Task-Specific Routing (Weeks 5-8)
- Task classifier implementation
- Model capability profiles for all providers
- Cost-quality Pareto optimization
- User preference configuration
- **Tests:** 30 unit tests + 10 integration

### Phase 3: Online Learning (Weeks 9-12)
- Feedback collector implementation
- Replay buffer + periodic retraining
- Distribution shift detection
- Exploration strategies (ε-greedy + UCB)
- Dynamic budget adjustment
- **Tests:** 25 unit tests + 10 integration

### Phase 4: A/B Testing & Deployment (Weeks 13-16)
- A/B testing framework
- Bayesian hypothesis testing
- Automatic rollout of winning strategies
- Production monitoring
- **Tests:** 20 unit tests + 15 integration + 5 E2E

---

## IV. Model Selection Rules

| Task Type | Primary | Secondary | Fallback |
|-----------|---------|-----------|----------|
| Code Generation | Sonnet | Haiku | Opus |
| Research | Opus | Sonnet | Haiku |
| Analysis | Sonnet | Opus | Haiku |
| Planning | Opus | Sonnet | - |
| Review | Haiku | Sonnet | - |
| Simple Query | Haiku | - | Sonnet |
| Architecture | Opus | Sonnet | - |
| Debugging | Sonnet | Opus | Haiku |

---

## V. Testing Plan

| Test Type | Count | Coverage |
|-----------|-------|----------|
| NeuralUCB unit tests | 25 | 95% |
| Context extractor tests | 15 | 90% |
| Model registry tests | 15 | 90% |
| Pareto optimizer tests | 15 | 95% |
| Online learner tests | 20 | 90% |
| A/B testing tests | 15 | 90% |
| Integration tests | 20 | N/A |
| E2E tests | 10 | N/A |
| Performance benchmarks | 15 | N/A |
| **Total** | **150** | **90%+** |

---

## VI. Success Metrics

- [ ] 70%+ cost reduction vs baseline routing
- [ ] 10%+ quality improvement vs baseline
- [ ] <10ms routing decision latency (p95)
- [ ] 95%+ routing accuracy
- [ ] A/B testing framework operational
- [ ] Online learning demonstrates improvement over time
- [ ] 150+ tests, 90%+ coverage
- [ ] Supports all configured model providers
