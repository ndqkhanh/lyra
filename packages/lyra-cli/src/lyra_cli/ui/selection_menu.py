"""Selection menu - Interactive menu with keyboard navigation"""

from dataclasses import dataclass

from lyra_cli.ui import ColorEngine, SymbolRegistry


@dataclass
class MenuOption:
    """Menu option"""
    label: str
    description: str
    value: str
    active: bool = False


class SelectionMenu:
    """Interactive selection menu (model picker, etc.)

    Implements Claude Code-style selection menus with:
    - Keyboard navigation (↑↓)
    - Current selection indicator (❯)
    - Active item marker (✔)
    """

    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description
        self.options: list[MenuOption] = []
        self.selected_index = 0
        self.symbols = SymbolRegistry()
        self.colors = ColorEngine()

    def add_option(
        self,
        label: str,
        description: str,
        value: str,
        active: bool = False
    ) -> None:
        """Add menu option

        Args:
            label: Option label
            description: Option description
            value: Option value
            active: Whether currently active
        """
        self.options.append(MenuOption(
            label=label,
            description=description,
            value=value,
            active=active
        ))

    def move_up(self) -> None:
        """Move selection up"""
        if self.selected_index > 0:
            self.selected_index -= 1

    def move_down(self) -> None:
        """Move selection down"""
        if self.selected_index < len(self.options) - 1:
            self.selected_index += 1

    def get_selected(self) -> MenuOption | None:
        """Get currently selected option"""
        if 0 <= self.selected_index < len(self.options):
            return self.options[self.selected_index]
        return None

    def render(self, width: int = 80) -> str:
        """Render selection menu

        Args:
            width: Menu width

        Returns:
            Formatted menu string
        """
        lines = []

        # Top divider
        lines.append(self.colors.dim("─" * width))

        # Title
        lines.append(f"  {self.title}")

        # Description
        if self.description:
            lines.append(f"  {self.colors.dim(self.description)}")

        lines.append("")

        # Options
        for i, option in enumerate(self.options):
            is_selected = (i == self.selected_index)

            # Prefix
            if is_selected:
                prefix = self.symbols.get("❯")
            else:
                prefix = " "

            # Suffix
            suffix = ""
            if option.active:
                suffix = f" {self.symbols.get('✔')}"

            # Format line
            line = f"  {prefix} {i + 1}. {option.label}"
            if suffix:
                line += self.colors.green(suffix)

            lines.append(line)

            # Description (indented)
            if option.description:
                desc_line = f"      {self.colors.dim(option.description)}"
                lines.append(desc_line)

        lines.append("")

        # Keyboard hints
        hints = "Enter to confirm · Esc to cancel"
        lines.append(f"  {self.colors.dim(hints)}")

        # Bottom divider
        lines.append(self.colors.dim("─" * width))

        return "\n".join(lines)
