# Command System

The command system provides user-facing slash commands for common workflows. Commands are defined as markdown files with YAML frontmatter and can delegate to agents or reference skills.

## Architecture

### Core Components

- **CommandMetadata**: Dataclass representing command definitions
- **CommandRegistry**: Loads and manages commands from directories
- **CommandDispatcher**: Executes commands by name

### Command Definition Format

Commands are defined in markdown files with YAML frontmatter:

```markdown
---
name: command-name
description: Brief description
agent: agent-name (optional)
skill: skill-name (optional)
args: [arg1, arg2] (optional)
---

# /command-name Command

Detailed documentation here.
```

## Usage

### Loading Commands

```python
from lyra_cli.core.command_registry import CommandRegistry
from pathlib import Path

# Initialize registry with command directories
registry = CommandRegistry([
    Path("src/lyra_cli/commands")
])

# Load all commands
registry.load_commands()
```

### Executing Commands

```python
from lyra_cli.core.command_dispatcher import CommandDispatcher

# Create dispatcher with registry
dispatcher = CommandDispatcher(registry)

# Execute command
result = dispatcher.dispatch("plan", {"feature": "auth"})

if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
```

### Searching Commands

```python
# Get specific command
cmd = registry.get_command("plan")

# Search by keyword
results = registry.search_commands("test")

# List all commands
all_commands = registry.list_commands()
```

## Core Commands

### Planning & Design

#### /plan
- **Description**: Create implementation plan
- **Agent**: planner
- **Usage**: `/plan [feature_description]`

### Development Workflow

#### /tdd
- **Description**: Test-driven development workflow
- **Agent**: tdd-guide
- **Skill**: tdd-workflow
- **Usage**: `/tdd [feature]`

#### /verify
- **Description**: Run verification loop (build → lint → test → type-check)
- **Usage**: `/verify`

#### /build-fix
- **Description**: Fix build errors
- **Agent**: build-error-resolver
- **Usage**: `/build-fix`

### Code Quality

#### /code-review
- **Description**: Comprehensive code review
- **Agent**: code-reviewer
- **Usage**: `/code-review [file_path]`

#### /python-review
- **Description**: Python-specific code review
- **Agent**: python-reviewer
- **Skill**: python-patterns
- **Usage**: `/python-review [file_path]`

#### /security-review
- **Description**: Security vulnerability analysis
- **Agent**: security-reviewer
- **Skill**: security-checklist
- **Usage**: `/security-review [file_path]`

#### /quality-gate
- **Description**: Quality gate check against project standards
- **Usage**: `/quality-gate`

### Testing

#### /e2e
- **Description**: Generate and run E2E tests
- **Usage**: `/e2e [feature]`

#### /test-coverage
- **Description**: Report test coverage
- **Usage**: `/test-coverage`

### Refactoring & Maintenance

#### /refactor-clean
- **Description**: Clean up dead code
- **Agent**: refactor-cleaner
- **Usage**: `/refactor-clean [directory]`

#### /update-docs
- **Description**: Update documentation
- **Agent**: doc-updater
- **Usage**: `/update-docs [file_path]`

### Session Management

#### /save-session
- **Description**: Save current session state
- **Usage**: `/save-session [session_name]`

#### /resume-session
- **Description**: Resume saved session
- **Usage**: `/resume-session [session_name]`

#### /learn
- **Description**: Extract reusable patterns from session
- **Usage**: `/learn`

## Creating Custom Commands

### 1. Create Command File

Create a markdown file in `src/lyra_cli/commands/`:

```markdown
---
name: my-command
description: My custom command
agent: my-agent
skill: my-skill
---

# /my-command Command

Command documentation.

## Usage

\`\`\`
/my-command [args]
\`\`\`

## Examples

\`\`\`
/my-command example
\`\`\`
```

### 2. Register Command

Commands are automatically loaded from the commands directory when the registry is initialized.

### 3. Implement Execution Logic

If the command requires custom execution logic beyond agent delegation, extend the CommandDispatcher class.

## Best Practices

1. **Clear Naming**: Use descriptive, action-oriented command names
2. **Agent Delegation**: Delegate complex logic to specialized agents
3. **Skill References**: Reference skills for reusable patterns
4. **Documentation**: Provide clear usage examples
5. **Error Handling**: Return meaningful error messages

## Testing

Commands are tested at three levels:

1. **Metadata Tests**: Verify command metadata parsing
2. **Registry Tests**: Test command loading and searching
3. **Dispatcher Tests**: Test command execution

Run tests:

```bash
pytest tests/commands/ -v
```

## Integration with Other Systems

### Agents
Commands can delegate to agents for complex tasks:
```yaml
agent: planner
```

### Skills
Commands can reference skills for reusable patterns:
```yaml
skill: tdd-workflow
```

### TUI
Commands are integrated into the TUI for interactive use.

## API Reference

### CommandMetadata

```python
@dataclass
class CommandMetadata:
    name: str
    description: str
    agent: Optional[str] = None
    skill: Optional[str] = None
    args: Optional[List[str]] = None
    file_path: Optional[str] = None
```

### CommandRegistry

```python
class CommandRegistry:
    def __init__(self, command_dirs: Optional[List[Path]] = None)
    def load_commands(self) -> Dict[str, CommandMetadata]
    def get_command(self, name: str) -> Optional[CommandMetadata]
    def search_commands(self, query: str) -> List[CommandMetadata]
    def list_commands(self) -> List[CommandMetadata]
```

### CommandDispatcher

```python
class CommandDispatcher:
    def __init__(self, registry: CommandRegistry)
    def dispatch(self, command_name: str, args: Optional[Dict[str, Any]] = None) -> CommandResult
```

### CommandResult

```python
@dataclass
class CommandResult:
    success: bool
    output: str
    error: Optional[str] = None
```

## See Also

- [AGENTS.md](AGENTS.md) - Agent system documentation
- [SKILLS.md](SKILLS.md) - Skills library documentation
- [LYRA_ECC_INTEGRATION_ULTRA_PLAN.md](../LYRA_ECC_INTEGRATION_ULTRA_PLAN.md) - Full integration plan
