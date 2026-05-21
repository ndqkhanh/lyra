# Lyra ECC Integration Package

ECC (Enhanced Claude Code) compatibility layer for Lyra.

## Features

- **Skills Import**: Import 232+ ECC production skills
- **Agent Fleet**: Merge 60 ECC agents with Lyra's RSI agents
- **Hooks System**: Event-driven automation (PreToolUse, PostToolUse, etc.)
- **Rules Engine**: 34 language-specific coding rules
- **Cross-Platform**: Compatible with Claude Code, Cursor, Codex, etc.

## Installation

```bash
cd packages/lyra-ecc
pip install -e .
```

## Quick Start

```python
from lyra_ecc import ECCCompatibilityLayer, ECCImporter

# Initialize compatibility layer
compat = ECCCompatibilityLayer()
compat.initialize()

# Get compatibility report
report = compat.get_compatibility_report()
print(report)

# Import ECC components
importer = ECCImporter()
skills_result = importer.import_skills()
agents_result = importer.import_agents()

print(f"Imported {skills_result.items_imported} skills")
print(f"Imported {agents_result.items_imported} agents")
```

## Components

### Compatibility Layer

Provides compatibility between ECC and Lyra architectures.

```python
from lyra_ecc.compatibility import ECCCompatibilityLayer

compat = ECCCompatibilityLayer()
compat.initialize()
```

### Importer

Imports ECC skills, agents, and rules.

```python
from lyra_ecc.importer import ECCImporter

importer = ECCImporter()
result = importer.import_skills()
```

### Hooks Engine

Event-driven automation system.

```python
from lyra_ecc.hooks import ECCHooksEngine, HookType, HookContext

engine = ECCHooksEngine()

# Register custom hook
def my_hook(context: HookContext):
    return HookResult(success=True)

engine.register_hook(HookType.POST_TOOL_USE, my_hook)
```

### Rules Engine

Code quality and style rules.

```python
from lyra_ecc.rules import RulesEngine

engine = RulesEngine()
engine.activate_for_project(Path("my_project"))

violations = engine.check(code, file_path)
```

## Testing

```bash
pytest packages/lyra-ecc/tests/ -v
```

## Documentation

See [LYRA_ECC_INTEGRATION_ULTRA_PLAN.md](../../LYRA_ECC_INTEGRATION_ULTRA_PLAN.md) for the complete integration plan.

## License

MIT License - see [LICENSE](../../LICENSE) for details.
