# Subagent Worktree Deep Dive

## Advanced Patterns

### Pattern 1: Speculative Execution

Execute multiple approaches in parallel and pick the best result.

```python
class SpeculativeExecutor:
    """
    Spawn multiple subagents with different approaches,
    evaluate results, and merge the best one.
    """
    
    def __init__(self, orchestrator: SubagentOrchestrator):
        self.orchestrator = orchestrator
    
    def execute_speculative(
        self,
        task: str,
        approaches: list[dict],
        evaluator: Callable[[SubagentResult], float],
    ) -> SubagentResult:
        """
        Execute multiple approaches speculatively.
        
        Args:
            task: Base task description
            approaches: List of approach configs
            evaluator: Function to score results (higher is better)
        
        Returns:
            Best result according to evaluator
        """
        import concurrent.futures
        
        # Spawn all approaches in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i, approach in enumerate(approaches):
                purpose = f"{task} - Approach {i+1}: {approach['strategy']}"
                future = executor.submit(
                    self.orchestrator.spawn,
                    purpose=purpose,
                    scope=approach['scope'],
                    budgets=approach.get('budgets'),
                )
                futures.append((approach, future))
            
            # Collect results
            results = []
            for approach, future in futures:
                try:
                    result = future.result()
                    score = evaluator(result)
                    results.append((score, result, approach))
                except Exception as e:
                    logger.warning(f"Approach failed: {e}")
            
            # Pick best result
            if not results:
                raise ValueError("All approaches failed")
            
            results.sort(key=lambda x: x[0], reverse=True)
            best_score, best_result, best_approach = results[0]
            
            logger.info(
                "Speculative execution complete",
                best_score=best_score,
                best_approach=best_approach['strategy'],
                total_cost=sum(r[1].cost_usd for r in results),
            )
            
            return best_result


# Example usage
def evaluate_test_quality(result: SubagentResult) -> float:
    """
    Score test implementation quality.
    """
    score = 0.0
    
    # Higher score for more tests added
    if result.test_delta:
        score += result.test_delta.added * 10
        score += result.test_delta.passing_new * 5
        score -= result.test_delta.regressions * 20
    
    # Lower score for higher cost
    score -= result.cost_usd * 10
    
    # Lower score if failed
    if result.status != "success":
        score -= 50
    
    return score


executor = SpeculativeExecutor(orchestrator)
result = executor.execute_speculative(
    task="Add comprehensive tests for auth module",
    approaches=[
        {
            "strategy": "unit tests first",
            "scope": ["tests/unit/auth/**"],
            "budgets": {"max_steps": 20, "max_cost_usd": 1.0},
        },
        {
            "strategy": "integration tests first",
            "scope": ["tests/integration/auth/**"],
            "budgets": {"max_steps": 20, "max_cost_usd": 1.0},
        },
        {
            "strategy": "property-based tests",
            "scope": ["tests/property/auth/**"],
            "budgets": {"max_steps": 25, "max_cost_usd": 1.5},
        },
    ],
    evaluator=evaluate_test_quality,
)
```

### Pattern 2: Progressive Refinement

Use subagent results to spawn more focused subagents.

```python
class ProgressiveRefiner:
    """
    Iteratively refine work through multiple subagent passes.
    """
    
    def refine_progressive(
        self,
        initial_purpose: str,
        scope: list[str],
        max_iterations: int = 3,
    ) -> list[SubagentResult]:
        """
        Progressive refinement through multiple passes.
        """
        results = []
        current_scope = scope
        
        for iteration in range(max_iterations):
            # Spawn subagent for this iteration
            purpose = f"{initial_purpose} - Iteration {iteration + 1}"
            if iteration > 0:
                # Incorporate feedback from previous iteration
                prev_result = results[-1]
                purpose += f"\n\nPrevious result: {prev_result.summary}"
                purpose += f"\nFocus on: {self._extract_todos(prev_result)}"
            
            result = self.orchestrator.spawn(
                purpose=purpose,
                scope=current_scope,
                budgets=Budgets(max_steps=15),
            )
            
            results.append(result)
            
            # Check if refinement is complete
            if self._is_complete(result):
                logger.info(f"Refinement complete after {iteration + 1} iterations")
                break
            
            # Narrow scope for next iteration based on what's left
            current_scope = self._narrow_scope(result, current_scope)
        
        return results
    
    def _is_complete(self, result: SubagentResult) -> bool:
        """Check if work is complete (no TODOs, tests passing)."""
        # In practice, use more sophisticated checks
        return "TODO" not in result.summary.lower()
```

### Pattern 3: Decomposition DAG

Break complex tasks into a dependency graph of subagents.

```python
class TaskDAG:
    """
    Dependency graph of subagent tasks.
    """
    
    def __init__(self):
        self.nodes = {}  # task_id -> task_config
        self.edges = {}  # task_id -> list[dependency_task_ids]
        self.results = {}  # task_id -> SubagentResult
    
    def add_task(
        self,
        task_id: str,
        purpose: str,
        scope: list[str],
        depends_on: list[str] = None,
    ):
        """Add a task to the DAG."""
        self.nodes[task_id] = {
            "purpose": purpose,
            "scope": scope,
        }
        self.edges[task_id] = depends_on or []
    
    def execute(self, orchestrator: SubagentOrchestrator) -> dict[str, SubagentResult]:
        """
        Execute DAG with maximum parallelism.
        """
        completed = set()
        in_flight = {}
        
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        while len(completed) < len(self.nodes):
            # Find ready tasks (dependencies satisfied)
            ready = [
                task_id
                for task_id in self.nodes
                if task_id not in completed
                and task_id not in in_flight
                and all(dep in completed for dep in self.edges[task_id])
            ]
            
            # Spawn ready tasks
            for task_id in ready:
                config = self.nodes[task_id]
                future = executor.submit(
                    orchestrator.spawn,
                    purpose=config["purpose"],
                    scope=config["scope"],
                )
                in_flight[task_id] = future
            
            # Wait for any task to complete
            if in_flight:
                done, pending = concurrent.futures.wait(
                    in_flight.values(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                
                # Process completed tasks
                for task_id, future in list(in_flight.items()):
                    if future in done:
                        self.results[task_id] = future.result()
                        completed.add(task_id)
                        del in_flight[task_id]
        
        executor.shutdown()
        return self.results


# Example: Refactor auth module
dag = TaskDAG()

# Phase 1: Analysis
dag.add_task(
    "analyze-auth",
    purpose="Analyze auth module and document current structure",
    scope=["docs/analysis/**"],
)

# Phase 2: Extract utilities (depends on analysis)
dag.add_task(
    "extract-utils",
    purpose="Extract reusable utilities from auth module",
    scope=["src/auth/utils/**"],
    depends_on=["analyze-auth"],
)

# Phase 3: Refactor handlers (depends on analysis and utils)
dag.add_task(
    "refactor-handlers",
    purpose="Refactor auth handlers to use extracted utilities",
    scope=["src/auth/handlers/**"],
    depends_on=["analyze-auth", "extract-utils"],
)

# Phase 3: Add tests (parallel with refactor)
dag.add_task(
    "add-tests",
    purpose="Add unit tests for auth utilities",
    scope=["tests/auth/**"],
    depends_on=["extract-utils"],
)

# Execute DAG
results = dag.execute(orchestrator)
```

## Optimization Techniques

### 1. Context Compression

Aggressively compress context seed to maximize subagent working memory.

```python
class ContextCompressor:
    """
    Compress parent context for subagent seeding.
    """
    
    def compress_soul(self, soul_content: str, max_tokens: int = 1000) -> str:
        """
        Compress SOUL.md to essential information.
        """
        # Use LLM to summarize
        prompt = f"""Summarize this project SOUL to {max_tokens} tokens, preserving:
- Core project purpose
- Key architectural decisions
- Critical constraints

SOUL:
{soul_content}
"""
        return self.llm.generate(prompt, max_tokens=max_tokens)
    
    def compress_plan(self, plan: Plan, focus_item: str) -> str:
        """
        Extract only the relevant plan section.
        """
        # Find the relevant feature item
        for section in plan.sections:
            for item in section.items:
                if focus_item in item.title:
                    return f"""Current Feature: {item.title}

Description: {item.description}

Acceptance Criteria:
{chr(10).join(f"- {c}" for c in item.acceptance_criteria)}

Status: {item.status}
"""
        
        # Fallback: return summary
        return plan.summarize(max_lines=30)
```

### 2. Lazy Artifact Loading

Return artifact references instead of full content.

```python
class ArtifactReference:
    """
    Reference to an artifact in storage.
    """
    
    def __init__(self, hash: str, artifact_type: str):
        self.hash = hash
        self.artifact_type = artifact_type
    
    def load(self, artifact_store) -> Any:
        """
        Lazy load artifact content.
        """
        return artifact_store.get(self.hash)


class SubagentResult:
    # ... existing fields ...
    
    trace_ref: Optional[ArtifactReference] = None
    
    def get_trace(self, artifact_store):
        """
        Lazy load trace on demand.
        """
        if self.trace_ref:
            return self.trace_ref.load(artifact_store)
        return None
```

### 3. Smart Model Caching

Cache LLM responses across subagents for identical contexts.

```python
class CachedLLM:
    """
    LLM wrapper with response caching.
    """
    
    def __init__(self, base_llm, cache_dir: Path):
        self.base_llm = base_llm
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate response with caching.
        """
        import hashlib
        import json
        
        # Generate cache key
        cache_key = hashlib.sha256(
            json.dumps({"prompt": prompt, "kwargs": kwargs}).encode()
        ).hexdigest()
        
        cache_file = self.cache_dir / cache_key
        
        # Check cache
        if cache_file.exists():
            logger.debug("Cache hit", cache_key=cache_key[:8])
            return cache_file.read_text()
        
        # Generate and cache
        response = self.base_llm.generate(prompt, **kwargs)
        cache_file.write_text(response)
        
        return response
```

## Edge Cases

### 1. Binary Files in Scope

**Problem**: Subagent attempts to edit binary files (images, compiled assets).

**Solution**: Filter binary files at scope validation.

```python
class FSSandbox:
    def is_binary(self, path: Path) -> bool:
        """
        Check if file is binary.
        """
        try:
            with open(path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except:
            return False
    
    def validate_write(self, path: Path):
        """
        Validate write, rejecting binary files.
        """
        if not self.is_in_scope(path):
            raise PermissionError(f"Path {path} outside scope")
        
        if self.is_binary(path):
            raise PermissionError(f"Cannot edit binary file {path}")
        
        logger.debug("Write allowed", path=str(path))
```

### 2. Circular Dependencies in DAG

**Problem**: Task A depends on B, B depends on A.

**Solution**: Detect cycles before execution.

```python
class TaskDAG:
    def validate(self):
        """
        Detect cycles using DFS.
        """
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.edges.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.nodes:
            if node not in visited:
                if has_cycle(node):
                    raise ValueError(f"Cycle detected in task DAG")
```

### 3. Subagent Exceeds Scope After Merge

**Problem**: Subagent's changes conflict with concurrent parent edits.

**Solution**: Pre-merge validation.

```python
class SubagentOrchestrator:
    def _merge_changes(self, subagent: Subagent, result: SubagentResult):
        """
        Merge with pre-validation.
        """
        # Get files modified by subagent
        subagent_files = set(result.files_touched)
        
        # Get files modified by parent since spawn
        parent_files = self._get_parent_modifications_since(subagent.start_time)
        
        # Check for overlap
        overlap = subagent_files & parent_files
        if overlap:
            logger.warning(
                "Subagent and parent modified same files",
                overlap=list(overlap),
            )
            # Invoke conflict resolver or escalate
        
        # Proceed with merge
        subprocess.run(
            ["git", "merge", "--no-ff", subagent.branch_name],
            cwd=self.parent_session.repo_root,
            check=True,
        )
```

### 4. Worktree Disk Space Exhaustion

**Problem**: Spawning 100+ subagents fills disk.

**Solution**: Preflight disk check and shallow worktrees.

```python
class SubagentOrchestrator:
    def _check_disk_space(self):
        """
        Check available disk space before spawning.
        """
        import shutil
        
        total, used, free = shutil.disk_usage(self.parent_session.repo_root)
        usage_percent = used / total
        
        if usage_percent > 0.90:
            raise DiskSpaceError(
                f"Disk usage at {usage_percent:.0%}, refusing to spawn subagent"
            )
        
        logger.debug(f"Disk usage: {usage_percent:.0%}")
```

## Internal Algorithms

### Conflict Resolution Algorithm

```python
class ConflictResolver:
    """
    Automated conflict resolution for subagent merges.
    """
    
    def resolve(
        self,
        subagent_branch: str,
        session_branch: str,
        repo_root: Path,
    ) -> bool:
        """
        Attempt to resolve merge conflict automatically.
        
        Returns:
            True if resolved, False if manual intervention needed
        """
        # Get conflict files
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        
        conflict_files = result.stdout.strip().split('\n')
        
        logger.info(f"Resolving conflicts in {len(conflict_files)} files")
        
        for file_path in conflict_files:
            if not self._resolve_file(file_path, repo_root):
                return False
        
        # Stage resolved files
        subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
        
        # Complete merge
        subprocess.run(
            ["git", "commit", "--no-edit"],
            cwd=repo_root,
            check=True,
        )
        
        return True
    
    def _resolve_file(self, file_path: str, repo_root: Path) -> bool:
        """
        Resolve conflicts in a single file.
        """
        full_path = repo_root / file_path
        content = full_path.read_text()
        
        # Strategy 1: Take ours (session branch) for certain file types
        if file_path.endswith(('.lock', 'package-lock.json', 'yarn.lock')):
            subprocess.run(
                ["git", "checkout", "--ours", file_path],
                cwd=repo_root,
                check=True,
            )
            return True
        
        # Strategy 2: Take theirs (subagent) for test files
        if 'test' in file_path:
            subprocess.run(
                ["git", "checkout", "--theirs", file_path],
                cwd=repo_root,
                check=True,
            )
            return True
        
        # Strategy 3: LLM-based resolution
        return self._llm_resolve(file_path, content, repo_root)
    
    def _llm_resolve(
        self, file_path: str, content: str, repo_root: Path
    ) -> bool:
        """
        Use LLM to resolve complex conflicts.
        """
        prompt = f"""Resolve this git merge conflict by choosing the best version.

File: {file_path}

Content with conflict markers:
{content}

Respond with the resolved content (without conflict markers).
"""
        
        resolved = self.llm.generate(prompt)
        
        # Validate resolved content (ensure no conflict markers)
        if '<<<<<<' in resolved or '>>>>>>>' in resolved:
            logger.error("LLM failed to resolve conflict")
            return False
        
        # Write resolved content
        (repo_root / file_path).write_text(resolved)
        return True
```

### Observation Summarizer Algorithm

```python
class ObservationSummarizer:
    """
    Generate concise observations from agent traces.
    """
    
    def summarize(
        self,
        outcome: AgentOutcome,
        purpose: str,
    ) -> str:
        """
        Summarize agent outcome into observation.
        """
        # Extract key facts from trace
        facts = self._extract_facts(outcome.trace)
        
        # Generate structured summary
        prompt = f"""Summarize this subagent execution into a concise observation.

Purpose: {purpose}

Facts:
{chr(10).join(f"- {fact}" for fact in facts)}

Trace summary:
- Steps: {len(outcome.trace)}
- Status: {outcome.stop_reason}
- Files modified: {', '.join(self._get_modified_files(outcome.trace))}

Generate a 2-3 sentence observation covering:
1. What was accomplished
2. Key findings or issues
3. Next steps (if incomplete)
"""
        
        return self.llm.generate(prompt, max_tokens=200)
    
    def _extract_facts(self, trace: list[dict]) -> list[str]:
        """
        Extract key facts from trace.
        """
        facts = []
        
        for step in trace:
            if step['type'] == 'tool_result':
                tool_name = step['tool_name']
                
                if tool_name == 'Bash':
                    # Extract test results
                    if 'passed' in step['result'].lower():
                        facts.append("Tests passed")
                    elif 'failed' in step['result'].lower():
                        facts.append("Tests failed")
                
                elif tool_name == 'Grep':
                    # Extract search findings
                    count = len(step['result'].split('\n'))
                    facts.append(f"Found {count} occurrences")
        
        return facts
```

## Research References

### Academic Papers

1. **"AutoGPT: An Autonomous GPT-4 Experiment"** (2023)
   - Early exploration of autonomous agent systems
   - Relevance: Task decomposition patterns

2. **"ReAct: Synergizing Reasoning and Acting in Language Models"** (Yao et al., 2023)
   - Interleaving reasoning and action
   - Relevance: Agent loop design

3. **"Voyager: An Open-Ended Embodied Agent with Large Language Models"** (Wang et al., 2023)
   - Curriculum learning for agents
   - Relevance: Progressive refinement pattern

4. **"ToolFormer: Language Models Can Teach Themselves to Use Tools"** (Schick et al., 2023)
   - Tool use learning
   - Relevance: Tool narrowing and validation

### Production Systems

1. **Devin (Cognition Labs)** - Autonomous software engineer
   - Multi-agent coordination
   - Long-running tasks with checkpointing

2. **AutoGPT** - Autonomous task execution
   - Goal decomposition
   - Self-reflection loops

3. **Claude Code (Anthropic)** - AI pair programmer
   - Context management
   - Permission system design

## Future Improvements

### Short-term (v2)

1. **Shallow Worktrees**
   - Reduce disk usage 5x
   - Faster allocation (30ms vs 50ms)
   - Opt-in with compatibility checks

2. **Worktree Pooling**
   - Pre-allocate worktrees for instant spawn
   - Reset state between uses
   - Reduce allocation overhead to near-zero

3. **Advanced Conflict Resolution**
   - Machine learning model trained on conflict patterns
   - Project-specific resolution strategies
   - Higher success rate (95%+ vs 90%)

4. **Cost Prediction**
   - ML model to estimate subagent cost before spawn
   - Based on purpose, scope, historical data
   - Better budget allocation

### Medium-term (v3)

1. **Remote Execution**
   - Burst to cloud runners (Modal, Fly, Lambda)
   - 10x+ parallelism
   - Geographic distribution for latency

2. **Cross-Subagent Communication**
   - Shared scratchpad for coordination
   - Message passing between subagents
   - Complex multi-agent workflows

3. **Incremental Context Loading**
   - Stream parent context as needed
   - Reduce initial context seed size
   - Adaptive context based on task

4. **Subagent Observability Dashboard**
   - Real-time visualization of active subagents
   - Trace viewer with timeline
   - Cost and performance analytics

### Long-term (Research)

1. **Self-Improving Subagents**
   - Learn from past executions
   - Optimize scope and budgets automatically
   - Meta-learning across projects

2. **Formal Verification**
   - Prove correctness of subagent changes
   - Type-level guarantees for scope enforcement
   - Conflict-free merge guarantees

3. **Neuromorphic Isolation**
   - Hardware-level isolation using specialized chips
   - Sub-millisecond spawn times
   - Energy-efficient parallel execution

## Conclusion

The Subagent Worktree system demonstrates that git worktrees provide an elegant isolation mechanism for parallel agent work. Key insights:

1. **Native Git Integration**: Worktrees are a first-class git feature, providing isolation without heavyweight containers
2. **Context Efficiency**: Observation summaries preserve parent context budget
3. **Fail-Safe Design**: Multiple layers of scope enforcement and automated conflict resolution
4. **Composable**: Subagents use the same tools as parent, enabling consistent patterns

The system scales to hundreds of subagents per session with careful resource management and optimization. Future improvements focus on further reducing overhead and enabling more sophisticated coordination patterns.

---

**Related Documentation:**
- [Architecture](./architecture.md)
- [Architecture Tradeoffs](./architecture-tradeoffs.md)
- [System Design](./system-design.md)
- [Implementation Guide](./implementation-guide.md)
