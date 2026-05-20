# Phase 7 — Banners, Notifications & Themes

Modules: `banner.py`, `notifications.py`, `themes.py`

## Banner System (`banner.py`)

Adaptive banners with themes and animations.

```python
from lyra_ui import (
    BannerSystem,
    BannerStyle,
    BannerTheme,
    BannerStats,
    StartupBanner,
    ShutdownBanner,
)

banner = BannerSystem(style=BannerStyle.FULL, theme=BannerTheme.DRACULA)

stats = BannerStats(
    tokens_used=10000,
    total_cost=0.50,
    elapsed_time=60.0,
    agents_active=3,
)
banner.display(
    title="Lyra",
    subtitle="AI Research Agent",
    status="Processing",
    stats=stats,
)

StartupBanner().display(version="1.0.0", loading_message="Initializing...")
ShutdownBanner().display(tasks_completed=10, total_time=120.5)
```

**Features**

- Adaptive width (36–100 cols)
- Multiple styles (minimal, standard, full)
- Theme support (default, dark, light, solarized, dracula)
- Status indicators
- Quick stats display (tokens, cost, time, agents)
- Startup / shutdown animations

## Notification System (`notifications.py`)

Toast notifications with optional sound integration.

```python
from lyra_ui import NotificationSystem, NotificationLevel

notif_system = NotificationSystem(max_history=100, enable_sound=True)

notif_system.info("Task Started", "Research task has started")
notif_system.success("Task Completed", "Research completed successfully")
notif_system.warning("Low Memory", "Memory usage is high")
notif_system.error("Task Failed", "Analysis task failed")

# Toast display
notif = notif_system.info("Update", "New data available")
notif_system.display_toast(notif)

# History
history = notif_system.get_history(level=NotificationLevel.ERROR, limit=10)
unread = notif_system.get_history(unread_only=True)

notif_system.mark_read(notif.id)
notif_system.mark_all_read()
count = notif_system.get_unread_count()

# Quick toast / history viewer
from lyra_ui import ToastNotification, NotificationHistory
ToastNotification().show("Quick message", level=NotificationLevel.SUCCESS)
NotificationHistory().display(notif_system.notifications)
```

**Features**

- Non-blocking toast notifications
- Levels: info, success, warning, error
- Notification history with filtering
- Read / unread tracking
- Sound integration (via `lyra-audio`)
- Notification persistence
- Action support

## Theme System (`themes.py`)

Customizable color themes and animations.

```python
from lyra_ui import ThemeManager, ThemeName, ThemeColors, AnimationEffects

theme_mgr = ThemeManager()
theme_mgr.set_theme(ThemeName.DRACULA)
theme = theme_mgr.get_current_theme()

colors = ThemeColors(
    primary="cyan",
    secondary="blue",
    success="green",
    warning="yellow",
    error="red",
    info="cyan",
    background="black",
    foreground="white",
    dim="dim white",
    bright="bright_white",
)
theme_mgr.create_custom_theme("my_theme", colors)
theme_mgr.preview_theme(ThemeName.NORD)

# Export / import
theme_dict = theme_mgr.export_theme(ThemeName.DRACULA)
theme_mgr.import_theme("imported_theme", theme_dict)
themes = theme_mgr.list_themes()

# Animations
effects = AnimationEffects()
effects.typing_indicator("Agent is thinking")
effects.pulse_effect("Processing", color="cyan")
effects.loading_spinner("Loading data")
effects.success_animation("Task completed")
effects.error_animation("Task failed")
```

**Features**

- 9 built-in themes (default, dark, light, solarized, dracula, monokai, nord, gruvbox, ...)
- Custom theme creation
- Theme preview
- Theme import / export
- Animation effects (typing, pulse, loading, success, error)
- Per-component styling

## Components

- `BannerSystem` — Adaptive banner with themes
- `StartupBanner` / `ShutdownBanner` — Startup & shutdown animations
- `NotificationSystem` — Toast notifications with history
- `ToastNotification` — Quick toast display
- `NotificationHistory` — History viewer
- `ThemeManager` — Theme management
- `AnimationEffects` — Visual animations
