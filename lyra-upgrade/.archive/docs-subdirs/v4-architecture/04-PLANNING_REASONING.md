# Lyra v4.0 Planning & Reasoning Design

**Version**: 1.0  
**Status**: 🚧 Draft  
**Last Updated**: 2026-05-21

---

## Overview

The Planning & Reasoning system enables Lyra to tackle complex, long-horizon goals through strategic planning, logical reasoning, and adaptive execution. This document details the architecture and implementation.

---

## Design Goals

### 1. Strategic Planning
- Decompose complex goals into manageable steps
- Create executable plans
- Optimize for efficiency and success

### 2. Logical Reasoning
- Apply multiple reasoning strategies
- Draw valid conclusions
- Handle uncertainty

### 3. Adaptability
- Adjust plans based on feedback
- Learn from failures
- Improve over time

### 4. Transparency
- Explain reasoning process
- Show decision rationale
- Enable user oversight

### 5. Efficiency
- Minimize unnecessary steps
- Optimize resource usage
- Achieve goals quickly

---

## System Architecture

```
Planning & Reasoning System
│
├── Goal Manager
│   ├── Goal Parser
│   ├── Goal Validator
│   ├── Goal Tracker
│   └── Goal Evaluator
│
├── Planner
│   ├── Decomposition Engine
│   ├── Plan Generator
│   ├── Plan Optimizer
│   └── Plan Executor
│
├── Reasoner
│   ├── Logical Reasoning
│   ├── Causal Reasoning
│   ├── Analogical Reasoning
│   └── Abductive Reasoning
│
└── Adaptation Engine
    ├── Feedback Processor
    ├── Plan Adjuster
    ├── Learning Module
    └── Strategy Selector
```

---

## Goal Management

### Goal Structure

```python
class Goal:
    id: str
    objective: str             # User's goal
    status: GoalStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    
    # Decomposition
    sub_goals: list[Goal]
    parent_goal: str | None
    
    # Planning
    plan: Plan | None
    current_step: int
    
    # Constraints
    budget: Budget
    deadline: datetime | None
    
    # Evaluation
    success_criteria: str
    verification_method: str
    
    # Tracking
    progress: float            # 0.0-1.0
    cost_used: float
    time_used: float
    
    # Context
    context: dict
    memory_snapshot: dict

class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Goal Parser

```python
class GoalParser:
    """Parse and structure user goals"""
    
    async def parse(self, objective: str) -> Goal:
        """Parse objective into structured goal"""
        # Extract key components
        components = await self.extract_components(objective)
        
        # Identify constraints
        constraints = await self.identify_constraints(objective)
        
        # Determine success criteria
        success_criteria = await self.determine_success_criteria(objective)
        
        # Create goal
        goal = Goal(
            id=generate_id(),
            objective=objective,
            status=GoalStatus.PENDING,
            created_at=datetime.now(),
            budget=constraints.get("budget", Budget()),
            deadline=constraints.get("deadline"),
            success_criteria=success_criteria,
            verification_method=self.select_verification_method(success_criteria)
        )
        
        return goal
    
    async def extract_components(self, objective: str) -> dict:
        """Extract goal components"""
        # Use LLM to extract:
        # - Main action (what to do)
        # - Target (what to act on)
        # - Constraints (limitations)
        # - Context (background info)
        
        prompt = f"""
        Extract components from this goal:
        "{objective}"
        
        Return JSON with:
        - action: main action verb
        - target: what to act on
        - constraints: any limitations
        - context: background information
        """
        
        response = await self.llm.complete(prompt)
        return json.loads(response)
```

### Goal Validator

```python
class GoalValidator:
    """Validate goals are achievable and safe"""
    
    async def validate(self, goal: Goal) -> ValidationResult:
        """Validate goal"""
        issues = []
        
        # Check clarity
        if not self.is_clear(goal.objective):
            issues.append("Goal is ambiguous or unclear")
        
        # Check feasibility
        if not await self.is_feasible(goal):
            issues.append("Goal may not be achievable")
        
        # Check safety
        if not await self.is_safe(goal):
            issues.append("Goal may have safety concerns")
        
        # Check resources
        if not self.has_sufficient_resources(goal):
            issues.append("Insufficient resources for goal")
        
        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            suggestions=self.generate_suggestions(issues)
        )
    
    def is_clear(self, objective: str) -> bool:
        """Check if goal is clear and specific"""
        # Check for vague terms
        vague_terms = ["improve", "better", "optimize", "enhance"]
        has_vague = any(term in objective.lower() for term in vague_terms)
        
        # Check for measurable criteria
        has_measurable = any(
            term in objective.lower()
            for term in ["test", "verify", "measure", "check"]
        )
        
        return not has_vague or has_measurable
    
    async def is_feasible(self, goal: Goal) -> bool:
        """Check if goal is achievable"""
        # Check if we have necessary tools
        required_tools = await self.identify_required_tools(goal)
        available_tools = self.get_available_tools()
        
        if not all(tool in available_tools for tool in required_tools):
            return False
        
        # Check if similar goals have succeeded
        similar_goals = await self.find_similar_goals(goal)
        if similar_goals:
            success_rate = sum(
                1 for g in similar_goals if g.status == GoalStatus.COMPLETED
            ) / len(similar_goals)
            return success_rate > 0.5
        
        return True
```

---

## Planning

### Plan Structure

```python
class Plan:
    id: str
    goal_id: str
    created_at: datetime
    updated_at: datetime
    
    # Steps
    steps: list[Step]
    current_step_index: int
    
    # Metadata
    estimated_duration: float
    estimated_cost: float
    confidence: float          # 0.0-1.0
    
    # Execution
    execution_strategy: str    # "sequential", "parallel", "adaptive"
    
    # Tracking
    actual_duration: float
    actual_cost: float

class Step:
    id: str
    order: int
    description: str
    action: str                # What to do
    
    # Dependencies
    depends_on: list[str]      # Step IDs
    blocks: list[str]          # Step IDs
    
    # Execution
    agent_type: str            # Which agent should execute
    tools: list[str]           # Required tools
    estimated_duration: float
    estimated_cost: float
    
    # Status
    status: StepStatus
    started_at: datetime | None
    completed_at: datetime | None
    result: Any | None
    error: str | None
    
    # Verification
    success_criteria: str
    verification_method: str

class StepStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

### Decomposition Engine

```python
class DecompositionEngine:
    """Decompose goals into executable steps"""
    
    async def decompose(self, goal: Goal) -> list[Step]:
        """Decompose goal into steps"""
        # Analyze goal complexity
        complexity = await self.analyze_complexity(goal)
        
        if complexity == "simple":
            # Direct decomposition
            steps = await self.simple_decomposition(goal)
        elif complexity == "moderate":
            # Hierarchical decomposition
            steps = await self.hierarchical_decomposition(goal)
        else:
            # Iterative decomposition
            steps = await self.iterative_decomposition(goal)
        
        # Add dependencies
        steps = self.add_dependencies(steps)
        
        # Estimate resources
        steps = await self.estimate_resources(steps)
        
        return steps
    
    async def simple_decomposition(self, goal: Goal) -> list[Step]:
        """Simple linear decomposition"""
        prompt = f"""
        Break down this goal into 3-7 concrete steps:
        Goal: {goal.objective}
        
        Return JSON array of steps with:
        - description: what to do
        - action: specific action
        - tools: required tools
        """
        
        response = await self.llm.complete(prompt)
        steps_data = json.loads(response)
        
        steps = [
            Step(
                id=generate_id(),
                order=i,
                description=step["description"],
                action=step["action"],
                tools=step["tools"],
                status=StepStatus.PENDING
            )
            for i, step in enumerate(steps_data)
        ]
        
        return steps
    
    async def hierarchical_decomposition(self, goal: Goal) -> list[Step]:
        """Hierarchical decomposition for complex goals"""
        # First level: major phases
        phases = await self.identify_phases(goal)
        
        # Second level: steps within each phase
        all_steps = []
        for i, phase in enumerate(phases):
            phase_steps = await self.simple_decomposition(
                Goal(objective=phase)
            )
            
            # Adjust order
            for step in phase_steps:
                step.order = len(all_steps)
                all_steps.append(step)
        
        return all_steps
```

### Plan Generator

```python
class PlanGenerator:
    """Generate executable plans"""
    
    def __init__(self):
        self.decomposer = DecompositionEngine()
        self.optimizer = PlanOptimizer()
    
    async def generate(self, goal: Goal) -> Plan:
        """Generate plan for goal"""
        # Decompose into steps
        steps = await self.decomposer.decompose(goal)
        
        # Create initial plan
        plan = Plan(
            id=generate_id(),
            goal_id=goal.id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            steps=steps,
            current_step_index=0,
            execution_strategy="sequential"
        )
        
        # Optimize plan
        plan = await self.optimizer.optimize(plan)
        
        # Estimate resources
        plan.estimated_duration = sum(s.estimated_duration for s in steps)
        plan.estimated_cost = sum(s.estimated_cost for s in steps)
        
        # Calculate confidence
        plan.confidence = await self.calculate_confidence(plan)
        
        return plan
    
    async def calculate_confidence(self, plan: Plan) -> float:
        """Calculate confidence in plan success"""
        factors = []
        
        # Step clarity
        clarity = sum(
            1 for s in plan.steps
            if self.is_step_clear(s)
        ) / len(plan.steps)
        factors.append(clarity)
        
        # Tool availability
        required_tools = set()
        for step in plan.steps:
            required_tools.update(step.tools)
        
        available_tools = self.get_available_tools()
        availability = len(
            required_tools & available_tools
        ) / len(required_tools)
        factors.append(availability)
        
        # Historical success
        similar_plans = await self.find_similar_plans(plan)
        if similar_plans:
            success_rate = sum(
                1 for p in similar_plans
                if p.status == "completed"
            ) / len(similar_plans)
            factors.append(success_rate)
        
        # Average factors
        return sum(factors) / len(factors)
```

### Plan Optimizer

```python
class PlanOptimizer:
    """Optimize plans for efficiency"""
    
    async def optimize(self, plan: Plan) -> Plan:
        """Optimize plan"""
        # Identify parallelizable steps
        plan = self.identify_parallel_steps(plan)
        
        # Reorder for efficiency
        plan = self.reorder_steps(plan)
        
        # Merge similar steps
        plan = self.merge_steps(plan)
        
        # Remove redundant steps
        plan = self.remove_redundant_steps(plan)
        
        return plan
    
    def identify_parallel_steps(self, plan: Plan) -> Plan:
        """Identify steps that can run in parallel"""
        for i, step in enumerate(plan.steps):
            # Check if step has dependencies
            if not step.depends_on:
                # Check if next step is independent
                if i + 1 < len(plan.steps):
                    next_step = plan.steps[i + 1]
                    if not next_step.depends_on:
                        # Mark as parallelizable
                        step.parallel_with = [next_step.id]
        
        return plan
    
    def reorder_steps(self, plan: Plan) -> Plan:
        """Reorder steps for efficiency"""
        # Topological sort based on dependencies
        sorted_steps = self.topological_sort(plan.steps)
        
        # Update order
        for i, step in enumerate(sorted_steps):
            step.order = i
        
        plan.steps = sorted_steps
        return plan
```

---

## Reasoning

### Reasoning Types

#### 1. Logical Reasoning

```python
class LogicalReasoner:
    """Apply logical reasoning"""
    
    async def deduce(self, premises: list[str]) -> list[str]:
        """Deduce conclusions from premises"""
        prompt = f"""
        Given these premises:
        {chr(10).join(f"- {p}" for p in premises)}
        
        What logical conclusions can be drawn?
        Return JSON array of conclusions with confidence scores.
        """
        
        response = await self.llm.complete(prompt)
        conclusions = json.loads(response)
        
        return [c["conclusion"] for c in conclusions if c["confidence"] > 0.7]
    
    async def verify_consistency(self, statements: list[str]) -> bool:
        """Check if statements are logically consistent"""
        prompt = f"""
        Are these statements logically consistent?
        {chr(10).join(f"- {s}" for s in statements)}
        
        Return JSON with:
        - consistent: true/false
        - contradictions: list of contradicting pairs
        """
        
        response = await self.llm.complete(prompt)
        result = json.loads(response)
        
        return result["consistent"]
```

#### 2. Causal Reasoning

```python
class CausalReasoner:
    """Apply causal reasoning"""
    
    async def identify_causes(self, effect: str, context: dict) -> list[str]:
        """Identify potential causes of an effect"""
        prompt = f"""
        What could cause this effect?
        Effect: {effect}
        Context: {json.dumps(context)}
        
        Return JSON array of potential causes with likelihood scores.
        """
        
        response = await self.llm.complete(prompt)
        causes = json.loads(response)
        
        return [c["cause"] for c in causes if c["likelihood"] > 0.5]
    
    async def predict_effects(self, action: str, context: dict) -> list[str]:
        """Predict effects of an action"""
        prompt = f"""
        What effects would this action have?
        Action: {action}
        Context: {json.dumps(context)}
        
        Return JSON array of predicted effects with confidence scores.
        """
        
        response = await self.llm.complete(prompt)
        effects = json.loads(response)
        
        return [e["effect"] for e in effects if e["confidence"] > 0.6]
```

#### 3. Analogical Reasoning

```python
class AnalogicalReasoner:
    """Apply analogical reasoning"""
    
    async def find_analogies(self, situation: str) -> list[Analogy]:
        """Find analogous situations"""
        # Search memory for similar situations
        similar = await self.memory.recall(
            query=situation,
            networks=["episodes", "strategies"],
            limit=5
        )
        
        analogies = []
        for memory in similar:
            analogy = Analogy(
                source=memory.content,
                target=situation,
                similarity=memory.relevance_score,
                mapping=await self.create_mapping(memory.content, situation)
            )
            analogies.append(analogy)
        
        return analogies
    
    async def transfer_solution(self, analogy: Analogy) -> str:
        """Transfer solution from analogy"""
        prompt = f"""
        Given this analogy:
        Source: {analogy.source}
        Target: {analogy.target}
        Mapping: {json.dumps(analogy.mapping)}
        
        How can the solution from the source be adapted to the target?
        """
        
        response = await self.llm.complete(prompt)
        return response
```

#### 4. Abductive Reasoning

```python
class AbductiveReasoner:
    """Apply abductive reasoning (inference to best explanation)"""
    
    async def find_best_explanation(
        self,
        observations: list[str],
        context: dict
    ) -> Explanation:
        """Find best explanation for observations"""
        # Generate candidate explanations
        candidates = await self.generate_explanations(observations, context)
        
        # Score explanations
        scored = []
        for explanation in candidates:
            score = await self.score_explanation(explanation, observations)
            scored.append((explanation, score))
        
        # Return best explanation
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]
    
    async def score_explanation(
        self,
        explanation: str,
        observations: list[str]
    ) -> float:
        """Score explanation quality"""
        # Factors:
        # - Explains all observations
        # - Simple (Occam's razor)
        # - Consistent with known facts
        # - Testable
        
        prompt = f"""
        Score this explanation (0-1):
        Explanation: {explanation}
        Observations: {json.dumps(observations)}
        
        Consider:
        - Coverage: explains all observations
        - Simplicity: minimal assumptions
        - Consistency: fits known facts
        - Testability: can be verified
        
        Return JSON with score and reasoning.
        """
        
        response = await self.llm.complete(prompt)
        result = json.loads(response)
        
        return result["score"]
```

---

## Adaptation

### Feedback Processing

```python
class FeedbackProcessor:
    """Process feedback and learn from execution"""
    
    async def process_step_result(
        self,
        step: Step,
        result: Result,
        plan: Plan
    ) -> Feedback:
        """Process step execution result"""
        feedback = Feedback(
            step_id=step.id,
            success=result.success,
            actual_duration=result.duration,
            actual_cost=result.cost,
            issues=[]
        )
        
        # Check for issues
        if not result.success:
            feedback.issues.append(f"Step failed: {result.error}")
        
        if result.duration > step.estimated_duration * 1.5:
            feedback.issues.append("Step took longer than expected")
        
        if result.cost > step.estimated_cost * 1.5:
            feedback.issues.append("Step cost more than expected")
        
        # Generate recommendations
        feedback.recommendations = await self.generate_recommendations(
            step,
            result,
            plan
        )
        
        return feedback
    
    async def generate_recommendations(
        self,
        step: Step,
        result: Result,
        plan: Plan
    ) -> list[str]:
        """Generate recommendations based on result"""
        recommendations = []
        
        if not result.success:
            # Suggest retry with different approach
            recommendations.append("Retry with alternative approach")
            
            # Suggest breaking down further
            if step.estimated_duration > 300:  # 5 minutes
                recommendations.append("Break step into smaller sub-steps")
        
        if result.duration > step.estimated_duration * 2:
            # Suggest optimization
            recommendations.append("Optimize step execution")
        
        return recommendations
```

### Plan Adjustment

```python
class PlanAdjuster:
    """Adjust plans based on feedback"""
    
    async def adjust(self, plan: Plan, feedback: Feedback) -> Plan:
        """Adjust plan based on feedback"""
        if not feedback.success:
            # Handle failure
            plan = await self.handle_failure(plan, feedback)
        
        if feedback.issues:
            # Address issues
            plan = await self.address_issues(plan, feedback)
        
        # Update estimates
        plan = self.update_estimates(plan, feedback)
        
        return plan
    
    async def handle_failure(self, plan: Plan, feedback: Feedback) -> Plan:
        """Handle step failure"""
        failed_step = next(
            s for s in plan.steps if s.id == feedback.step_id
        )
        
        # Try alternative approach
        if failed_step.retry_count < 3:
            failed_step.retry_count += 1
            failed_step.status = StepStatus.READY
            
            # Modify approach
            failed_step.action = await self.generate_alternative_approach(
                failed_step
            )
        else:
            # Skip step or abort
            if failed_step.optional:
                failed_step.status = StepStatus.SKIPPED
            else:
                plan.status = "failed"
        
        return plan
    
    def update_estimates(self, plan: Plan, feedback: Feedback) -> Plan:
        """Update estimates based on actual performance"""
        step = next(s for s in plan.steps if s.id == feedback.step_id)
        
        # Update step estimates
        step.estimated_duration = (
            step.estimated_duration * 0.7 +
            feedback.actual_duration * 0.3
        )
        step.estimated_cost = (
            step.estimated_cost * 0.7 +
            feedback.actual_cost * 0.3
        )
        
        # Update plan estimates
        plan.estimated_duration = sum(
            s.estimated_duration for s in plan.steps
        )
        plan.estimated_cost = sum(
            s.estimated_cost for s in plan.steps
        )
        
        return plan
```

### Learning Module

```python
class LearningModule:
    """Learn from execution history"""
    
    async def learn_from_execution(self, plan: Plan, outcome: str):
        """Learn from plan execution"""
        # Extract patterns
        patterns = await self.extract_patterns(plan)
        
        # Update strategies
        for pattern in patterns:
            await self.update_strategy(pattern, outcome)
        
        # Store lessons learned
        lesson = Lesson(
            plan_id=plan.id,
            goal=plan.goal_id,
            outcome=outcome,
            patterns=patterns,
            insights=await self.generate_insights(plan, outcome)
        )
        
        await self.memory.store(lesson)
    
    async def extract_patterns(self, plan: Plan) -> list[Pattern]:
        """Extract patterns from plan"""
        patterns = []
        
        # Step sequence patterns
        if len(plan.steps) >= 3:
            for i in range(len(plan.steps) - 2):
                sequence = [
                    plan.steps[i].action,
                    plan.steps[i + 1].action,
                    plan.steps[i + 2].action
                ]
                patterns.append(Pattern(
                    type="sequence",
                    elements=sequence
                ))
        
        # Tool usage patterns
        tool_usage = {}
        for step in plan.steps:
            for tool in step.tools:
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        patterns.append(Pattern(
            type="tool_usage",
            elements=tool_usage
        ))
        
        return patterns
```

---

## Plan Execution

### Executor

```python
class PlanExecutor:
    """Execute plans"""
    
    def __init__(self):
        self.agents = AgentPool()
        self.feedback_processor = FeedbackProcessor()
        self.plan_adjuster = PlanAdjuster()
    
    async def execute(self, plan: Plan) -> ExecutionResult:
        """Execute plan"""
        plan.status = "executing"
        results = []
        
        try:
            for step in plan.steps:
                # Check if step is ready
                if not self.is_step_ready(step, plan):
                    continue
                
                # Execute step
                result = await self.execute_step(step, plan)
                results.append(result)
                
                # Process feedback
                feedback = await self.feedback_processor.process_step_result(
                    step,
                    result,
                    plan
                )
                
                # Adjust plan if needed
                if feedback.issues:
                    plan = await self.plan_adjuster.adjust(plan, feedback)
                
                # Check if should continue
                if not self.should_continue(plan, feedback):
                    break
            
            # Mark as completed
            plan.status = "completed"
            
            return ExecutionResult(
                success=True,
                plan=plan,
                results=results
            )
        
        except Exception as e:
            plan.status = "failed"
            return ExecutionResult(
                success=False,
                plan=plan,
                results=results,
                error=str(e)
            )
    
    async def execute_step(self, step: Step, plan: Plan) -> Result:
        """Execute single step"""
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now()
        
        try:
            # Select agent
            agent = await self.agents.get_agent(step.agent_type)
            
            # Execute
            result = await agent.execute(step)
            
            # Update step
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()
            step.result = result
            
            return result
        
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            raise
```

---

## Summary

Planning & Reasoning provides:
- ✅ **Goal management**: Parse, validate, track goals
- ✅ **Planning**: Decompose, generate, optimize plans
- ✅ **4 reasoning types**: Logical, causal, analogical, abductive
- ✅ **Adaptation**: Process feedback, adjust plans, learn
- ✅ **Execution**: Execute plans with monitoring

**Key Features**:
- Strategic decomposition
- Multiple reasoning strategies
- Adaptive execution
- Continuous learning
- Transparent decision-making

**Next**: See `05-SAFETY_GOVERNANCE.md` for safety and governance mechanisms.
