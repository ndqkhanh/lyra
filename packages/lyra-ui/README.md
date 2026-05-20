# Lyra UI - Phase 1: Rich/Textual Foundation

## Overview

Phase 1 implements the foundational UI system using Rich and Textual frameworks for beautiful terminal output.

## Features

### 1. Rich Console (`console.py`)

Singleton console with theme support:

```python
from lyra_ui import console

# Print styled messages
console.print_success("Operation successful!")
console.print_error("Error occurred")
console.print_warning("Warning message")
console.print_info("Information")

# Custom printing
console.print("[bold blue]Custom styled text[/bold blue]")
```

**Features**:
- Singleton pattern for consistent styling
- Built-in themes (success, error, warning, info)
- Agent status colors
- Context indicator colors
- Custom theme support

### 2. Progress Indicators (`progress.py`)

Progress bars and spinners:

```python
from lyra_ui import ProgressManager, Spinner

# Progress bar
manager = ProgressManager()
manager.add_task("download", "Downloading...", total=100)
manager.update_task("download", advance=10)
manager.complete_task("download")
manager.stop()

# Spinner
with Spinner("Processing...") as spinner:
    # Do work
    spinner.update("Still processing...")
```

**Features**:
- Multiple progress bars
- Spinners for indeterminate tasks
- Time tracking (elapsed, remaining)
- Task management (add, update, complete, remove)

## Installation

```bash
cd packages/lyra-ui
pip install -e .
```

## Testing

Run tests:
```bash
pytest tests/ -v
```

## Architecture

```
┌─────────────────────────────────────────┐
│    Rich Console                         │
│  (Styled Output)                        │
│                                         │
│  • Singleton instance                  │
│  • Theme management                    │
│  • Status messages                     │
└─────────────────────────────────────────┘
           │
           ↓
┌─────────────────────────────────────────┐
│    Progress Manager                     │
│  (Progress Tracking)                    │
│                                         │
│  • Multiple progress bars              │
│  • Spinners                            │
│  • Time tracking                       │
└─────────────────────────────────────────┘
```

## Usage Examples

### Basic Console Output

```python
from lyra_ui import console

console.print_info("Starting Lyra...")
console.print_success("✓ Initialization complete")
console.print_warning("⚠ High token usage")
console.print_error("✗ Connection failed")
```

### Progress Tracking

```python
from lyra_ui import ProgressManager

manager = ProgressManager()

# Add multiple tasks
manager.add_task("compile", "Compiling...", total=100)
manager.add_task("test", "Running tests...", total=50)

# Update progress
for i in range(100):
    manager.update_task("compile", advance=1)

for i in range(50):
    manager.update_task("test", advance=1)

manager.stop()
```

### Spinner for Async Operations

```python
from lyra_ui import Spinner

with Spinner("Connecting to API...") as spinner:
    # Async operation
    spinner.update("Authenticating...")
    # More work
    spinner.update("Fetching data...")
```

## Version

Current version: **0.1.0**

## Next Phase

Phase 2 will implement:
- Dual-pane layout with Textual
- Conversation pane
- Status panel
- Resizable panes

## References

- [Rich Documentation](https://rich.readthedocs.io/)
- [Textual Documentation](https://textual.textualize.io/)
- Lyra UI/UX Plan: `.omc/plans/LYRA_UI_UX_ULTIMATE_UPGRADE_PLAN.md`
