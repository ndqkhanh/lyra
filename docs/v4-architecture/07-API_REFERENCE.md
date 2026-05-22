# Lyra v4.0 API Reference

**Version**: 1.0  
**Status**: 🚧 Draft  
**Last Updated**: 2026-05-21

---

## Overview

Complete API reference for Lyra v4.0 components. This document covers all public APIs, interfaces, and integration points.

---

## Table of Contents

1. [Memory System API](#memory-system-api)
2. [Agent System API](#agent-system-api)
3. [Planning System API](#planning-system-api)
4. [Safety System API](#safety-system-api)
5. [Tool Integration API](#tool-integration-api)

---

## Memory System API

### MemorySystem

Main interface for memory operations.

```python
class MemorySystem:
    """Complete memory system with 5 networks"""
    
    def __init__(self, storage: Optional[MemoryStorage] = None):
        """
        Initialize memory system.
        
        Args:
            storage: Optional custom storage backend
        """
        pass
    
    # Network access
    beliefs: BeliefsNetwork
    episodes: EpisodesNetwork
    entities: EntitiesNetwork
    procedures: ProceduresNetwork
    strategies: StrategiesNetwork
    
    def get_network(self, name: str) -> MemoryNetwork:
        """
        Get network by name.
        
        Args:
            name: Network name (beliefs, episodes, entities, procedures, strategies)
            
        Returns:
            MemoryNetwork instance
            
        Raises:
            KeyError: If network name is invalid
        """
        pass
```

### MemoryNetwork

Base class for all memory networks.

```python
class MemoryNetwork:
    """Base memory network"""
    
    def store(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Store memory in network.
        
        Args:
            content: Memory content
            importance: Importance score (0.0-1.0)
            metadata: Optional metadata dict
            
        Returns:
            Memory ID
            
        Example:
            >>> memory_id = network.store(
            ...     "Python is a programming language",
            ...     importance=0.9,
            ...     metadata={"category": "programming"}
            ... )
        """
        pass
    
    def recall(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> list[Memory]:
        """
        Recall memories from network.
        
        Args:
            query: Search query
            limit: Maximum results
            min_importance: Minimum importance threshold
            
        Returns:
            List of Memory objects
            
        Example:
            >>> memories = network.recall(
            ...     "programming languages",
            ...     limit=5,
            ...     min_importance=0.7
            ... )
        """
        pass
    
    def forget(self, memory_id: str):
        """
        Delete memory from network.
        
        Args:
            memory_id: ID of memory to delete
            
        Example:
            >>> network.forget("mem_123")
        """
        pass
```

### Memory

Memory data object.

```python
@dataclass
class Memory:
    """Memory object"""
    
    id: str                      # Unique identifier
    network: str                 # Network name
    content: str                 # Memory content
    importance: float            # Importance score (0.0-1.0)
    created_at: datetime         # Creation timestamp
    accessed_at: datetime        # Last access timestamp
    access_count: int            # Number of accesses
    metadata: Optional[dict]     # Optional metadata
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        pass
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        """Create from dictionary"""
        pass
```

### MemoryStorage

Low-level storage interface.

```python
class MemoryStorage:
    """SQLite-based memory storage"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        pass
    
    def store(
        self,
        network: str,
        content: str,
        embedding: Optional[bytes] = None,
        importance: float = 0.5,
        metadata: Optional[dict] = None
    ) -> str:
        """Store memory"""
        pass
    
    def retrieve(self, memory_id: str) -> Optional[dict]:
        """Retrieve memory by ID"""
        pass
    
    def search(
        self,
        network: Optional[str] = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> list[dict]:
        """Search memories"""
        pass
    
    def delete(self, memory_id: str):
        """Delete memory"""
        pass
    
    def close(self):
        """Close database connection"""
        pass
```

---

## Agent System API

### Agent

Base agent interface.

```python
class Agent(ABC):
    """Base agent class"""
    
    id: str                      # Agent identifier
    status: AgentStatus          # Current status
    current_task: Optional[Task] # Current task
    
    @abstractmethod
    async def execute(self, task: Task) -> Result:
        """
        Execute task.
        
        Args:
            task: Task to execute
            
        Returns:
            Result object
            
        Example:
            >>> result = await agent.execute(task)
            >>> if result.success:
            ...     print(result.data)
        """
        pass
    
    async def can_handle(self, task: Task) -> bool:
        """
        Check if agent can handle task.
        
        Args:
            task: Task to check
            
        Returns:
            True if agent can handle task
        """
        pass
    
    def capability_score(self, task: Task) -> float:
        """
        Score capability for task.
        
        Args:
            task: Task to score
            
        Returns:
            Capability score (0.0-1.0)
        """
        pass
```

### PrimaryAgent

Main orchestrator agent.

```python
class PrimaryAgent(Agent):
    """Primary orchestrator agent"""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        memory: Optional[MemorySystem] = None
    ):
        """
        Initialize primary agent.
        
        Args:
            agent_id: Optional agent ID
            memory: Optional memory system
        """
        pass
    
    async def handle_request(self, request: str) -> str:
        """
        Handle user request.
        
        Args:
            request: User request text
            
        Returns:
            Response text
            
        Example:
            >>> response = await agent.handle_request(
            ...     "Create a Python function to calculate fibonacci"
            ... )
        """
        pass
    
    async def delegate(self, task: Task, agent_type: str) -> Result:
        """
        Delegate task to specialist agent.
        
        Args:
            task: Task to delegate
            agent_type: Type of agent (code, research, test, review)
            
        Returns:
            Result from specialist agent
        """
        pass
```

### SpecialistAgent

Base class for specialist agents.

```python
class SpecialistAgent(Agent):
    """Base specialist agent"""
    
    domain: str                  # Domain of expertise
    capabilities: list[str]      # List of capabilities
    tools: list[str]             # Available tools
    
    async def execute(self, task: Task) -> Result:
        """Execute specialized task"""
        pass
```

### Task

Task data object.

```python
@dataclass
class Task:
    """Task for agent"""
    
    id: str                      # Task identifier
    description: str             # Task description
    action: str                  # Action to perform
    params: dict                 # Task parameters
    context: Optional[Context]   # Execution context
    created_at: datetime         # Creation timestamp
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        pass
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Create from dictionary"""
        pass
```

### Result

Result data object.

```python
@dataclass
class Result:
    """Generic result type"""
    
    success: bool                # Success flag
    data: Any                    # Result data
    error: Optional[str]         # Error message if failed
    metadata: dict               # Additional metadata
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        pass
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Result':
        """Create from dictionary"""
        pass
```

---

## Planning System API

### Planner

Strategic planning interface.

```python
class Planner:
    """Strategic planner"""
    
    def __init__(
        self,
        decomposer: Optional[DecompositionEngine] = None,
        optimizer: Optional[PlanOptimizer] = None
    ):
        """
        Initialize planner.
        
        Args:
            decomposer: Optional decomposition engine
            optimizer: Optional plan optimizer
        """
        pass
    
    async def create_plan(self, goal: Goal) -> Plan:
        """
        Create execution plan for goal.
        
        Args:
            goal: Goal to plan for
            
        Returns:
            Execution plan
            
        Example:
            >>> plan = await planner.create_plan(goal)
            >>> print(f"Plan has {len(plan.steps)} steps")
        """
        pass
    
    async def optimize_plan(self, plan: Plan) -> Plan:
        """
        Optimize execution plan.
        
        Args:
            plan: Plan to optimize
            
        Returns:
            Optimized plan
        """
        pass
```

### Goal

Goal data object.

```python
@dataclass
class Goal:
    """Goal object"""
    
    id: str                      # Goal identifier
    objective: str               # Goal objective
    status: GoalStatus           # Current status
    created_at: datetime         # Creation timestamp
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Planning
    plan: Optional[Plan]         # Execution plan
    current_step: int            # Current step index
    
    # Constraints
    budget: Budget               # Resource budget
    deadline: Optional[datetime] # Deadline
    
    # Evaluation
    success_criteria: str        # Success criteria
    verification_method: str     # Verification method
    
    # Tracking
    progress: float              # Progress (0.0-1.0)
    cost_used: float            # Cost used
    time_used: float            # Time used
```

### Plan

Plan data object.

```python
@dataclass
class Plan:
    """Execution plan"""
    
    id: str                      # Plan identifier
    goal_id: str                 # Associated goal ID
    created_at: datetime         # Creation timestamp
    updated_at: datetime         # Last update timestamp
    
    # Steps
    steps: list[Step]            # Execution steps
    current_step_index: int      # Current step
    
    # Metadata
    estimated_duration: float    # Estimated duration (seconds)
    estimated_cost: float        # Estimated cost (USD)
    confidence: float            # Confidence score (0.0-1.0)
    
    # Execution
    execution_strategy: str      # Strategy (sequential, parallel, adaptive)
    
    # Tracking
    actual_duration: float       # Actual duration
    actual_cost: float          # Actual cost
```

### Step

Step data object.

```python
@dataclass
class Step:
    """Execution step"""
    
    id: str                      # Step identifier
    order: int                   # Execution order
    description: str             # Step description
    action: str                  # Action to perform
    
    # Dependencies
    depends_on: list[str]        # Dependency step IDs
    blocks: list[str]            # Blocked step IDs
    
    # Execution
    agent_type: str              # Agent type to use
    tools: list[str]             # Required tools
    estimated_duration: float    # Estimated duration
    estimated_cost: float        # Estimated cost
    
    # Status
    status: StepStatus           # Current status
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Any                  # Step result
    error: Optional[str]         # Error if failed
```

### Reasoner

Reasoning interface.

```python
class Reasoner:
    """Multi-strategy reasoner"""
    
    def __init__(self):
        """Initialize reasoner"""
        pass
    
    async def deduce(self, premises: list[str]) -> list[str]:
        """
        Logical deduction.
        
        Args:
            premises: List of premises
            
        Returns:
            List of conclusions
            
        Example:
            >>> conclusions = await reasoner.deduce([
            ...     "All humans are mortal",
            ...     "Socrates is human"
            ... ])
            >>> # ["Socrates is mortal"]
        """
        pass
    
    async def identify_causes(
        self,
        effect: str,
        context: dict
    ) -> list[str]:
        """
        Causal reasoning.
        
        Args:
            effect: Observed effect
            context: Context information
            
        Returns:
            List of potential causes
        """
        pass
    
    async def find_analogies(self, situation: str) -> list[Analogy]:
        """
        Analogical reasoning.
        
        Args:
            situation: Current situation
            
        Returns:
            List of analogous situations
        """
        pass
```

---

## Safety System API

### SafetyValidator

Safety validation interface.

```python
class SafetyValidator:
    """Multi-layer safety validator"""
    
    def __init__(
        self,
        input_validator: Optional[InputValidator] = None,
        action_validator: Optional[ActionValidator] = None,
        risk_assessor: Optional[RiskAssessor] = None
    ):
        """Initialize safety validator"""
        pass
    
    async def validate_input(self, input_text: str) -> ValidationResult:
        """
        Validate user input.
        
        Args:
            input_text: Input to validate
            
        Returns:
            ValidationResult
            
        Example:
            >>> result = await validator.validate_input(user_input)
            >>> if not result.valid:
            ...     print(f"Issues: {result.issues}")
        """
        pass
    
    async def validate_action(self, action: Action) -> ValidationResult:
        """
        Validate action before execution.
        
        Args:
            action: Action to validate
            
        Returns:
            ValidationResult
        """
        pass
    
    async def assess_risk(self, action: Action) -> RiskAssessment:
        """
        Assess action risk.
        
        Args:
            action: Action to assess
            
        Returns:
            RiskAssessment
        """
        pass
```

### BudgetManager

Budget management interface.

```python
class BudgetManager:
    """Resource budget manager"""
    
    def __init__(self):
        """Initialize budget manager"""
        pass
    
    async def check_budget(
        self,
        goal_id: str,
        action: Action
    ) -> BudgetCheck:
        """
        Check if action is within budget.
        
        Args:
            goal_id: Goal identifier
            action: Action to check
            
        Returns:
            BudgetCheck result
            
        Example:
            >>> check = await budget_manager.check_budget(goal_id, action)
            >>> if not check.allowed:
            ...     print(f"Budget exceeded: {check.issues}")
        """
        pass
    
    async def record_usage(
        self,
        goal_id: str,
        cost_usd: float,
        time_seconds: float,
        tokens: int
    ):
        """
        Record resource usage.
        
        Args:
            goal_id: Goal identifier
            cost_usd: Cost in USD
            time_seconds: Time in seconds
            tokens: Token count
        """
        pass
    
    def get_budget(self, goal_id: str) -> Budget:
        """
        Get budget for goal.
        
        Args:
            goal_id: Goal identifier
            
        Returns:
            Budget object
        """
        pass
```

### Budget

Budget data object.

```python
@dataclass
class Budget:
    """Resource budget"""
    
    # Cost limits
    max_cost_usd: Optional[float]
    current_cost_usd: float
    
    # Time limits
    max_time_seconds: Optional[float]
    current_time_seconds: float
    
    # Token limits
    max_tokens: Optional[int]
    current_tokens: int
    
    # Turn limits
    max_turns: Optional[int]
    current_turns: int
    
    # Alerts
    alert_thresholds: dict[str, float]
    alerts_sent: set[str]
    
    def is_exceeded(self) -> bool:
        """Check if budget is exceeded"""
        pass
    
    def usage_percentage(self) -> dict[str, float]:
        """Get usage percentages"""
        pass
```

### AuditLogger

Audit logging interface.

```python
class AuditLogger:
    """Audit logging system"""
    
    def __init__(self):
        """Initialize audit logger"""
        pass
    
    async def log_operation(self, operation: Operation):
        """
        Log operation.
        
        Args:
            operation: Operation to log
            
        Example:
            >>> await audit_logger.log_operation(operation)
        """
        pass
    
    async def log_decision(self, decision: Decision):
        """
        Log decision.
        
        Args:
            decision: Decision to log
        """
        pass
    
    async def query_logs(
        self,
        filters: dict,
        limit: int = 100
    ) -> list[AuditRecord]:
        """
        Query audit logs.
        
        Args:
            filters: Filter criteria
            limit: Maximum results
            
        Returns:
            List of audit records
            
        Example:
            >>> logs = await audit_logger.query_logs(
            ...     {"goal_id": "goal_123"},
            ...     limit=50
            ... )
        """
        pass
```

---

## Tool Integration API

### Tool

Tool interface.

```python
class Tool(ABC):
    """Base tool interface"""
    
    name: str                    # Tool name
    description: str             # Tool description
    parameters: dict             # Parameter schema
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute tool.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool result
            
        Example:
            >>> result = await tool.execute(param1="value1")
        """
        pass
    
    def validate_parameters(self, params: dict) -> bool:
        """
        Validate parameters.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if valid
        """
        pass
```

### ToolRegistry

Tool registry interface.

```python
class ToolRegistry:
    """Tool registry"""
    
    def __init__(self):
        """Initialize tool registry"""
        pass
    
    def register(self, tool: Tool):
        """
        Register tool.
        
        Args:
            tool: Tool to register
            
        Example:
            >>> registry.register(my_tool)
        """
        pass
    
    def get(self, name: str) -> Optional[Tool]:
        """
        Get tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None
        """
        pass
    
    def list_tools(self) -> list[Tool]:
        """
        List all registered tools.
        
        Returns:
            List of tools
        """
        pass
    
    def search(self, query: str) -> list[Tool]:
        """
        Search tools.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tools
        """
        pass
```

---

## Error Handling

### Exceptions

```python
class LyraError(Exception):
    """Base Lyra exception"""
    pass

class MemoryError(LyraError):
    """Memory system error"""
    pass

class AgentError(LyraError):
    """Agent system error"""
    pass

class PlanningError(LyraError):
    """Planning system error"""
    pass

class SafetyError(LyraError):
    """Safety system error"""
    pass

class BudgetExceededError(SafetyError):
    """Budget exceeded error"""
    pass

class ValidationError(SafetyError):
    """Validation error"""
    pass
```

---

## Usage Examples

### Complete Example

```python
from lyra import Lyra
from lyra.core.config import LyraConfig

# Initialize Lyra
config = LyraConfig(
    anthropic_api_key="your-api-key",
    default_max_cost_usd=5.0
)
lyra = Lyra(config)

# Handle request
async def main():
    response = await lyra.handle_request(
        "Create a Python function to calculate fibonacci numbers"
    )
    print(response)

# Run
import asyncio
asyncio.run(main())
```

### Memory Example

```python
from lyra.memory import MemorySystem

# Initialize memory
memory = MemorySystem()

# Store belief
memory_id = memory.beliefs.store(
    "Python is a high-level programming language",
    importance=0.9,
    metadata={"category": "programming"}
)

# Recall beliefs
memories = memory.beliefs.recall(
    "programming languages",
    limit=5
)

for mem in memories:
    print(f"{mem.content} (importance: {mem.importance})")
```

### Agent Example

```python
from lyra.agents import PrimaryAgent, Task

# Initialize agent
agent = PrimaryAgent()

# Create task
task = Task(
    description="Analyze code quality",
    action="analyze",
    params={"file": "main.py"}
)

# Execute
result = await agent.execute(task)
if result.success:
    print(result.data)
```

### Planning Example

```python
from lyra.planning import Planner, Goal

# Initialize planner
planner = Planner()

# Create goal
goal = Goal(
    objective="Build a REST API with authentication",
    success_criteria="API passes all tests"
)

# Create plan
plan = await planner.create_plan(goal)

# Execute plan
for step in plan.steps:
    print(f"Step {step.order}: {step.description}")
```

---

## Summary

This API reference provides:
- ✅ Complete API documentation
- ✅ Type signatures
- ✅ Usage examples
- ✅ Error handling
- ✅ Integration patterns

For implementation details, see the Implementation Guide.
