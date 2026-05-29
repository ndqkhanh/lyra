"""Tests for keyboard navigation."""


from lyra_ui import (
    CommandPalette,
    KeyBinding,
    NavigationMode,
    QuickActions,
    VimNavigator,
)

# Vim Navigator Tests


def test_vim_navigator_init():
    """Test Vim navigator initialization."""
    nav = VimNavigator()
    assert nav.mode == NavigationMode.NORMAL
    assert len(nav.bindings) > 0


def test_vim_navigator_default_bindings():
    """Test default Vim bindings."""
    nav = VimNavigator()

    # Check navigation keys
    assert nav.get_binding("h") is not None
    assert nav.get_binding("j") is not None
    assert nav.get_binding("k") is not None
    assert nav.get_binding("l") is not None

    # Check special keys
    assert nav.get_binding("gg") is not None
    assert nav.get_binding("G") is not None


def test_vim_navigator_get_binding():
    """Test getting key binding."""
    nav = VimNavigator()
    binding = nav.get_binding("h")
    assert binding is not None
    assert binding.action == "move_left"
    assert binding.description == "Move left"


def test_vim_navigator_add_binding():
    """Test adding custom binding."""
    nav = VimNavigator()
    custom = KeyBinding("ctrl+s", "save", "Save file")
    nav.add_binding(custom)

    binding = nav.get_binding("ctrl+s")
    assert binding is not None
    assert binding.action == "save"


def test_vim_navigator_remove_binding():
    """Test removing binding."""
    nav = VimNavigator()
    nav.remove_binding("h")
    assert nav.get_binding("h") is None


def test_vim_navigator_set_mode():
    """Test setting navigation mode."""
    nav = VimNavigator()
    nav.set_mode(NavigationMode.INSERT)
    assert nav.get_mode() == NavigationMode.INSERT


def test_vim_navigator_list_bindings():
    """Test listing bindings."""
    nav = VimNavigator()
    bindings = nav.list_bindings()
    assert len(bindings) > 0
    assert all(isinstance(b, KeyBinding) for b in bindings)


def test_vim_navigator_list_bindings_by_mode():
    """Test listing bindings by mode."""
    nav = VimNavigator()
    normal_bindings = nav.list_bindings(mode=NavigationMode.NORMAL)
    assert len(normal_bindings) > 0


# Command Palette Tests


def test_command_palette_init():
    """Test command palette initialization."""
    palette = CommandPalette()
    assert len(palette.commands) == 0
    assert len(palette.history) == 0


def test_command_palette_register_command():
    """Test registering command."""
    palette = CommandPalette()

    def test_cmd():
        return "executed"

    palette.register_command("test", test_cmd, category="testing")
    assert "test" in palette.commands


def test_command_palette_execute_command():
    """Test executing command."""
    palette = CommandPalette()

    def add(a, b):
        return a + b

    palette.register_command("add", add)
    result = palette.execute_command("add", 2, 3)
    assert result == 5


def test_command_palette_command_history():
    """Test command history."""
    palette = CommandPalette()

    def cmd1():
        pass

    def cmd2():
        pass

    palette.register_command("cmd1", cmd1)
    palette.register_command("cmd2", cmd2)

    palette.execute_command("cmd1")
    palette.execute_command("cmd2")

    history = palette.get_recent_commands()
    assert "cmd1" in history
    assert "cmd2" in history


def test_command_palette_search_commands():
    """Test searching commands."""
    palette = CommandPalette()

    def file_open():
        pass

    def file_save():
        pass

    def edit_copy():
        pass

    palette.register_command("file:open", file_open)
    palette.register_command("file:save", file_save)
    palette.register_command("edit:copy", edit_copy)

    # Search for "file"
    results = palette.search_commands("file")
    assert len(results) == 2
    assert "file:open" in results
    assert "file:save" in results


def test_command_palette_get_recent_commands():
    """Test getting recent commands."""
    palette = CommandPalette()

    for i in range(15):
        palette.register_command(f"cmd{i}", lambda: None)
        palette.execute_command(f"cmd{i}")

    recent = palette.get_recent_commands(limit=5)
    assert len(recent) == 5


def test_command_palette_categories():
    """Test command categories."""
    palette = CommandPalette()

    def cmd1():
        pass

    def cmd2():
        pass

    palette.register_command("cmd1", cmd1, category="file")
    palette.register_command("cmd2", cmd2, category="edit")

    categories = palette.list_categories()
    assert "file" in categories
    assert "edit" in categories


def test_command_palette_get_category_commands():
    """Test getting commands by category."""
    palette = CommandPalette()

    def cmd1():
        pass

    def cmd2():
        pass

    palette.register_command("open", cmd1, category="file")
    palette.register_command("save", cmd2, category="file")

    file_commands = palette.get_category_commands("file")
    assert len(file_commands) == 2
    assert "open" in file_commands
    assert "save" in file_commands


# Quick Actions Tests


def test_quick_actions_init():
    """Test quick actions initialization."""
    actions = QuickActions()
    assert len(actions.actions) == 3  # @, #, /


def test_quick_actions_get_action():
    """Test getting action."""
    actions = QuickActions()
    assert actions.get_action("@") == "file_picker"
    assert actions.get_action("#") == "skill_picker"
    assert actions.get_action("/") == "command_picker"


def test_quick_actions_add_action():
    """Test adding action."""
    actions = QuickActions()
    actions.add_action("!", "shell_command")
    assert actions.get_action("!") == "shell_command"


def test_quick_actions_remove_action():
    """Test removing action."""
    actions = QuickActions()
    actions.remove_action("@")
    assert actions.get_action("@") is None


def test_quick_actions_list_actions():
    """Test listing actions."""
    actions = QuickActions()
    all_actions = actions.list_actions()
    assert len(all_actions) == 3
    assert "@" in all_actions
    assert "#" in all_actions
    assert "/" in all_actions


# Integration Tests


def test_vim_navigator_with_command_palette():
    """Test Vim navigator with command palette."""
    VimNavigator()
    palette = CommandPalette()

    # Register command
    def goto_line(line):
        return f"Going to line {line}"

    palette.register_command("goto", goto_line)

    # Execute via palette
    result = palette.execute_command("goto", 42)
    assert result == "Going to line 42"


def test_complete_keyboard_workflow():
    """Test complete keyboard workflow."""
    # Set up navigator
    nav = VimNavigator()
    nav.set_mode(NavigationMode.NORMAL)

    # Set up command palette
    palette = CommandPalette()

    def save_file():
        return "saved"

    def open_file():
        return "opened"

    palette.register_command("save", save_file, category="file")
    palette.register_command("open", open_file, category="file")

    # Set up quick actions
    actions = QuickActions()

    # Execute workflow
    assert nav.get_mode() == NavigationMode.NORMAL
    assert actions.get_action("@") == "file_picker"

    # Search and execute command
    results = palette.search_commands("save")
    assert "save" in results

    result = palette.execute_command("save")
    assert result == "saved"


def test_key_binding_dataclass():
    """Test KeyBinding dataclass."""
    binding = KeyBinding(
        key="ctrl+s",
        action="save",
        description="Save file",
        mode=NavigationMode.NORMAL,
    )

    assert binding.key == "ctrl+s"
    assert binding.action == "save"
    assert binding.description == "Save file"
    assert binding.mode == NavigationMode.NORMAL


def test_navigation_mode_enum():
    """Test NavigationMode enum."""
    assert NavigationMode.NORMAL.value == "normal"
    assert NavigationMode.INSERT.value == "insert"
    assert NavigationMode.VISUAL.value == "visual"
    assert NavigationMode.COMMAND.value == "command"
