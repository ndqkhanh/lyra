# Hooks System

The hooks system provides event-driven automation at key lifecycle points. Hooks enable validation, modification, formatting, and verification without manual intervention.

## Architecture

### Core Components

- **HookMetadata**: Dataclass representing hook definitions
- **HookRegistry**: Loads and manages hooks from directories
- **HookExecutor**: Executes hooks at lifecycle points
- **HookType**: Enum defining hook execution types

### Hook Types

- **PreToolUse**: Before tool execution (validation, parameter modification)
- **PostToolUse**: After tool execution (auto-format, checks)
- **Stop**: When session ends (cleanup, final verification)
- **SessionStart**: When session starts (load context, check environment)
- **SessionEnd**: When session ends (generate summary, save state)
- **PreCompact**: Before context compaction (preserve state, backup)

### Hook Definition Format

Hooks are defined in markdown files with YAML frontmatter:

```markdown
---
name: hook-name
description: Brief description
type: PreToolUse
script: script_name.py
enabled: true
---

# Hook Name

Detailed documentation here.
```

## Usage

### Loading Hooks

```python
from lyra_cli.core.hook_registry import HookRegistry
from pathlib import Path

# Initialize registry with hook directories
registry = HookRegistry([
    Path("src/lyra_cli/hooks")
])

# Load all hooks
registry.load_hooks()
```

### Executing Hooks

```python
from lyra_cli.core.hook_executor import HookExecutor
from lyra_cli.core.hook_metadata import HookType

# Create executor with registry
executor = HookExecutor(registry)

# Execute hooks of a specific type
results = executor.execute_hooks(HookType.PRE_TOOL_USE)

for result in results:
    if result.success:
        print(result.output)
    else:
        print(f"Error: {result.error}")
```

### Managing Hooks

```python
# Get specific hook
hook = registry.get_hook("validate-tool-params")

# Get hooks by type
pre_hooks = registry.get_hooks_by_type(HookType.PRE_TOOL_USE)

# Search hooks
results = registry.search_hooks("validate")

# List all hooks
all_hooks = registry.list_hooks()
```

## Core Hooks

### PreToolUse Hooks

#### validate-tool-params
- **Description**: Validate tool parameters before execution
- **Script**: validate_params.py
- **Checks**: Required parameters, types, file paths, constraints

#### modify-tool-params
- **Description**: Modify tool parameters before execution
- **Script**: modify_params.py
- **Modifications**: Normalize paths, add defaults, apply preferences

### PostToolUse Hooks

#### auto-format
- **Description**: Auto-format code after tool execution
- **Script**: auto_format.py
- **Formatting**: Language-specific formatters, import ordering, style

#### run-checks
- **Description**: Run quality checks after tool execution
- **Script**: run_checks.py
- **Checks**: Lint, type annotations, imports, quick tests

### Stop Hooks

#### cleanup-temp-files
- **Description**: Clean up temporary files before session ends
- **Script**: cleanup_temp.py
- **Cleanup**: Temp files, build artifacts, cache, logs

#### final-verification
- **Description**: Run final verification before session ends
- **Script**: final_verification.py
- **Verification**: Tests pass, no uncommitted changes, quality metrics

### SessionStart Hooks

#### load-context
- **Description**: Load project context when session starts
- **Script**: load_context.py
- **Loading**: Project memory, preferences, agent registry, skills

#### check-environment
- **Description**: Check development environment when session starts
- **Script**: check_environment.py
- **Checks**: Required tools, Python version, dependencies, git status

### SessionEnd Hooks

#### generate-summary
- **Description**: Generate session summary when session ends
- **Script**: generate_summary.py
- **Summary**: Changes made, files modified, tasks completed, metrics

#### save-session-state
- **Description**: Save session state when session ends
- **Script**: save_session.py
- **Saving**: Conversation history, project memory, preferences, artifacts

### PreCompact Hooks

#### preserve-state
- **Description**: Preserve critical state before compaction
- **Script**: preserve_state.py
- **Preservation**: Important messages, task list, active modes, directives

#### backup-context
- **Description**: Backup context before compaction
- **Script**: backup_context.py
- **Backup**: Conversation state, project memory, context, recovery point

## Creating Custom Hooks

### 1. Create Hook File

Create a markdown file in `src/lyra_cli/hooks/`:

```markdown
---
name: my-hook
description: My custom hook
type: PostToolUse
script: my_hook.py
enabled: true
---

# My Hook

Hook documentation.
```

### 2. Implement Hook Script

Create the corresponding Python script:

```python
def execute(context):
    # Hook logic here
    return {"success": True, "output": "Hook executed"}
```

### 3. Register Hook

Hooks are automatically loaded from the hooks directory when the registry is initialized.

## Best Practices

1. **Single Responsibility**: Each hook should do one thing well
2. **Fast Execution**: Hooks should execute quickly to avoid blocking
3. **Error Handling**: Handle errors gracefully and return meaningful messages
4. **Idempotent**: Hooks should be safe to run multiple times
5. **Conditional Logic**: Use enabled flag to control hook execution

## Testing

Hooks are tested at three levels:

1. **Metadata Tests**: Verify hook metadata parsing
2. **Registry Tests**: Test hook loading and searching
3. **Executor Tests**: Test hook execution

Run tests:

```bash
pytest tests/hooks/ -v
```

## API Reference

### HookType

```python
class HookType(Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    PRE_COMPACT = "PreCompact"
```

### HookMetadata

```python
@dataclass
class HookMetadata:
    name: str
    description: str
    hook_type: HookType
    script: str
    enabled: bool = True
    file_path: Optional[str] = None
```

### HookRegistry

```python
class HookRegistry:
    def __init__(self, hook_dirs: Optional[List[Path]] = None)
    def load_hooks(self) -> Dict[str, HookMetadata]
    def get_hook(self, name: str) -> Optional[HookMetadata]
    def get_hooks_by_type(self, hook_type: HookType) -> List[HookMetadata]
    def search_hooks(self, query: str) -> List[HookMetadata]
    def list_hooks(self) -> List[HookMetadata]
```

### HookExecutor

```python
class HookExecutor:
    def __init__(self, registry: HookRegistry)
    def execute_hooks(self, hook_type: HookType, context: Optional[Dict[str, Any]] = None) -> List[HookResult]
```

### HookResult

```python
@dataclass
class HookResult:
    success: bool
    output: str
    error: Optional[str] = None
```

## Integration with Other Systems

### Agents
Hooks can trigger agent execution for complex tasks.

### Commands
Commands can be executed from hooks for automation.

### TUI
Hooks integrate with the TUI for visual feedback.

## See Also

- [AGENTS.md](AGENTS.md) - Agent system documentation
- [SKILLS.md](SKILLS.md) - Skills library documentation
- [COMMANDS.md](COMMANDS.md) - Command system documentation
- [LYRA_ECC_INTEGRATION_ULTRA_PLAN.md](../LYRA_ECC_INTEGRATION_ULTRA_PLAN.md) - Full integration plan
