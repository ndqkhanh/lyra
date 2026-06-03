# Plan Mode Implementation Guide

## Overview

This guide walks through implementing Plan Mode from scratch, providing step-by-step instructions, code examples, configuration, testing strategies, debugging tips, and common pitfalls.

## Prerequisites

- Python 3.11+
- Git repository (optional but recommended)
- LLM API access (OpenAI, Anthropic, DeepSeek, etc.)
- Basic understanding of async/await patterns

## Step 1: Project Structure

Create the directory structure for plan mode components:

```bash
mkdir -p lyra_core/plan
mkdir -p lyra_core/permissions
mkdir -p lyra_core/storage
mkdir -p tests/plan
mkdir -p .lyra/plans

# Create __init__.py files
touch lyra_core/__init__.py
touch lyra_core/plan/__init__.py
touch lyra_core/permissions/__init__.py
touch lyra_core/storage/__init__.py
```

Directory layout:

```
lyra_core/
├── plan/
│   ├── __init__.py
│   ├── planner.py          # Planner agent implementation
│   ├── artifact.py         # Plan artifact schema
│   ├── heuristics.py       # Triviality detection
│   ├── approval.py         # Approval gateways
│   └── orchestrator.py     # Main workflow coordinator
├── permissions/
│   ├── __init__.py
│   └── manager.py          # Permission enforcement
└── storage/
    ├── __init__.py
    └── plan_store.py       # Plan persistence
```

## Step 2: Define Plan Artifact Schema

Create `lyra_core/plan/artifact.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import yaml
import hashlib
import re

@dataclass
class PlanArtifact:
    """Plan artifact with YAML frontmatter + markdown body."""
    
    # Frontmatter fields
    session_id: str
    created_at: datetime
    planner_model: str
    estimated_cost_usd: float
    goal_hash: str
    
    # Body fields
    title: str
    acceptance_tests: List[str] = field(default_factory=list)
    expected_files: List[Dict[str, str]] = field(default_factory=list)
    forbidden_files: List[Dict[str, str]] = field(default_factory=list)
    feature_items: List[Dict[str, str]] = field(default_factory=list)
    open_questions: List[Dict[str, str]] = field(default_factory=list)
    notes: Optional[str] = None
    
    # Metadata
    revision_num: int = 0
    path: Optional[str] = None
    
    @classmethod
    def from_markdown(cls, content: str) -> "PlanArtifact":
        """Parse markdown with YAML frontmatter."""
        # Split frontmatter and body
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid plan format: missing frontmatter")
        
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()
        
        # Parse body sections
        sections = cls._parse_body_sections(body)
        
        return cls(
            session_id=frontmatter["session_id"],
            created_at=datetime.fromisoformat(frontmatter["created_at"]),
            planner_model=frontmatter["planner_model"],
            estimated_cost_usd=float(frontmatter["estimated_cost_usd"]),
            goal_hash=frontmatter["goal_hash"],
            title=sections.get("title", ""),
            acceptance_tests=sections.get("acceptance_tests", []),
            expected_files=sections.get("expected_files", []),
            forbidden_files=sections.get("forbidden_files", []),
            feature_items=sections.get("feature_items", []),
            open_questions=sections.get("open_questions", []),
            notes=sections.get("notes"),
        )
    
    @staticmethod
    def _parse_body_sections(body: str) -> Dict:
        """Extract sections from markdown body."""
        sections = {}
        
        # Extract title
        title_match = re.search(r"^#\s+Plan:\s+(.+)$", body, re.MULTILINE)
        if title_match:
            sections["title"] = title_match.group(1).strip()
        
        # Extract acceptance tests
        tests_section = re.search(
            r"##\s+Acceptance tests\n(.*?)(?=\n##|\Z)",
            body,
            re.DOTALL,
        )
        if tests_section:
            tests = re.findall(r"^-\s+(.+)$", tests_section.group(1), re.MULTILINE)
            sections["acceptance_tests"] = tests
        
        # Extract expected files
        files_section = re.search(
            r"##\s+Expected files\n(.*?)(?=\n##|\Z)",
            body,
            re.DOTALL,
        )
        if files_section:
            files = []
            for line in files_section.group(1).strip().split("\n"):
                match = re.match(r"-\s+([^\s(]+)\s*(?:\(([^)]+)\))?", line)
                if match:
                    files.append({
                        "path": match.group(1),
                        "note": match.group(2) if match.group(2) else "",
                    })
            sections["expected_files"] = files
        
        # Extract forbidden files
        forbidden_section = re.search(
            r"##\s+Forbidden files\n(.*?)(?=\n##|\Z)",
            body,
            re.DOTALL,
        )
        if forbidden_section:
            forbidden = []
            for line in forbidden_section.group(1).strip().split("\n"):
                match = re.match(r"-\s+([^\s#]+)\s*(?:#\s*(.+))?", line)
                if match:
                    forbidden.append({
                        "path": match.group(1),
                        "reason": match.group(2).strip() if match.group(2) else "",
                    })
            sections["forbidden_files"] = forbidden
        
        # Extract feature items
        items_section = re.search(
            r"##\s+Feature items\n(.*?)(?=\n##|\Z)",
            body,
            re.DOTALL,
        )
        if items_section:
            items = []
            for line in items_section.group(1).strip().split("\n"):
                match = re.match(r"\d+\.\s+\*\*\(([^)]+)\)\*\*\s+(.+)", line)
                if match:
                    items.append({
                        "skill": match.group(1),
                        "description": match.group(2),
                    })
            sections["feature_items"] = items
        
        return sections
    
    def to_markdown(self) -> str:
        """Serialize to markdown with YAML frontmatter."""
        frontmatter = {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "planner_model": self.planner_model,
            "estimated_cost_usd": self.estimated_cost_usd,
            "goal_hash": self.goal_hash,
        }
        
        frontmatter_str = yaml.dump(frontmatter, default_flow_style=False)
        
        body_parts = [f"# Plan: {self.title}\n"]
        
        # Acceptance tests
        if self.acceptance_tests:
            body_parts.append("## Acceptance tests\n")
            for test in self.acceptance_tests:
                body_parts.append(f"- {test}\n")
            body_parts.append("\n")
        
        # Expected files
        if self.expected_files:
            body_parts.append("## Expected files\n")
            for file_entry in self.expected_files:
                note = f" ({file_entry['note']})" if file_entry.get("note") else ""
                body_parts.append(f"- {file_entry['path']}{note}\n")
            body_parts.append("\n")
        
        # Forbidden files
        if self.forbidden_files:
            body_parts.append("## Forbidden files\n")
            for file_entry in self.forbidden_files:
                reason = f" # {file_entry['reason']}" if file_entry.get("reason") else ""
                body_parts.append(f"- {file_entry['path']}{reason}\n")
            body_parts.append("\n")
        
        # Feature items
        if self.feature_items:
            body_parts.append("## Feature items\n")
            for i, item in enumerate(self.feature_items, 1):
                body_parts.append(f"{i}. **({item['skill']})** {item['description']}\n")
            body_parts.append("\n")
        
        # Open questions
        if self.open_questions:
            body_parts.append("## Open questions\n")
            for q in self.open_questions:
                default = f" (default: {q['default']})" if q.get("default") else ""
                body_parts.append(f"- {q['question']}{default}\n")
            body_parts.append("\n")
        
        # Notes
        if self.notes:
            body_parts.append("## Notes\n")
            body_parts.append(f"{self.notes}\n")
        
        return f"---\n{frontmatter_str}---\n\n{''.join(body_parts)}"
    
    def compute_hash(self) -> str:
        """Compute deterministic hash for plan identity."""
        content = f"{self.title}|{self.acceptance_tests}|{self.feature_items}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
```

**Testing the artifact parser:**

```python
# tests/plan/test_artifact.py
import pytest
from datetime import datetime
from lyra_core.plan.artifact import PlanArtifact

def test_roundtrip_serialization():
    """Test markdown serialization and parsing."""
    plan = PlanArtifact(
        session_id="test-123",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        planner_model="deepseek-v4-pro",
        estimated_cost_usd=2.5,
        goal_hash="abc123",
        title="Add dark mode",
        acceptance_tests=["tests/test_theme.py::test_toggle"],
        expected_files=[{"path": "src/theme.tsx", "note": "new component"}],
        forbidden_files=[{"path": "package.json", "reason": "no new deps"}],
        feature_items=[{"skill": "edit", "description": "Create theme hook"}],
    )
    
    markdown = plan.to_markdown()
    parsed = PlanArtifact.from_markdown(markdown)
    
    assert parsed.session_id == plan.session_id
    assert parsed.title == plan.title
    assert parsed.acceptance_tests == plan.acceptance_tests
    assert parsed.expected_files == plan.expected_files

# Run: pytest tests/plan/test_artifact.py
```

## Step 3: Implement Permission Manager

Create `lyra_core/permissions/manager.py`:

```python
from enum import Enum
from contextlib import contextmanager
from typing import Dict

class PermissionMode(Enum):
    PLAN = "plan"
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"

class ToolPermission(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"

class PermissionManager:
    """Enforces tool permissions based on mode."""
    
    RULES: Dict[PermissionMode, Dict[str, ToolPermission]] = {
        PermissionMode.PLAN: {
            # Read-only tools
            "Read": ToolPermission.ALLOW,
            "Grep": ToolPermission.ALLOW,
            "Glob": ToolPermission.ALLOW,
            "LSP": ToolPermission.ALLOW,
            "WebFetch": ToolPermission.ALLOW,
            "AskUser": ToolPermission.ALLOW,
            # Write tools (denied)
            "Write": ToolPermission.DENY,
            "Edit": ToolPermission.DENY,
            "Bash": ToolPermission.DENY,
            "Delete": ToolPermission.DENY,
        },
        PermissionMode.DEFAULT: {
            "Write": ToolPermission.ASK,
            "Edit": ToolPermission.ASK,
            "Bash": ToolPermission.ASK,
            "Delete": ToolPermission.ASK,
        },
    }
    
    def __init__(self):
        self._mode_stack = [PermissionMode.DEFAULT]
    
    @property
    def current_mode(self) -> PermissionMode:
        return self._mode_stack[-1]
    
    @contextmanager
    def scope(self, mode: PermissionMode):
        """Temporarily change permission mode."""
        self._mode_stack.append(mode)
        try:
            yield
        finally:
            self._mode_stack.pop()
    
    def check_tool(self, tool_name: str) -> ToolPermission:
        """Check if tool is allowed in current mode."""
        mode = self.current_mode
        rules = self.RULES.get(mode, {})
        return rules.get(tool_name, ToolPermission.ASK)
    
    def enforce(self, tool_name: str):
        """Raise exception if tool is denied."""
        permission = self.check_tool(tool_name)
        if permission == ToolPermission.DENY:
            raise PermissionError(
                f"Tool '{tool_name}' is denied in {self.current_mode.value} mode"
            )

# tests/permissions/test_manager.py
import pytest
from lyra_core.permissions.manager import (
    PermissionManager,
    PermissionMode,
    ToolPermission,
)

def test_plan_mode_denies_writes():
    pm = PermissionManager()
    
    with pm.scope(PermissionMode.PLAN):
        assert pm.check_tool("Read") == ToolPermission.ALLOW
        assert pm.check_tool("Write") == ToolPermission.DENY
        
        with pytest.raises(PermissionError):
            pm.enforce("Write")

def test_mode_stack():
    pm = PermissionManager()
    
    assert pm.current_mode == PermissionMode.DEFAULT
    
    with pm.scope(PermissionMode.PLAN):
        assert pm.current_mode == PermissionMode.PLAN
    
    assert pm.current_mode == PermissionMode.DEFAULT
```

## Step 4: Implement Triviality Heuristics

Create `lyra_core/plan/heuristics.py`:

```python
import re
from typing import Dict, List

class TrivialityHeuristics:
    """Determines if a task is trivial enough to skip plan mode."""
    
    TRIVIAL_KEYWORDS = [
        "typo", "fix comment", "rename variable", "add log",
        "update doc", "fix formatting", "fix spacing",
    ]
    
    COMPLEX_KEYWORDS = [
        "plan", "design", "architect", "refactor", "migrate",
        "implement", "add feature", "build", "create system",
    ]
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
    
    def is_trivial(self, task: str, repo_info: Dict = None) -> bool:
        """
        Returns True if task should skip plan mode.
        
        Args:
            task: User's task string
            repo_info: Optional dict with repo stats (file_count, recent_edits)
        """
        score = self.compute_score(task, repo_info or {})
        return score >= self.threshold
    
    def compute_score(self, task: str, repo_info: Dict) -> float:
        """
        Compute triviality score 0.0 (complex) to 1.0 (trivial).
        """
        score = 0.0
        task_lower = task.lower()
        
        # Check for explicit complexity keywords (overrides everything)
        if any(kw in task_lower for kw in self.COMPLEX_KEYWORDS):
            return 0.0
        
        # Task length (shorter = more trivial)
        if len(task) < 80:
            score += 0.3
        elif len(task) < 150:
            score += 0.1
        
        # Trivial keyword matching
        matches = sum(1 for kw in self.TRIVIAL_KEYWORDS if kw in task_lower)
        if matches > 0:
            score += min(0.4, matches * 0.2)
        
        # File scope (single file = more trivial)
        file_mentions = re.findall(r'\b\w+\.\w{2,5}\b', task)
        if len(file_mentions) == 1:
            score += 0.2
        elif len(file_mentions) == 0:
            score += 0.1
        
        # Recent activity (already in flow)
        if repo_info.get("recent_edits", 0) > 20:
            score += 0.1
        
        return min(score, 1.0)

# tests/plan/test_heuristics.py
def test_trivial_detection():
    h = TrivialityHeuristics(threshold=0.7)
    
    # Trivial tasks
    assert h.is_trivial("fix typo in README.md")
    assert h.is_trivial("rename getUserName to getUsername")
    
    # Non-trivial tasks
    assert not h.is_trivial("design and implement auth system")
    assert not h.is_trivial("refactor the entire codebase")
    assert not h.is_trivial("plan the migration to microservices")

def test_explicit_override():
    h = TrivialityHeuristics()
    
    # Even short, "plan" keyword forces non-trivial
    assert not h.is_trivial("plan this")
```

## Step 5: Implement Plan Storage

Create `lyra_core/storage/plan_store.py`:

```python
from pathlib import Path
import json
from typing import Optional, List, Dict
from lyra_core.plan.artifact import PlanArtifact

class PlanStore:
    """Manages plan artifact persistence."""
    
    def __init__(self, plans_dir: Path):
        self.plans_dir = Path(plans_dir)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.plans_dir / "index.json"
        self._index = self._load_index()
    
    def save(self, plan: PlanArtifact) -> Path:
        """Save plan to filesystem and update index."""
        # Determine filename
        if plan.revision_num > 0:
            filename = f"{plan.session_id}.rev-{plan.revision_num}.md"
        else:
            filename = f"{plan.session_id}.md"
        
        plan_path = self.plans_dir / filename
        
        # Write markdown
        plan_path.write_text(plan.to_markdown())
        
        # Update index
        self._index[plan.session_id] = {
            "session_id": plan.session_id,
            "created_at": plan.created_at.isoformat(),
            "title": plan.title,
            "status": "pending",
            "revisions": plan.revision_num,
            "path": str(plan_path),
        }
        self._save_index()
        
        plan.path = str(plan_path)
        return plan_path
    
    def load(self, session_id: str, revision: Optional[int] = None) -> PlanArtifact:
        """Load plan by session ID."""
        if session_id not in self._index:
            raise KeyError(f"No plan found for session {session_id}")
        
        if revision is not None:
            path = self.plans_dir / f"{session_id}.rev-{revision}.md"
        else:
            path = Path(self._index[session_id]["path"])
        
        if not path.exists():
            raise FileNotFoundError(f"Plan file missing: {path}")
        
        content = path.read_text()
        plan = PlanArtifact.from_markdown(content)
        plan.path = str(path)
        return plan
    
    def mark_approved(self, session_id: str, approver: str):
        """Mark plan as approved in index."""
        if session_id in self._index:
            self._index[session_id]["status"] = "approved"
            self._index[session_id]["approver"] = approver
            self._save_index()
    
    def list_all(self) -> List[Dict]:
        """List all plans."""
        return list(self._index.values())
    
    def _load_index(self) -> Dict:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text())
        return {}
    
    def _save_index(self):
        self.index_path.write_text(json.dumps(self._index, indent=2))

# tests/storage/test_plan_store.py
import tempfile
from pathlib import Path
from lyra_core.storage.plan_store import PlanStore
from lyra_core.plan.artifact import PlanArtifact
from datetime import datetime

def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = PlanStore(Path(tmpdir) / "plans")
        
        plan = PlanArtifact(
            session_id="test-123",
            created_at=datetime.utcnow(),
            planner_model="test-model",
            estimated_cost_usd=1.0,
            goal_hash="abc",
            title="Test plan",
        )
        
        # Save
        path = store.save(plan)
        assert path.exists()
        
        # Load
        loaded = store.load("test-123")
        assert loaded.session_id == plan.session_id
        assert loaded.title == plan.title
```

## Step 6: Implement Planner Agent (Simplified)

Create `lyra_core/plan/planner.py`:

```python
from lyra_core.plan.artifact import PlanArtifact
from lyra_core.permissions.manager import PermissionManager, PermissionMode
from datetime import datetime
import hashlib

class SimplePlanner:
    """Simplified planner for demonstration."""
    
    SYSTEM_PROMPT = """You are the Planner. Generate a structured plan.
Output format: YAML frontmatter + markdown sections.
Must include: acceptance tests, expected files, feature items."""
    
    def __init__(self, model_id: str, permission_manager: PermissionManager):
        self.model_id = model_id
        self.permissions = permission_manager
    
    async def generate_plan(self, task: str, session_id: str) -> PlanArtifact:
        """Generate a plan for the task."""
        with self.permissions.scope(PermissionMode.PLAN):
            # In real implementation, call LLM with read-only tools
            # For now, create a template plan
            
            plan = PlanArtifact(
                session_id=session_id,
                created_at=datetime.utcnow(),
                planner_model=self.model_id,
                estimated_cost_usd=self._estimate_cost(task),
                goal_hash=self._compute_goal_hash(task),
                title=task[:100],  # Simplified
                acceptance_tests=[],  # LLM would populate
                expected_files=[],
                forbidden_files=[],
                feature_items=[],
            )
            
            return plan
    
    def _estimate_cost(self, task: str) -> float:
        """Rough cost estimate based on task length."""
        return len(task) / 1000 * 0.5
    
    def _compute_goal_hash(self, task: str) -> str:
        """Hash the task for identity."""
        return hashlib.sha256(task.encode()).hexdigest()[:16]
```

## Step 7: Configuration

Create `config.yaml`:

```yaml
plan_mode:
  enabled: true
  auto_skip_trivial: true
  trivial_threshold: 0.7
  max_feature_items: 30

models:
  smart_slot: deepseek-v4-pro
  fast_slot: deepseek-chat

storage:
  plans_dir: .lyra/plans

permissions:
  default_mode: default
```

## Common Pitfalls

### 1. Forgetting to Restore Permission Mode

❌ **Wrong:**
```python
permissions.scope(PermissionMode.PLAN)
# ... planning code
# Mode never restored!
```

✅ **Correct:**
```python
with permissions.scope(PermissionMode.PLAN):
    # ... planning code
# Mode automatically restored
```

### 2. Not Validating Plan Artifact

❌ **Wrong:**
```python
plan = PlanArtifact.from_markdown(content)
store.save(plan)  # Could be invalid!
```

✅ **Correct:**
```python
plan = PlanArtifact.from_markdown(content)
validator.validate(plan)  # Raises if invalid
store.save(plan)
```

### 3. Hardcoding File Paths

❌ **Wrong:**
```python
plan_path = "/home/user/.lyra/plans/plan.md"
```

✅ **Correct:**
```python
plan_path = Path(config.storage.plans_dir) / f"{session_id}.md"
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Now see detailed permission checks
logger = logging.getLogger("lyra.permissions")
logger.setLevel(logging.DEBUG)
```

### Inspect Plan Artifacts

```bash
# Pretty-print plan
python -m lyra.tools.inspect_plan .lyra/plans/01HXK2N.md

# Validate plan schema
python -m lyra.tools.validate_plan .lyra/plans/01HXK2N.md
```

### Test with Mock LLM

```python
class MockPlanner(Planner):
    """Deterministic planner for testing."""
    
    async def generate_plan(self, context) -> PlanArtifact:
        return PlanArtifact(
            session_id=context.session_id,
            created_at=datetime.utcnow(),
            planner_model="mock",
            estimated_cost_usd=0.0,
            goal_hash="test",
            title=context.task,
            acceptance_tests=["tests/test_mock.py::test_pass"],
            feature_items=[{"skill": "edit", "description": "Mock change"}],
        )
```

## Testing Strategy

### Unit Tests

```python
# Test individual components
pytest tests/plan/test_artifact.py        # Artifact serialization
pytest tests/permissions/test_manager.py  # Permission enforcement
pytest tests/plan/test_heuristics.py     # Triviality detection
```

### Integration Tests

```python
# Test full workflow
pytest tests/integration/test_plan_mode.py

def test_full_plan_workflow():
    """Test plan generation → approval → storage."""
    orchestrator = create_orchestrator()
    result = await orchestrator.run(
        task="Add auth",
        session_id="test-123",
        config=default_config(),
    )
    
    assert result.status == "approved"
    assert result.plan is not None
    assert len(result.plan.feature_items) > 0
```

### Property-Based Tests

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=10, max_size=1000))
def test_plan_hash_deterministic(task):
    """Plan hash should be deterministic for same input."""
    plan1 = create_plan(task)
    plan2 = create_plan(task)
    assert plan1.compute_hash() == plan2.compute_hash()
```

## Next Steps

- [Architecture Overview](architecture.md) — Understand system design
- [Architecture Tradeoffs](architecture-tradeoffs.md) — Design decisions
- [System Design](system-design.md) — High-level abstractions
- [Deep Dive](deep-dive.md) — Advanced patterns and optimizations

## Resources

- Python async/await: https://docs.python.org/3/library/asyncio.html
- YAML parsing: https://pyyaml.org/wiki/PyYAMLDocumentation
- Testing with pytest: https://docs.pytest.org/
