# Code Researcher: Deep Research Agent Analysis

**Paper**: Code Researcher: Deep Research Agent for Large Systems Code and Commit History  
**Authors**: Ramneet Singh, Sathvik Joel, Abhav Mehrotra, Nalin Wadhwa, et al. (Microsoft Research)  
**Date**: 2025  
**Status**: Under review

## Executive Summary

Code Researcher is the first deep research agent designed specifically for code, targeting complex systems codebases like the Linux kernel. It achieves a 58% crash resolution rate on kBenchSyz (200 Linux kernel crashes), significantly outperforming SWE-agent (37.5%) and baseline LLMs. The agent performs multi-step reasoning over code semantics, patterns, and commit history to gather sufficient context before generating patches.

### Key Innovations

1. **Multi-hop reasoning over code**: Combines control/data flow analysis, pattern detection, and causal analysis over commit history
2. **Structured context memory**: Maintains (action, result) pairs across reasoning steps
3. **Commit history integration**: First agent to leverage historical commits for bug resolution
4. **Three-phase architecture**: Analysis → Synthesis → Validation
5. **Deep exploration**: Explores ~10 files per trajectory vs 1.33 for SWE-agent

### Performance Highlights

- **58% crash resolution rate** (GPT-4o + o1) on kBenchSyz
- **48% with GPT-4o alone** vs 31.5% for SWE-agent
- **61.1% resolution rate** when both agents edit correct files (vs 37.8% for SWE-agent)
- **63.7% context overlap** with developer-referenced context (vs 54.18% for SWE-agent)
- **7/10 crashes resolved** on FFmpeg (generalization test)

---

## 1. Multi-Hop Reasoning Architecture

### 1.1 Three-Phase Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     ANALYSIS PHASE                          │
│  Multi-step reasoning + Context gathering                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Reasoning    │───▶│   Actions    │───▶│   Memory     │ │
│  │ Strategies   │    │ (search ops) │    │  (context)   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                                        │          │
│         └────────────── Iterative ───────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    SYNTHESIS PHASE                          │
│  Filter memory + Generate hypothesis + Create patch         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Filter     │───▶│  Hypothesis  │───▶│    Patch     │ │
│  │   Context    │    │  Generation  │    │  Generation  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   VALIDATION PHASE                          │
│  Apply patch + Compile + Run reproducer                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Apply Patch  │───▶│   Compile    │───▶│ Run Test     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                                                  │          │
│                                    ┌─────────────┴────────┐ │
│                                    │ Success  │  Failure  │ │
│                                    └──────────┴───────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Reasoning Strategies

The Analysis phase employs three complementary reasoning strategies:

#### Strategy 1: Chasing Control and Data Flow Chains

**Purpose**: Understand execution paths and data dependencies

**Mechanism**:
- Traces function calls, branches, loops, gotos, conditional compilation
- Follows variable assignments and data propagation
- Uses `search_definition(sym)` to explore related symbols
- Uses `search_code(regex)` for specific patterns (e.g., `x\s*=` for assignments)

**Example**: When analyzing a crash in `smsusb_term_device`, the agent traces:
1. Stack trace → `__flush_work` warning
2. Control flow → `smsusb_stop_streaming` → `cancel_work_sync`
3. Data flow → `dev->surbs[i].wq` work item initialization

#### Strategy 2: Searching for Patterns and Anti-Patterns

**Purpose**: Detect anomalies by comparing against normal behavior

**Mechanism**:
- Identifies common coding patterns in the codebase
- Detects deviations (anti-patterns) that may indicate bugs
- Uses regex searches to find pattern occurrences

**Example**: Missing null check detection
```c
// Search for null checks: search_code("if\s*\(ptr==NULL\)")
// Search for allocations: search_code("ptr\s*=.*alloc\(.*\)")
// Compare: Does allocation site have corresponding null check?
```

#### Strategy 3: Causal Analysis Over Historical Commits

**Purpose**: Leverage development history to understand bug context

**Mechanism**:
- Searches commit messages and diffs using `search_commits(regex)`
- Identifies related past fixes, refactorings, or introductions
- Traces bug origins to specific commits

**Example**: Finding memory leak patterns
```
search_commits("memory leak|kfree")
→ Discovers commit 5cda3ee5: "fix memory leak in gs_cmd_reset()"
→ Shows pattern: missing kfree() after usb_control_msg()
→ Applies same fix pattern to current bug
```

### 1.3 Iterative Deep Research Process

**Decision Loop**: At each step, the agent evaluates:
1. Has sufficient context been gathered?
2. If yes → proceed to Synthesis phase
3. If no → select reasoning strategy and issue search actions

**Multi-path Exploration**: Agent can pursue multiple lines of inquiry simultaneously
- Issue multiple search actions in parallel
- Explore different hypotheses concurrently
- Prune irrelevant paths in Synthesis phase

**Scratchpad**: Simple markdown list for tracking discoveries
- Emphasizes important findings for future steps
- Maintains focus across long trajectories
- Helps with context management

---

## 2. Code Research Methodologies

### 2.1 Search Actions

**Five core actions** enable codebase exploration:

#### `search_definition(sym)` or `search_definition(filePath, sym)`
- Finds definitions of functions, structs, macros, constants, unions
- Uses ctags indexing (built once at start)
- Returns annotated code with crash-relevant lines marked
- Optionally scoped to specific file

#### `search_code(regex)`
- Regex-based search across all tracked files
- Uses `git grep -E` with 2 lines of context
- Limited to 5 matches per query
- Progressive search strategy: context files → crash files → subsystem → all files

#### `search_commits(regex)`
- Searches commit messages (`git log -E --grep`) and diffs (`git log -E -G`)
- Returns message + patch (truncated to 100 lines)
- 60-second timeout with prioritization
- Limited to 5 results per query

#### `close_definition(filePath, symbolName, startLine)`
- Removes irrelevant definitions from memory
- Helps manage context window
- Focuses attention on relevant code

#### `done`
- Signals completion of Analysis phase
- Requires justification in `<justification>` tags
- Triggers transition to Synthesis

### 2.2 Structured Context Memory

**Format**: List of (action, result) pairs for each reasoning step

**Example Memory Entry**:
```
Query: search_code("INIT_WORK")
Results:
drivers/media/usb/siano/smsusb.c:146: INIT_WORK(&surb->wq, do_submit_urb);
kernel/workqueue.c:525: void __init_work(struct work_struct *work, int onstack)
===
Query: search_commits("smsusb_term_device")
Results:
Commit: 31e0456de5be379b10fea0fa94a681057114a96e
Author: Alan Stern
Message: media: usb: siano: Fix general protection fault in smsusb...
Patch: [diff content]
```

**Memory Management**:
- All previous searches visible at each step
- Currently open definitions maintained separately
- Agent reviews full memory before each action
- Synthesis phase filters irrelevant entries

### 2.3 Progressive Search Strategy

**Prioritization** (for faster results on large codebases):
1. Files with symbol definitions in context memory
2. Files mentioned in crash report
3. Files in relevant kernel subsystems
4. All files in codebase

**Benefits**:
- Reduces search time on massive codebases (Linux: 75K files, 28M LOC)
- Maintains relevance of results
- Enables 60-second timeout for git operations
- Still finds relevant results in most cases

---

## 3. Agent Coordination Patterns

### 3.1 Single-Agent Architecture

**Unlike multi-agent systems**, Code Researcher uses a **single agent** with:
- Unified reasoning across all strategies
- Coherent context accumulation
- No inter-agent communication overhead
- Simplified coordination

### 3.2 Phase Transitions

**Analysis → Synthesis**:
- Triggered by `done` action
- Passes: memory + reasoning trace + crash report
- Agent decides when sufficient context gathered

**Synthesis → Validation**:
- Automatic after patch generation
- External tools (compiler, VM) provide feedback
- No LLM involvement in validation

### 3.3 Sampling Strategy

**Analysis Phase**:
- Temperature: 0.6
- Sample k independent trajectories
- Budget: max_calls LLM calls per trajectory
- Each trajectory explores different paths

**Synthesis Phase**:
- Increasing temperatures: 0, 0.3, 0.6
- Max 3 attempts for correctly-formatted patch
- For o1: use n parameter (number of completions)

**Pass@k Evaluation**:
- Success if ≥1 of k patches prevents crash
- Enables exploration of multiple hypotheses

---

## 4. Knowledge Synthesis Techniques

### 4.1 Memory Filtering

**Problem**: Analysis phase may collect irrelevant information while exploring multiple paths

**Solution**: Synthesis phase filters memory before patch generation

**Process**:
1. Review all (action, result) pairs in memory
2. Evaluate relevance to crash resolution
3. Discard irrelevant entries
4. Keep only context needed for patch

**Impact**: Improves patch quality by reducing noise

### 4.2 Hypothesis Generation

**Input**: Filtered memory + reasoning trace + crash report

**Output**: Structured hypothesis about bug nature and remedy

**Format**:
```xml
<hypothesis>
The crash occurs because work items in dev->surbs[i].wq are 
canceled before initialization. If smsusb_stop_streaming is 
called before any URB completes, cancel_work_sync attempts to 
flush uninitialized work items with NULL function pointers, 
triggering the warning in __flush_work.
</hypothesis>
```

**Key Elements**:
- Root cause identification
- Causal chain explanation
- Proposed remedy approach

### 4.3 Patch Generation

**Format**: XML-based structured output
```xml
<patch>
  <symbol file="path/to/file.c" name="function_name" start="123">
    [Complete rewritten definition with changes]
  </symbol>
</patch>
```

**Characteristics**:
- Complete symbol rewrite (not diff-based)
- Multiple symbols can be modified
- Spans multiple files if needed
- Includes all necessary changes

**Quality Categories** (from qualitative evaluation):

1. **Accurate** (best): Correctly identifies and fixes root cause, resembles developer solution
2. **Overspecialized**: Prevents crash but may be too defensive or specific
3. **Incomplete**: Correct approach but missing some fixes
4. **Incorrect**: Fails to address root cause or introduces issues

### 4.4 Context Overlap Analysis

**Developer Context Extraction**:
- Symbols mentioned in commit messages: s*_b
- Commit IDs referenced: c*_b

**Tool Context Extraction**:
- Symbols whose definitions were seen: s_b,i
- Commits retrieved in trajectory: c_b,i

**Metrics**:
- Symbol ratio: SR_b,i = |s_b,i| / |s*_b|
- Overlapping if SR ≥ 0.33
- Commit overlap: |c_b,i| / |c*_b| = 1

**Results**:
- Code Researcher: 63.7% symbol overlap vs SWE-agent: 54.01%
- Code Researcher: 30.8% commit overlap (SWE-agent: 0%, no commit search)
- P(resolves | overlapping context) = 0.309 vs P(resolves | non-overlapping) = 0.116

---

## 5. Research Automation Strategies

### 5.1 Automated Crash Reproduction

**Infrastructure** (built on kGym platform):
- **kBuilder**: Checks out code, applies patch, compiles kernel, uploads artifacts
- **kReproducer**: Runs kernel on reproducer in 4 parallel VMs (handles non-determinism)
- **kScheduler**: Orchestrates build → reproduction flow via message queue
- **kDashboard**: Web UI for logs and results

**Optimizations**:
- ccache for build artifact caching
- Custom git checkout caching
- Cloud storage for compiled kernels
- 10 distributed replicas for parallel evaluation

**Validation Criteria**:
- Crash reproduced: Any VM crashes within 10 minutes OR connection lost
- Patch successful: Compiled kernel does NOT crash on reproducer

### 5.2 Automated Indexing

**ctags Integration**:
- Index built once at start (few minutes for Linux kernel)
- Enables fast `search_definition(sym)` lookups
- Supports functions, structs, macros, constants, unions
- Reused throughout Analysis trajectory

**Git Integration**:
- `git grep -E` for code pattern search
- `git log -E -G` for diff search
- `git log -E --grep` for commit message search
- Progressive search with timeouts

### 5.3 Test-Time Scaling

**Two axes of scaling**:

1. **max_calls** (trajectory length):
   - Doubling from 15 to 30: minimal CRR improvement
   - Suggests depth has diminishing returns
   - Most context gathered in first 15 calls

2. **k trajectories** (breadth):
   - Increasing from P@5 to P@10: significant improvement
   - SWE-agent: 31.5% → 37.5% (+6%)
   - Code Researcher: 48% → 54% (+6%)
   - Breadth more valuable than depth

**Implication**: Sample multiple diverse trajectories rather than making single trajectory longer

### 5.4 Model Routing

**Hybrid approach** (best performance):
- **GPT-4o for Analysis**: Multi-step reasoning, context gathering
- **o1 for Synthesis**: Patch generation with deep reasoning
- **58% CRR** vs 48% with GPT-4o alone

**Rationale**:
- Analysis requires many iterative calls (cost-sensitive)
- Synthesis benefits from reasoning model (quality-sensitive)
- Well-researched context enables o1 to excel

---

## 6. Novel Approaches for Code Understanding

### 6.1 Commit History as First-Class Context

**Innovation**: First coding agent to explicitly leverage commit history

**Mechanism**:
- `search_commits(regex)` searches messages and diffs
- Identifies bug-introducing commits (via "Fixes:" tags)
- Discovers related past fixes and patterns
- Traces causal relationships

**Impact** (ablation study on 96 resolved bugs):
- **Without commit search**: 38% CRR (10% drop)
- **With commit search**: 48% CRR
- Average recall drops from 0.51 to 0.33
- "All files" metric drops from 48.2% to 32.6%

**Example**: Memory leak bug
```
Developer commit message: "Fixes: 6679f4c5e5a6"
Code Researcher trajectory:
  search_commits("bt_const_extended|memory leak")
  → Finds commit 6679f4c5e5a6 (bug introduction)
  → Finds commit 5cda3ee5 (similar fix pattern)
  → Applies same pattern: add kfree() after usage
```

### 6.2 Deep vs Shallow Exploration

**Code Researcher** (deep exploration):
- 29.13 unique files per bug (across 5 trajectories)
- 10 files per trajectory average
- 5+ top-level directories explored
- Multiple reasoning strategies applied

**SWE-agent** (shallow exploration):
- 1.91 unique files per bug
- 1.33 files per trajectory average
- Minimal cross-file analysis
- Quick navigation to suspected files

**Why the difference?**
- SWE-bench tasks: issue descriptions with file hints
- kBenchSyz tasks: stack traces without natural language hints
- Systems code: requires understanding global invariants
- Deep exploration essential for complex bugs

### 6.3 Pattern-Based Anomaly Detection

**Traditional approach**: Static analysis tools with predefined rules

**Code Researcher approach**: LLM-based pattern inference
- Searches for common patterns in codebase
- Identifies deviations automatically
- Adapts to codebase-specific conventions
- No predefined rule set needed

**Example**: Null check detection
```python
# Agent reasoning:
# 1. Notice: ptr allocated but not checked
# 2. Search: search_code("if\s*\(ptr==NULL\)")
# 3. Analyze: 95% of allocations have null checks
# 4. Conclude: Missing null check is anomaly
# 5. Fix: Add null check
```

### 6.4 Structured Memory vs Long Context

**Long context approach** (baseline):
- Feed entire codebase to LLM
- Relies on model's attention mechanism
- "Lost in the middle" problem
- Limited by context window (2M tokens ≈ 100K LOC)

**Structured memory approach** (Code Researcher):
- Selective context gathering via search
- Explicit (action, result) pairs
- Agent controls what to remember
- Scales beyond context limits

**Results**:
- Stack context (all crash files): 40% CRR (o1)
- Code Researcher: 58% CRR (GPT-4o + o1)
- Structured memory outperforms even with smaller model

---

## 7. Applicable Techniques for Lyra

### 7.1 Multi-Hop Reasoning Framework

**Direct Application**:
```python
# Lyra research pipeline with multi-hop reasoning
class MultiHopResearcher:
    def __init__(self):
        self.memory = StructuredMemory()
        self.strategies = [
            ControlFlowStrategy(),
            PatternDetectionStrategy(),
            HistoryAnalysisStrategy()
        ]
    
    def research(self, query: str) -> ResearchResult:
        while not self.has_sufficient_context():
            # Select strategy based on current state
            strategy = self.select_strategy()
            
            # Execute search actions
            actions = strategy.plan_actions(self.memory)
            results = self.execute_actions(actions)
            
            # Update memory
            self.memory.add(actions, results)
        
        # Synthesize findings
        return self.synthesize(self.memory)
```

**Benefits for Lyra**:
- Systematic exploration of research topics
- Structured context accumulation
- Multiple reasoning perspectives
- Iterative refinement

### 7.2 Commit History Integration

**Lyra Implementation**:
```python
# Add git history search to Lyra's research tools
class GitHistoryTool:
    def search_commits(self, regex: str, repo_path: str) -> List[Commit]:
        """Search commit messages and diffs"""
        # Search messages
        messages = git_log_grep(regex, repo_path)
        # Search diffs
        diffs = git_log_G(regex, repo_path)
        return merge_and_rank(messages, diffs)
    
    def trace_bug_origin(self, file: str, line: int) -> List[Commit]:
        """Find commits that introduced/modified specific code"""
        return git_blame_with_history(file, line)
    
    def find_related_fixes(self, keywords: List[str]) -> List[Commit]:
        """Find past fixes for similar issues"""
        return search_commits("|".join(keywords))
```

**Use Cases**:
- Trace API evolution for documentation
- Find design decision rationale
- Discover related work and prior art
- Understand breaking changes

### 7.3 Structured Context Memory

**Lyra Memory System**:
```python
class ResearchMemory:
    def __init__(self):
        self.entries: List[Tuple[Action, Result]] = []
        self.scratchpad: List[str] = []
        self.open_contexts: Dict[str, Any] = {}
    
    def add(self, action: Action, result: Result):
        """Add (action, result) pair"""
        self.entries.append((action, result))
    
    def filter_relevant(self, query: str) -> List[Tuple[Action, Result]]:
        """Filter memory for relevant entries"""
        # Use LLM to evaluate relevance
        return [e for e in self.entries if is_relevant(e, query)]
    
    def get_context_window(self) -> str:
        """Format memory for LLM consumption"""
        return format_memory(self.entries, self.scratchpad)
```

**Benefits**:
- Explicit tracking of research steps
- Easy to review and debug
- Supports iterative refinement
- Enables memory filtering

### 7.4 Progressive Search Strategy

**Lyra Search Prioritization**:
```python
class ProgressiveSearch:
    def search(self, query: str, context: ResearchContext) -> List[Result]:
        # Priority 1: Already-referenced sources
        results = self.search_scope(query, context.referenced_sources)
        if len(results) >= threshold:
            return results
        
        # Priority 2: Domain-specific sources
        results += self.search_scope(query, context.domain_sources)
        if len(results) >= threshold:
            return results
        
        # Priority 3: General web search
        results += self.search_scope(query, "web")
        return results
```

**Benefits**:
- Faster results on focused queries
- Maintains relevance
- Reduces noise
- Scales to large search spaces

### 7.5 Hybrid Model Routing

**Lyra Model Selection**:
```python
class ModelRouter:
    def route(self, task: Task) -> Model:
        if task.type == "exploration":
            # Many iterative calls, cost-sensitive
            return Model.HAIKU
        elif task.type == "synthesis":
            # Deep reasoning, quality-sensitive
            return Model.OPUS
        elif task.type == "standard":
            # Balanced performance
            return Model.SONNET
        
    def research_pipeline(self, query: str):
        # Exploration with Haiku
        context = self.explore(query, model=Model.HAIKU)
        
        # Synthesis with Opus
        result = self.synthesize(context, model=Model.OPUS)
        
        return result
```

**Benefits**:
- Cost optimization
- Quality where it matters
- Faster iteration
- Better resource utilization

### 7.6 Test-Time Scaling Strategy

**Lyra Parallel Exploration**:
```python
class ParallelResearcher:
    def research_with_scaling(self, query: str, k: int = 5):
        """Sample k independent research trajectories"""
        trajectories = []
        
        # Launch k parallel research paths
        with ThreadPoolExecutor(max_workers=k) as executor:
            futures = [
                executor.submit(self.single_trajectory, query, temp=0.6)
                for _ in range(k)
            ]
            trajectories = [f.result() for f in futures]
        
        # Synthesize best findings
        return self.merge_trajectories(trajectories)
    
    def single_trajectory(self, query: str, temp: float):
        """Single research trajectory with temperature"""
        memory = ResearchMemory()
        for step in range(max_calls):
            action = self.plan_action(memory, temperature=temp)
            result = self.execute(action)
            memory.add(action, result)
            if self.is_sufficient(memory):
                break
        return memory
```

**Benefits**:
- Explore multiple hypotheses in parallel
- Increase success rate without longer trajectories
- Diverse perspectives on same query
- Better than single deep trajectory

---

## 8. Implementation Recommendations

### 8.1 Core Architecture

**Recommended Structure**:
```python
# lyra/research/multi_hop.py
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

class ActionType(Enum):
    SEARCH_CODE = "search_code"
    SEARCH_COMMITS = "search_commits"
    SEARCH_DOCS = "search_docs"
    SEARCH_WEB = "search_web"
    DONE = "done"

@dataclass
class Action:
    type: ActionType
    query: str
    scope: Optional[str] = None

@dataclass
class Result:
    content: str
    source: str
    relevance_score: float

class StructuredMemory:
    def __init__(self):
        self.entries: List[Tuple[Action, Result]] = []
        self.scratchpad: List[str] = []
    
    def add(self, action: Action, result: Result):
        self.entries.append((action, result))
    
    def filter(self, relevance_threshold: float = 0.5) -> List[Tuple[Action, Result]]:
        return [(a, r) for a, r in self.entries if r.relevance_score >= relevance_threshold]
    
    def format_for_llm(self) -> str:
        formatted = []
        for action, result in self.entries:
            formatted.append(f"Query: {action.type.value}({action.query})")
            formatted.append(f"Results:\n{result.content}")
            formatted.append("===")
        return "\n".join(formatted)

class MultiHopResearcher:
    def __init__(self, client, max_calls: int = 15):
        self.client = client
        self.max_calls = max_calls
        self.memory = StructuredMemory()
    
    def research(self, query: str) -> str:
        """Main research loop"""
        for step in range(self.max_calls):
            # Get next action from LLM
            action = self._plan_next_action(query)
            
            if action.type == ActionType.DONE:
                break
            
            # Execute action
            result = self._execute_action(action)
            
            # Update memory
            self.memory.add(action, result)
        
        # Synthesize findings
        return self._synthesize()
    
    def _plan_next_action(self, query: str) -> Action:
        """Ask LLM to plan next research action"""
        prompt = f"""
Research Query: {query}

Current Memory:
{self.memory.format_for_llm()}

Scratchpad:
{chr(10).join(self.memory.scratchpad)}

What should be the next research action? Choose from:
- search_code(regex): Search codebase
- search_commits(regex): Search git history
- search_docs(query): Search documentation
- search_web(query): Web search
- done: Sufficient context gathered

Respond with action in format: <action>type(query)</action>
"""
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.6,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_action(response.content[0].text)
    
    def _execute_action(self, action: Action) -> Result:
        """Execute research action and return result"""
        if action.type == ActionType.SEARCH_CODE:
            return self._search_code(action.query)
        elif action.type == ActionType.SEARCH_COMMITS:
            return self._search_commits(action.query)
        elif action.type == ActionType.SEARCH_DOCS:
            return self._search_docs(action.query)
        elif action.type == ActionType.SEARCH_WEB:
            return self._search_web(action.query)
    
    def _synthesize(self) -> str:
        """Synthesize findings from memory"""
        # Filter relevant entries
        filtered_memory = self.memory.filter(relevance_threshold=0.5)
        
        prompt = f"""
Based on the following research findings, synthesize a comprehensive answer:

{self._format_filtered_memory(filtered_memory)}

Provide a structured synthesis with:
1. Key findings
2. Supporting evidence
3. Conclusions
4. Recommendations
"""
        response = self.client.messages.create(
            model="claude-opus-4-20250514",  # Use Opus for synthesis
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
```

### 8.2 Git History Integration

**Implementation**:
```python
# lyra/research/git_tools.py
import subprocess
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Commit:
    hash: str
    author: str
    date: str
    message: str
    diff: str

class GitHistoryTool:
    def __init__(self, repo_path: str, timeout: int = 60):
        self.repo_path = repo_path
        self.timeout = timeout
    
    def search_commits(self, regex: str, max_results: int = 5) -> List[Commit]:
        """Search commit messages and diffs"""
        commits = []
        
        # Search commit messages
        try:
            result = subprocess.run(
                ["git", "log", "-E", "--grep", regex, f"--max-count={max_results}",
                 "--format=%H|%an|%ad|%s", "--date=short"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                hash, author, date, message = line.split("|", 3)
                
                # Get diff for this commit
                diff = self._get_commit_diff(hash)
                
                commits.append(Commit(hash, author, date, message, diff))
        
        except subprocess.TimeoutExpired:
            print(f"Git search timed out after {self.timeout}s")
        
        # Search diffs if needed
        if len(commits) < max_results:
            commits.extend(self._search_diffs(regex, max_results - len(commits)))
        
        return commits[:max_results]
    
    def _get_commit_diff(self, commit_hash: str, max_lines: int = 100) -> str:
        """Get diff for a specific commit"""
        result = subprocess.run(
            ["git", "show", commit_hash, "--format=", "--unified=2"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        lines = result.stdout.split("\n")
        return "\n".join(lines[:max_lines])
    
    def _search_diffs(self, regex: str, max_results: int) -> List[Commit]:
        """Search commit diffs"""
        result = subprocess.run(
            ["git", "log", "-E", "-G", regex, f"--max-count={max_results}",
             "--format=%H|%an|%ad|%s", "--date=short"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            hash, author, date, message = line.split("|", 3)
            diff = self._get_commit_diff(hash)
            commits.append(Commit(hash, author, date, message, diff))
        
        return commits
    
    def trace_file_history(self, file_path: str, line_number: int) -> List[Commit]:
        """Trace history of specific line in file"""
        result = subprocess.run(
            ["git", "log", "-L", f"{line_number},{line_number}:{file_path}",
             "--format=%H|%an|%ad|%s", "--date=short"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line or not "|" in line:
                continue
            hash, author, date, message = line.split("|", 3)
            diff = self._get_commit_diff(hash)
            commits.append(Commit(hash, author, date, message, diff))
        
        return commits
```

### 8.3 Progressive Search Implementation

**Implementation**:
```python
# lyra/research/progressive_search.py
from typing import List, Set, Optional
from dataclasses import dataclass

@dataclass
class SearchScope:
    name: str
    priority: int
    sources: List[str]

class ProgressiveSearchEngine:
    def __init__(self):
        self.scopes = [
            SearchScope("context", 1, []),  # Files already in context
            SearchScope("referenced", 2, []),  # Referenced in research
            SearchScope("domain", 3, []),  # Domain-specific sources
            SearchScope("global", 4, [])  # All sources
        ]
        self.seen_results: Set[str] = set()
    
    def search(self, query: str, context_files: List[str] = None,
               threshold: int = 5) -> List[Dict]:
        """Progressive search with prioritization"""
        results = []
        
        # Update context scope
        if context_files:
            self.scopes[0].sources = context_files
        
        # Search each scope in priority order
        for scope in sorted(self.scopes, key=lambda s: s.priority):
            scope_results = self._search_scope(query, scope)
            
            # Add unique results
            for result in scope_results:
                if result["id"] not in self.seen_results:
                    results.append(result)
                    self.seen_results.add(result["id"])
            
            # Stop if threshold reached
            if len(results) >= threshold:
                break
        
        return results[:threshold]
    
    def _search_scope(self, query: str, scope: SearchScope) -> List[Dict]:
        """Search within a specific scope"""
        if scope.name == "context":
            return self._search_files(query, scope.sources)
        elif scope.name == "referenced":
            return self._search_referenced(query)
        elif scope.name == "domain":
            return self._search_domain(query)
        elif scope.name == "global":
            return self._search_global(query)
        return []
    
    def _search_files(self, query: str, files: List[str]) -> List[Dict]:
        """Search specific files using git grep"""
        if not files:
            return []
        
        # Use git grep with file list
        import subprocess
        result = subprocess.run(
            ["git", "grep", "-E", "-n", "-C", "2", query] + files,
            capture_output=True,
            text=True
        )
        
        return self._parse_grep_results(result.stdout)
    
    def _parse_grep_results(self, output: str) -> List[Dict]:
        """Parse git grep output into structured results"""
        results = []
        for line in output.split("\n"):
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                file, line_num, content = parts
                results.append({
                    "id": f"{file}:{line_num}",
                    "file": file,
                    "line": int(line_num),
                    "content": content.strip()
                })
        return results
```

### 8.4 Integration with Lyra CLI

**Add to research pipeline**:
```python
# lyra/cli/research_pipeline.py
from lyra.research.multi_hop import MultiHopResearcher
from lyra.research.git_tools import GitHistoryTool
from lyra.research.progressive_search import ProgressiveSearchEngine

class EnhancedResearchPipeline:
    def __init__(self, client, repo_path: str = None):
        self.client = client
        self.repo_path = repo_path
        
        # Initialize components
        self.researcher = MultiHopResearcher(client, max_calls=15)
        if repo_path:
            self.git_tool = GitHistoryTool(repo_path)
        self.search_engine = ProgressiveSearchEngine()
    
    def research(self, query: str, use_git: bool = True) -> Dict:
        """Enhanced research with multi-hop reasoning"""
        # Phase 1: Multi-hop exploration
        context = self.researcher.research(query)
        
        # Phase 2: Git history analysis (if enabled)
        if use_git and self.repo_path:
            commits = self.git_tool.search_commits(query)
            context["git_history"] = commits
        
        # Phase 3: Synthesis
        synthesis = self._synthesize_findings(context)
        
        return {
            "query": query,
            "context": context,
            "synthesis": synthesis,
            "metadata": {
                "steps": len(self.researcher.memory.entries),
                "files_explored": self._count_unique_files(context)
            }
        }
    
    def _synthesize_findings(self, context: Dict) -> str:
        """Synthesize research findings"""
        return self.researcher._synthesize()
    
    def _count_unique_files(self, context: Dict) -> int:
        """Count unique files explored"""
        files = set()
        for action, result in self.researcher.memory.entries:
            if hasattr(result, "source"):
                files.add(result.source)
        return len(files)
```

---

## 9. Evaluation and Benchmarking

### 9.1 Key Metrics

**Crash Resolution Rate (CRR)**:
- Primary metric for bug fixing tasks
- Success = patch prevents crash without breaking compilation
- Measured at Pass@1, Pass@5, Pass@10

**Context Overlap**:
- Symbol ratio: |agent_symbols| / |developer_symbols|
- Commit overlap: |agent_commits| / |developer_commits|
- Threshold: ≥33% overlap considered "overlapping"

**File Localization**:
- "All files": Patch edits all ground-truth buggy files
- "Some files": Patch edits at least one ground-truth file
- "No files": Patch misses all ground-truth files

**Exploration Depth**:
- Unique files per trajectory
- Unique files per bug (across k trajectories)
- Top-level directories explored

### 9.2 Benchmark Results Summary

| Metric | Code Researcher | SWE-agent | Improvement |
|--------|----------------|-----------|-------------|
| CRR (Pass@1) | 48% | 31.5% | +52% |
| CRR (Pass@10) | 54% | 37.5% | +44% |
| Files/trajectory | 10.0 | 1.33 | +7.5x |
| Context overlap | 63.7% | 54.18% | +9.5pp |
| All files edited | 48.2% | - | - |

**With o1 reasoning model**:
- Code Researcher (GPT-4o + o1): 58% CRR
- o1 alone (assisted): 51% CRR
- GPT-4o alone (assisted): 36% CRR

**Cross-domain (FFmpeg)**:
- 7/10 crashes resolved (70% success rate)
- Demonstrates generalizability beyond Linux kernel

### 9.3 Ablation Study Results

**Removing commit search** (96 resolved bugs):
- With commits: 48% CRR
- Without commits: 38% CRR (-10pp)
- Average recall: 0.51 → 0.33
- All files metric: 48.2% → 32.6%

**Trajectory length scaling**:
- max_calls=15: 48% CRR
- max_calls=30: ~48% CRR (minimal improvement)
- Conclusion: Depth has diminishing returns

**Breadth scaling**:
- Pass@5: 48% CRR
- Pass@10: 54% CRR (+6pp)
- Conclusion: Breadth more valuable than depth

---

## 10. Comparison with Related Work

### 10.1 vs SWE-agent

**Architecture**:
- SWE-agent: File navigation + editing tools
- Code Researcher: Search-based exploration + structured memory

**Exploration**:
- SWE-agent: 1.33 files/trajectory (shallow)
- Code Researcher: 10 files/trajectory (deep)

**Context**:
- SWE-agent: 54.18% overlap with developer context
- Code Researcher: 63.7% overlap

**Performance**:
- SWE-agent: 31.5% CRR on kBenchSyz
- Code Researcher: 48% CRR (+52%)

**Key Difference**: SWE-agent designed for SWE-bench (issue descriptions with hints), Code Researcher for systems code (stack traces without hints)

### 10.2 vs Long-Context LLMs

**Approach**:
- Long-context: Feed entire codebase to LLM
- Code Researcher: Selective search + structured memory

**Limitations of long-context**:
- Linux kernel (28M LOC) exceeds 2M token limit
- "Lost in the middle" problem
- No explicit reasoning trace

**Results**:
- Stack context only (o1): 40% CRR
- Code Researcher (GPT-4o + o1): 58% CRR

**Conclusion**: Structured exploration outperforms passive long-context

### 10.3 vs Agentless

**Architecture**:
- Agentless: Two-stage localization + repair
- Code Researcher: Iterative multi-hop reasoning

**Performance**:
- Agentless: 31% CRR on kBenchSyz
- Code Researcher: 48% CRR (+55%)

**Key Difference**: Agentless uses predefined pipeline, Code Researcher adapts exploration dynamically

---

## 11. Limitations and Future Work

### 11.1 Current Limitations

**Scope**:
- Focused on crash resolution
- Untested on performance bugs, resource leaks, flakiness
- Requires crash reproducer for validation

**Validation**:
- Test-based evaluation cannot guarantee correctness
- May miss untested functionality
- Overspecialized patches may pass tests but be suboptimal

**Scalability**:
- 60-second timeout on git operations
- Progressive search may miss relevant results
- Context window limits (50K tokens)

**Cost**:
- Multiple trajectories increase API costs
- Deep exploration requires many LLM calls
- Trade-off between quality and cost

### 11.2 Future Research Directions

**Broader Applications**:
- Performance optimization
- Security vulnerability detection
- Code refactoring
- API migration

**Enhanced Reasoning**:
- Multi-agent collaboration
- Specialized reasoning models
- Formal verification integration
- Symbolic execution

**Improved Search**:
- Semantic code search (embeddings)
- Cross-repository search
- API documentation integration
- Stack Overflow integration

**Better Validation**:
- Formal correctness proofs
- Comprehensive test generation
- Regression detection
- Performance impact analysis

---

## 12. Key Takeaways for Lyra

### 12.1 Architectural Principles

1. **Multi-hop reasoning beats single-shot**: Iterative exploration with structured memory outperforms direct generation
2. **Commit history is valuable**: Historical context provides causal insights not available in current code
3. **Deep exploration essential**: Systems-level understanding requires exploring 10+ files, not 1-2
4. **Structured memory scales**: Explicit (action, result) pairs scale beyond context limits
5. **Breadth > depth**: Multiple diverse trajectories better than single long trajectory

### 12.2 Implementation Priorities

**High Priority** (immediate value):
1. Structured memory system for research context
2. Git history search integration
3. Progressive search with prioritization
4. Multi-trajectory sampling (Pass@k)

**Medium Priority** (significant value):
1. Hybrid model routing (Haiku exploration, Opus synthesis)
2. Pattern-based anomaly detection
3. Memory filtering for synthesis
4. Automated indexing (ctags equivalent)

**Low Priority** (nice to have):
1. Formal validation framework
2. Cross-repository search
3. Semantic code search
4. Multi-agent coordination

### 12.3 Success Metrics

**For Lyra research pipeline**:
- Context overlap with ground truth
- Unique sources explored per query
- Synthesis quality (human evaluation)
- Cost per research task
- Time to sufficient context

**Targets** (based on Code Researcher):
- 60%+ context overlap with expert research
- 10+ unique sources per query
- 3-5 reasoning strategies applied
- <$1 per research task
- <5 minutes to synthesis

---

## Sources

- [Code Researcher: Deep Research Agent for Large Systems Code and Commit History](https://www.microsoft.com/en-us/research/publication/code-researcher-deep-research-agent-for-large-systems-code-and-commit-history/)
- [ArXiv Paper: 2506.11060](https://arxiv.org/abs/2506.11060)
- [HTML Version on ar5iv](https://ar5iv.labs.arxiv.org/html/2506.11060)
- [RefactorBench: Evaluating Stateful Reasoning in Language Agents Through Code](https://www.microsoft.com/en-us/research/publication/refactorbench-evaluating-stateful-reasoning-in-language-agents-through-code/)

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-26  
**Analyzed By**: Lyra Research Agent
