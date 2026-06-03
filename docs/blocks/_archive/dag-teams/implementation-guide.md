# DAG Teams Implementation Guide

## Prerequisites

- Python 3.10+
- Git 2.35+ (worktree support)
- NetworkX (graph algorithms)
- Anthropic SDK
- Repository with `.lyra/` directory

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Install core dependencies
pip install networkx anthropic asyncio

# Verify git version (need 2.35+ for worktree improvements)
git --version
```

### Step 2: Project Structure

```bash
lyra/
├── harness/
│   └── plugins/
│       └── dag_teams/
│           ├── __init__.py
│           ├── planner.py
│           ├── validator.py
│           ├── scheduler.py
│           ├── dispatcher.py
│           ├── merge_coordinator.py
│           ├── verifier.py
│           └── models.py
```

### Step 3: Define Data Models

**File**: `models.py`

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class NodeKind(Enum):
    LOCALIZE = "localize"
    EDIT = "edit"
    TEST_GEN = "test_gen"
    REVIEW = "review"
    REFACTOR = "refactor"
    MIGRATE = "migrate"

class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    PARKED = "parked"
    BLOCKED_UPSTREAM = "blocked_upstream"

@dataclass(frozen=True)
class TaskNode:
    id: str
    kind: NodeKind
    description: str
    scope_files: List[str]
    depends_on: List[str]
    estimated_cost_usd: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class TaskDAG:
    nodes: List[TaskNode]
    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    planner_version: str = "1.0"
    
    @property
    def node_map(self) -> Dict[str, TaskNode]:
        return {node.id: node for node in self.nodes}

@dataclass
class SubagentResult:
    node_id: str
    status: NodeStatus
    commit_hash: Optional[str]
    files_touched: List[str]
    cost_usd: float
    duration_seconds: float
    summary: str
    error: Optional[str] = None
    tests_added: int = 0
    tests_passing: int = 0
    tests_failing: int = 0
```

### Step 4: Implement DAG Validator

**File**: `validator.py`

```python
import networkx as nx
from typing import List, Tuple
from .models import TaskDAG, TaskNode

class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

def validate_dag(dag: TaskDAG, session_budget: float) -> ValidationResult:
    result = ValidationResult()
    
    # Check 1: Build graph and detect cycles
    graph = nx.DiGraph()
    for node in dag.nodes:
        graph.add_node(node.id)
        for dep in node.depends_on:
            graph.add_edge(dep, node.id)
    
    if not nx.is_directed_acyclic_graph(graph):
        result.errors.append("DAG contains cycle")
        return result
    
    # Check 2: Reference integrity
    node_ids = {node.id for node in dag.nodes}
    for node in dag.nodes:
        for dep in node.depends_on:
            if dep not in node_ids:
                result.errors.append(
                    f"Node {node.id} depends on unknown node {dep}"
                )
    
    # Check 3: Budget validation
    total_cost = sum(n.estimated_cost_usd * 1.5 for n in dag.nodes)
    if total_cost > session_budget:
        result.warnings.append(
            f"Estimated cost ${total_cost:.2f} exceeds budget ${session_budget:.2f}"
        )
    
    # Check 4: Depth and width limits
    try:
        depth = nx.dag_longest_path_length(graph)
        if depth > 10:
            result.warnings.append(f"DAG depth {depth} > 10 (sequential bottleneck)")
    except nx.NetworkXError:
        pass
    
    # Check 5: Write scope conflicts (same wave)
    waves = partition_into_waves(dag)
    for wave_idx, wave_nodes in enumerate(waves):
        scopes = [(n.id, n.scope_files) for n in wave_nodes]
        conflicts = find_scope_conflicts(scopes)
        if conflicts:
            result.errors.append(
                f"Wave {wave_idx} has overlapping scopes: {conflicts}"
            )
    
    return result

def partition_into_waves(dag: TaskDAG) -> List[List[TaskNode]]:
    """Partition DAG into waves using topological sort."""
    node_map = dag.node_map
    remaining = set(dag.nodes)
    completed = set()
    waves = []
    
    while remaining:
        ready = [
            n for n in remaining
            if all(dep in completed for dep in n.depends_on)
        ]
        
        if not ready:
            raise ValueError("DAG is not acyclic or has unresolved dependencies")
        
        waves.append(ready)
        completed.update(n.id for n in ready)
        remaining -= set(ready)
    
    return waves

def find_scope_conflicts(
    scopes: List[Tuple[str, List[str]]]
) -> List[Tuple[str, str]]:
    """Find overlapping file scopes between nodes."""
    from fnmatch import fnmatch
    
    conflicts = []
    for i, (node_a, files_a) in enumerate(scopes):
        for j, (node_b, files_b) in enumerate(scopes[i+1:], start=i+1):
            for pattern_a in files_a:
                for pattern_b in files_b:
                    if patterns_overlap(pattern_a, pattern_b):
                        conflicts.append((node_a, node_b))
                        break
    
    return conflicts

def patterns_overlap(pattern_a: str, pattern_b: str) -> bool:
    """Check if two glob patterns overlap."""
    if pattern_a == pattern_b:
        return True
    if pattern_a.startswith(pattern_b) or pattern_b.startswith(pattern_a):
        return True
    return False
```

### Step 5: Implement Planner

**File**: `planner.py`

```python
import anthropic
import json
from typing import Optional
from .models import TaskDAG, TaskNode, NodeKind

PLANNER_PROMPT = """
You are a task decomposition expert for code editing tasks.

Given a user request and repository context, produce a JSON task DAG.

Request: {request}

Repository context:
- File tree: {file_tree}
- Tech stack: {tech_stack}
- Recent changes: {recent_commits}

Requirements:
1. Break into 3-12 nodes (prefer fewer, high-level nodes)
2. Each node needs: id, kind, description, scope_files, depends_on, estimated_cost_usd
3. Node kinds: localize, edit, test_gen, review, refactor, migrate
4. Maximize parallelism: only add dependencies that are NECESSARY for correctness
5. Scope files: be specific (e.g., src/auth/*.ts not src/**)
6. Cost estimates: $0.05-$0.50 per node (localize cheap, edit expensive)

Output ONLY valid JSON matching this schema:
{{
  "nodes": [
    {{
      "id": "n1",
      "kind": "localize",
      "description": "Find all usages of authenticate function",
      "scope_files": ["src/**/*.ts"],
      "depends_on": [],
      "estimated_cost_usd": 0.08
    }}
  ]
}}
"""

class Planner:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def decompose(
        self,
        request: str,
        repo_context: dict,
        session_id: str,
        session_budget: float
    ) -> TaskDAG:
        """Decompose user request into task DAG."""
        
        prompt = PLANNER_PROMPT.format(
            request=request,
            file_tree=repo_context.get("file_tree", ""),
            tech_stack=repo_context.get("tech_stack", ""),
            recent_commits=repo_context.get("recent_commits", "")
        )
        
        response = self.client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        content = response.content[0].text
        dag_json = json.loads(content)
        
        # Convert to TaskDAG
        nodes = [
            TaskNode(
                id=n["id"],
                kind=NodeKind(n["kind"]),
                description=n["description"],
                scope_files=n["scope_files"],
                depends_on=n.get("depends_on", []),
                estimated_cost_usd=n["estimated_cost_usd"]
            )
            for n in dag_json["nodes"]
        ]
        
        return TaskDAG(
            nodes=nodes,
            session_id=session_id
        )
```

### Step 6: Implement Scheduler

**File**: `scheduler.py`

```python
from typing import List
from .models import TaskDAG, TaskNode

class Wave:
    def __init__(self, wave_id: int, nodes: List[TaskNode]):
        self.id = wave_id
        self.nodes = nodes
        self.status = "pending"

class ExecutionPlan:
    def __init__(self, dag: TaskDAG, waves: List[Wave]):
        self.dag = dag
        self.waves = waves
        self.total_cost = sum(n.estimated_cost_usd for n in dag.nodes)

class Scheduler:
    def partition(self, dag: TaskDAG) -> ExecutionPlan:
        """Partition DAG into waves using topological sort."""
        node_map = dag.node_map
        remaining = list(dag.nodes)
        completed = set()
        waves = []
        
        while remaining:
            ready = [
                n for n in remaining
                if all(dep in completed for dep in n.depends_on)
            ]
            
            if not ready:
                raise ValueError("Cannot partition DAG: cycle or missing deps")
            
            wave = Wave(wave_id=len(waves), nodes=ready)
            waves.append(wave)
            
            completed.update(n.id for n in ready)
            remaining = [n for n in remaining if n not in ready]
        
        return ExecutionPlan(dag=dag, waves=waves)
```

### Step 7: Implement Dispatcher

**File**: `dispatcher.py`

```python
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional
from .models import TaskNode, SubagentResult, NodeStatus, NodeKind
from datetime import datetime

# Tool mapping by node kind
TOOL_SETS = {
    NodeKind.LOCALIZE: ["Read", "Grep", "LSP"],
    NodeKind.EDIT: ["Read", "Write", "Edit", "Bash"],
    NodeKind.TEST_GEN: ["Read", "Write", "Bash"],
    NodeKind.REVIEW: ["Read", "Bash"],
    NodeKind.REFACTOR: ["Read", "Write", "Edit", "LSP"],
    NodeKind.MIGRATE: ["Read", "Write", "Bash"]
}

class Dispatcher:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.worktree_base = repo_root / ".lyra" / "worktrees"
        self.worktree_base.mkdir(parents=True, exist_ok=True)
    
    async def dispatch_wave(
        self,
        wave,
        session_id: str
    ) -> List[SubagentResult]:
        """Dispatch all nodes in wave in parallel."""
        tasks = [
            self.dispatch_node(node, session_id)
            for node in wave.nodes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(SubagentResult(
                    node_id=wave.nodes[i].id,
                    status=NodeStatus.FAILURE,
                    commit_hash=None,
                    files_touched=[],
                    cost_usd=0.0,
                    duration_seconds=0.0,
                    summary="",
                    error=str(result)
                ))
            else:
                processed.append(result)
        
        return processed
    
    async def dispatch_node(
        self,
        node: TaskNode,
        session_id: str
    ) -> SubagentResult:
        """Execute node in isolated worktree."""
        start_time = datetime.utcnow()
        
        # Create worktree
        worktree_path = self.worktree_base / f"dag-{session_id}-{node.id}"
        branch_name = f"dag/{session_id}/{node.id}"
        
        try:
            # Setup worktree
            self._create_worktree(worktree_path, branch_name)
            
            # Execute subagent
            result = await self._run_subagent(node, worktree_path)
            
            # Get commit hash
            commit_hash = self._get_commit_hash(worktree_path)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return SubagentResult(
                node_id=node.id,
                status=NodeStatus.SUCCESS,
                commit_hash=commit_hash,
                files_touched=result.get("files_touched", []),
                cost_usd=result.get("cost_usd", 0.0),
                duration_seconds=duration,
                summary=result.get("summary", ""),
            )
        
        finally:
            # Cleanup worktree
            self._remove_worktree(worktree_path)
    
    def _create_worktree(self, path: Path, branch: str):
        """Create git worktree."""
        subprocess.run([
            "git", "worktree", "add",
            str(path), "-b", branch
        ], cwd=self.repo_root, check=True)
    
    def _remove_worktree(self, path: Path):
        """Remove git worktree."""
        subprocess.run([
            "git", "worktree", "remove",
            str(path), "--force"
        ], cwd=self.repo_root)
    
    def _get_commit_hash(self, worktree_path: Path) -> Optional[str]:
        """Get current commit hash in worktree."""
        result = subprocess.run([
            "git", "rev-parse", "HEAD"
        ], cwd=worktree_path, capture_output=True, text=True)
        
        return result.stdout.strip() if result.returncode == 0 else None
    
    async def _run_subagent(
        self,
        node: TaskNode,
        worktree_path: Path
    ) -> dict:
        """Run subagent in worktree."""
        # In real implementation, this initializes Lyra subagent
        # with scope_files, budgets, allowed_tools
        await asyncio.sleep(0.5)  # Simulate work
        
        return {
            "files_touched": [],
            "cost_usd": node.estimated_cost_usd,
            "summary": f"Completed {node.description}"
        }
```

### Step 8: CLI Integration

**File**: `harness/plugins/dag_teams/__init__.py`

```python
import asyncio
from pathlib import Path
from .planner import Planner
from .validator import validate_dag
from .scheduler import Scheduler
from .dispatcher import Dispatcher

class DAGTeamsPlugin:
    def __init__(self, repo_root: Path, api_key: str):
        self.planner = Planner(api_key)
        self.scheduler = Scheduler()
        self.dispatcher = Dispatcher(repo_root)
    
    async def execute(
        self,
        request: str,
        repo_context: dict,
        session_id: str,
        session_budget: float
    ):
        """Execute DAG Teams workflow."""
        
        # Phase 1: Planning
        print("Planning...")
        dag = self.planner.decompose(
            request, repo_context, session_id, session_budget
        )
        
        # Validate
        validation = validate_dag(dag, session_budget)
        if not validation.is_valid:
            raise ValueError(f"Invalid DAG: {validation.errors}")
        
        # Phase 2: Scheduling
        print("Scheduling...")
        plan = self.scheduler.partition(dag)
        print(f"Generated {len(plan.waves)} waves")
        
        # Phase 3: Execution
        for wave_idx, wave in enumerate(plan.waves):
            print(f"Executing wave {wave_idx} ({len(wave.nodes)} nodes)...")
            results = await self.dispatcher.dispatch_wave(wave, session_id)
            print(f"Wave {wave_idx} complete")
        
        print("DAG Teams execution complete")
```

## Testing

### Unit Tests

```python
import pytest
from harness.plugins.dag_teams.models import TaskDAG, TaskNode, NodeKind
from harness.plugins.dag_teams.validator import validate_dag

def test_validate_dag_detects_cycle():
    nodes = [
        TaskNode("n1", NodeKind.EDIT, "A", ["a.py"], ["n2"], 0.1),
        TaskNode("n2", NodeKind.EDIT, "B", ["b.py"], ["n1"], 0.1),
    ]
    dag = TaskDAG(nodes, "test-session")
    
    result = validate_dag(dag, 10.0)
    assert not result.is_valid
    assert "cycle" in result.errors[0].lower()
```

## Debugging Tips

1. **Enable verbose logging**: `logging.basicConfig(level=logging.DEBUG)`
2. **Inspect DAG**: Save to `.lyra/state/dag.json`
3. **View worktrees**: Run `git worktree list`
4. **Check merge status**: `git status` in session branch

## Common Pitfalls

1. **Worktree cleanup**: Always use try/finally
2. **Budget tracking**: Account for 1.5× estimated cost
3. **Scope validation**: Verify glob patterns don't overlap
4. **Cycle detection**: Run validator before scheduling

## References

- [architecture.md](architecture.md) - System overview
- [system-design.md](system-design.md) - API contracts
