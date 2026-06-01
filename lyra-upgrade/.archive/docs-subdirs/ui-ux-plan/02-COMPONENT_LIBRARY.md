# 02 - Component Library

**Reusable UI components for Lyra**

---

## 🧩 Core Components

### 1. Message Bubbles

**User Message**
```
┌─ 👤 You ──────────────────────────────────────────────────┐
│ Fix the authentication bug in src/auth.py                 │
└────────────────────────────────────────────────────────────┘
```

**Assistant Message**
```
┌─ 🤖 Assistant ─────────────────────────────────────────────┐
│ I'll analyze and fix the authentication bug.              │
│                                                            │
│ 🔍 Reading src/auth.py...                                 │
└────────────────────────────────────────────────────────────┘
```

**System Message**
```
┌─ ⚙️ System ────────────────────────────────────────────────┐
│ Session started at 2024-05-21 10:30:45                    │
└────────────────────────────────────────────────────────────┘
```

**Implementation**
```python
from rich.panel import Panel
from rich.console import Console

def user_message(text: str) -> Panel:
    return Panel(
        text,
        title="👤 You",
        title_align="left",
        border_style="blue",
        padding=(0, 1)
    )

def assistant_message(text: str) -> Panel:
    return Panel(
        text,
        title="🤖 Assistant",
        title_align="left",
        border_style="green",
        padding=(0, 1)
    )
```

---

### 2. Tool Call Display

**Compact Format (Default)**
```
  ⚡ read_file(path="src/auth.py")
  ✅ Read 245 lines (3.2 KB)
```

**Expanded Format (--verbose)**
```
╭─ 🔧 Tool Call ─────────────────────────────────────────────╮
│ read_file                                                  │
│                                                            │
│ Arguments:                                                 │
│   path: "src/auth.py"                                      │
│   encoding: "utf-8"                                        │
│                                                            │
│ Result:                                                    │
│   ✅ Success                                               │
│   Lines: 245                                               │
│   Size: 3.2 KB                                             │
│   Duration: 12ms                                           │
╰────────────────────────────────────────────────────────────╯
```

**Implementation**
```python
def tool_call_compact(name: str, args: dict, result: str) -> str:
    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
    return f"  ⚡ {name}({args_str})\n  ✅ {result}"

def tool_call_expanded(name: str, args: dict, result: dict) -> Panel:
    content = f"[bold]{name}[/bold]\n\n"
    content += "Arguments:\n"
    for k, v in args.items():
        content += f"  {k}: {repr(v)}\n"
    content += "\nResult:\n"
    content += f"  ✅ {result['status']}\n"
    for k, v in result.items():
        if k != 'status':
            content += f"  {k}: {v}\n"
    
    return Panel(content, title="🔧 Tool Call", border_style="cyan")
```

---

### 3. Status Indicators

**Spinner (Loading)**
```python
from rich.spinner import Spinner

spinner = Spinner("dots", text="Processing...", style="yellow")
```

**Progress Bar**
```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    transient=True
) as progress:
    task = progress.add_task("Analyzing files...", total=None)
```

**Status Badge**
```
✅ Success    ⚠️ Warning    ❌ Error    ℹ️ Info    ⏳ Pending    🔄 Running
```

**Implementation**
```python
STATUS_ICONS = {
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
    "info": "ℹ️",
    "pending": "⏳",
    "running": "🔄"
}

def status_badge(status: str, text: str) -> str:
    icon = STATUS_ICONS.get(status, "•")
    color = {
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "blue",
        "pending": "yellow",
        "running": "cyan"
    }.get(status, "white")
    
    return f"[{color}]{icon} {text}[/{color}]"
```

---

### 4. Tables

**Simple Table**
```
┌────────────┬─────────┬──────────┐
│ File       │ Lines   │ Status   │
├────────────┼─────────┼──────────┤
│ auth.py    │ 245     │ ✅ Pass  │
│ db.py      │ 189     │ ✅ Pass  │
│ api.py     │ 456     │ ⚠️ Warn  │
└────────────┴─────────┴──────────┘
```

**Implementation**
```python
from rich.table import Table

def create_table(title: str, columns: list, rows: list) -> Table:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    
    for col in columns:
        table.add_column(col)
    
    for row in rows:
        table.add_row(*row)
    
    return table
```

---

### 5. Code Blocks

**Inline Code**
```
Run `pytest tests/` to verify the changes.
```

**Code Block**
```python
╭─ src/auth.py ──────────────────────────────────────────────╮
│  42 │ def validate_token(token: str) -> bool:               │
│  43 │     if not token:                                     │
│  44 │         return False                                  │
│  45 │     return verify_jwt(token)                          │
╰────────────────────────────────────────────────────────────╯
```

**Diff View**
```diff
╭─ Changes in src/auth.py ───────────────────────────────────╮
│  42 │ def authenticate(request):                            │
│  43 │     token = request.headers.get('Authorization')      │
│ +44 │     if not validate_token(token):                     │
│ +45 │         return Response(status=401)                   │
│  46 │     return process_request(request)                   │
╰────────────────────────────────────────────────────────────╯
```

**Implementation**
```python
from rich.syntax import Syntax

def code_block(code: str, language: str, title: str = None) -> Panel:
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    return Panel(syntax, title=title, border_style="dim")
```

---

### 6. Lists

**Bullet List**
```
• First item
• Second item
  • Nested item
  • Another nested
• Third item
```

**Numbered List**
```
1. First step
2. Second step
3. Third step
```

**Checklist**
```
✅ Completed task
✅ Another done
⏳ In progress
□ Not started
```

**Implementation**
```python
def bullet_list(items: list, indent: int = 0) -> str:
    lines = []
    prefix = "  " * indent
    for item in items:
        if isinstance(item, list):
            lines.append(bullet_list(item, indent + 1))
        else:
            lines.append(f"{prefix}• {item}")
    return "\n".join(lines)
```

---

### 7. Alerts & Notifications

**Info Alert**
```
╭─ ℹ️ Info ──────────────────────────────────────────────────╮
│ This is an informational message.                         │
╰────────────────────────────────────────────────────────────╯
```

**Success Alert**
```
╭─ ✅ Success ───────────────────────────────────────────────╮
│ Operation completed successfully!                          │
╰────────────────────────────────────────────────────────────╯
```

**Warning Alert**
```
╭─ ⚠️ Warning ───────────────────────────────────────────────╮
│ This action may have unintended consequences.             │
╰────────────────────────────────────────────────────────────╯
```

**Error Alert**
```
╭─ ❌ Error ─────────────────────────────────────────────────╮
│ An error occurred: File not found                         │
╰────────────────────────────────────────────────────────────╯
```

**Implementation**
```python
def alert(message: str, level: str = "info") -> Panel:
    styles = {
        "info": ("ℹ️ Info", "blue"),
        "success": ("✅ Success", "green"),
        "warning": ("⚠️ Warning", "yellow"),
        "error": ("❌ Error", "red")
    }
    
    title, color = styles.get(level, styles["info"])
    return Panel(message, title=title, border_style=color)
```

---

### 8. Headers & Footers

**App Header**
```
╭─────────────────────────────────────────────────────────────╮
│ 🌟 Lyra v3.14.0                              💬 Chat Mode │
╰─────────────────────────────────────────────────────────────╯
```

**Section Header**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 Analysis Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Footer**
```
───────────────────────────────────────────────────────────────
  💡 Tip: Use /help to see all available commands
```

---

### 9. Input Components

**Text Input**
```
┌─ Enter your message ───────────────────────────────────────┐
│ > _                                                         │
└─────────────────────────────────────────────────────────────┘
```

**Select Menu**
```
┌─ Choose an option ─────────────────────────────────────────┐
│ ▸ Option 1                                                 │
│   Option 2                                                 │
│   Option 3                                                 │
└─────────────────────────────────────────────────────────────┘
```

**Confirmation**
```
⚠️ Are you sure you want to delete this file? (y/N)
```

---

### 10. Metrics & Stats

**Key-Value Pairs**
```
╭─ Session Stats ────────────────────────────────────────────╮
│ Duration:     45m 23s                                      │
│ Messages:     42                                           │
│ Tool Calls:   18                                           │
│ Tokens:       12,456                                       │
│ Cost:         $0.23                                        │
╰────────────────────────────────────────────────────────────╯
```

**Compact Stats**
```
⏱️ 45m 23s  |  💬 42 msgs  |  🔧 18 tools  |  💰 $0.23
```

---

## 🎨 Component Composition

### Chat Message with Tool Calls
```
┌─ 🤖 Assistant ─────────────────────────────────────────────┐
│ I'll fix the bug by updating the validation logic.        │
└────────────────────────────────────────────────────────────┘

  ⚡ read_file(path="src/auth.py")
  ✅ Read 245 lines (3.2 KB)

  ⚡ edit_file(path="src/auth.py", ...)
  ✅ Applied 1 change

┌─ 🤖 Assistant ─────────────────────────────────────────────┐
│ ✅ Fixed! Added token validation on line 42.              │
│                                                            │
│ 📝 Changes:                                               │
│   • Added validate_token() check                          │
│   • Returns 401 if token invalid                          │
└────────────────────────────────────────────────────────────┘
```

---

**Next**: [03-LAYOUTS.md](03-LAYOUTS.md)
