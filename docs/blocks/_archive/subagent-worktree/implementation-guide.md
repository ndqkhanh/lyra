# Subagent Worktree Implementation Guide

## Prerequisites

Before implementing subagent worktrees, ensure:

- Python 3.11+
- Git 2.30+ (worktree support)
- LiteLLM configured with provider credentials
- Existing AgentLoop implementation
- ToolRegistry with Read, Edit, Write, Bash, Grep

## Step-by-Step Implementation

### Step 1: WorktreeManager Setup

Create the worktree management layer.

```python
# lyra/subagent/worktree_manager.py

from pathlib import Path
import subprocess
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import structlog

logger = structlog.get_logger()

@dataclass
class WorktreeAllocation:
    subagent_id: str
    path: Path
    branch_name: str
    created_at: str
    session_id: str
    
    def to_dict(self):
        return {
            **asdict(self),
            'path': str(self.path),
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            subagent_id=data['subagent_id'],
            path=Path(data['path']),
            branch_name=data['branch_name'],
            created_at=data['created_at'],
            session_id=data['session_id'],
        )


class WorktreeRegistry:
    """Persistent registry of active worktrees."""
    
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._write({})
    
    def _read(self) -> dict:
        with open(self.registry_path) as f:
            return json.load(f)
    
    def _write(self, data: dict):
        with open(self.registry_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register(self, allocation: WorktreeAllocation):
        data = self._read()
        data[allocation.subagent_id] = allocation.to_dict()
        self._write(data)
    
    def unregister(self, subagent_id: str):
        data = self._read()
        data.pop(subagent_id, None)
        self._write(data)
    
    def get(self, subagent_id: str) -> Optional[WorktreeAllocation]:
        data = self._read()
        if subagent_id in data:
            return WorktreeAllocation.from_dict(data[subagent_id])
        return None
    
    def all(self) -> list[WorktreeAllocation]:
        data = self._read()
        return [WorktreeAllocation.from_dict(v) for v in data.values()]


class WorktreeManager:
    """Manages git worktree lifecycle."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.worktree_base = repo_root / ".lyra" / "worktrees"
        self.registry = WorktreeRegistry(
            self.worktree_base / "registry.json"
        )
    
    def allocate(
        self, session_id: str, subagent_id: str, base_branch: str
    ) -> WorktreeAllocation:
        """
        Create a new git worktree on a session-scoped branch.
        
        Args:
            session_id: Parent session ID
            subagent_id: Unique subagent identifier
            base_branch: Branch to branch from (usually session branch)
        
        Returns:
            WorktreeAllocation with path and branch name
        """
        branch_name = f"{session_id}-sub-{subagent_id}"
        worktree_path = self.worktree_base / session_id / subagent_id
        
        # Ensure parent directory exists
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Allocating worktree",
            subagent_id=subagent_id,
            path=str(worktree_path),
            branch=branch_name,
        )
        
        try:
            # Create worktree
            subprocess.run(
                [
                    "git", "worktree", "add",
                    "-b", branch_name,
                    str(worktree_path),
                    base_branch,
                ],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                "Worktree allocation failed",
                error=e.stderr,
                subagent_id=subagent_id,
            )
            raise WorktreeAllocationError(f"Failed to create worktree: {e.stderr}")
        
        allocation = WorktreeAllocation(
            subagent_id=subagent_id,
            path=worktree_path,
            branch_name=branch_name,
            created_at=datetime.utcnow().isoformat(),
            session_id=session_id,
        )
        
        self.registry.register(allocation)
        return allocation
    
    def remove(self, subagent_id: str):
        """
        Remove worktree and delete branch.
        """
        allocation = self.registry.get(subagent_id)
        if not allocation:
            logger.warning(
                "Attempted to remove non-existent worktree",
                subagent_id=subagent_id,
            )
            return
        
        logger.info(
            "Removing worktree",
            subagent_id=subagent_id,
            path=str(allocation.path),
        )
        
        # Remove worktree
        try:
            subprocess.run(
                ["git", "worktree", "remove", str(allocation.path)],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            # Force removal if worktree is modified
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(allocation.path)],
                cwd=self.repo_root,
                check=True,
            )
        
        # Delete branch
        subprocess.run(
            ["git", "branch", "-D", allocation.branch_name],
            cwd=self.repo_root,
            check=True,
        )
        
        self.registry.unregister(subagent_id)
    
    def reconcile_stale(self) -> list[str]:
        """
        Remove worktrees left from crashed sessions.
        
        Returns:
            List of removed subagent IDs
        """
        logger.info("Reconciling stale worktrees")
        
        # Get list of active worktrees from git
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        
        active_paths = set()
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                active_paths.add(line.split()[1])
        
        # Find registry entries without active worktrees
        removed = []
        for allocation in self.registry.all():
            if str(allocation.path) not in active_paths:
                logger.warning(
                    "Found stale worktree",
                    subagent_id=allocation.subagent_id,
                    path=str(allocation.path),
                )
                self.registry.unregister(allocation.subagent_id)
                removed.append(allocation.subagent_id)
        
        return removed


class WorktreeAllocationError(Exception):
    """Failed to allocate worktree."""
```

### Step 2: FSSandbox Implementation

Enforce scope restrictions at the filesystem layer.

```python
# lyra/subagent/fs_sandbox.py

from pathlib import Path
import pathspec
import structlog

logger = structlog.get_logger()


class FSSandbox:
    """
    Enforces filesystem scope constraints.
    """
    
    def __init__(self, root: Path, scope_globs: list[str]):
        self.root = root.resolve()
        self.scope_globs = scope_globs
        # Use pathspec for gitignore-style glob matching
        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', scope_globs)
    
    def is_in_scope(self, path: Path) -> bool:
        """
        Check if path matches any scope pattern.
        """
        # Resolve to absolute path
        resolved = (self.root / path).resolve()
        
        # Check if inside root
        try:
            relative = resolved.relative_to(self.root)
        except ValueError:
            # Path is outside root
            return False
        
        # Check against scope patterns
        return self.spec.match_file(str(relative))
    
    def validate_write(self, path: Path):
        """
        Validate write operation is within scope.
        Raises PermissionError if outside scope.
        """
        if not self.is_in_scope(path):
            logger.error(
                "Write denied: outside scope",
                path=str(path),
                scope=self.scope_globs,
            )
            raise PermissionError(
                f"Write to {path} denied: outside scope {self.scope_globs}"
            )
        
        logger.debug("Write allowed", path=str(path))
    
    def validate_read(self, path: Path):
        """
        Log reads outside scope (allowed but audited).
        """
        if not self.is_in_scope(path):
            logger.warning(
                "Read outside scope",
                path=str(path),
                scope=self.scope_globs,
            )
    
    def wrap_tool(self, tool):
        """
        Wrap a tool to inject scope validation.
        """
        original_execute = tool.execute
        
        def validated_execute(**kwargs):
            # Extract file paths from kwargs
            paths = []
            for key in ['file_path', 'path', 'file']:
                if key in kwargs:
                    paths.append(Path(kwargs[key]))
            
            # Validate based on tool type
            if tool.writes:
                for path in paths:
                    self.validate_write(path)
            else:
                for path in paths:
                    self.validate_read(path)
            
            # Execute original tool
            return original_execute(**kwargs)
        
        tool.execute = validated_execute
        return tool
```

### Step 3: Subagent Implementation

The core subagent execution logic.

```python
# lyra/subagent/subagent.py

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Optional
import structlog

from lyra.agent.loop import AgentLoop, AgentOutcome
from lyra.agent.message import Message
from lyra.subagent.fs_sandbox import FSSandbox
from lyra.tools.registry import ToolRegistry
from lyra.llm.builder import build_llm

logger = structlog.get_logger()


@dataclass
class Budgets:
    max_steps: Optional[int] = None
    max_cost_usd: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            max_steps=data.get('max_steps'),
            max_cost_usd=data.get('max_cost_usd'),
        )


@dataclass
class SubagentResult:
    subagent_id: str
    status: str  # success, budget_exceeded, error
    summary: str
    files_touched: list[str]
    commit_hash: Optional[str]
    cost_usd: float
    duration_ms: int
    trace_hash: str
    
    def to_json(self) -> str:
        import json
        return json.dumps(self.__dict__, indent=2)


class Subagent:
    """
    An agent instance that runs in an isolated worktree.
    """
    
    def __init__(
        self,
        parent_session,
        subagent_id: str,
        purpose: str,
        scope: list[str],
        worktree_path: Path,
        branch_name: str,
        budgets: Budgets,
        allowed_tools: list[str],
    ):
        self.parent_session = parent_session
        self.subagent_id = subagent_id
        self.purpose = purpose
        self.scope = scope
        self.worktree_path = worktree_path
        self.branch_name = branch_name
        self.budgets = budgets
        self.allowed_tools = allowed_tools or [
            "Read", "Edit", "Write", "Bash", "Grep"
        ]
        
        # Initialize components
        self.fs_sandbox = FSSandbox(worktree_path, scope)
        self.narrowed_tools = self._build_narrowed_tools()
        self.llm = self._build_llm_smart()
        self.start_time = None
        self.end_time = None
    
    def run(self) -> SubagentResult:
        """
        Execute the subagent's task.
        """
        import time
        self.start_time = time.time()
        
        logger.info(
            "Starting subagent",
            subagent_id=self.subagent_id,
            purpose=self.purpose[:100],
            scope=self.scope,
        )
        
        context_seed = self._build_context_seed()
        system_prompt = self._build_system_prompt()
        
        loop = AgentLoop(
            llm=self.llm,
            tools=self.narrowed_tools,
            hooks=[],
            permission_mode=(
                "auto" if self.parent_session.trust_level == "high" else "manual"
            ),
            system_prompt=system_prompt,
            budget=self.budgets,
        )
        
        try:
            outcome = loop.run(
                task=self.purpose,
                initial_messages=context_seed,
            )
            
            observation = self._summarize_outcome(outcome)
            commit_hash = self._commit_changes()
            
            self.end_time = time.time()
            duration_ms = int((self.end_time - self.start_time) * 1000)
            
            result = SubagentResult(
                subagent_id=self.subagent_id,
                status=outcome.stop_reason,
                summary=observation,
                files_touched=self._get_modified_files(),
                commit_hash=commit_hash,
                cost_usd=loop.cost_usd,
                duration_ms=duration_ms,
                trace_hash=self._offload_trace(outcome),
            )
            
            logger.info(
                "Subagent completed",
                subagent_id=self.subagent_id,
                status=result.status,
                files_touched=len(result.files_touched),
                cost_usd=result.cost_usd,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Subagent failed",
                subagent_id=self.subagent_id,
                error=str(e),
            )
            raise
    
    def _build_llm_smart(self):
        """
        Build LLM with smart model (deepseek-v4-pro → deepseek-reasoner).
        """
        return build_llm(
            model=self.parent_session.smart_model,
            provider=self.parent_session.provider,
        )
    
    def _build_context_seed(self) -> list[Message]:
        """
        Build initial context: SOUL + plan + purpose + scope.
        """
        soul = self.parent_session.soul_content
        plan_summary = self.parent_session.plan.summarize(max_lines=50)
        
        context = f"""Context from parent session:

SOUL (Project Identity):
{soul}

Plan Summary:
{plan_summary}

Your Purpose:
{self.purpose}

Your Scope (files you may edit):
{chr(10).join(f"  - {pattern}" for pattern in self.scope)}
"""
        
        return [Message(role="system", content=context)]
    
    def _build_system_prompt(self) -> str:
        """
        Subagent-specific system prompt with constraints.
        """
        return f"""You are a subagent working on a focused task.

Purpose: {self.purpose}

Scope: You may only edit files matching these patterns:
{chr(10).join(f"  - {pattern}" for pattern in self.scope)}

Constraints:
- Do not edit files outside your scope
- Do not spawn subagents (recursion depth limit)
- Return a clear summary of what you accomplished
- Honor the parent's SOUL and plan

Work efficiently to complete your task within the given scope.
"""
    
    def _build_narrowed_tools(self) -> list:
        """
        Build tool registry with scope enforcement.
        """
        # Get all tools
        all_tools = ToolRegistry.all()
        
        # Remove Spawn tool (prevent recursion)
        tools = [t for t in all_tools if t.name != "Spawn"]
        
        # Filter to allowed tools
        tools = [t for t in tools if t.name in self.allowed_tools]
        
        # Wrap with sandbox
        return [self.fs_sandbox.wrap_tool(t) for t in tools]
    
    def _summarize_outcome(self, outcome: AgentOutcome) -> str:
        """
        Summarize agent outcome into observation.
        """
        # Extract key information from trace
        # In practice, use LLM to generate summary
        return f"Completed {self.purpose}. Status: {outcome.stop_reason}"
    
    def _commit_changes(self) -> Optional[str]:
        """
        Commit changes in worktree and return commit hash.
        """
        # Check if there are changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
        )
        
        if not status.stdout.strip():
            logger.info("No changes to commit", subagent_id=self.subagent_id)
            return None
        
        # Add all changes
        subprocess.run(
            ["git", "add", "."],
            cwd=self.worktree_path,
            check=True,
        )
        
        # Commit
        commit_msg = f"Subagent {self.subagent_id}: {self.purpose[:80]}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=self.worktree_path,
            check=True,
        )
        
        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        
        commit_hash = result.stdout.strip()
        logger.info(
            "Changes committed",
            subagent_id=self.subagent_id,
            commit=commit_hash[:8],
        )
        
        return commit_hash
    
    def _get_modified_files(self) -> list[str]:
        """
        Get list of files modified in worktree.
        """
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD^", "HEAD"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return []
        
        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]
    
    def _offload_trace(self, outcome: AgentOutcome) -> str:
        """
        Offload trace to artifact storage and return hash.
        """
        import hashlib
        import json
        
        trace_json = json.dumps(outcome.trace, indent=2)
        trace_hash = hashlib.sha256(trace_json.encode()).hexdigest()
        
        # Write to artifact storage
        artifact_path = (
            self.parent_session.repo_root
            / ".lyra"
            / "artifacts"
            / trace_hash
        )
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(trace_json)
        
        return trace_hash
```

### Step 4: Orchestrator Implementation

Coordinate subagent lifecycle.

```python
# lyra/subagent/orchestrator.py

from threading import Semaphore
import structlog

from lyra.subagent.worktree_manager import WorktreeManager
from lyra.subagent.subagent import Subagent, Budgets, SubagentResult

logger = structlog.get_logger()


class SubagentOrchestrator:
    """
    Central coordinator for subagent lifecycle.
    """
    
    def __init__(self, parent_session):
        self.parent_session = parent_session
        self.worktree_manager = WorktreeManager(parent_session.repo_root)
        self.concurrency_limiter = Semaphore(value=4)  # Default: 4 concurrent
        self.active_subagents = {}
        self.next_id = 0
    
    def spawn(
        self,
        purpose: str,
        scope: list[str],
        budgets: Optional[Budgets] = None,
        allowed_tools: Optional[list[str]] = None,
    ) -> SubagentResult:
        """
        Spawn a subagent in an isolated worktree.
        Blocks until subagent completes.
        """
        with self.concurrency_limiter:
            subagent_id = self._generate_id()
            
            try:
                # Allocate worktree
                allocation = self.worktree_manager.allocate(
                    session_id=self.parent_session.id,
                    subagent_id=subagent_id,
                    base_branch=self.parent_session.branch,
                )
                
                # Build subagent
                subagent = Subagent(
                    parent_session=self.parent_session,
                    subagent_id=subagent_id,
                    purpose=purpose,
                    scope=scope,
                    worktree_path=allocation.path,
                    branch_name=allocation.branch_name,
                    budgets=budgets or Budgets(),
                    allowed_tools=allowed_tools,
                )
                
                self.active_subagents[subagent_id] = subagent
                
                # Run subagent
                result = subagent.run()
                
                # Merge changes
                if result.commit_hash:
                    self._merge_changes(subagent, result)
                
                return result
                
            finally:
                # Always cleanup
                self._cleanup_subagent(subagent_id)
    
    def _generate_id(self) -> str:
        """Generate unique subagent ID."""
        self.next_id += 1
        return f"sub-{self.next_id}"
    
    def _merge_changes(self, subagent: Subagent, result: SubagentResult):
        """
        Merge subagent branch into session branch.
        """
        import subprocess
        
        logger.info(
            "Merging subagent changes",
            subagent_id=subagent.subagent_id,
            branch=subagent.branch_name,
        )
        
        # Checkout session branch
        subprocess.run(
            ["git", "checkout", self.parent_session.branch],
            cwd=self.parent_session.repo_root,
            check=True,
        )
        
        # Attempt merge
        try:
            subprocess.run(
                ["git", "merge", "--no-ff", subagent.branch_name],
                cwd=self.parent_session.repo_root,
                check=True,
                capture_output=True,
            )
            logger.info("Merge successful", subagent_id=subagent.subagent_id)
            
        except subprocess.CalledProcessError:
            logger.warning("Merge conflict detected", subagent_id=subagent.subagent_id)
            # In production, invoke conflict-resolver here
            raise MergeConflictError(
                f"Merge conflict for subagent {subagent.subagent_id}"
            )
    
    def _cleanup_subagent(self, subagent_id: str):
        """
        Cleanup subagent resources.
        """
        try:
            self.active_subagents.pop(subagent_id, None)
            self.worktree_manager.remove(subagent_id)
        except Exception as e:
            logger.error(
                "Cleanup failed",
                subagent_id=subagent_id,
                error=str(e),
            )


class MergeConflictError(Exception):
    """Failed to merge subagent changes."""
```

## Configuration

Add to `lyra.toml`:

```toml
[subagent]
# Maximum concurrent subagents
max_concurrent = 4

# Default budgets
default_max_steps = 30
default_max_cost_usd = 2.0

# Smart model for subagents
smart_model = "deepseek-v4-pro"

# Disk usage threshold (refuse spawn if exceeded)
disk_threshold = 0.90

# Enable auto-merge (vs always manual review)
auto_merge = true
```

## Testing

### Unit Tests

```python
# tests/subagent/test_worktree_manager.py

import pytest
from pathlib import Path
from lyra.subagent.worktree_manager import WorktreeManager

def test_allocate_worktree(tmp_path):
    """Test worktree allocation."""
    # Setup git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    
    manager = WorktreeManager(repo)
    allocation = manager.allocate("session-1", "sub-1", "main")
    
    assert allocation.path.exists()
    assert allocation.branch_name == "session-1-sub-sub-1"
    
    # Cleanup
    manager.remove("sub-1")
    assert not allocation.path.exists()


# tests/subagent/test_fs_sandbox.py

def test_scope_enforcement():
    """Test FSSandbox scope validation."""
    sandbox = FSSandbox(Path("/tmp/worktree"), ["src/**", "tests/**"])
    
    # In scope
    assert sandbox.is_in_scope(Path("src/foo.py"))
    assert sandbox.is_in_scope(Path("tests/test_foo.py"))
    
    # Out of scope
    assert not sandbox.is_in_scope(Path("docs/README.md"))
    
    # Write validation
    with pytest.raises(PermissionError):
        sandbox.validate_write(Path("docs/README.md"))
```

### Integration Tests

```python
# tests/subagent/test_integration.py

def test_subagent_lifecycle(session):
    """Test complete subagent spawn-to-merge."""
    orchestrator = SubagentOrchestrator(session)
    
    result = orchestrator.spawn(
        purpose="Add test for foo()",
        scope=["tests/**"],
        budgets=Budgets(max_steps=10, max_cost_usd=0.50),
    )
    
    assert result.status == "success"
    assert len(result.files_touched) > 0
    assert result.commit_hash is not None
    assert result.cost_usd < 0.50
```

## Common Pitfalls

### 1. Forgetting to Set CWD

**Problem**: Tools execute in wrong directory.

**Solution**: Always pass `cwd=worktree_path` to subprocess calls.

```python
# Wrong
subprocess.run(["git", "status"], check=True)

# Right
subprocess.run(["git", "status"], cwd=self.worktree_path, check=True)
```

### 2. Not Cleaning Up on Error

**Problem**: Worktrees leak on exceptions.

**Solution**: Use `try/finally` in orchestrator.

```python
try:
    result = subagent.run()
    return result
finally:
    self._cleanup_subagent(subagent_id)
```

### 3. Scope Patterns Too Broad

**Problem**: `scope=["**"]` defeats isolation.

**Solution**: Be specific: `["src/auth/**", "tests/auth/**"]`

### 4. Not Handling Merge Conflicts

**Problem**: Merge failures crash the session.

**Solution**: Catch `CalledProcessError`, invoke conflict-resolver or escalate.

## Debugging Tips

### View Subagent Traces

```bash
# Find trace hash in SubagentResult
cat .lyra/artifacts/<trace_hash>
```

### List Active Worktrees

```bash
git worktree list
cat .lyra/worktrees/registry.json
```

### Force Cleanup Stale Worktrees

```python
from lyra.subagent.worktree_manager import WorktreeManager

manager = WorktreeManager(Path("."))
removed = manager.reconcile_stale()
print(f"Removed {len(removed)} stale worktrees")
```

### Enable Debug Logging

```python
import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
)
```

## Performance Optimization

### 1. Worktree Pooling (Future)

Pre-allocate worktrees for instant spawn:

```python
class WorktreePool:
    def __init__(self, manager: WorktreeManager, pool_size: int = 4):
        self.manager = manager
        self.pool = Queue(maxsize=pool_size)
        self._fill_pool()
    
    def acquire(self) -> WorktreeAllocation:
        return self.pool.get()
    
    def release(self, allocation: WorktreeAllocation):
        # Reset worktree state
        subprocess.run(["git", "reset", "--hard"], cwd=allocation.path)
        self.pool.put(allocation)
```

### 2. Shallow Worktrees (v2)

Reduce disk and speed up allocation:

```bash
git worktree add --depth=1 -b branch path base
```

### 3. Parallel Spawn

Spawn multiple subagents without waiting:

```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(orchestrator.spawn, purpose, scope)
        for purpose, scope in tasks
    ]
    results = [f.result() for f in futures]
```

---

**Related Documentation:**
- [Architecture](./architecture.md)
- [Architecture Tradeoffs](./architecture-tradeoffs.md)
- [System Design](./system-design.md)
- [Deep Dive](./deep-dive.md)
