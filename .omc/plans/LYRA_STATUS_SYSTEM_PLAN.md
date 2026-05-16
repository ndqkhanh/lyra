# Lyra Status System Implementation Plan

**Goal:** Implement Claude Code-style rich status display with background tasks, sub-agents, and progress tracking

**Inspired by:** Claude Code's status bar showing:
- Active operation with spinner and duration
- Background task count
- Sub-agent hierarchy with status icons
- Token usage per agent
- Interactive task selection

---

## Phase 1: Task Queue System (2-3 days)

### 1.1 Background Task Manager
**File:** `packages/lyra-cli/src/lyra_cli/cli/task_queue.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import asyncio
from datetime import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BackgroundTask:
    id: str
    name: str
    agent_type: str  # "general-purpose", "planner", "executor", etc.
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime]
    tokens_used: int
    cost: float
    parent_id: Optional[str]  # For sub-agents
    
class TaskQueue:
    """Manages background tasks and sub-agents."""
    
    def __init__(self):
        self.tasks: dict[str, BackgroundTask] = {}
        self.active_task_id: Optional[str] = None
        
    def add_task(self, task: BackgroundTask) -> str:
        """Add a new background task."""
        self.tasks[task.id] = task
        return task.id
        
    def get_active_tasks(self) -> list[BackgroundTask]:
        """Get all running tasks."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]
        
    def get_task_tree(self) -> dict:
        """Get hierarchical task tree (parent -> children)."""
        tree = {}
        for task in self.tasks.values():
            if task.parent_id is None:
                tree[task.id] = self._get_children(task.id)
        return tree
        
    def _get_children(self, parent_id: str) -> list[BackgroundTask]:
        """Get child tasks recursively."""
        children = [t for t in self.tasks.values() if t.parent_id == parent_id]
        result = []
        for child in children:
            result.append({
                "task": child,
                "children": self._get_children(child.id)
            })
        return result
```

### 1.2 Integration with Agent System
**File:** `packages/lyra-cli/src/lyra_cli/cli/agent_integration.py`

Add task tracking to agent integration:
```python
class TUIAgentIntegration:
    def __init__(self, model: str, repo_root, task_queue: TaskQueue, ...):
        self.task_queue = task_queue
        self.current_task_id: Optional[str] = None
        
    async def run_agent(self, user_input: str, parent_task_id: Optional[str] = None):
        # Create task
        task = BackgroundTask(
            id=str(uuid.uuid4()),
            name=user_input[:50],
            agent_type="general-purpose",
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
            completed_at=None,
            tokens_used=0,
            cost=0.0,
            parent_id=parent_task_id
        )
        self.current_task_id = self.task_queue.add_task(task)
        
        try:
            # Run agent...
            async for event in self._run_anthropic(user_input):
                yield event
                
            # Mark completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
        except Exception as e:
            task.status = TaskStatus.FAILED
            raise
```

---

## Phase 2: Rich Status Bar (2-3 days)

### 2.1 Status Bar Renderer
**File:** `packages/lyra-cli/src/lyra_cli/cli/status_bar.py`

```python
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from datetime import datetime

class StatusBarRenderer:
    """Renders Claude Code-style status bar."""
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.console = Console()
        
    def render(self) -> Panel:
        """Render full status display."""
        # Top section: Active operation
        active_section = self._render_active_operation()
        
        # Middle section: Task tree
        task_tree = self._render_task_tree()
        
        # Bottom section: Controls
        controls = self._render_controls()
        
        return Panel(
            f"{active_section}\n\n{task_tree}\n\n{controls}",
            border_style="blue"
        )
        
    def _render_active_operation(self) -> str:
        """Render active operation with spinner."""
        active_tasks = self.task_queue.get_active_tasks()
        if not active_tasks:
            return "✶ Idle"
            
        task = active_tasks[0]
        duration = (datetime.now() - task.started_at).total_seconds()
        
        # Spinner animation
        spinner = self._get_spinner()
        
        return f"{spinner} {task.name}… ({duration:.0f}s · ↓ {task.tokens_used} tokens)"
        
    def _render_task_tree(self) -> str:
        """Render hierarchical task tree."""
        tree = Tree("Tasks")
        
        task_tree = self.task_queue.get_task_tree()
        for task_id, children in task_tree.items():
            task = self.task_queue.tasks[task_id]
            self._add_task_node(tree, task, children)
            
        return tree
        
    def _add_task_node(self, parent, task: BackgroundTask, children: list):
        """Add task node to tree."""
        # Status icon
        icon = {
            TaskStatus.PENDING: "◻",
            TaskStatus.RUNNING: "◉",
            TaskStatus.COMPLETED: "✓",
            TaskStatus.FAILED: "✗",
            TaskStatus.CANCELLED: "⊗"
        }[task.status]
        
        # Duration
        if task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()
            duration_str = f"{duration:.0f}s"
        else:
            duration = (datetime.now() - task.started_at).total_seconds()
            duration_str = f"{duration:.0f}s"
            
        # Node text
        node_text = f"{icon} {task.agent_type}  {task.name}  {duration_str} · ↓ {task.tokens_used} tokens"
        
        branch = parent.add(node_text)
        
        # Add children recursively
        for child_data in children:
            self._add_task_node(branch, child_data["task"], child_data["children"])
            
    def _render_controls(self) -> str:
        """Render control hints."""
        bg_count = len(self.task_queue.get_active_tasks())
        return f"⏵⏵ bypass permissions on · {bg_count} background tasks · esc to interrupt · ctrl+t to toggle"
        
    def _get_spinner(self) -> str:
        """Get animated spinner character."""
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        import time
        idx = int(time.time() * 10) % len(spinners)
        return spinners[idx]
```

### 2.2 Live Status Updates
**File:** `packages/lyra-cli/src/lyra_cli/cli/status_live.py`

```python
from rich.live import Live
import asyncio

class LiveStatusDisplay:
    """Live-updating status display."""
    
    def __init__(self, status_renderer: StatusBarRenderer):
        self.renderer = status_renderer
        self.live = None
        
    async def start(self):
        """Start live display."""
        self.live = Live(self.renderer.render(), refresh_per_second=4)
        self.live.start()
        
        # Update loop
        while True:
            await asyncio.sleep(0.25)
            self.live.update(self.renderer.render())
            
    def stop(self):
        """Stop live display."""
        if self.live:
            self.live.stop()
```

---

## Phase 3: Interactive Task Selection (1-2 days)

### 3.1 Task Selector
**File:** `packages/lyra-cli/src/lyra_cli/cli/task_selector.py`

```python
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.application import Application

class TaskSelector:
    """Interactive task selector (↑/↓ to select, Enter to view)."""
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.selected_index = 0
        
    def create_key_bindings(self) -> KeyBindings:
        """Create key bindings for task selection."""
        kb = KeyBindings()
        
        @kb.add("up")
        def move_up(event):
            self.selected_index = max(0, self.selected_index - 1)
            
        @kb.add("down")
        def move_down(event):
            tasks = self.task_queue.get_active_tasks()
            self.selected_index = min(len(tasks) - 1, self.selected_index + 1)
            
        @kb.add("enter")
        def view_task(event):
            tasks = self.task_queue.get_active_tasks()
            if tasks:
                selected_task = tasks[self.selected_index]
                self._show_task_details(selected_task)
                
        return kb
        
    def _show_task_details(self, task: BackgroundTask):
        """Show detailed task view."""
        from rich.console import Console
        from rich.panel import Panel
        
        console = Console()
        
        details = f"""
Task ID: {task.id}
Agent Type: {task.agent_type}
Status: {task.status.value}
Started: {task.started_at.strftime('%H:%M:%S')}
Duration: {(datetime.now() - task.started_at).total_seconds():.0f}s
Tokens: {task.tokens_used:,}
Cost: ${task.cost:.4f}
        """
        
        console.print(Panel(details, title=task.name, border_style="cyan"))
```

---

## Phase 4: Sub-Agent Spawning (2-3 days)

### 4.1 Agent Orchestrator
**File:** `packages/lyra-cli/src/lyra_cli/cli/agent_orchestrator.py`

```python
class AgentOrchestrator:
    """Orchestrates multiple agents with parent-child relationships."""
    
    def __init__(self, task_queue: TaskQueue):
        self.task_queue = task_queue
        self.agents: dict[str, TUIAgentIntegration] = {}
        
    async def spawn_agent(
        self,
        agent_type: str,
        task: str,
        parent_task_id: Optional[str] = None
    ) -> str:
        """Spawn a new sub-agent."""
        agent = TUIAgentIntegration(
            model=self._get_model_for_agent(agent_type),
            repo_root=Path.cwd(),
            task_queue=self.task_queue
        )
        
        await agent.initialize()
        
        # Run in background
        task_id = await agent.run_agent(task, parent_task_id=parent_task_id)
        self.agents[task_id] = agent
        
        return task_id
        
    def _get_model_for_agent(self, agent_type: str) -> str:
        """Get appropriate model for agent type."""
        model_map = {
            "planner": "opus",
            "executor": "sonnet",
            "researcher": "sonnet",
            "writer": "haiku",
            "general-purpose": "auto"
        }
        return model_map.get(agent_type, "auto")
```

### 4.2 Integration with /team Command
Update `tui.py` to spawn sub-agents:

```python
def _handle_team_command(self, args: list[str]):
    """Handle /team command with sub-agents."""
    task = " ".join(args[1:])
    
    # Spawn orchestrator
    orchestrator = AgentOrchestrator(self.task_queue)
    
    # Spawn sub-agents
    asyncio.create_task(orchestrator.spawn_agent("planner", f"Plan: {task}"))
    asyncio.create_task(orchestrator.spawn_agent("executor", f"Execute: {task}"))
    asyncio.create_task(orchestrator.spawn_agent("researcher", f"Research: {task}"))
```

---

## Phase 5: Integration with TUI (1-2 days)

### 5.1 Update Main TUI
**File:** `packages/lyra-cli/src/lyra_cli/cli/tui.py`

```python
class LyraTUI:
    def __init__(self, ...):
        # Add task queue
        self.task_queue = TaskQueue()
        
        # Add status renderer
        self.status_renderer = StatusBarRenderer(self.task_queue)
        
        # Add live display
        self.live_status = LiveStatusDisplay(self.status_renderer)
        
    def _setup_ui(self):
        """Setup UI with status display."""
        # ... existing code ...
        
        # Add status display above input
        status_window = Window(
            content=FormattedTextControl(self._get_status_display),
            height=Dimension(min=5, max=15)
        )
        
        layout = Layout(
            HSplit([
                status_bar,
                status_window,  # NEW: Status display
                input_rule_top,
                self.input_area,
                input_rule_bot,
                completions_menu,
            ])
        )
        
    def _get_status_display(self) -> list[tuple[str, str]]:
        """Get status display fragments."""
        # Render status using status_renderer
        return self.status_renderer.render_compact()
```

---

## Phase 6: Testing & Polish (1-2 days)

### 6.1 Test Scenarios
1. Single agent execution
2. Multiple background tasks
3. Sub-agent hierarchy (3 levels deep)
4. Task cancellation
5. Task selection and viewing
6. Long-running tasks (>1 minute)

### 6.2 Performance Optimization
- Limit status bar refresh rate (4 FPS)
- Lazy render task tree (only visible nodes)
- Cache spinner animation frames

### 6.3 Visual Polish
- Color coding by task status
- Smooth animations
- Proper text truncation
- Responsive layout

---

## Implementation Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Task Queue | 2-3 days | None |
| Phase 2: Status Bar | 2-3 days | Phase 1 |
| Phase 3: Task Selection | 1-2 days | Phase 2 |
| Phase 4: Sub-Agents | 2-3 days | Phase 1 |
| Phase 5: TUI Integration | 1-2 days | Phase 2, 4 |
| Phase 6: Testing | 1-2 days | All |

**Total: 9-15 days**

---

## Success Criteria

✅ Status bar shows active operation with spinner and duration
✅ Background task count displayed
✅ Task tree shows parent-child relationships
✅ Token usage per agent visible
✅ Interactive task selection (↑/↓ + Enter)
✅ Sub-agents spawn correctly
✅ Real-time updates (4 FPS)
✅ Smooth animations
✅ No performance degradation with 10+ tasks

---

## Example Output

```
✶ Galloping… (32s · ↓ 20 tokens)
  ⎿  ◻ Phase 9: Production Readiness
     ◻ Phase 3: Implement Research Pipeline
     ◻ Phase 6: Interactive UI & Themes
     ◻ Phase 5: Memory Systems
     ◻ Phase 2: Integrate Real Agent Loop
      … +3 pending

────────────────────────────────────────────────────────────────────────────────
❯
────────────────────────────────────────────────────────────────────────────────
  ⏵⏵ bypass permissions on · 5 background tasks · esc to interrupt · ctrl+t toggle

  ⏺ main                                           ↑/↓ to select · Enter to view
  ◯ general-purpose  Deep research: Kilo, Hermes…  3m 4s · ↓ 63.6k tokens
  ◯ general-purpose  Verify model diversity…       3m 3s · ↓ 102.2k tokens
```

---

## Next Steps

1. Review and approve this plan
2. Start with Phase 1 (Task Queue System)
3. Commit each phase to GitHub
4. Test incrementally after each phase
