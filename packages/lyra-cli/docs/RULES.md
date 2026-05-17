# Rules Framework

The rules framework enforces coding standards, testing requirements, security guidelines, and best practices across the codebase.

## Architecture

### Core Components

- **RuleMetadata**: Dataclass representing rule definitions
- **RuleRegistry**: Loads and manages rules from directories
- **RuleValidator**: Validates code against rules
- **RuleCategory**: Enum defining rule categories
- **RuleSeverity**: Enum defining severity levels

### Rule Categories

- **CodingStandards**: Code style, organization, error handling
- **Testing**: Coverage requirements, TDD workflow, test isolation
- **Security**: OWASP Top 10, secrets management, input validation
- **Performance**: Model selection, context management, parallel execution
- **GitWorkflow**: Commit format, PR workflow
- **Documentation**: Documentation standards

### Rule Severity Levels

- **Critical**: Must fix before merge
- **High**: Should fix before merge
- **Medium**: Consider fixing
- **Low**: Optional improvement

### Rule Definition Format

Rules are defined in markdown files with YAML frontmatter:

```markdown
---
name: rule-name
description: Brief description
category: CodingStandards
severity: high
enabled: true
---

# Rule Name

Detailed documentation here.
```

## Usage

### Loading Rules

```python
from lyra_cli.core.rule_registry import RuleRegistry
from pathlib import Path

# Initialize registry with rule directories
registry = RuleRegistry([
    Path("src/lyra_cli/rules")
])

# Load all rules
registry.load_rules()
```

### Validating Code

```python
from lyra_cli.core.rule_validator import RuleValidator
from lyra_cli.core.rule_metadata import RuleCategory

# Create validator with registry
validator = RuleValidator(registry)

# Validate against all rules
result = validator.validate()

if not result.passed:
    for violation in result.violations:
        print(f"{violation.severity.value}: {violation.message}")

# Validate specific category
security_result = validator.validate_category(RuleCategory.SECURITY)
```

### Managing Rules

```python
# Get specific rule
rule = registry.get_rule("immutability-required")

# Get rules by category
coding_rules = registry.get_rules_by_category(RuleCategory.CODING_STANDARDS)

# Search rules
results = registry.search_rules("test")

# List all rules
all_rules = registry.list_rules()
```

## Core Rules

### Coding Standards (3 rules)

#### immutability-required
- **Severity**: High
- **Description**: Always create new objects, never mutate existing ones
- **Rationale**: Prevents hidden side effects, enables safe concurrency

#### comprehensive-error-handling
- **Severity**: High
- **Description**: Handle errors explicitly at every level
- **Rationale**: Prevents silent failures, makes debugging easier

#### small-files-preferred
- **Severity**: Medium
- **Description**: Many small files (200-400 lines) over few large files (800 max)
- **Rationale**: Easier to understand, test, and maintain

### Testing Requirements (3 rules)

#### minimum-test-coverage
- **Severity**: Critical
- **Description**: Minimum 80% test coverage required
- **Rationale**: High coverage catches bugs early

#### tdd-workflow-required
- **Severity**: High
- **Description**: Follow TDD workflow (RED-GREEN-REFACTOR)
- **Rationale**: Ensures testable code, catches edge cases

#### test-isolation-required
- **Severity**: High
- **Description**: Tests must be isolated and independent
- **Rationale**: Reliable tests, easier debugging

### Security Guidelines (3 rules)

#### owasp-top-10-compliance
- **Severity**: Critical
- **Description**: Follow OWASP Top 10 security guidelines
- **Rationale**: Prevents most critical security risks

#### no-hardcoded-secrets
- **Severity**: Critical
- **Description**: Never hardcode secrets in source code
- **Rationale**: Prevents credential exposure

#### input-validation-required
- **Severity**: Critical
- **Description**: Validate all input at system boundaries
- **Rationale**: Prevents injection attacks

### Performance Optimization (3 rules)

#### model-selection-strategy
- **Severity**: Medium
- **Description**: Use appropriate model for task complexity
- **Rationale**: Optimizes cost and performance

#### context-window-management
- **Severity**: Medium
- **Description**: Avoid last 20% of context window for complex operations
- **Rationale**: Maintains model performance

#### parallel-execution-preferred
- **Severity**: Medium
- **Description**: Execute independent tasks in parallel
- **Rationale**: Reduces total execution time

### Git Workflow (2 rules)

#### conventional-commits-required
- **Severity**: High
- **Description**: Use conventional commit format
- **Rationale**: Enables automated changelog generation

#### pr-workflow-required
- **Severity**: High
- **Description**: All changes through PR workflow
- **Rationale**: Enables code review and quality control

### Documentation (1 rule)

#### documentation-standards
- **Severity**: Medium
- **Description**: Maintain clear and up-to-date documentation
- **Rationale**: Reduces onboarding time, prevents misuse

## Best Practices

1. **Enable Critical Rules**: Always enable critical severity rules
2. **Regular Validation**: Run validation before commits
3. **Category-Specific**: Validate specific categories during development
4. **Fix High Severity**: Address high severity violations promptly
5. **Document Exceptions**: Document why rules are disabled if needed

## Testing

Rules are tested at three levels:

1. **Metadata Tests**: Verify rule metadata parsing
2. **Registry Tests**: Test rule loading and searching
3. **Validator Tests**: Test rule validation

Run tests:

```bash
pytest tests/rules/ -v
```

## API Reference

### RuleCategory

```python
class RuleCategory(Enum):
    CODING_STANDARDS = "coding-standards"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    GIT_WORKFLOW = "git-workflow"
    DOCUMENTATION = "documentation"
```

### RuleSeverity

```python
class RuleSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

### RuleMetadata

```python
@dataclass
class RuleMetadata:
    name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    enabled: bool = True
    file_path: Optional[str] = None
```

### RuleRegistry

```python
class RuleRegistry:
    def __init__(self, rule_dirs: Optional[List[Path]] = None)
    def load_rules(self) -> Dict[str, RuleMetadata]
    def get_rule(self, name: str) -> Optional[RuleMetadata]
    def get_rules_by_category(self, category: RuleCategory) -> List[RuleMetadata]
    def search_rules(self, query: str) -> List[RuleMetadata]
    def list_rules(self) -> List[RuleMetadata]
```

### RuleValidator

```python
class RuleValidator:
    def __init__(self, registry: RuleRegistry)
    def validate(self, context: Optional[Dict[str, Any]] = None) -> ValidationResult
    def validate_category(self, category: RuleCategory, context: Optional[Dict[str, Any]] = None) -> ValidationResult
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    passed: bool
    violations: List[RuleViolation]
    rules_checked: int
```

### RuleViolation

```python
@dataclass
class RuleViolation:
    rule_name: str
    severity: RuleSeverity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
```

## Integration with Other Systems

### Code Review
Rules are checked during code review process.

### CI/CD
Rules can be enforced in CI/CD pipelines.

### Pre-commit Hooks
Rules can run as pre-commit hooks.

## See Also

- [AGENTS.md](AGENTS.md) - Agent system documentation
- [SKILLS.md](SKILLS.md) - Skills library documentation
- [COMMANDS.md](COMMANDS.md) - Command system documentation
- [HOOKS.md](HOOKS.md) - Hooks system documentation
- [LYRA_ECC_INTEGRATION_ULTRA_PLAN.md](../LYRA_ECC_INTEGRATION_ULTRA_PLAN.md) - Full integration plan
