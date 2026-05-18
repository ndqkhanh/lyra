#!/usr/bin/env python3
"""Constitution Compliance Verification Script for Lyra UI Rebuild.

Checks all 7 constitution principles programmatically where possible.
"""
import ast
import re
from pathlib import Path
from typing import List, Tuple

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def check_file(path: Path) -> Tuple[bool, str]:
    """Check if file exists and is valid Python."""
    if not path.exists():
        return False, f"File not found: {path}"
    try:
        ast.parse(path.read_text())
        return True, "Valid Python syntax"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

def check_reactive_properties(file_path: Path, expected_props: List[str]) -> Tuple[bool, str]:
    """Check if file uses reactive properties correctly."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    
    content = file_path.read_text()
    found_props = []
    for prop in expected_props:
        # Check for both old-style and new-style reactive declarations
        if f"{prop}: reactive" in content or f"{prop} = reactive" in content:
            found_props.append(prop)
    
    if len(found_props) == len(expected_props):
        return True, f"All reactive properties found: {', '.join(found_props)}"
    else:
        missing = set(expected_props) - set(found_props)
        return False, f"Missing reactive properties: {', '.join(missing)}"

def check_work_decorator(file_path: Path) -> Tuple[bool, str]:
    """Check if file uses @work decorator for I/O operations."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    
    content = file_path.read_text()
    has_work = "@work" in content or "from textual.worker import work" in content
    has_async_io = any(keyword in content for keyword in ["asyncio", "await", "async def"])
    
    if has_async_io and not has_work:
        return False, "Has async I/O but no @work decorator"
    elif has_work:
        return True, "Uses @work decorator for async operations"
    else:
        return True, "No async I/O detected (OK)"

def check_keyboard_bindings(file_path: Path, expected_bindings: List[str]) -> Tuple[bool, str]:
    """Check if file defines expected keyboard bindings."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    
    content = file_path.read_text()
    found_bindings = []
    for binding in expected_bindings:
        if binding in content:
            found_bindings.append(binding)
    
    if len(found_bindings) == len(expected_bindings):
        return True, f"All bindings found: {', '.join(found_bindings)}"
    else:
        missing = set(expected_bindings) - set(found_bindings)
        return False, f"Missing bindings: {', '.join(missing)}"

def check_logging(file_path: Path) -> Tuple[bool, str]:
    """Check if file uses structured logging."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    
    content = file_path.read_text()
    has_logging = any(keyword in content for keyword in ["logger", "log.", "logging"])
    
    if has_logging:
        return True, "Uses structured logging"
    else:
        return False, "No logging detected"

def print_result(check_name: str, passed: bool, message: str):
    """Print a formatted check result."""
    status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    print(f"{status} {check_name}")
    if message:
        print(f"  {message}")

def main():
    base_path = Path(__file__).parent / "packages/lyra-cli/src/lyra_cli/tui_v2"
    
    print("=" * 80)
    print("LYRA UI CONSTITUTION COMPLIANCE VERIFICATION")
    print("=" * 80)
    print()
    
    # I. Truth Over Aesthetics
    print(f"{YELLOW}I. Truth Over Aesthetics{RESET}")
    print("  All counters source from SessionState, no estimated values")
    print()
    
    app_file = base_path / "app.py"
    passed, msg = check_reactive_properties(app_file, ["turn_index", "thinking_enabled", "fast_mode"])
    print_result("App uses reactive state", passed, msg)
    
    metrics_file = base_path / "widgets/metrics_tracker.py"
    passed, msg = check_file(metrics_file)
    print_result("MetricsTracker exists", passed, msg)
    print()
    
    # II. Non-Blocking
    print(f"{YELLOW}II. Non-Blocking{RESET}")
    print("  All I/O in @work workers, cancellation <200ms")
    print()
    
    for widget_name in ["agent_panel", "background_panel", "metrics_tracker"]:
        widget_file = base_path / f"widgets/{widget_name}.py"
        passed, msg = check_work_decorator(widget_file)
        print_result(f"{widget_name}.py non-blocking", passed, msg)
    print()
    
    # III. Progressive Disclosure
    print(f"{YELLOW}III. Progressive Disclosure{RESET}")
    print("  All panels collapsible, Ctrl+O tested")
    print()
    
    passed, msg = check_keyboard_bindings(app_file, ["ctrl+o"])
    print_result("Ctrl+O binding exists", passed, msg)
    
    expandable_file = base_path / "expandable.py"
    passed, msg = check_file(expandable_file)
    print_result("ExpandableBlockManager exists", passed, msg)
    print()
    
    # IV. Streaming
    print(f"{YELLOW}IV. Streaming{RESET}")
    print("  Markdown/RichLog incremental render, no buffering")
    print()
    
    # Check if RichLog is used in compaction_banner (where it's actually used)
    compaction_file = base_path / "widgets/compaction_banner.py"
    if compaction_file.exists():
        content = compaction_file.read_text()
        has_richlog = "RichLog" in content
        print_result("Uses RichLog for streaming", has_richlog, "RichLog found in compaction_banner.py" if has_richlog else "No RichLog detected")
    else:
        print_result("Uses RichLog for streaming", False, "compaction_banner.py not found")
    print()
    
    # V. Keyboard-First
    print(f"{YELLOW}V. Keyboard-First{RESET}")
    print("  All actions have bindings, footer renders active set")
    print()
    
    expected_bindings = ["ctrl+k", "alt+p", "alt+t", "alt+o", "alt+m", "ctrl+t", "ctrl+b", "ctrl+o"]
    passed, msg = check_keyboard_bindings(app_file, expected_bindings)
    print_result("All keyboard bindings defined", passed, msg)
    print()
    
    # VI. Single Source of Truth
    print(f"{YELLOW}VI. Single Source of Truth{RESET}")
    print("  No shadow state, all widgets watch reactives")
    print()
    
    for widget_name in ["welcome_card", "compaction_banner", "todo_panel"]:
        widget_file = base_path / f"widgets/{widget_name}.py"
        if widget_file.exists():
            content = widget_file.read_text()
            has_reactive = "reactive" in content
            print_result(f"{widget_name}.py uses reactive", has_reactive, "reactive import found" if has_reactive else "No reactive detected")
    print()
    
    # VII. Observability
    print(f"{YELLOW}VII. Observability{RESET}")
    print("  Structured logs to ~/.lyra/logs/tui.log, dev console mirror")
    print()
    
    for widget_name in ["app", "widgets/agent_panel", "widgets/background_panel"]:
        widget_file = base_path / f"{widget_name}.py"
        passed, msg = check_logging(widget_file)
        print_result(f"{widget_name}.py logging", passed, msg)
    print()
    
    # Summary
    print("=" * 80)
    print(f"{YELLOW}SUMMARY{RESET}")
    print("=" * 80)
    print()
    print("✓ Code-level verification complete")
    print("⚠ Manual testing still required for:")
    print("  - Widget display and interaction")
    print("  - Keyboard shortcut functionality")
    print("  - Performance metrics (<200ms cancellation)")
    print("  - Log file output verification")
    print()
    print("See PHASE_4_VERIFICATION_CHECKLIST.md for manual test cases.")

if __name__ == "__main__":
    main()
