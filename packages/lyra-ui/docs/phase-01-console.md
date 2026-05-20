# Phase 1 — Rich Console & Progress

Modules: `console.py`, `progress.py`

## Rich Console (`console.py`)

Singleton console with theme support.

```python
from lyra_ui import console

console.print_success("Operation successful!")
console.print_error("Error occurred")
console.print_warning("Warning message")
console.print_info("Information")

console.print("[bold blue]Custom styled text[/bold blue]")
```

**Features**

- Singleton pattern for consistent styling
- Built-in themes (success, error, warning, info)
- Agent status colors
- Context indicator colors
- Custom theme support

## Progress Indicators (`progress.py`)

Progress bars and spinners.

```python
from lyra_ui import ProgressManager, Spinner

manager = ProgressManager()
manager.add_task("download", "Downloading...", total=100)
manager.update_task("download", advance=10)
manager.complete_task("download")
manager.stop()

with Spinner("Processing...") as spinner:
    spinner.update("Still processing...")
```

**Features**

- Multiple concurrent progress bars
- Spinners for indeterminate tasks
- Time tracking (elapsed, remaining)
- Task management (add, update, complete, remove)
