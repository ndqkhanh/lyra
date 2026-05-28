# Lyra Plugin Examples

This directory contains example plugins demonstrating Lyra's plugin system.

## Plugin Structure

A Lyra plugin is a Python module that exports a `manifest` dictionary:

```python
manifest = {
    "name": "plugin-name",
    "version": "1.0.0",
    "description": "Plugin description",
    "author": "Author Name",
    "tools": [
        {
            "name": "tool_name",
            "function": tool_function,
            "description": "Tool description",
            "category": "tool_category",
        }
    ],
}
```

## Examples

### 1. greeting_plugin.py

Simple plugin with a single tool demonstrating basic plugin structure.

**Features:**
- Single tool function
- Simple parameters
- Basic return structure

**Usage:**
```python
from lyra_cli.plugins.examples import greeting_plugin

result = greeting_plugin.greet("Alice", formal=True)
# {"greeting": "Good day, Alice.", "name": "Alice", "formal": True}
```

### 2. metrics_plugin.py

Complex plugin with multiple tools and stateful operations.

**Features:**
- Multiple tools
- Stateful analyzer with caching
- AST-based code analysis
- Cache management

**Usage:**
```python
from lyra_cli.plugins.examples import metrics_plugin

# Analyze a file
result = metrics_plugin.analyzer.analyze_file("src/main.py")
# {"lines": 150, "functions": 12, "classes": 3, "imports": 8, "analyzed": True}

# Clear cache
metrics_plugin.analyzer.clear_cache()
# {"cleared": 5, "cache_size": 0}
```

## Creating Your Own Plugin

1. Create a new Python file in the plugins directory
2. Define your tool functions
3. Create a manifest dictionary
4. Register the plugin with Lyra

### Minimal Example

```python
"""My custom plugin."""
from typing import Any

def my_tool(param: str) -> dict[str, Any]:
    """My tool description."""
    return {"result": f"Processed: {param}"}

manifest = {
    "name": "my-plugin",
    "version": "1.0.0",
    "description": "My custom plugin",
    "author": "Your Name",
    "tools": [
        {
            "name": "my_tool",
            "function": my_tool,
            "description": "Process a parameter",
            "category": "automation",
        }
    ],
}
```

## Plugin Categories

Available tool categories:
- `filesystem` - File operations
- `code` - Code analysis and manipulation
- `search` - Search operations
- `shell` - Shell commands
- `git` - Git operations
- `web_browser` - Web browsing
- `database` - Database operations
- `document` - Document processing
- `media` - Media operations
- `network` - Network operations
- `security` - Security tools
- `agent` - Agent operations
- `memory` - Memory operations
- `skill` - Skill management
- `observability` - Monitoring and logging
- `automation` - Automation tools
- `communication` - Communication tools
- `mcp` - MCP server tools
- `voice` - Voice operations
- `ui` - UI operations

## Best Practices

1. **Error Handling**: Always return error information in the result dict
2. **Type Hints**: Use type hints for all parameters and return values
3. **Documentation**: Provide clear docstrings for all tools
4. **Validation**: Validate inputs before processing
5. **Immutability**: Prefer immutable operations when possible
6. **Testing**: Write tests for your plugin tools

## Loading Plugins

Plugins are automatically discovered from:
- `~/.lyra/plugins/` (user plugins)
- `.lyra/plugins/` (project plugins)
- `lyra-cli/plugins/` (built-in plugins)

To manually load a plugin:

```python
from lyra_core.plugins import load_plugin

plugin = load_plugin("path/to/plugin.py")
```

## Plugin Lifecycle

1. **Discovery**: Plugins are discovered at startup
2. **Validation**: Manifest is validated
3. **Registration**: Tools are registered with the tool registry
4. **Execution**: Tools are available for use
5. **Hot Reload**: Plugins can be reloaded without restart (if enabled)

## See Also

- [Plugin System Documentation](../../docs/plugins.md)
- [Tool Registry Documentation](../../docs/tools.md)
- [Plugin API Reference](../../docs/api/plugins.md)
