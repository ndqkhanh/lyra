"""Welcome banner for Lyra - Claude Code style"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class WelcomeBannerConfig:
    """Configuration for welcome banner"""
    version: str
    model: str
    effort: str
    provider: str
    working_dir: str
    context_window: Optional[str] = None


class WelcomeBanner:
    """Renders Lyra welcome banner in Claude Code style"""

    # Lyra ASCII art (Lyre/Harp)
    LYRA_ART = [
        "  ╦  ╦ ╦ ╦═╗ ╔═╗",
        "  ║  ╚╦╝ ╠╦╝ ╠═╣",
        "  ╩═╝ ╩  ╩╚═ ╩ ╩"
    ]

    def __init__(self, width: int = 80):
        self.width = width

    def render(self, config: WelcomeBannerConfig) -> str:
        """Render the welcome banner"""
        lines = []

        # Top border with title
        title = f"Lyra v{config.version}"
        border_content = f"─── {title} "
        remaining = self.width - len(border_content) - 1
        top_border = f"╭{border_content}{'─' * remaining}"
        lines.append(top_border)

        # Line 1: ASCII art + version
        art_line_1 = self.LYRA_ART[0]
        info_1 = f"Lyra v{config.version}"
        line_1 = f"{art_line_1}   {info_1}"
        lines.append(line_1)

        # Line 2: ASCII art + model info
        art_line_2 = self.LYRA_ART[1]
        context = f" ({config.context_window})" if config.context_window else ""
        info_2 = f"{config.model}{context} · {config.effort} effort · {config.provider}"
        line_2 = f"{art_line_2}   {info_2}"
        lines.append(line_2)

        # Line 3: ASCII art + working directory
        art_line_3 = self.LYRA_ART[2]
        # Shorten path if too long
        path = self._shorten_path(config.working_dir, self.width - len(art_line_3) - 3)
        line_3 = f"{art_line_3}   {path}"
        lines.append(line_3)

        return "\n".join(lines)

    def _shorten_path(self, path: str, max_length: int) -> str:
        """Shorten path to fit within max_length"""
        if len(path) <= max_length:
            return path

        # Replace home directory with ~
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]

        if len(path) <= max_length:
            return path

        # Truncate from the middle
        parts = path.split(os.sep)
        if len(parts) <= 3:
            # Too short to truncate meaningfully
            return "..." + path[-(max_length - 3):]

        # Keep first and last parts, truncate middle
        first = parts[0] or os.sep
        last = parts[-1]
        middle_budget = max_length - len(first) - len(last) - 5  # 5 for separators and ...

        if middle_budget > 0:
            middle_parts = parts[1:-1]
            middle = os.sep.join(middle_parts)
            if len(middle) > middle_budget:
                middle = "..."
            return f"{first}{os.sep}{middle}{os.sep}{last}"
        else:
            return f"{first}{os.sep}...{os.sep}{last}"


def create_welcome_banner(
    version: str = "0.1.0",
    model: str = "Opus 4.7",
    effort: str = "high",
    provider: str = "Anthropic API",
    working_dir: Optional[str] = None,
    context_window: Optional[str] = "1M context",
    width: int = 80
) -> str:
    """
    Create a welcome banner for Lyra

    Args:
        version: Lyra version
        model: Model name (e.g., "Opus 4.7")
        effort: Effort level (low, medium, high, xhigh)
        provider: Provider name (e.g., "Anthropic API")
        working_dir: Current working directory (defaults to cwd)
        context_window: Context window size (e.g., "1M context")
        width: Terminal width

    Returns:
        Formatted welcome banner string
    """
    if working_dir is None:
        working_dir = os.getcwd()

    config = WelcomeBannerConfig(
        version=version,
        model=model,
        effort=effort,
        provider=provider,
        working_dir=working_dir,
        context_window=context_window
    )

    banner = WelcomeBanner(width=width)
    return banner.render(config)


if __name__ == "__main__":
    # Demo
    print(create_welcome_banner(
        version="0.1.0",
        model="Opus 4.7",
        effort="xhigh",
        provider="Anthropic API",
        working_dir="~/Downloads/MyCV/research/harness-engineering",
        context_window="1M context"
    ))
    print()

    # Test with different models
    print(create_welcome_banner(
        version="0.1.0",
        model="Sonnet 4.6",
        effort="high",
        provider="Anthropic API",
        context_window="200K context"
    ))
    print()

    print(create_welcome_banner(
        version="0.1.0",
        model="GPT-4 Turbo",
        effort="medium",
        provider="OpenAI API",
        context_window="128K context"
    ))
