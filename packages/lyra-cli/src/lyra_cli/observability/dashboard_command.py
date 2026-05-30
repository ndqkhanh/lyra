"""Dashboard Command — user-facing `/dashboard` CLI command for real-time system overview.

Provides panel-based dashboard with status, metrics, alerts, and trace panels
with configurable refresh intervals and text-based rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PanelType(StrEnum):
    STATUS = "status"
    METRICS = "metrics"
    ALERTS = "alerts"
    TRACES = "traces"
    CUSTOM = "custom"


@dataclass(frozen=True)
class DashboardPanel:
    title: str
    panel_type: PanelType
    content: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    refresh_interval_seconds: float = 2.0
    max_panels: int = 10
    show_alerts: bool = True
    show_traces: bool = True


class DashboardCommand:
    """User-facing `/dashboard` command for real-time system observability.

    Manages configurable dashboard panels for status, metrics, alerts,
    and traces with text-based rendering for terminal display.

    Usage::

        cmd = DashboardCommand()
        cmd.add_panel("System Health", PanelType.STATUS, "All systems operational")
        cmd.add_panel("API Metrics", PanelType.METRICS, "p50=12ms p95=45ms p99=200ms")
        print(cmd.render())
    """

    def __init__(self, config: DashboardConfig | None = None) -> None:
        self.config = config or DashboardConfig()
        self._panels: dict[str, DashboardPanel] = {}

    @property
    def panel_count(self) -> int:
        return len(self._panels)

    def add_panel(
        self,
        title: str,
        panel_type: PanelType,
        content: str = "",
        metadata: dict[str, str] | None = None,
    ) -> DashboardPanel:
        if len(self._panels) >= self.config.max_panels:
            oldest = next(iter(self._panels))
            del self._panels[oldest]
        panel = DashboardPanel(
            title=title,
            panel_type=panel_type,
            content=content,
            metadata=metadata or {},
        )
        self._panels[title] = panel
        return panel

    def remove_panel(self, title: str) -> bool:
        if title in self._panels:
            del self._panels[title]
            return True
        return False

    def update_panel(
        self,
        title: str,
        content: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> DashboardPanel | None:
        panel = self._panels.get(title)
        if panel is None:
            return None
        new_panel = DashboardPanel(
            title=panel.title,
            panel_type=panel.panel_type,
            content=content if content is not None else panel.content,
            metadata=metadata if metadata is not None else panel.metadata,
        )
        self._panels[title] = new_panel
        return new_panel

    def get_panel(self, title: str) -> DashboardPanel | None:
        return self._panels.get(title)

    def render(self) -> str:
        if not self._panels:
            return "Dashboard is empty. Use /dashboard add <title> <type> to add panels."

        lines = ["=" * 60, "  LYRA OBSERVABILITY DASHBOARD", "=" * 60, ""]
        for title, panel in self._panels.items():
            icon = self._panel_icon(panel.panel_type)
            lines.append(f"  {icon} {title} [{panel.panel_type.value}]")
            lines.append(f"  {'─' * 50}")
            for line in panel.content.split("\n"):
                lines.append(f"  {line}")
            lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def list_panels(self) -> list[DashboardPanel]:
        return list(self._panels.values())

    def reset(self) -> None:
        self._panels.clear()

    @staticmethod
    def _panel_icon(panel_type: PanelType) -> str:
        icons = {
            PanelType.STATUS: "[S]",
            PanelType.METRICS: "[M]",
            PanelType.ALERTS: "[!]",
            PanelType.TRACES: "[T]",
            PanelType.CUSTOM: "[C]",
        }
        return icons.get(panel_type, "[?]")
