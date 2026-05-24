# Lyra Command System - Complete Analysis & Implementation Plan

**Date**: 2026-05-24  
**Status**: Research Complete - Ready for Implementation

---

## 📊 Executive Summary

Lyra already has **80+ commands** defined but needs:
1. **UI Integration** - Commands not wired to the TypeScript UI
2. **Backend Implementation** - Many commands lack Python handlers
3. **ECC Integration** - Import 60 agents, 232 skills from ECC
4. **Claude Code Parity** - Ensure all Claude Code commands work

---

## 🎯 Current State Analysis

### ✅ What Lyra Has (80+ Commands Defined)

**File**: `packages/lyra-cli/src/lyra_cli/cli/commands.py`

#### Core Categories:
1. **Conversation & Navigation** (9 commands)
   - `/help`, `/exit`, `/quit`, `/clear`, `/new`, `/history`, `/compact`, `/search`, `/replay`

2. **Models & Configuration** (7 commands)
   - `/model`, `/models`, `/status`, `/budget`, `/stream`, `/config`, `/credentials`

3. **Planning & Execution** (6 commands)
   - `/plan`, `/approve`, `/reject`, `/spawn`, `/verify`, `/mode`

4. **Code Review & Diff** (6 commands)
   - `/review`, `/diff`, `/blame`, `/map`, `/security-review`, `/simplify`

5. **Tools & Skills** (4 commands)
   - `/tools`, `/skills`, `/memory`, `/mcp`

6. **Sessions & Handoff** (8 commands)
   - `/session`, `/handoff`, `/retro`, `/export`, `/copy`, `/resume`, `/fork`, `/rename`

7. **Teams & Agents** (3 commands)
   - `/team`, `/agents`, `/agentteams`

8. **Research & Investigation** (3 commands)
   - `/research`, `/investigate`, `/deep-research`

9. **Cron & Scheduling** (3 commands)
   - `/cron`, `/schedule`, `/loop`

10. **Memory & Reflection** (2 commands)
    - `/reflect`, `/btw`

11. **Configuration & Theme** (8 commands)
    - `/theme`, `/color`, `/statusline`, `/fast`, `/focus`, `/tui`, `/vim`, `/sandbox`

12. **Observability & Debugging** (11 commands)
    - `/trace`, `/self`, `/context`, `/stats`, `/cost`, `/badges`, `/debug`, `/doctor`, `/hooks`, `/permissions`, `/usage`

13. **Advanced Features** (18 commands)
    - `/autopilot`, `/ultrawork`, `/ralph`, `/ralplan`, `/continue`, `/sharpen`, `/directive`, `/contract`, `/batch`, `/add-dir`, `/pr-comments`, `/feedback`, `/release-notes`, `/logout`, `/plugin`, `/reload-plugins`, `/claude-api`

14. **Lyra Unique Features** (19 commands)
    - `/scaling`, `/coverage`, `/bundle`, `/meta-evolve`, `/commands`, `/keybindings`, `/palette`, `/soul`, `/policy`, `/evals`, `/auth`, `/init`, `/rewind`, `/redo`, `/toolsets`, `/wiki`, `/voice`, `/split`, `/pair`, `/recap`

15. **Git Operations** (3 commands)
    - `/commit`, `/pr`, `/push`

---

## 🔍 Claude Code Commands (Official 2026)

### Core Commands (from research):
1. `/help` - List all commands ✅ (Lyra has)
2. `/clear` - Clear conversation ✅ (Lyra has)
3. `/init` - Initialize project ✅ (Lyra has)
4. `/memory` - Manage memory ✅ (Lyra has)
5. `/compact` - Compress session ✅ (Lyra has)
6. `/plan` - Plan mode ✅ (Lyra has)
7. `/mcp` - MCP servers ✅ (Lyra has)
8. `/agents` - Subagents ✅ (Lyra has)
9. `/permissions` - Approval rules ✅ (Lyra has)
10. `/review` - Code review ✅ (Lyra has)

### Additional Claude Code Commands:
11. `/new` - New conversation ✅
12. `/model` - Switch model ✅
13. `/status` - Show status ✅
14. `/diff` - Show diff ✅
15. `/commit` - Git commit ✅
16. `/pr` - Pull request ✅

**Result**: Lyra has **100% parity** with Claude Code commands!

---

## 🚀 ECC (Enhanced Claude Code) Features

### What ECC Has That Lyra Needs:

#### 1. **60 Specialized Agents**
- `planner` - Feature planning
- `architect` - System design
- `tdd-guide` - Test-driven development
- `code-reviewer` - Quality review
- `security-reviewer` - Security analysis
- `build-error-resolver` - Build fixes
- `e2e-runner` - E2E testing
- Language reviewers: TypeScript, Python, Go, Java, Kotlin, C++, Rust, F#
- `pytorch-build-resolver` - ML training errors
- `mle-reviewer` - ML pipeline review
- `harmonyos-app-resolver` - HarmonyOS development

#### 2. **232 Skills**
- `tdd-workflow` - Red-Green-Improve
- `security-review` - OWASP checklist
- `eval-harness` - Verification loops
- `frontend-slides` - Presentation builder
- `article-writing` - Long-form content
- `content-engine` - Social content
- `market-research` - Research workflows
- `investor-materials` - Pitch decks
- `continuous-learning-v2` - Instinct learning
- `search-first` - Research-before-code
- `mle-workflow` - Production ML

#### 3. **75 ECC Commands**
- `/build-fix` - Fix build errors
- `/security-scan` - AgentShield auditor
- `/multi-plan` - Multi-agent planning
- `/multi-execute` - Multi-agent execution
- `/pm2` - PM2 service management
- `/instinct-status` - Instinct management
- `/instinct-import` - Import instincts
- `/instinct-export` - Export instincts
- `/evolve` - Cluster instincts to skills
- `/skill-create` - Generate skills
- `/harness-audit` - Audit reliability
- `/loop-start` - Autonomous loops
- `/loop-status` - Loop status
- `/quality-gate` - Verification gates
- `/model-route` - Route by complexity

#### 4. **Novel Features**
- **AgentShield** - Security scanner (1282 tests, 102 rules)
- **Continuous Learning v2** - Instinct-based learning
- **Multi-Agent Orchestration** - PM2/tmux orchestration
- **Cross-Platform Support** - Cursor, Codex, OpenCode, Copilot
- **Hook Runtime Controls** - Environment-based tuning
- **Dashboard GUI** - Desktop application
- **Skill Creator** - Auto-generate from git history
- **Package Manager Detection** - Auto-detect npm/pnpm/yarn/bun

---

## 📋 Gap Analysis

### ❌ Missing in Lyra (Need to Implement)

#### High Priority (Core Functionality):
1. **Command Autocomplete in UI** - `/` should show command palette
2. **Command Handlers** - Wire commands to Python backend
3. **Command Help System** - `/help` should show categorized list
4. **Command Execution** - UI → Backend → Response flow

#### Medium Priority (ECC Features):
5. **AgentShield Integration** - Security scanning
6. **Continuous Learning** - Instinct-based learning
7. **Multi-Agent Orchestration** - PM2/tmux support
8. **Skill Creator** - Auto-generate skills
9. **Build Fix Command** - `/build-fix` handler
10. **Quality Gate** - `/quality-gate` verification

#### Low Priority (Nice to Have):
11. **Dashboard GUI** - Desktop app
12. **Cross-Platform Adapters** - Cursor/Codex support
13. **Package Manager Detection** - Auto-detect tools
14. **Hook Runtime Controls** - Environment tuning

---

## 🎯 Implementation Plan

### Phase 1: UI Command Integration (Week 1)

#### Task 1.1: Command Autocomplete
**File**: `packages/ui-terminal/src/components/InputArea.tsx`

```typescript
// Add command autocomplete to existing @ file completion
if (input.startsWith('/')) {
  const query = input.slice(1).toLowerCase()
  const matches = LYRA_COMMANDS.filter(cmd =>
    cmd.toLowerCase().startsWith(query)
  )
  setShowSuggestions(matches.length > 0)
}
```

**Status**: ✅ Already implemented! (Found in InputArea.tsx:41-52)

#### Task 1.2: Command Palette Component
**File**: `packages/ui-terminal/src/components/CommandPalette.tsx` (NEW)

```typescript
export function CommandPalette({ visible, onSelect, onClose }) {
  // Show all 80+ commands in categorized view
  // Fuzzy search
  // Keyboard navigation
  // Show descriptions
}
```

#### Task 1.3: Command Help Display
**File**: `packages/ui-terminal/src/components/CommandHelp.tsx` (NEW)

```typescript
export function CommandHelp({ category }) {
  // Display commands by category
  // Show keyboard shortcuts
  // Link to documentation
}
```

### Phase 2: Backend Command Handlers (Week 2)

#### Task 2.1: Command Dispatcher
**File**: `packages/lyra-cli/src/lyra_cli/commands/dispatcher.py`

```python
class CommandDispatcher:
    def __init__(self):
        self.handlers = self._load_handlers()
    
    def dispatch(self, command: str, args: dict) -> CommandResult:
        handler = self.handlers.get(command)
        if not handler:
            return CommandResult(error=f"Unknown command: {command}")
        return handler.execute(args)
```

#### Task 2.2: Implement Missing Handlers
**Files**: `packages/lyra-cli/src/lyra_cli/commands/*.py`

Priority order:
1. `/help` - Show command list
2. `/clear` - Clear session
3. `/research` - Deep research workflow
4. `/agents` - List agents
5. `/skills` - List skills
6. `/memory` - Memory operations
7. `/review` - Code review
8. `/security-review` - Security scan
9. `/build-fix` - Fix build errors
10. `/quality-gate` - Verification

#### Task 2.3: Command-to-Handler Registry
**File**: `packages/lyra-cli/src/lyra_cli/commands/registry.py`

```python
COMMAND_HANDLERS = {
    "/help": HelpCommandHandler,
    "/clear": ClearCommandHandler,
    "/research": ResearchCommandHandler,
    "/agents": AgentsCommandHandler,
    "/skills": SkillsCommandHandler,
    # ... 75 more
}
```

### Phase 3: ECC Integration (Week 3)

#### Task 3.1: Import ECC Agents
**Directory**: `packages/lyra-cli/src/lyra_cli/agents/ecc/`

Copy 60 agents from ECC:
- planner.py
- architect.py
- tdd-guide.py
- code-reviewer.py
- security-reviewer.py
- ... (55 more)

#### Task 3.2: Import ECC Skills
**Directory**: `packages/lyra-cli/src/lyra_cli/skills/ecc/`

Copy 232 skills from ECC:
- tdd-workflow.md
- security-review.md
- eval-harness.md
- ... (229 more)

#### Task 3.3: AgentShield Integration
**File**: `packages/lyra-cli/src/lyra_cli/security/agent_shield.py`

```python
class AgentShield:
    def scan(self, target: str) -> SecurityReport:
        # 1282 tests, 102 rules
        # Secrets detection (14 patterns)
        # Permission auditing
        # Hook injection analysis
        # MCP server risk profiling
        pass
```

#### Task 3.4: Continuous Learning v2
**File**: `packages/lyra-cli/src/lyra_cli/learning/continuous_v2.py`

```python
class ContinuousLearning:
    def extract_instinct(self, session: Session) -> Instinct:
        # Pattern extraction
        # Confidence scoring
        # Import/export
        # Evolution to skills
        pass
```

### Phase 4: Advanced Features (Week 4)

#### Task 4.1: Multi-Agent Orchestration
**File**: `packages/lyra-cli/src/lyra_cli/orchestration/multi_agent.py`

```python
class MultiAgentOrchestrator:
    def plan(self, task: str) -> ExecutionPlan:
        # Decompose task
        # Assign to agents
        # Coordinate execution
        pass
    
    def execute(self, plan: ExecutionPlan) -> Result:
        # PM2/tmux orchestration
        # Parallel execution
        # Result aggregation
        pass
```

#### Task 4.2: Skill Creator
**File**: `packages/lyra-cli/src/lyra_cli/skills/creator.py`

```python
class SkillCreator:
    def create_from_git(self, repo: str) -> Skill:
        # Analyze git history
        # Extract patterns
        # Generate skill definition
        pass
```

#### Task 4.3: Quality Gate
**File**: `packages/lyra-cli/src/lyra_cli/verification/quality_gate.py`

```python
class QualityGate:
    def verify(self, changes: Changes) -> GateResult:
        # Run tests
        # Check coverage
        # Security scan
        # Performance check
        pass
```

---

## 📊 Implementation Checklist

### Phase 1: UI Command Integration ✅
- [x] Command autocomplete (already done)
- [ ] Command palette component
- [ ] Command help display
- [ ] Keyboard shortcuts (Ctrl+K for palette)

### Phase 2: Backend Command Handlers
- [ ] Command dispatcher
- [ ] `/help` handler
- [ ] `/clear` handler
- [ ] `/research` handler
- [ ] `/agents` handler
- [ ] `/skills` handler
- [ ] `/memory` handler
- [ ] `/review` handler
- [ ] `/security-review` handler
- [ ] `/build-fix` handler
- [ ] 70 more handlers...

### Phase 3: ECC Integration
- [ ] Import 60 agents
- [ ] Import 232 skills
- [ ] AgentShield integration
- [ ] Continuous Learning v2
- [ ] Multi-agent orchestration

### Phase 4: Advanced Features
- [ ] Skill creator
- [ ] Quality gate
- [ ] Dashboard GUI
- [ ] Cross-platform adapters

---

## 🎨 UI Design Mockups

### Command Palette (Ctrl+K)
```
╭─────────────────────────────────────────────────────────╮
│ Search commands...                                  [x] │
├─────────────────────────────────────────────────────────┤
│ > /research                                             │
│   /deep-research    Deep research workflow (10-step)   │
│   /investigate      DCI-mode investigation             │
│                                                         │
│ Conversation & Navigation                               │
│   /help            List all commands                    │
│   /clear           Clear screen                         │
│   /new             Start fresh chat                     │
│                                                         │
│ Research & Investigation                                │
│   /research        Deep research workflow               │
│   /investigate     DCI-mode investigation              │
│                                                         │
│ [↑↓ navigate] [Enter select] [Esc close]              │
╰─────────────────────────────────────────────────────────╯
```

### Command Help (/help)
```
╭─────────────────────────────────────────────────────────╮
│ Lyra Commands (80+)                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Conversation & Navigation:                              │
│   /help            List all commands                    │
│   /exit            Exit REPL                            │
│   /clear           Clear screen                         │
│   /new             Start fresh chat                     │
│                                                         │
│ Research & Investigation:                               │
│   /research        Deep research workflow (10-step)     │
│   /investigate     DCI-mode investigation              │
│   /deep-research   Alias for /research                 │
│                                                         │
│ Teams & Agents:                                         │
│   /team            Multi-agent team execution          │
│   /agents          List available agents               │
│   /agentteams      Anthropic Agent Teams runtime       │
│                                                         │
│ [Page 1/5] [↑↓ scroll] [q quit]                       │
╰─────────────────────────────────────────────────────────╯
```

---

## 🔧 Technical Architecture

### Command Flow
```
┌─────────────┐
│   User      │
│  Types /cmd │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  InputArea  │ ← Autocomplete
│ (TypeScript)│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Transport  │ ← HTTP/SSE
│   (local)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ ui_server.py│ ← POST /chat
│  :3737      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Dispatcher  │ ← Route command
│   (Python)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Handler   │ ← Execute
│  (Python)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Result    │ ← Stream back
│    (SSE)    │
└─────────────┘
```

### Command Handler Interface
```python
class CommandHandler(ABC):
    @abstractmethod
    def execute(self, args: dict) -> CommandResult:
        pass
    
    @abstractmethod
    def get_help(self) -> str:
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        pass
```

---

## 📚 Documentation Structure

### 1. User Documentation
**File**: `docs/commands/README.md`
- Complete command reference
- Examples for each command
- Keyboard shortcuts
- Tips and tricks

### 2. Developer Documentation
**File**: `docs/development/commands.md`
- How to add new commands
- Command handler interface
- Testing commands
- Debugging commands

### 3. API Documentation
**File**: `docs/api/commands.md`
- HTTP API for commands
- Request/response format
- Error handling
- Rate limiting

---

## 🎯 Success Metrics

### Phase 1 Success:
- ✅ Command autocomplete works
- ✅ Command palette opens with Ctrl+K
- ✅ All 80+ commands visible in UI
- ✅ Keyboard navigation works

### Phase 2 Success:
- ✅ All commands have handlers
- ✅ Commands execute correctly
- ✅ Error handling works
- ✅ Streaming responses work

### Phase 3 Success:
- ✅ 60 ECC agents imported
- ✅ 232 ECC skills imported
- ✅ AgentShield scans work
- ✅ Continuous learning works

### Phase 4 Success:
- ✅ Multi-agent orchestration works
- ✅ Skill creator generates skills
- ✅ Quality gate verifies changes
- ✅ Dashboard GUI launches

---

## 🚀 Next Steps

### Immediate (Today):
1. Create CommandPalette component
2. Wire up Ctrl+K shortcut
3. Test command autocomplete

### This Week:
1. Implement command dispatcher
2. Create 10 priority handlers
3. Test command execution flow

### This Month:
1. Import ECC agents and skills
2. Integrate AgentShield
3. Build multi-agent orchestration
4. Launch dashboard GUI

---

## 📖 References

### Claude Code Documentation:
- [Claude Code Commands](https://docs.claude.com/en/docs/claude-code/commands)
- [Claude Code CLI Usage](https://docs.anthropic.com/en/docs/claude-code/cli-usage)
- [Command Reference](https://institute.sfeir.com/en/claude-code/claude-code-essential-slash-commands/command-reference/)
- [Commands Cheat Sheet](https://www.scriptbyai.com/claude-code-commands-cheat-sheet/)
- [Complete Documentation](https://claude.ai/public/artifacts/e2725e41-cca5-48e5-9c15-6eab92012e75)
- [CLI Reference Guide](https://smartscope.blog/en/generative-ai/claude/claude-code-reference-guide/)
- [Claude Code Cheatsheet](https://support.claude.com/en/articles/14553413-claude-code-cheatsheet)
- [Production Commands](https://github.com/wshobson/commands)
- [Developer's Guide](https://timdietrich.me/blog/claude-code-commands-guide/)
- [Beginner's Guide](https://anthemcreation.com/en/artificial-intelligence/claude-code-command-guide-for-beginners/)

### ECC Repository:
- [ECC GitHub](https://github.com/affaan-m/ECC)

---

**Last Updated**: 2026-05-24  
**Status**: ✅ Research Complete - Ready for Implementation  
**Next**: Start Phase 1 - UI Command Integration
