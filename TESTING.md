# Lyra Test Coverage Report

## Current Coverage

Run tests with coverage:

```bash
# Test all packages
pytest packages/lyra-cli/tests/ --cov=packages/lyra-cli/src --cov-report=term-missing
pytest packages/lyra-core/tests/ --cov=packages/lyra-core/src --cov-report=term-missing
pytest packages/lyra-skills/tests/ --cov=packages/lyra-skills/src --cov-report=term-missing
```

## Coverage Goals

- **Target:** 80%+ coverage across all packages
- **Critical paths:** 90%+ coverage
- **New code:** 100% coverage required

## Coverage by Package

### lyra-cli
- **Current:** TBD (run tests to measure)
- **Goal:** 80%+
- **Critical modules:**
  - `tui_v2/` - TUI components
  - `interactive/` - Interactive features
  - `commands/` - CLI commands

### lyra-core
- **Current:** TBD (run tests to measure)
- **Goal:** 80%+
- **Critical modules:**
  - `providers/` - Provider integrations
  - `tools/` - Tool implementations
  - `memory/` - Memory systems

### lyra-skills
- **Current:** TBD (run tests to measure)
- **Goal:** 80%+
- **Critical modules:**
  - `mcp_integration.py` - MCP server management
  - `production_installer.py` - Skill installation

## Running Coverage Locally

```bash
# Install coverage tools
pip install pytest-cov

# Run with HTML report
pytest tests/ --cov=src --cov-report=html

# Open report
open htmlcov/index.html
```

## CI/CD Integration

Coverage is automatically measured in CI/CD pipeline:
- Reports uploaded to Codecov
- PR comments show coverage changes
- Failing coverage blocks merge

## Improving Coverage

1. **Identify gaps:**
   ```bash
   pytest --cov=src --cov-report=term-missing
   ```

2. **Add tests for uncovered lines**

3. **Focus on critical paths first**

4. **Use parametrized tests for multiple scenarios**

## Coverage Exclusions

Exclude from coverage:
- `__init__.py` files (imports only)
- Type stubs
- Debug code
- Deprecated code marked for removal
