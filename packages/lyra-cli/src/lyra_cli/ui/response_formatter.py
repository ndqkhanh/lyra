"""Response format patterns - Claude Code-style response formatting"""

from lyra_cli.ui import ColorEngine, SymbolRegistry


class ResponseFormatter:
    """Claude Code-style response formatter

    Implements all response format patterns:
    - ⏺ Active response indicator
    - ✻ Stats line
    - ✶ Thinking indicator
    - ⎿ Tool call display
    """

    def __init__(self, use_colors: bool = True, use_unicode: bool = True):
        self.symbols = SymbolRegistry(use_unicode=use_unicode)
        self.colors = ColorEngine(use_colors=use_colors)

    def format_active_response(self, message: str) -> str:
        """Format active response with ⏺ symbol

        Args:
            message: Response message

        Returns:
            Formatted string with ⏺ prefix
        """
        symbol = self.symbols.status("running")
        return f"{self.colors.yellow(symbol)} {message}"

    def format_stats_line(
        self,
        duration_s: float,
        tool_count: int,
        tokens: int
    ) -> str:
        """Format stats line with ✻ symbol

        Args:
            duration_s: Duration in seconds
            tool_count: Number of tools used
            tokens: Total tokens

        Returns:
            Formatted stats line
        """
        symbol = self.symbols.get("✻")
        time_str = f"{duration_s:.1f}s"
        stats = f"{time_str} · {tool_count} tools · {tokens:,} tokens"
        return f"{self.colors.dim(symbol)} {self.colors.dim(stats)}"

    def format_thinking(self, message: str, elapsed_s: float | None = None) -> str:
        """Format thinking indicator with ✶ symbol

        Args:
            message: Thinking message
            elapsed_s: Optional elapsed time

        Returns:
            Formatted thinking line
        """
        symbol = self.symbols.get("✶")
        if elapsed_s is not None:
            time_str = f"({elapsed_s:.0f}s)"
            return f"{self.colors.dim(symbol)} {message} {self.colors.dim(time_str)}"
        return f"{self.colors.dim(symbol)} {message}"

    def format_tool_call(
        self,
        tool_name: str,
        description: str = "",
        collapsed: bool = True
    ) -> str:
        """Format tool call with ⎿ symbol

        Args:
            tool_name: Tool name
            description: Optional description
            collapsed: Whether collapsed

        Returns:
            Formatted tool call line
        """
        symbol = self.symbols.get("⎿")
        line = f"  {self.colors.dim(symbol)}  {tool_name}"

        if description:
            line += f" {self.colors.dim(description)}"

        if not collapsed:
            line += f" {self.colors.dim('(ctrl+o to collapse)')}"

        return line

    def format_tool_result(
        self,
        result: str,
        indent_level: int = 1
    ) -> str:
        """Format tool result with proper indentation

        Args:
            result: Tool result text
            indent_level: Indentation level

        Returns:
            Formatted tool result
        """
        indent = "  " * indent_level
        symbol = self.symbols.get("⎿")
        return f"{indent}{self.colors.dim(symbol)}  {result}"

    def format_success(self, message: str) -> str:
        """Format success message with ✓ symbol

        Args:
            message: Success message

        Returns:
            Formatted success line
        """
        symbol = self.symbols.get("✓")
        return f"{self.colors.green(symbol)} {message}"

    def format_error(self, message: str) -> str:
        """Format error message with ✗ symbol

        Args:
            message: Error message

        Returns:
            Formatted error line
        """
        symbol = self.symbols.get("✗")
        return f"{self.colors.red(symbol)} {message}"

    def format_warning(self, message: str) -> str:
        """Format warning message with ⚠ symbol

        Args:
            message: Warning message

        Returns:
            Formatted warning line
        """
        symbol = self.symbols.get("⚠")
        return f"{self.colors.yellow(symbol)} {message}"

    def format_info(self, message: str) -> str:
        """Format info message with ℹ symbol

        Args:
            message: Info message

        Returns:
            Formatted info line
        """
        symbol = self.symbols.get("ℹ")
        return f"{self.colors.cyan(symbol)} {message}"

    def format_prompt(self, text: str = "") -> str:
        """Format prompt with ❯ symbol

        Args:
            text: Prompt text

        Returns:
            Formatted prompt line
        """
        symbol = self.symbols.get("❯")
        if text:
            return f"{symbol} {text}"
        return symbol

    def format_separator(self, width: int = 80) -> str:
        """Format horizontal separator

        Args:
            width: Separator width

        Returns:
            Formatted separator line
        """
        return self.colors.dim("─" * width)
