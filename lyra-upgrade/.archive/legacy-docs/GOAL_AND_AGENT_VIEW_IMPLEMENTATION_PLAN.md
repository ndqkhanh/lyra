# 🎯 Lyra Goal Mode & Agent View Implementation Plan

**Based on Claude Code's /goal and /agent-view features**

Date: 2024-05-21  
Status: 📋 Planning  
Priority: 🔥 High

---

## 📚 Research Summary

### What is /goal?

**Claude Code's /goal command** enables autonomous, long-running agent execution:

1. **User sets a completion condition** (e.g., "all tests pass")
2. **Agent works autonomously** across multiple turns
3. **Separate evaluator model** checks condition after each turn
4. **Continues until condition met** or manually stopped

**Key Architecture:**
- **Dual-model system**: Main agent (Opus/Sonnet) + Evaluator (Haiku)
- **Evaluator independence**: Fresh model prevents "done bias"
- **Session-scoped**: Goal persists within a session
- **Hook-based**: Implemented as a Stop hook
- **Budget tracking**: Turns, tokens, wall-clock time

### What is /agent-view?

**Claude Code's agent view** provides multi-session orchestration:

1. **Supervisor process** manages multiple background sessions
2. **TUI dashboard** shows all sessions in one view
3. **Session states**: running, waiting, done, failed
4. **Dispatch & monitor** without attaching to full transcripts
5. **Peek & reply** to sessions without full context

**Key Architecture:**
- **Supervisor daemon**: Background process managing sessions
- **Session persistence**: Survives sleep, not shutdown
- **Worktree isolation**: Each session gets its own git worktree
- **State management**: SQLite-backed session state
- **Keyboard shortcuts**: Navigate, attach, dispatch

---

## 🎯 Implementation Goals for Lyra

### Phase 1: Goal Mode ✅ Priority
Implement autonomous goal-driven execution with evaluator separation.

### Phase 2: Agent View 🔄 High Priority
Implement multi-session orchestration and management.

---

## 📋 Phase 1: Goal Mode Implementation

### 1.1 Core Goal System

**File**: `packages/lyra-cli/lyra/goal/goal_manager.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal
from enum import Enum

class GoalStatus(Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    CLEARED = "cleared"
    FAILED = "failed"

@dataclass
class Goal:
    """Represents an active or completed goal."""
    condition: str
    status: GoalStatus
    created_at: datetime
    turns: int = 0
    tokens: int = 0
    elapsed_seconds: float = 0.0
    last_reason: Optional[str] = None
    achieved_at: Optional[datetime] = None
    
class GoalManager:
    """Manages goal lifecycle for a session."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_goal: Optional[Goal] = None
        
    def set_goal(self, condition: str) -> Goal:
        """Set a new goal, replacing any active goal."""
        self.current_goal = Goal(
            condition=condition,
            status=GoalStatus.ACTIVE,
            created_at=datetime.now()
        )
        return self.current_goal
        
    def clear_goal(self) -> None:
        """Clear the active goal."""
        if self.current_goal:
            self.current_goal.status = GoalStatus.CLEARED
            
    def is_active(self) -> bool:
        """Check if a goal is currently active."""
        return (self.current_goal is not None and 
                self.current_goal.status == GoalStatus.ACTIVE)
                
    def update_metrics(self, turns: int = 0, tokens: int = 0) -> None:
        """Update goal metrics after a turn."""
        if self.current_goal:
            self.current_goal.turns += turns
            self.current_goal.tokens += tokens
            self.current_goal.elapsed_seconds = (
                datetime.now() - self.current_goal.created_at
            ).total_seconds()
```

### 1.2 Evaluator System

**File**: `packages/lyra-cli/lyra/goal/evaluator.py`

```python
from typing import Tuple, Literal
from lyra.providers import get_provider

class GoalEvaluator:
    """Evaluates goal completion using a separate model."""
    
    def __init__(self, provider: str = "anthropic", model: str = "claude-3-5-haiku-20241022"):
        """
        Initialize evaluator with a small, fast model.
        
        Args:
            provider: LLM provider (anthropic, openai, etc.)
            model: Small fast model for evaluation (Haiku, GPT-4o-mini)
        """
        self.provider = get_provider(provider)
        self.model = model
        
    async def evaluate(
        self, 
        condition: str, 
        conversation_history: list[dict]
    ) -> Tuple[bool, str]:
        """
        Evaluate if the goal condition is met.
        
        Args:
            condition: The goal condition to check
            conversation_history: Full conversation transcript
            
        Returns:
            (is_met, reason): Boolean and explanation
        """
        
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(condition, conversation_history)
        
        # Call evaluator model
        response = await self.provider.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.0  # Deterministic evaluation
        )
        
        # Parse response
        is_met, reason = self._parse_evaluation(response)
        
        return is_met, reason
        
    def _build_evaluation_prompt(
        self, 
        condition: str, 
        conversation_history: list[dict]
    ) -> str:
        """Build the evaluation prompt."""
        
        # Format conversation
        transcript = self._format_transcript(conversation_history)
        
        return f"""You are an objective evaluator checking if a goal condition is met.

GOAL CONDITION:
{condition}

CONVERSATION TRANSCRIPT:
{transcript}

Your task:
1. Read the conversation transcript carefully
2. Check if the goal condition is satisfied based on what's in the transcript
3. You cannot run commands or read files - only judge from the transcript
4. Return your decision in this exact format:

DECISION: [YES or NO]
REASON: [One sentence explaining why]

Be strict: only return YES if the condition is clearly and verifiably met in the transcript.
"""

    def _format_transcript(self, history: list[dict]) -> str:
        """Format conversation history for evaluation."""
        lines = []
        for msg in history[-20:]:  # Last 20 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"[{role.upper()}]: {content[:500]}")
        return "\n\n".join(lines)
        
    def _parse_evaluation(self, response: str) -> Tuple[bool, str]:
        """Parse evaluator response."""
        lines = response.strip().split("\n")
        
        decision = False
        reason = "No reason provided"
        
        for line in lines:
            if line.startswith("DECISION:"):
                decision = "YES" in line.upper()
            elif line.startswith("REASON:"):
                reason = line.replace("REASON:", "").strip()
                
        return decision, reason
```

### 1.3 Goal Loop Integration

**File**: `packages/lyra-cli/lyra/goal/goal_loop.py`

```python
import asyncio
from typing import Optional
from lyra.goal.goal_manager import GoalManager, GoalStatus
from lyra.goal.evaluator import GoalEvaluator
from lyra.agent import Agent

class GoalLoop:
    """Autonomous goal-driven execution loop."""
    
    def __init__(
        self, 
        agent: Agent,
        goal_manager: GoalManager,
        evaluator: GoalEvaluator,
        max_turns: int = 100,
        max_tokens: int = 1_000_000
    ):
        self.agent = agent
        self.goal_manager = goal_manager
        self.evaluator = evaluator
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        
    async def run(self) -> GoalStatus:
        """
        Run the goal loop until completion or limits reached.
        
        Returns:
            Final goal status
        """
        
        if not self.goal_manager.is_active():
            raise ValueError("No active goal")
            
        goal = self.goal_manager.current_goal
        
        print(f"🎯 Goal: {goal.condition}")
        print(f"⏱️  Starting autonomous execution...")
        
        while self.goal_manager.is_active():
            # Check budget limits
            if goal.turns >= self.max_turns:
                print(f"⚠️  Max turns ({self.max_turns}) reached")
                goal.status = GoalStatus.FAILED
                goal.last_reason = "Turn limit exceeded"
                break
                
            if goal.tokens >= self.max_tokens:
                print(f"⚠️  Max tokens ({self.max_tokens}) reached")
                goal.status = GoalStatus.FAILED
                goal.last_reason = "Token limit exceeded"
                break
            
            # Execute one agent turn
            print(f"\n🔄 Turn {goal.turns + 1}...")
            turn_tokens = await self.agent.execute_turn()
            
            # Update metrics
            self.goal_manager.update_metrics(turns=1, tokens=turn_tokens)
            
            # Evaluate goal condition
            is_met, reason = await self.evaluator.evaluate(
                condition=goal.condition,
                conversation_history=self.agent.get_history()
            )
            
            goal.last_reason = reason
            
            if is_met:
                print(f"✅ Goal achieved: {reason}")
                goal.status = GoalStatus.ACHIEVED
                goal.achieved_at = datetime.now()
                break
            else:
                print(f"⏳ Not yet: {reason}")
                
            # Small delay between turns
            await asyncio.sleep(1)
            
        # Print summary
        self._print_summary(goal)
        
        return goal.status
        
    def _print_summary(self, goal):
        """Print goal execution summary."""
        print(f"\n{'='*60}")
        print(f"🎯 Goal Summary")
        print(f"{'='*60}")
        print(f"Status: {goal.status.value}")
        print(f"Turns: {goal.turns}")
        print(f"Tokens: {goal.tokens:,}")
        print(f"Time: {goal.elapsed_seconds:.1f}s")
        print(f"Reason: {goal.last_reason}")
        print(f"{'='*60}")
```

### 1.4 CLI Commands

**File**: `packages/lyra-cli/lyra/commands/goal.py`

```python
import click
from lyra.goal.goal_manager import GoalManager
from lyra.goal.evaluator import GoalEvaluator
from lyra.goal.goal_loop import GoalLoop

@click.group()
def goal():
    """Goal-driven autonomous execution."""
    pass

@goal.command()
@click.argument('condition', required=False)
@click.option('--max-turns', default=100, help='Maximum turns')
@click.option('--max-tokens', default=1_000_000, help='Maximum tokens')
@click.option('--evaluator-model', default='claude-3-5-haiku-20241022', 
              help='Evaluator model')
def set(condition, max_turns, max_tokens, evaluator_model):
    """Set a goal and run until completion."""
    
    if not condition:
        # Show status if no condition provided
        manager = GoalManager(session_id=get_current_session())
        if manager.current_goal:
            print_goal_status(manager.current_goal)
        else:
            click.echo("No active goal")
        return
        
    # Initialize components
    session_id = get_current_session()
    manager = GoalManager(session_id)
    evaluator = GoalEvaluator(model=evaluator_model)
    agent = get_current_agent()
    
    # Set goal
    goal = manager.set_goal(condition)
    
    # Run goal loop
    loop = GoalLoop(
        agent=agent,
        goal_manager=manager,
        evaluator=evaluator,
        max_turns=max_turns,
        max_tokens=max_tokens
    )
    
    import asyncio
    status = asyncio.run(loop.run())
    
    if status == GoalStatus.ACHIEVED:
        click.echo("✅ Goal achieved!")
    else:
        click.echo(f"⚠️  Goal ended: {status.value}")

@goal.command()
def clear():
    """Clear the active goal."""
    manager = GoalManager(session_id=get_current_session())
    manager.clear_goal()
    click.echo("Goal cleared")

@goal.command()
def status():
    """Show goal status."""
    manager = GoalManager(session_id=get_current_session())
    if manager.current_goal:
        print_goal_status(manager.current_goal)
    else:
        click.echo("No active goal")
```

---

## 📋 Phase 2: Agent View Implementation

### 2.1 Supervisor Process

**File**: `packages/lyra-cli/lyra/supervisor/supervisor.py`

```python
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

class SessionState(Enum):
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"

@dataclass
class Session:
    """Represents a background session."""
    id: str
    prompt: str
    state: SessionState
    created_at: datetime
    last_activity: datetime
    turns: int = 0
    tokens: int = 0
    last_message: Optional[str] = None
    goal: Optional[str] = None
    
class Supervisor:
    """Manages multiple background sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.running = False
        
    async def start(self):
        """Start the supervisor daemon."""
        self.running = True
        print("🎛️  Supervisor started")
        
        # Main supervisor loop
        while self.running:
            await self._check_sessions()
            await asyncio.sleep(1)
            
    async def stop(self):
        """Stop the supervisor daemon."""
        self.running = False
        print("🛑 Supervisor stopped")
        
    def dispatch(self, prompt: str, goal: Optional[str] = None) -> str:
        """
        Dispatch a new background session.
        
        Args:
            prompt: Initial prompt for the session
            goal: Optional goal condition
            
        Returns:
            Session ID
        """
        session_id = self._generate_session_id()
        
        session = Session(
            id=session_id,
            prompt=prompt,
            state=SessionState.RUNNING,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            goal=goal
        )
        
        self.sessions[session_id] = session
        
        # Start session in background
        asyncio.create_task(self._run_session(session))
        
        return session_id
        
    async def _run_session(self, session: Session):
        """Run a session in the background."""
        try:
            # Create agent for this session
            agent = create_agent(session.id)
            
            # If goal is set, use goal loop
            if session.goal:
                manager = GoalManager(session.id)
                manager.set_goal(session.goal)
                evaluator = GoalEvaluator()
                loop = GoalLoop(agent, manager, evaluator)
                await loop.run()
            else:
                # Regular execution
                await agent.execute(session.prompt)
                
            session.state = SessionState.DONE
            
        except Exception as e:
            session.state = SessionState.FAILED
            session.last_message = str(e)
            
    async def _check_sessions(self):
        """Check and update session states."""
        for session in self.sessions.values():
            # Update last activity
            # Check for timeouts
            # Handle state transitions
            pass
            
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid
        return f"session_{uuid.uuid4().hex[:8]}"
```

### 2.2 Agent View TUI

**File**: `packages/lyra-cli/lyra/tui/agent_view.py`

```python
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
import asyncio

class AgentView:
    """Terminal UI for managing multiple sessions."""
    
    def __init__(self, supervisor: Supervisor):
        self.supervisor = supervisor
        self.console = Console()
        self.selected_index = 0
        
    async def run(self):
        """Run the agent view TUI."""
        
        with Live(self._render(), refresh_per_second=2) as live:
            while True:
                # Handle keyboard input
                # Update display
                live.update(self._render())
                await asyncio.sleep(0.5)
                
    def _render(self) -> Layout:
        """Render the agent view layout."""
        
        layout = Layout()
        
        # Header
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Header panel
        layout["header"].update(
            Panel(
                "🎛️  Lyra Agent View - Manage Multiple Sessions",
                style="bold blue"
            )
        )
        
        # Session table
        table = self._build_session_table()
        layout["body"].update(table)
        
        # Footer with shortcuts
        layout["footer"].update(
            Panel(
                "↑/↓: Navigate | Enter: Attach | D: Dispatch | C: Clear | Q: Quit",
                style="dim"
            )
        )
        
        return layout
        
    def _build_session_table(self) -> Table:
        """Build the session list table."""
        
        table = Table(title="Active Sessions")
        
        table.add_column("ID", style="cyan")
        table.add_column("State", style="green")
        table.add_column("Prompt", style="white")
        table.add_column("Turns", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Time", justify="right")
        table.add_column("Last Activity")
        
        for i, session in enumerate(self.supervisor.sessions.values()):
            # Highlight selected row
            style = "bold" if i == self.selected_index else ""
            
            # State icon
            state_icon = {
                SessionState.RUNNING: "🔄",
                SessionState.WAITING: "⏸️",
                SessionState.DONE: "✅",
                SessionState.FAILED: "❌"
            }[session.state]
            
            # Calculate elapsed time
            elapsed = (datetime.now() - session.created_at).total_seconds()
            time_str = f"{elapsed:.0f}s"
            
            table.add_row(
                session.id[:8],
                f"{state_icon} {session.state.value}",
                session.prompt[:40],
                str(session.turns),
                f"{session.tokens:,}",
                time_str,
                session.last_message or "-",
                style=style
            )
            
        return table
```

### 2.3 CLI Integration

**File**: `packages/lyra-cli/lyra/commands/agents.py`

```python
import click
from lyra.supervisor.supervisor import Supervisor
from lyra.tui.agent_view import AgentView

@click.group()
def agents():
    """Multi-session agent management."""
    pass

@agents.command()
def view():
    """Open agent view dashboard."""
    supervisor = get_supervisor()
    view = AgentView(supervisor)
    
    import asyncio
    asyncio.run(view.run())

@agents.command()
@click.argument('prompt')
@click.option('--goal', help='Goal condition')
def dispatch(prompt, goal):
    """Dispatch a new background session."""
    supervisor = get_supervisor()
    session_id = supervisor.dispatch(prompt, goal=goal)
    click.echo(f"✅ Dispatched session: {session_id}")

@agents.command()
def list():
    """List all sessions."""
    supervisor = get_supervisor()
    
    for session in supervisor.sessions.values():
        click.echo(f"{session.id}: {session.state.value} - {session.prompt}")
```

---

## 🗂️ File Structure

```
packages/lyra-cli/lyra/
├── goal/
│   ├── __init__.py
│   ├── goal_manager.py       # Goal lifecycle management
│   ├── evaluator.py           # Separate evaluator model
│   └── goal_loop.py           # Autonomous execution loop
├── supervisor/
│   ├── __init__.py
│   ├── supervisor.py          # Multi-session supervisor
│   └── session_store.py       # Session persistence (SQLite)
├── tui/
│   ├── __init__.py
│   └── agent_view.py          # Terminal UI dashboard
└── commands/
    ├── goal.py                # /goal commands
    └── agents.py              # /agents commands
```

---

## 📊 Implementation Phases

### Phase 1: Goal Mode (Week 1-2)
- [x] Research complete
- [ ] Core goal manager
- [ ] Evaluator system
- [ ] Goal loop
- [ ] CLI commands
- [ ] Testing
- [ ] Documentation

### Phase 2: Agent View (Week 3-4)
- [ ] Supervisor process
- [ ] Session persistence
- [ ] TUI dashboard
- [ ] Keyboard shortcuts
- [ ] CLI integration
- [ ] Testing
- [ ] Documentation

### Phase 3: Integration (Week 5)
- [ ] Integrate with existing Lyra systems
- [ ] Memory system integration
- [ ] RSI system integration
- [ ] Observability integration
- [ ] End-to-end testing

### Phase 4: Polish (Week 6)
- [ ] Performance optimization
- [ ] Error handling
- [ ] User experience improvements
- [ ] Documentation completion
- [ ] Examples and tutorials

---

## 🎯 Success Criteria

### Goal Mode
- ✅ Can set goal with condition
- ✅ Autonomous execution across turns
- ✅ Separate evaluator model
- ✅ Budget tracking (turns, tokens, time)
- ✅ Clear status reporting
- ✅ Works with existing Lyra agents

### Agent View
- ✅ Supervisor manages multiple sessions
- ✅ TUI shows all sessions
- ✅ Can dispatch new sessions
- ✅ Can attach to sessions
- ✅ Session persistence
- ✅ Keyboard navigation

---

## 🔧 Technical Decisions

### 1. Evaluator Model Choice
**Decision**: Use Claude 3.5 Haiku by default
**Rationale**: 
- Fast and cheap
- Good at structured evaluation
- Same provider as main agent
- Can be overridden by user

### 2. Session Persistence
**Decision**: SQLite database
**Rationale**:
- Simple, no external dependencies
- Good for local development
- Easy to query and debug
- Can migrate to PostgreSQL later

### 3. TUI Framework
**Decision**: Rich library
**Rationale**:
- Already used in Lyra
- Excellent table and layout support
- Good keyboard handling
- Active development

### 4. Supervisor Architecture
**Decision**: Asyncio-based daemon
**Rationale**:
- Native Python async
- Good for I/O-bound tasks
- Easy to integrate with existing code
- No additional dependencies

---

## 📚 Dependencies

### New Dependencies
```toml
[tool.poetry.dependencies]
rich = "^13.7.0"          # TUI framework (already in Lyra)
aiosqlite = "^0.19.0"     # Async SQLite
prompt-toolkit = "^3.0.43" # Keyboard input
```

### Existing Dependencies
- anthropic (for evaluator)
- openai (optional evaluator)
- asyncio (standard library)

---

## 🧪 Testing Strategy

### Unit Tests
- Goal manager lifecycle
- Evaluator parsing
- Session state transitions
- Supervisor dispatch

### Integration Tests
- Goal loop with mock agent
- Multi-session execution
- TUI rendering
- CLI commands

### End-to-End Tests
- Real goal execution
- Multi-session workflows
- Error handling
- Budget limits

---

## 📖 Documentation

### User Documentation
- `/goal` command guide
- `/agents` command guide
- Writing effective conditions
- Multi-session workflows
- Troubleshooting

### Developer Documentation
- Architecture overview
- Evaluator system design
- Supervisor implementation
- TUI components
- Extension points

---

## 🚀 Future Enhancements

### Goal Mode
- [ ] Multiple evaluator strategies (self-audit, hybrid)
- [ ] Custom evaluator prompts
- [ ] Goal templates library
- [ ] Goal composition (sub-goals)
- [ ] Budget alerts and warnings

### Agent View
- [ ] Remote sessions (SSH)
- [ ] Session sharing
- [ ] Session replay
- [ ] Performance metrics
- [ ] Cost tracking per session

### Integration
- [ ] Web UI for agent view
- [ ] Mobile notifications
- [ ] Slack/Discord integration
- [ ] CI/CD integration
- [ ] Cloud deployment

---

## 📝 Notes

### Key Insights from Research

1. **Evaluator Independence is Critical**
   - Separate model prevents "done bias"
   - Fresh context for each evaluation
   - Haiku is fast and cheap enough

2. **Session Isolation Matters**
   - Git worktrees for file isolation
   - Separate process per session
   - Clean state management

3. **User Experience Focus**
   - Clear status indicators
   - Keyboard shortcuts
   - Minimal context switching
   - Peek without full attach

4. **Budget Management**
   - Multiple budget types (turns, tokens, time)
   - Clear warnings before limits
   - Graceful degradation

### Differences from Claude Code

1. **Lyra Advantages**
   - Already has RSI system
   - Multi-layer memory
   - Advanced learning systems
   - Better observability

2. **Lyra Adaptations**
   - Integrate with existing memory
   - Use RSI for goal optimization
   - Leverage learning systems
   - Add Lyra-specific features

---

## ✅ Next Steps

1. **Review this plan** with team
2. **Prioritize features** (MVP vs future)
3. **Set up development branch**
4. **Start Phase 1 implementation**
5. **Create tracking issues**

---

**Status**: 📋 Ready for Implementation  
**Estimated Time**: 6 weeks  
**Priority**: 🔥 High  
**Dependencies**: None (can start immediately)

---

**References:**
- [Claude Code /goal docs](https://code.claude.com/docs/en/goal)
- [Claude Code agent view docs](https://code.claude.com/docs/en/agent-view)
- Research articles and blog posts (see web search results)
