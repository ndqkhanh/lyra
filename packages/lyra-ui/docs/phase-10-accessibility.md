# Phase 10 — Accessibility (WCAG 2.1 AA)

Module: `accessibility.py`

ARIA attributes, screen reader support, keyboard shortcuts, focus management,
and accessibility auditing.

## ARIA Attributes

```python
from lyra_ui import AriaAttributes, AriaRole, AriaLive

attrs = AriaAttributes(
    role=AriaRole.BUTTON,
    label="Save document",
    pressed=False,
    live=AriaLive.POLITE,
)
html_attrs = attrs.to_dict()
# {"role": "button", "aria-label": "Save document",
#  "aria-pressed": "false", "aria-live": "polite"}
```

**Roles** (`AriaRole`): `ALERT`, `BUTTON`, `CHECKBOX`, `DIALOG`, `LINK`,
`LISTBOX`, `MENU`, `MENUITEM`, `PROGRESSBAR`, `RADIO`, `REGION`, `STATUS`,
`TAB`, `TABPANEL`, `TEXTBOX`, `TREE`.

**Live politeness** (`AriaLive`): `OFF`, `POLITE`, `ASSERTIVE`.

## Screen Reader

```python
from lyra_ui import ScreenReader

reader = ScreenReader()
reader.announce("File saved successfully")
reader.announce("Error: file not found", assertive=True)

announcements = reader.get_announcements()
reader.clear()
```

- Polite & assertive announcements
- Bounded announcement queue (rate limited)

## Keyboard Shortcuts

```python
from lyra_ui import KeyboardShortcut, KeyboardShortcutManager

manager = KeyboardShortcutManager()
manager.register("save", KeyboardShortcut(key="s", ctrl=True, description="Save"))
manager.register("copy", KeyboardShortcut(key="c", ctrl=True, description="Copy"))

action = manager.get_action("s", ctrl=True, alt=False, shift=False, meta=False)
# -> "save"

help_text = manager.get_help()
# [("Ctrl+S", "Save"), ("Ctrl+C", "Copy")]
```

`KeyboardShortcut.to_string()` produces a human-readable label (e.g.
`"Ctrl+Shift+S"`, `"Cmd+C"`).

## Focus Management

```python
from lyra_ui import FocusManager

focus = FocusManager()
focus.push("dialog-button-1")
focus.push("dialog-button-2")

focus.trap(True)              # Trap focus inside a modal
current = focus.get_current() # "dialog-button-2"

focus.pop()                   # back to "dialog-button-1"
focus.trap(False)
```

- Focus stack (push / pop / get_current)
- Focus trap for modal dialogs

## Accessibility Audit

```python
from lyra_ui import AccessibilityAuditor

auditor = AccessibilityAuditor()
auditor.check_aria_labels([
    {"id": "button1", "aria-label": "Save"},
    {"id": "button2", "aria-labelledby": "label2"},
    {"id": "button3"},  # missing label
])
auditor.check_keyboard_navigation(["button1", "button2"])
auditor.check_color_contrast("#000000", "#FFFFFF")

report = auditor.get_report()
print(f"Score: {report.get_score():.0%}")
print(f"Passed: {report.passed}, Failed: {report.failed}")
for issue in report.issues:
    print(issue)
```

WCAG 2.1 AA checks covered:

- ARIA labels (`aria-label` / `aria-labelledby` presence)
- Keyboard navigation (focusable elements present)
- Color contrast (foreground vs background)

## Components

- `AriaAttributes`, `AriaRole`, `AriaLive`
- `ScreenReader`
- `KeyboardShortcut`, `KeyboardShortcutManager`
- `FocusManager`
- `AccessibilityReport`, `AccessibilityAuditor`
