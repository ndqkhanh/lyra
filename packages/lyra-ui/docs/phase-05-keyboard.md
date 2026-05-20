# Phase 5 — Advanced Keyboard Navigation

Module: `keyboard.py`

Vim-style keyboard navigation and command palette.

```python
from lyra_ui import (
    VimNavigator,
    NavigationMode,
    KeyBinding,
    CommandPalette,
    QuickActions,
)

# Vim-style navigation
nav = VimNavigator()
binding = nav.get_binding("h")  # Move left
print(f"{binding.key}: {binding.description}")

# Custom binding
custom = KeyBinding("ctrl+s", "save", "Save file")
nav.add_binding(custom)

# Mode switching
nav.set_mode(NavigationMode.INSERT)

# Command palette
palette = CommandPalette()

def save_file():
    return "File saved"

palette.register_command("save", save_file, category="file")
results = palette.search_commands("save")
result = palette.execute_command("save")

# Quick actions
actions = QuickActions()
actions.get_action("@")  # file_picker
actions.get_action("#")  # skill_picker
actions.get_action("/")  # command_picker
```

**Features**

- Vim-style navigation (`hjkl`, `gg`/`G`, `Ctrl+D`/`Ctrl+U`, `w`/`b`)
- Navigation modes (normal, insert, visual, command)
- Custom keybindings
- Command palette with fuzzy search
- Command history
- Command categories
- Quick actions (`@`, `#`, `/`)

See also the [Keyboard Shortcuts Cheat Sheet](../README.md#keyboard-shortcuts-cheat-sheet).

## Components

- `VimNavigator` — Vim-style keyboard navigation
- `NavigationMode` — Navigation mode enum
- `KeyBinding` — Key binding definition
- `CommandPalette` — Command palette with fuzzy search
- `QuickActions` — Quick action shortcuts
