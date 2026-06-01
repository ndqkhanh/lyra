# ✅ Lyra CLI - Claude Code Style Keybindings

## Keybindings Updated!

### `/` for Commands (Slash Commands)
```bash
> /[Tab]
  /help    Show available commands
  /status  Show session status
  /model   Switch or show current model
  /budget  Set or show budget cap
  /clear   Clear conversation history
  /history Show command history
  /exit    Exit the REPL
  /quit    Exit the REPL
```

### `@` for Files/Folders (Context References)
```bash
> @[Tab]
  @file:      Reference a file
  @folder:    Reference a folder
  @diff       Show git diff
  @staged     Show staged changes
  @clipboard  Paste from clipboard

> @file:[Tab]
  @file:src/main.py
  @file:README.md
  @file:package.json

> @folder:[Tab]
  @folder:src/
  @folder:tests/
  @folder:docs/
```

## Examples

### Slash Commands
```bash
> /he[Tab]           → /help
> /st[Tab]           → /status
> /mo[Tab]           → /model
```

### Context References
```bash
> @fi[Tab]           → @file:
> @file:src/[Tab]    → @file:src/main.py
> @fo[Tab]           → @folder:
> @folder:src/[Tab]  → @folder:src/components/
> @di[Tab]           → @diff
> @st[Tab]           → @staged
```

### Combined Usage
```bash
> Refactor @file:src/main.py using /model claude-opus-4
> Show me @diff and explain the changes
> Review @folder:src/components/ for bugs
```

## Auto-Suggestions (Ghost Text)

As you type, you'll see ghost text suggestions:

```bash
> /he[lp]           ← ghost text
> @file:[src/]      ← ghost text
> @di[ff]           ← ghost text
```

Press **Right Arrow** or **End** to accept the suggestion.

## All Keybindings

| Key | Action |
|-----|--------|
| `/` + Tab | Slash command completion |
| `@` + Tab | Context reference completion |
| **Enter** | Submit input |
| **Ctrl+C** | Cancel input / Interrupt |
| **Ctrl+D** | Exit (when buffer empty) |
| **Ctrl+L** | Clear screen |
| **Ctrl+R** | Reverse history search |
| **Alt+Enter** | Multi-line newline |
| **Ctrl+Enter** | Multi-line newline |
| **Tab** | Autocomplete |
| **Shift+Tab** | Previous completion |
| **Up/Down** | Navigate history |
| **Right/End** | Accept suggestion |

---

**Now Lyra works exactly like Claude Code!** 🎉

- `/` for commands
- `@` for files/folders
- Full autocomplete
- Ghost text suggestions
