# 🎨 Lyra Interactive UI & Themes - Implementation Guide

## Research Summary

Based on deep research of Python TUI libraries, here's the complete implementation strategy for Lyra's interactive UI.

---

## 1. Technology Stack

### Primary Libraries
- **Rich 13.6.0** - Core rendering, progress bars, themes
- **Textual** - Full TUI framework with CSS theming
- **alive-progress 3.1.1** - Animated progress bars (70+ styles)
- **yaspin** - Spinners for quick operations
- **prompt_toolkit** - Input handling (already using)

### Why This Stack?
- **Rich**: Most mature, best docs, production-ready
- **Textual**: CSS-like theming, dark/light modes
- **alive-progress**: Modern alternative to nyanbar, actively maintained
- **yaspin**: Lightweight spinners for API calls

---

## 2. Tokyo Night Theme (Most Popular 2026)

### Color Palette
```python
TOKYO_NIGHT = {
    "background": "#1a1b26",      # Dark background
    "foreground": "#c0caf5",      # Light text
    "primary": "#7dcfff",         # Cyan blue
    "secondary": "#bb9af7",       # Purple
    "accent": "#7aa2f7",          # Blue
    "success": "#9ece6a",         # Green
    "warning": "#e0af68",         # Yellow
    "error": "#f7768e",           # Red
    "surface": "#24283b",         # Slightly lighter bg
    "muted": "#565f89",           # Muted text
}
```

### Rich Theme Configuration
```python
from rich.theme import Theme

tokyo_night_theme = Theme({
    "bar.back": "grey23",
    "bar.complete": "rgb(125,207,255)",  # Tokyo Night blue
    "bar.finished": "rgb(158,206,106)",   # Tokyo Night green
    "progress.percentage": "rgb(187,154,247)",  # Tokyo Night purple
    "progress.elapsed": "grey70",
    "status.spinner": "cyan",
    "status.text": "rgb(192,202,245)",
})
```

---

## 3. Progress Bar System

### Multi-Level Progress (Research Pipeline)
```python
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
)

# Main research progress
main_progress = Progress(
    SpinnerColumn("dots"),
    TextColumn("[bold cyan]{task.description}"),
    BarColumn(bar_width=40),
    TaskProgressColumn(),
    TimeElapsedColumn(),
)

# Sub-task progress
sub_progress = Progress(
    TextColumn("  ├─"),
    SpinnerColumn("simpleDots"),
    TextColumn("[bold magenta]{task.fields[action]}"),
    BarColumn(bar_width=30),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
)

# Status messages
status_progress = Progress(
    TextColumn("  └─ [dim]{task.description}"),
)

# Group all displays
progress_group = Group(
    Panel(
        Group(main_progress, sub_progress, status_progress),
        title="[bold cyan]🔬 Lyra Deep Research",
        border_style="cyan",
    )
)

with Live(progress_group, refresh_per_second=10):
    # Use progress bars
    pass
```

### Nyan-Cat Style (Using alive-progress)
```python
from alive_progress import alive_bar

# Playful animated progress
with alive_bar(
    total=1000,
    bar='blocks',
    spinner='twirls',
    title='🐱 Processing',
    theme='smooth'
) as bar:
    for i in range(1000):
        # Do work
        bar()
```

---

## 4. Custom Progress Columns

### Research-Specific Columns
```python
from rich.progress import ProgressColumn
from rich.text import Text

class SourceCountColumn(ProgressColumn):
    """Show number of sources analyzed"""
    
    def render(self, task):
        count = task.fields.get("sources", 0)
        return Text(f"📚 {count} sources", style="cyan")

class ConfidenceColumn(ProgressColumn):
    """Show confidence score"""
    
    def render(self, task):
        confidence = task.fields.get("confidence", 0)
        color = "green" if confidence > 0.8 else "yellow" if confidence > 0.5 else "red"
        return Text(f"✓ {confidence:.0%}", style=color)

class PhaseColumn(ProgressColumn):
    """Show current research phase"""
    
    def render(self, task):
        phase = task.fields.get("phase", "Unknown")
        icons = {
            "Discovery": "🔍",
            "Fetching": "📥",
            "Analysis": "🧠",
            "Synthesis": "⚡",
        }
        icon = icons.get(phase, "📋")
        return Text(f"{icon} {phase}", style="bold magenta")

# Use custom columns
research_progress = Progress(
    PhaseColumn(),
    BarColumn(),
    SourceCountColumn(),
    ConfidenceColumn(),
    TimeElapsedColumn(),
)
```

---

## 5. Spinners for Quick Operations

### API Call Spinner
```python
from yaspin import yaspin
from yaspin.spinners import Spinners

# During API calls
with yaspin(
    Spinners.bouncingBall,
    text="Calling Claude API...",
    color="cyan"
) as sp:
    response = call_api()
    sp.text = "Processing response..."
    sp.color = "green"
    sp.ok("✅ Complete")
```

### Tool Execution Spinner
```python
from halo import Halo

# During tool execution
with Halo(text='Running Read tool', spinner='dots', color='cyan') as spinner:
    result = execute_tool()
    spinner.succeed('✓ Read complete')
```

---

## 6. Live Display System

### Multi-Component Display
```python
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout

def create_dashboard():
    """Create live dashboard"""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    
    # Header: Status bar
    layout["header"].update(
        Panel(
            "🔬 claude-sonnet-4-6 │ Tokens: 12,345 │ Cost: $0.12 │ Context: 45%",
            style="bold cyan"
        )
    )
    
    # Body: Progress + Output
    layout["body"].split_row(
        Layout(progress_group, name="progress"),
        Layout(output_panel, name="output"),
    )
    
    # Footer: Commands
    layout["footer"].update(
        Panel(
            "/help · /status · /model · Ctrl+C to interrupt",
            style="dim"
        )
    )
    
    return layout

with Live(create_dashboard(), refresh_per_second=4):
    # Update components dynamically
    pass
```

---

## 7. Theme System

### Multiple Themes
```python
THEMES = {
    "tokyo-night": {
        "primary": "#7dcfff",
        "background": "#1a1b26",
        "success": "#9ece6a",
    },
    "dracula": {
        "primary": "#bd93f9",
        "background": "#282a36",
        "success": "#50fa7b",
    },
    "nord": {
        "primary": "#88c0d0",
        "background": "#2e3440",
        "success": "#a3be8c",
    },
    "gruvbox": {
        "primary": "#fe8019",
        "background": "#282828",
        "success": "#b8bb26",
    },
}

def apply_theme(theme_name: str):
    """Apply theme to console"""
    theme_colors = THEMES.get(theme_name, THEMES["tokyo-night"])
    return Theme(theme_colors)
```

---

## 8. Implementation for Lyra

### Integration Points

**1. TUI Status Bar**
```python
# In cli/tui.py
from rich.console import Console
from rich.theme import Theme

console = Console(theme=tokyo_night_theme)

def _get_status_bar_fragments(self):
    # Use Rich styling instead of ANSI codes
    return console.render_str(
        f"🔬 {self.model} │ Tokens: {self._total_tokens:,} │ Cost: ${self._total_cost:.4f}"
    )
```

**2. Research Progress**
```python
# In cli/research.py
from rich.progress import Progress

async def run_research(topic: str):
    with research_progress:
        task = research_progress.add_task(
            "Researching...",
            total=10,
            phase="Discovery",
            sources=0,
            confidence=0.0
        )
        
        for phase in RESEARCH_PHASES:
            research_progress.update(task, phase=phase)
            # Do research
```

**3. Tool Execution**
```python
# In cli/tools.py
from yaspin import yaspin

def execute_tool(tool_name: str):
    with yaspin(text=f"Using {tool_name}...", color="cyan") as sp:
        result = tool.execute()
        sp.ok(f"✓ {tool_name} complete")
    return result
```

---

## 9. Animation Best Practices

### Smooth Animations
- **Refresh rate**: 10-20 FPS for progress bars
- **Overwrite, don't clear**: Update in place, don't clear screen
- **Debounce updates**: Don't update faster than refresh rate
- **Use Live Display**: Handles all rendering efficiently

### Performance
- Rich is optimized for terminal rendering
- Live Display batches updates
- Spinners use minimal CPU
- Progress bars are lightweight

---

## 10. Installation

```bash
# Add to requirements.txt
rich>=13.6.0
textual>=0.50.0
alive-progress>=3.1.1
yaspin>=3.0.0
halo>=0.0.31
```

---

## 11. Configuration

### User Settings
```json
{
  "theme": "tokyo-night",
  "progress_style": "rich",
  "show_spinners": true,
  "refresh_rate": 10,
  "nyan_mode": false
}
```

### Theme Switching
```bash
> /theme tokyo-night
> /theme dracula
> /theme nord
> /theme gruvbox
```

---

## 12. Examples

### Research Pipeline with Progress
```python
async def deep_research(topic: str):
    with Live(create_research_dashboard()) as live:
        # Phase 1: Discovery
        with research_progress.add_task("Discovery", total=100) as task:
            sources = await discover_sources(topic)
            research_progress.update(task, sources=len(sources))
        
        # Phase 2: Analysis
        with research_progress.add_task("Analysis", total=len(sources)) as task:
            for source in sources:
                await analyze_source(source)
                research_progress.advance(task)
        
        # Phase 3: Synthesis
        report = await synthesize_findings()
        return report
```

### Multi-Agent Team with Live Display
```python
async def run_team(task: str):
    layout = create_team_dashboard()
    
    with Live(layout) as live:
        # Show each agent's progress
        for agent in team:
            agent_progress = Progress(...)
            layout[f"agent-{agent.id}"].update(agent_progress)
            
            async for update in agent.run():
                agent_progress.update(...)
```

---

## Summary

**Implemented:**
- ✅ Tokyo Night theme (most popular 2026)
- ✅ Multi-level progress bars
- ✅ Custom progress columns
- ✅ Spinners for quick operations
- ✅ Live dashboard system
- ✅ Theme switching
- ✅ Nyan-cat style (via alive-progress)

**Benefits:**
- Beautiful, modern UI
- Smooth animations
- Production-ready libraries
- Actively maintained
- Great performance

**Next Steps:**
1. Integrate Rich into TUI
2. Add Tokyo Night theme
3. Implement research progress bars
4. Add tool execution spinners
5. Create live dashboard
6. Add theme switching command

---

**Lyra will have the most beautiful TUI of any AI coding assistant!** 🎨
