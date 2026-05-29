"""Tests for accessibility."""

from lyra_ui import (
    AccessibilityAuditor,
    AccessibilityReport,
    AriaAttributes,
    AriaLive,
    AriaRole,
    FocusManager,
    KeyboardShortcut,
    KeyboardShortcutManager,
    ScreenReader,
)

# AriaAttributes Tests


def test_aria_attributes_init():
    """Test ARIA attributes initialization."""
    attrs = AriaAttributes(role=AriaRole.BUTTON, label="Click me")
    assert attrs.role == AriaRole.BUTTON
    assert attrs.label == "Click me"


def test_aria_attributes_to_dict():
    """Test converting to dictionary."""
    attrs = AriaAttributes(
        role=AriaRole.BUTTON,
        label="Click me",
        disabled=True,
        pressed=True,
    )
    result = attrs.to_dict()

    assert result["role"] == "button"
    assert result["aria-label"] == "Click me"
    assert result["aria-disabled"] == "true"
    assert result["aria-pressed"] == "true"


def test_aria_attributes_optional():
    """Test optional attributes."""
    attrs = AriaAttributes()
    result = attrs.to_dict()

    assert "role" not in result
    assert "aria-label" not in result


def test_aria_attributes_expanded():
    """Test expanded attribute."""
    attrs = AriaAttributes(expanded=True)
    result = attrs.to_dict()
    assert result["aria-expanded"] == "true"

    attrs = AriaAttributes(expanded=False)
    result = attrs.to_dict()
    assert result["aria-expanded"] == "false"


def test_aria_attributes_live():
    """Test live region."""
    attrs = AriaAttributes(live=AriaLive.POLITE, atomic=True)
    result = attrs.to_dict()

    assert result["aria-live"] == "polite"
    assert result["aria-atomic"] == "true"


# ScreenReader Tests


def test_screen_reader_init():
    """Test screen reader initialization."""
    reader = ScreenReader()
    assert len(reader.announcements) == 0


def test_screen_reader_announce():
    """Test announcing message."""
    reader = ScreenReader()
    reader.announce("Hello")
    assert len(reader.announcements) == 1
    assert reader.announcements[0] == "Hello"


def test_screen_reader_max_announcements():
    """Test max announcements limit."""
    reader = ScreenReader()
    reader.max_announcements = 3

    for i in range(5):
        reader.announce(f"Message {i}")

    assert len(reader.announcements) == 3
    assert reader.announcements[0] == "Message 2"


def test_screen_reader_get_announcements():
    """Test getting announcements."""
    reader = ScreenReader()
    reader.announce("Test 1")
    reader.announce("Test 2")

    announcements = reader.get_announcements()
    assert len(announcements) == 2
    assert announcements == ["Test 1", "Test 2"]


def test_screen_reader_clear():
    """Test clearing announcements."""
    reader = ScreenReader()
    reader.announce("Test")
    reader.clear()

    assert len(reader.announcements) == 0


# KeyboardShortcut Tests


def test_keyboard_shortcut_init():
    """Test keyboard shortcut initialization."""
    shortcut = KeyboardShortcut(key="s", ctrl=True, description="Save")
    assert shortcut.key == "s"
    assert shortcut.ctrl is True
    assert shortcut.description == "Save"


def test_keyboard_shortcut_matches():
    """Test shortcut matching."""
    shortcut = KeyboardShortcut(key="s", ctrl=True, shift=True)

    assert shortcut.matches("s", ctrl=True, alt=False, shift=True, meta=False)
    assert not shortcut.matches("s", ctrl=True, alt=False, shift=False, meta=False)
    assert not shortcut.matches("a", ctrl=True, alt=False, shift=True, meta=False)


def test_keyboard_shortcut_to_string():
    """Test converting to string."""
    shortcut = KeyboardShortcut(key="s", ctrl=True, shift=True)
    assert shortcut.to_string() == "Ctrl+Shift+S"

    shortcut = KeyboardShortcut(key="c", meta=True)
    assert shortcut.to_string() == "Cmd+C"


# KeyboardShortcutManager Tests


def test_keyboard_shortcut_manager_init():
    """Test shortcut manager initialization."""
    manager = KeyboardShortcutManager()
    assert len(manager.shortcuts) == 0


def test_keyboard_shortcut_manager_register():
    """Test registering shortcut."""
    manager = KeyboardShortcutManager()
    shortcut = KeyboardShortcut(key="s", ctrl=True, description="Save")
    manager.register("save", shortcut)

    assert "save" in manager.shortcuts
    assert manager.shortcuts["save"] == shortcut


def test_keyboard_shortcut_manager_get_action():
    """Test getting action."""
    manager = KeyboardShortcutManager()
    manager.register("save", KeyboardShortcut(key="s", ctrl=True))
    manager.register("copy", KeyboardShortcut(key="c", ctrl=True))

    action = manager.get_action("s", ctrl=True, alt=False, shift=False, meta=False)
    assert action == "save"

    action = manager.get_action("c", ctrl=True, alt=False, shift=False, meta=False)
    assert action == "copy"

    action = manager.get_action("x", ctrl=True, alt=False, shift=False, meta=False)
    assert action is None


def test_keyboard_shortcut_manager_get_shortcuts():
    """Test getting all shortcuts."""
    manager = KeyboardShortcutManager()
    manager.register("save", KeyboardShortcut(key="s", ctrl=True))
    manager.register("copy", KeyboardShortcut(key="c", ctrl=True))

    shortcuts = manager.get_shortcuts()
    assert len(shortcuts) == 2
    assert "save" in shortcuts
    assert "copy" in shortcuts


def test_keyboard_shortcut_manager_get_help():
    """Test getting help."""
    manager = KeyboardShortcutManager()
    manager.register("save", KeyboardShortcut(key="s", ctrl=True, description="Save file"))
    manager.register("copy", KeyboardShortcut(key="c", ctrl=True, description="Copy text"))

    help_text = manager.get_help()
    assert len(help_text) == 2
    assert ("Ctrl+S", "Save file") in help_text
    assert ("Ctrl+C", "Copy text") in help_text


# FocusManager Tests


def test_focus_manager_init():
    """Test focus manager initialization."""
    manager = FocusManager()
    assert len(manager.focus_stack) == 0
    assert manager.trapped is False


def test_focus_manager_push():
    """Test pushing focus."""
    manager = FocusManager()
    manager.push("button1")
    assert len(manager.focus_stack) == 1
    assert manager.focus_stack[0] == "button1"


def test_focus_manager_pop():
    """Test popping focus."""
    manager = FocusManager()
    manager.push("button1")
    manager.push("button2")

    element = manager.pop()
    assert element == "button2"
    assert len(manager.focus_stack) == 1


def test_focus_manager_pop_empty():
    """Test popping from empty stack."""
    manager = FocusManager()
    element = manager.pop()
    assert element is None


def test_focus_manager_get_current():
    """Test getting current focus."""
    manager = FocusManager()
    assert manager.get_current() is None

    manager.push("button1")
    assert manager.get_current() == "button1"

    manager.push("button2")
    assert manager.get_current() == "button2"


def test_focus_manager_trap():
    """Test focus trap."""
    manager = FocusManager()
    assert manager.is_trapped() is False

    manager.trap(True)
    assert manager.is_trapped() is True

    manager.trap(False)
    assert manager.is_trapped() is False


# AccessibilityReport Tests


def test_accessibility_report_init():
    """Test report initialization."""
    report = AccessibilityReport()
    assert report.passed == 0
    assert report.failed == 0
    assert report.warnings == 0
    assert len(report.issues) == 0


def test_accessibility_report_add_pass():
    """Test adding pass."""
    report = AccessibilityReport()
    report.add_pass()
    assert report.passed == 1


def test_accessibility_report_add_fail():
    """Test adding fail."""
    report = AccessibilityReport()
    report.add_fail("Missing label")
    assert report.failed == 1
    assert len(report.issues) == 1
    assert "FAIL: Missing label" in report.issues


def test_accessibility_report_add_warning():
    """Test adding warning."""
    report = AccessibilityReport()
    report.add_warning("Low contrast")
    assert report.warnings == 1
    assert len(report.issues) == 1
    assert "WARN: Low contrast" in report.issues


def test_accessibility_report_get_score():
    """Test getting score."""
    report = AccessibilityReport()
    assert report.get_score() == 1.0

    report.add_pass()
    report.add_pass()
    report.add_fail("Issue")
    assert report.get_score() == 2 / 3


# AccessibilityAuditor Tests


def test_accessibility_auditor_init():
    """Test auditor initialization."""
    auditor = AccessibilityAuditor()
    assert auditor.report is not None


def test_accessibility_auditor_check_aria_labels():
    """Test checking ARIA labels."""
    auditor = AccessibilityAuditor()

    elements = [
        {"id": "button1", "aria-label": "Click me"},
        {"id": "button2", "aria-labelledby": "label2"},
        {"id": "button3"},
    ]

    report = auditor.check_aria_labels(elements)
    assert report.passed == 2
    assert report.failed == 1


def test_accessibility_auditor_check_keyboard_navigation():
    """Test checking keyboard navigation."""
    auditor = AccessibilityAuditor()

    # With focusable elements
    report = auditor.check_keyboard_navigation(["button1", "button2"])
    assert report.passed == 1
    assert report.failed == 0

    # Without focusable elements
    report = auditor.check_keyboard_navigation([])
    assert report.passed == 0
    assert report.failed == 1


def test_accessibility_auditor_check_color_contrast():
    """Test checking color contrast."""
    auditor = AccessibilityAuditor()

    # Different colors
    report = auditor.check_color_contrast("#000000", "#FFFFFF")
    assert report.passed == 1
    assert report.failed == 0

    # Same colors
    report = auditor.check_color_contrast("#000000", "#000000")
    assert report.passed == 0
    assert report.failed == 1


def test_accessibility_auditor_get_report():
    """Test getting report."""
    auditor = AccessibilityAuditor()
    auditor.check_aria_labels([{"id": "button1", "aria-label": "Click"}])

    report = auditor.get_report()
    assert report.passed == 1


# Integration Tests


def test_aria_with_screen_reader():
    """Test ARIA with screen reader."""
    reader = ScreenReader()
    attrs = AriaAttributes(
        role=AriaRole.ALERT,
        label="Error occurred",
        live=AriaLive.ASSERTIVE,
    )

    # Announce when alert is shown
    reader.announce(attrs.label or "")

    announcements = reader.get_announcements()
    assert len(announcements) == 1
    assert announcements[0] == "Error occurred"


def test_keyboard_shortcuts_with_focus():
    """Test keyboard shortcuts with focus management."""
    manager = KeyboardShortcutManager()
    focus = FocusManager()

    # Register shortcuts
    manager.register("next", KeyboardShortcut(key="Tab", description="Next element"))
    manager.register("prev", KeyboardShortcut(key="Tab", shift=True, description="Previous element"))

    # Simulate navigation
    focus.push("button1")
    action = manager.get_action("Tab", ctrl=False, alt=False, shift=False, meta=False)
    assert action == "next"

    focus.push("button2")
    action = manager.get_action("Tab", ctrl=False, alt=False, shift=True, meta=False)
    assert action == "prev"


def test_full_accessibility_audit():
    """Test full accessibility audit."""
    auditor = AccessibilityAuditor()

    # Check ARIA labels
    elements = [
        {"id": "button1", "aria-label": "Save"},
        {"id": "button2", "aria-label": "Cancel"},
    ]
    auditor.check_aria_labels(elements)

    # Check keyboard navigation
    auditor.check_keyboard_navigation(["button1", "button2"])

    # Check color contrast
    auditor.check_color_contrast("#000000", "#FFFFFF")

    report = auditor.get_report()
    assert report.passed > 0
    assert report.get_score() > 0.0
