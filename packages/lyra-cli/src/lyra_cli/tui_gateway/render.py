"""Rendering bridge — routes TUI content through Python-side renderers.

When the Lyra agent's rich_output module exists, its functions are used.
When it doesn't, everything returns None and the TUI falls back to its
own markdown.tsx.
"""

from __future__ import annotations


def render_message(text: str, cols: int = 80) -> str | None:
    """Render a message using the agent's rich output formatter if available."""
    try:
        from lyra_agents.rich_output import format_response
    except ImportError:
        return None

    try:
        return format_response(text, cols=cols)
    except TypeError:
        return format_response(text)
    except Exception:
        return None


def render_diff(text: str, cols: int = 80) -> str | None:
    """Render a diff using the agent's diff renderer if available."""
    try:
        from lyra_agents.rich_output import render_diff as _rd
    except ImportError:
        return None

    try:
        return _rd(text, cols=cols)
    except TypeError:
        return _rd(text)
    except Exception:
        return None


def make_stream_renderer(cols: int = 80):
    """Create a streaming renderer for incremental output, or None if unavailable."""
    try:
        from lyra_agents.rich_output import StreamingRenderer
    except ImportError:
        return None

    try:
        return StreamingRenderer(cols=cols)
    except TypeError:
        return StreamingRenderer()
    except Exception:
        return None
