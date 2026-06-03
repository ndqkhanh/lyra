# Plan Mode Deep Dive

## Overview

This document explores advanced patterns, optimization techniques, edge cases, internal algorithms, research references, and future improvements for Plan Mode. It's intended for contributors who want to understand the system at the deepest level.

## Advanced Patterns

### 1. Incremental Planning with Checkpoints

For large tasks (>30 feature items), break planning into phases with checkpoints:

```python
class IncrementalPlanner:
    """Planner that generates plans in phases with user checkpoints."""
    
    async def generate_incremental_plan(
        self,
        context: PlanningContext,
        phase_size: int = 10,
    ) -> PlanArtifact:
        """
        Generate plan in phases:
        1. Generate high-level phases (5-7 phases)
        2. For each phase, generate detailed items
        3. User approves each phase before next
        """
        # Phase 1: High-level breakdown
        phases = await self._generate_phases(context)
        
        all_items = []
        for i, phase in enumerate(phases):
            # Phase detail generation
            items = await self._generate_phase_items(phase, context)
            
            # Checkpoint: show items to user
            if not await self._checkpoint_approval(f"Phase {i+1}: {phase.title}", items):
                # User wants revision
                items = await self._revise_phase(phase, items)
            
            all_items.extend(items)
        
        # Assemble final plan
        return self._assemble_plan(context, all_items)
    
    async def _generate_phases(self, context: PlanningContext) -> List[Phase]:
        """Break task into 5-7 high-level phases."""
        prompt = f"""
Task: {context.task}

Break this into 5-7 high-level phases. Each phase should be:
- Independently valuable (can deliver & test)
- 4-8 feature items
- Sequential dependencies clear

Output format:
1. Phase name | Dependencies | Value delivered
"""
        phases = await self.llm.generate(prompt)
        return self._parse_phases(phases)
```

**Use case:** "Migrate monolith to microservices" — too large for single plan.

### 2. Parallel Planning with Merge

For tasks with independent subsystems, plan in parallel:

```python
class ParallelPlanner:
    """Generate sub-plans in parallel and merge."""
    
    async def generate_parallel_plan(
        self,
        context: PlanningContext,
    ) -> PlanArtifact:
        """
        1. Detect independent subsystems
        2. Generate sub-plan for each (parallel)
        3. Merge with dependency resolution
        """
        subsystems = await self._detect_subsystems(context)
        
        # Generate plans in parallel
        sub_plans = await asyncio.gather(*[
            self._plan_subsystem(subsystem, context)
            for subsystem in subsystems
        ])
        
        # Merge with topological sort
        merged = self._merge_plans(sub_plans)
        return merged
    
    def _merge_plans(self, sub_plans: List[PlanArtifact]) -> PlanArtifact:
        """
        Merge sub-plans while preserving dependencies.
        
        Algorithm:
        1. Build dependency graph from all items
        2. Topological sort
        3. Detect conflicts (same file in multiple plans)
        4. Resolve conflicts with user
        """
        graph = DependencyGraph()
        
        for plan in sub_plans:
            for item in plan.feature_items:
                graph.add_node(item)
                for dep in item.get("dependencies", []):
                    graph.add_edge(dep, item)
        
        # Detect file conflicts
        file_map = defaultdict(list)
        for plan in sub_plans:
            for file_entry in plan.expected_files:
                file_map[file_entry["path"]].append(plan.title)
        
        conflicts = {f: plans for f, plans in file_map.items() if len(plans) > 1}
        if conflicts:
            # Ask user to resolve
            resolutions = await self._resolve_conflicts(conflicts)
            graph.apply_resolutions(resolutions)
        
        # Topological sort for final order
        sorted_items = graph.topological_sort()
        
        return PlanArtifact(
            # ... metadata
            feature_items=sorted_items,
            expected_files=self._dedupe_files(sub_plans),
        )
```

**Use case:** "Add auth + payment system" — independent subsystems.

### 3. Adaptive Plan Granularity

Adjust feature item granularity based on task complexity and user experience:

```python
class AdaptivePlanner:
    """Adjusts plan granularity based on context."""
    
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.granularity_predictor = GranularityPredictor()
    
    async def generate_plan(self, context: PlanningContext) -> PlanArtifact:
        """Generate plan with adaptive granularity."""
        # Predict optimal granularity
        granularity = self.granularity_predictor.predict(
            task_complexity=self._estimate_complexity(context.task),
            user_experience=context.config.user_experience_level,
            repo_size=len(context.repo_snapshot.file_tree),
        )
        
        if granularity == "coarse":
            # High-level items: "Implement auth module" (10-20 items)
            return await self._generate_coarse_plan(context)
        elif granularity == "fine":
            # Detailed items: "Create User model class" (50-100 items)
            return await self._generate_fine_plan(context)
        else:
            # Balanced: "Create User model + tests" (20-40 items)
            return await self._generate_balanced_plan(context)

class GranularityPredictor:
    """ML model to predict optimal granularity."""
    
    def predict(
        self,
        task_complexity: float,
        user_experience: str,
        repo_size: int,
    ) -> str:
        """
        Predict granularity based on features.
        
        Rules:
        - High complexity + junior user → fine (more guidance)
        - Low complexity + senior user → coarse (less overhead)
        - Large repo → coarse (avoid drowning in details)
        """
        score = 0.0
        
        if task_complexity > 0.7:
            score += 0.3
        
        if user_experience == "junior":
            score += 0.4
        elif user_experience == "senior":
            score -= 0.3
        
        if repo_size > 10000:
            score -= 0.2
        
        if score > 0.5:
            return "fine"
        elif score < -0.3:
            return "coarse"
        else:
            return "balanced"
```

### 4. Plan Templates with Parameterization

Create reusable plan templates for common task patterns:

```python
class PlanTemplate:
    """Reusable plan template with parameters."""
    
    def __init__(self, name: str, template_path: str):
        self.name = name
        self.template = self._load_template(template_path)
    
    def instantiate(self, params: Dict[str, Any]) -> PlanArtifact:
        """
        Fill template with parameters.
        
        Example template:
        ---
        name: add-crud-api
        params:
          - resource_name: str
          - db_table: str
          - auth_required: bool
        ---
        
        ## Feature items
        1. **(model)** Create {{resource_name}} model for {{db_table}}
        2. **(api)** Implement {{resource_name}} CRUD endpoints
        {% if auth_required %}
        3. **(auth)** Add JWT middleware to {{resource_name}} routes
        {% endif %}
        """
        from jinja2 import Template
        
        rendered = Template(self.template).render(**params)
        return PlanArtifact.from_markdown(rendered)

# Usage
template = PlanTemplate("add-crud-api", "templates/crud-api.md")
plan = template.instantiate({
    "resource_name": "BlogPost",
    "db_table": "blog_posts",
    "auth_required": True,
})
```

## Optimization Techniques

### 1. Plan Caching with Fuzzy Matching

Cache plans for similar tasks to reduce LLM calls:

```python
class PlanCache:
    """Cache plans with fuzzy matching."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.cache: Dict[str, PlanArtifact] = {}
        self.threshold = similarity_threshold
    
    def get(self, task: str, repo_hash: str) -> Optional[PlanArtifact]:
        """Retrieve cached plan if similar task exists."""
        task_embedding = self._embed(task)
        
        for cached_key, cached_plan in self.cache.items():
            cached_task, cached_repo = cached_key.split("|")
            
            # Repo must match exactly
            if cached_repo != repo_hash:
                continue
            
            # Task similarity check
            similarity = self._cosine_similarity(
                task_embedding,
                self._embed(cached_task),
            )
            
            if similarity >= self.threshold:
                logger.info(f"Cache hit: {similarity:.2f} similarity")
                return cached_plan
        
        return None
    
    def put(self, task: str, repo_hash: str, plan: PlanArtifact):
        """Cache a plan."""
        key = f"{task}|{repo_hash}"
        self.cache[key] = plan
    
    def _embed(self, text: str) -> np.ndarray:
        """Generate embedding (using sentence-transformers)."""
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model.encode(text)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

**Performance gain:** 80-95% cost reduction for repeated similar tasks.

### 2. Streaming Plan Generation

Stream plan sections incrementally for faster UX:

```python
class StreamingPlanner:
    """Generate plan in streaming chunks."""
    
    async def generate_plan_streaming(
        self,
        context: PlanningContext,
    ) -> AsyncIterator[PlanChunk]:
        """
        Yield plan chunks as they're generated.
        
        Chunks:
        1. Frontmatter (metadata)
        2. Acceptance tests
        3. Expected files
        4. Feature items (streamed)
        """
        # Stream from LLM
        async for chunk in self.llm.stream(self._build_prompt(context)):
            parsed = self._parse_chunk(chunk)
            if parsed:
                yield parsed
        
        # Final assembly
        yield PlanChunk(type="complete", plan=self._assemble_chunks())

# Usage in CLI
async def display_streaming_plan(planner: StreamingPlanner, context):
    """Display plan as it's generated."""
    console = Console()
    
    with Live(console=console, refresh_per_second=4) as live:
        chunks = []
        async for chunk in planner.generate_plan_streaming(context):
            chunks.append(chunk)
            live.update(render_plan_chunks(chunks))
```

**UX improvement:** User sees plan forming in real-time, can interrupt early.

### 3. Parallel Tool Calls During Planning

Execute read-only tools in parallel for faster planning:

```python
class ParallelToolPlanner:
    """Planner with parallel tool execution."""
    
    async def gather_context(self, task: str, repo: Repo) -> Dict:
        """Gather all context in parallel."""
        # Define independent queries
        tasks = [
            self._search_relevant_files(task, repo),
            self._find_test_patterns(repo),
            self._analyze_architecture(repo),
            self._detect_dependencies(repo),
        ]
        
        # Execute in parallel
        results = await asyncio.gather(*tasks)
        
        return {
            "relevant_files": results[0],
            "test_patterns": results[1],
            "architecture": results[2],
            "dependencies": results[3],
        }
    
    async def _search_relevant_files(self, task: str, repo: Repo) -> List[str]:
        """Search for files related to task."""
        keywords = self._extract_keywords(task)
        return await repo.search(" OR ".join(keywords))
```

**Performance gain:** 3-5x faster context gathering vs sequential.

## Edge Cases and Solutions

### 1. Circular Dependencies in Feature Items

**Problem:** Plan contains circular dependencies (A depends on B, B depends on A).

**Detection:**

```python
def detect_circular_dependencies(plan: PlanArtifact) -> List[List[str]]:
    """Detect cycles in feature item dependencies."""
    graph = defaultdict(list)
    
    for i, item in enumerate(plan.feature_items):
        for dep in item.get("dependencies", []):
            graph[dep].append(i)
    
    def find_cycle(node, visited, path):
        if node in path:
            return path[path.index(node):]
        if node in visited:
            return None
        
        visited.add(node)
        path.append(node)
        
        for neighbor in graph[node]:
            cycle = find_cycle(neighbor, visited, path)
            if cycle:
                return cycle
        
        path.pop()
        return None
    
    cycles = []
    visited = set()
    for node in graph:
        cycle = find_cycle(node, visited, [])
        if cycle:
            cycles.append(cycle)
    
    return cycles
```

**Solution:**

```python
def resolve_circular_dependency(plan: PlanArtifact, cycle: List[int]) -> PlanArtifact:
    """
    Resolve by:
    1. Identify which dependency is weakest (can be deferred)
    2. Break cycle by removing that edge
    3. Ask user to confirm
    """
    # Analyze cycle strength (how many other items depend on each)
    dependency_counts = {i: len([x for x in plan.feature_items if i in x.get("dependencies", [])]) for i in cycle}
    
    # Break at weakest link
    weakest = min(cycle, key=lambda i: dependency_counts[i])
    
    # Remove dependency
    for item in plan.feature_items:
        if weakest in item.get("dependencies", []):
            item["dependencies"].remove(weakest)
            item["notes"] = f"TODO: Add {plan.feature_items[weakest]['description']} later"
    
    return plan
```

### 2. Plan-Reality Divergence During Execution

**Problem:** Plan says "edit file X", but X doesn't exist at execution time.

**Detection:**

```python
class PlanValidator:
    """Validates plan against current repo state."""
    
    async def validate_at_execution(self, plan: PlanArtifact, repo: Repo) -> ValidationResult:
        """Check if plan is still valid at execution time."""
        issues = []
        
        # Check expected files still make sense
        for file_entry in plan.expected_files:
            path = file_entry["path"]
            is_new = "new" in file_entry.get("note", "").lower()
            
            exists = await repo.file_exists(path)
            
            if is_new and exists:
                issues.append(f"File {path} marked as new but already exists")
            elif not is_new and not exists:
                issues.append(f"File {path} expected to exist but doesn't")
        
        # Check forbidden files haven't been modified
        for file_entry in plan.forbidden_files:
            if await repo.has_uncommitted_changes(file_entry["path"]):
                issues.append(f"Forbidden file {file_entry['path']} has changes")
        
        return ValidationResult(valid=len(issues) == 0, issues=issues)
```

**Solution:** Trigger replan with context.

### 3. Model Hallucination in Plan Generation

**Problem:** Planner invents non-existent files, libraries, or APIs.

**Detection:**

```python
class HallucinationDetector:
    """Detect hallucinated content in plans."""
    
    def detect(self, plan: PlanArtifact, repo: Repo) -> List[str]:
        """Find likely hallucinations."""
        issues = []
        
        # Check file references
        for item in plan.feature_items:
            mentioned_files = self._extract_file_mentions(item["description"])
            for file_path in mentioned_files:
                if not repo.file_exists(file_path) and "create" not in item["description"].lower():
                    issues.append(f"Non-existent file referenced: {file_path}")
        
        # Check library/API references
        mentioned_libs = self._extract_library_mentions(plan)
        for lib in mentioned_libs:
            if not self._verify_library_exists(lib):
                issues.append(f"Non-existent library: {lib}")
        
        return issues
    
    def _verify_library_exists(self, lib_name: str) -> bool:
        """Check if library exists in package registry."""
        # Check npm, PyPI, etc.
        registries = {
            "python": "https://pypi.org/pypi/{}/json",
            "javascript": "https://registry.npmjs.org/{}",
        }
        # ... implementation
```

**Solution:** Re-prompt with corrections.

### 4. Cost Estimation Inaccuracy

**Problem:** Estimated cost is 2x-10x off from actual cost.

**Improvement:**

```python
class MLCostEstimator:
    """Machine learning-based cost estimator."""
    
    def __init__(self):
        self.model = self._load_trained_model()
    
    def estimate(self, plan: PlanArtifact, repo: Repo) -> float:
        """
        Estimate cost using features:
        - Number of feature items
        - Average item complexity (keyword analysis)
        - Repo size
        - Historical execution times for similar plans
        """
        features = self._extract_features(plan, repo)
        predicted_tokens = self.model.predict([features])[0]
        
        # Convert tokens to USD
        cost_per_token = 0.00001  # Depends on model
        return predicted_tokens * cost_per_token
    
    def _extract_features(self, plan: PlanArtifact, repo: Repo) -> np.ndarray:
        """Extract features for ML model."""
        return np.array([
            len(plan.feature_items),
            np.mean([len(item["description"]) for item in plan.feature_items]),
            len(plan.expected_files),
            len(repo.file_tree),
            self._complexity_score(plan),
        ])
    
    def _complexity_score(self, plan: PlanArtifact) -> float:
        """Heuristic complexity score."""
        complex_keywords = ["refactor", "migrate", "design", "implement"]
        score = sum(
            1 for item in plan.feature_items
            if any(kw in item["description"].lower() for kw in complex_keywords)
        )
        return score / len(plan.feature_items)
```

## Internal Algorithms

### Plan Diff Algorithm

When user edits a plan, compute semantic diff:

```python
def compute_plan_diff(original: PlanArtifact, edited: PlanArtifact) -> PlanDiff:
    """
    Compute semantic diff between plans.
    
    Algorithm:
    1. Match feature items by description similarity (LCS)
    2. Detect: added, removed, modified, reordered
    3. Track acceptance test changes
    4. Track file changes
    """
    from difflib import SequenceMatcher
    
    # Match items
    matcher = SequenceMatcher(
        None,
        [item["description"] for item in original.feature_items],
        [item["description"] for item in edited.feature_items],
    )
    
    diff = PlanDiff()
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            diff.modified.extend(range(i1, i2))
        elif tag == "delete":
            diff.removed.extend(range(i1, i2))
        elif tag == "insert":
            diff.added.extend(range(j1, j2))
    
    # Test changes
    diff.test_changes = set(edited.acceptance_tests) - set(original.acceptance_tests)
    
    return diff
```

### Plan Compression for Context

When including plan in execution prompt, compress to save tokens:

```python
def compress_plan_for_context(plan: PlanArtifact) -> str:
    """
    Compress plan to ~300 tokens for execution context.
    
    Strategy:
    - Full: acceptance tests, expected files, forbidden files
    - Compressed: feature items (just titles, no details)
    - Omitted: open questions, notes
    """
    compressed = []
    
    compressed.append(f"Plan: {plan.title}\n")
    
    compressed.append("Tests:")
    for test in plan.acceptance_tests[:5]:  # Top 5 only
        compressed.append(f"  - {test}")
    if len(plan.acceptance_tests) > 5:
        compressed.append(f"  ... +{len(plan.acceptance_tests) - 5} more")
    
    compressed.append("\nExpected files:")
    for f in plan.expected_files[:10]:
        compressed.append(f"  - {f['path']}")
    
    compressed.append("\nForbidden:")
    for f in plan.forbidden_files:
        compressed.append(f"  - {f['path']}")
    
    compressed.append(f"\nSteps: {len(plan.feature_items)} items")
    
    return "\n".join(compressed)
```

## Research References

### Academic Foundations

1. **Task Decomposition:**
   - "Hierarchical Task Networks" (Erol et al., 1994)
   - LLM planning with hierarchical decomposition

2. **Program Synthesis:**
   - "Program Synthesis via Top-Down Reinforcement Learning" (Devlin et al., 2017)
   - Relevance: Planning as synthesis problem

3. **Human-AI Collaboration:**
   - "Guidelines for Human-AI Interaction" (Amershi et al., 2019)
   - Approval gates as human-in-the-loop pattern

4. **Cost Estimation:**
   - "Software Cost Estimation with Machine Learning" (Menzies et al., 2007)
   - Adapted for LLM token prediction

### Industry Patterns

- **GitHub Copilot Workspace:** Plan-first development paradigm
- **Devin AI:** Autonomous planning with human approval
- **Cursor Composer:** Incremental planning with checkpoints

## Future Improvements

### 1. Multi-Model Consensus Planning

Generate plans with 3 different models, merge via consensus:

```python
async def consensus_plan(task: str, models: List[str]) -> PlanArtifact:
    """Generate plans with multiple models and merge."""
    plans = await asyncio.gather(*[
        generate_plan(task, model) for model in models
    ])
    
    # Merge via voting
    consensus = vote_on_items(plans)
    return consensus
```

### 2. Continuous Plan Refinement

Plans improve over time as they're executed:

```python
class LearningPlanner:
    """Planner that learns from execution feedback."""
    
    async def generate_plan(self, context: PlanningContext) -> PlanArtifact:
        plan = await self.base_planner.generate_plan(context)
        
        # Augment with historical data
        similar_tasks = self.history.find_similar(context.task)
        if similar_tasks:
            plan = self._improve_with_history(plan, similar_tasks)
        
        return plan
```

### 3. Plan Visualization

Interactive graph view of plan structure:

```javascript
// Web UI: Interactive plan graph
function renderPlanGraph(plan) {
  const graph = new Cytoscape({
    elements: [
      ...plan.feature_items.map(item => ({
        data: { id: item.id, label: item.description }
      })),
      ...plan.dependencies.map(dep => ({
        data: { source: dep.from, target: dep.to }
      }))
    ],
    layout: { name: 'dagre' }
  });
}
```

### 4. Plan Portability

Export plans to other formats (Jira, GitHub Projects, Linear):

```python
class PlanExporter:
    """Export plans to external project management tools."""
    
    def to_jira(self, plan: PlanArtifact) -> dict:
        """Convert plan to Jira epic + stories."""
        return {
            "epic": {
                "summary": plan.title,
                "description": plan.notes,
            },
            "stories": [
                {
                    "summary": item["description"],
                    "story_points": self._estimate_points(item),
                }
                for item in plan.feature_items
            ]
        }
```

## Conclusion

Plan Mode is a sophisticated system balancing user control, cost efficiency, and execution quality. The patterns and techniques in this document enable:

- **Scalability:** Handle tasks from trivial to enterprise-scale
- **Adaptability:** Adjust to user experience and repo size
- **Reliability:** Detect and recover from edge cases
- **Performance:** Optimize for speed and cost

Future work will focus on learning from execution, multi-model consensus, and tighter integration with external tools.

## Related Documents

- [Architecture Overview](architecture.md) — System components
- [Architecture Tradeoffs](architecture-tradeoffs.md) — Design decisions
- [System Design](system-design.md) — High-level abstractions
- [Implementation Guide](implementation-guide.md) — Build from scratch

## Research Papers

1. Erol, K., et al. (1994). "Hierarchical Task Networks." AI Magazine.
2. Amershi, S., et al. (2019). "Guidelines for Human-AI Interaction." CHI Conference.
3. Menzies, T., et al. (2007). "Software Cost Estimation with Machine Learning." IEEE TSE.
4. OpenAI (2024). "Planning with Language Models." Technical Report.
