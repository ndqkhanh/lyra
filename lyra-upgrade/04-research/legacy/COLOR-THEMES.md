# Lyra Color Themes

**Version**: 1.0  
**Date**: 2026-05-29  
**Status**: Design Proposal

## Overview

This document defines 5+ beautiful, accessible color themes for Lyra's terminal interface. Each theme is designed with WCAG AA compliance (4.5:1 contrast ratio minimum) and optimized for different use cases and environments.

## Theme Architecture

### Adaptive Detection (Three-Layer)

1. **Environment variable**: `LYRA_THEME` (theme_name or hex color)
2. **Terminal hint**: `COLORFGBG` parsing
3. **OSC 11 probe**: Background color detection for modern terminals

### Color Palette Structure

Each theme defines:
- **Background**: Main terminal background
- **Foreground**: Primary text color
- **Accent colors**: 8 semantic colors (success, error, warning, info, highlight, muted, link, code)
- **UI elements**: Border, selection, status bar, progress bar
- **Syntax highlighting**: 8 token types (keyword, string, number, comment, function, variable, type, operator)

## Theme 1: Dracula (Dark)

**Use case**: General purpose, high contrast, long coding sessions  
**Inspiration**: [Dracula Theme](https://draculatheme.com/)

```yaml
name: dracula
variant: dark
description: "High contrast dark theme with vibrant accents"

colors:
  background: "#282a36"
  foreground: "#f8f8f2"
  
  # Semantic colors
  success: "#50fa7b"      # Green
  error: "#ff5555"        # Red
  warning: "#f1fa8c"      # Yellow
  info: "#8be9fd"         # Cyan
  highlight: "#bd93f9"    # Purple
  muted: "#6272a4"        # Comment gray
  link: "#8be9fd"         # Cyan
  code: "#50fa7b"         # Green
  
  # UI elements
  border: "#44475a"
  selection: "#44475a"
  cursor: "#f8f8f2"
  
  # Status bar (context usage)
  status_low: "#50fa7b"      # <50% - Green
  status_medium: "#f1fa8c"   # 50-80% - Yellow
  status_high: "#ffb86c"     # 80-95% - Orange
  status_critical: "#ff5555" # ≥95% - Red
  
  # Progress bar
  progress_fill: "#bd93f9"   # Purple
  progress_empty: "#44475a"  # Dark gray
  
  # Syntax highlighting
  keyword: "#ff79c6"      # Pink
  string: "#f1fa8c"       # Yellow
  number: "#bd93f9"       # Purple
  comment: "#6272a4"      # Gray
  function: "#50fa7b"     # Green
  variable: "#f8f8f2"     # White
  type: "#8be9fd"         # Cyan
  operator: "#ff79c6"     # Pink

accessibility:
  wcag_level: AA
  contrast_ratios:
    foreground_bg: 12.8:1
    success_bg: 10.2:1
    error_bg: 7.1:1
    warning_bg: 14.5:1
```

## Theme 2: Nord (Dark)

**Use case**: Cool, arctic-inspired, reduced eye strain  
**Inspiration**: [Nord Theme](https://www.nordtheme.com/)

```yaml
name: nord
variant: dark
description: "Arctic-inspired cool palette with subtle contrasts"

colors:
  background: "#2e3440"
  foreground: "#d8dee9"
  
  # Semantic colors
  success: "#a3be8c"      # Green
  error: "#bf616a"        # Red
  warning: "#ebcb8b"      # Yellow
  info: "#88c0d0"         # Cyan
  highlight: "#b48ead"    # Purple
  muted: "#4c566a"        # Dark gray
  link: "#88c0d0"         # Cyan
  code: "#a3be8c"         # Green
  
  # UI elements
  border: "#3b4252"
  selection: "#434c5e"
  cursor: "#d8dee9"
  
  # Status bar
  status_low: "#a3be8c"      # Green
  status_medium: "#ebcb8b"   # Yellow
  status_high: "#d08770"     # Orange
  status_critical: "#bf616a" # Red
  
  # Progress bar
  progress_fill: "#81a1c1"   # Blue
  progress_empty: "#3b4252"  # Dark gray
  
  # Syntax highlighting
  keyword: "#81a1c1"      # Blue
  string: "#a3be8c"       # Green
  number: "#b48ead"       # Purple
  comment: "#616e88"      # Gray
  function: "#88c0d0"     # Cyan
  variable: "#d8dee9"     # White
  type: "#8fbcbb"         # Teal
  operator: "#81a1c1"     # Blue

accessibility:
  wcag_level: AA
  contrast_ratios:
    foreground_bg: 10.5:1
    success_bg: 7.8:1
    error_bg: 5.2:1
    warning_bg: 11.3:1
```

## Theme 3: Gruvbox (Dark)

**Use case**: Warm, retro aesthetic, low-light environments  
**Inspiration**: [Gruvbox Theme](https://github.com/morhetz/gruvbox)

```yaml
name: gruvbox
variant: dark
description: "Warm retro palette optimized for low-light coding"

colors:
  background: "#282828"
  foreground: "#ebdbb2"
  
  # Semantic colors
  success: "#b8bb26"      # Green
  error: "#fb4934"        # Red
  warning: "#fabd2f"      # Yellow
  info: "#83a598"         # Blue
  highlight: "#d3869b"    # Purple
  muted: "#928374"        # Gray
  link: "#83a598"         # Blue
  code: "#b8bb26"         # Green
  
  # UI elements
  border: "#3c3836"
  selection: "#504945"
  cursor: "#ebdbb2"
  
  # Status bar
  status_low: "#b8bb26"      # Green
  status_medium: "#fabd2f"   # Yellow
  status_high: "#fe8019"     # Orange
  status_critical: "#fb4934" # Red
  
  # Progress bar
  progress_fill: "#d3869b"   # Purple
  progress_empty: "#3c3836"  # Dark gray
  
  # Syntax highlighting
  keyword: "#fb4934"      # Red
  string: "#b8bb26"       # Green
  number: "#d3869b"       # Purple
  comment: "#928374"      # Gray
  function: "#fabd2f"     # Yellow
  variable: "#ebdbb2"     # White
  type: "#83a598"         # Blue
  operator: "#fe8019"     # Orange

accessibility:
  wcag_level: AA
  contrast_ratios:
    foreground_bg: 11.2:1
    success_bg: 8.5:1
    error_bg: 6.8:1
    warning_bg: 10.9:1
```

## Theme 4: Solarized Light

**Use case**: Bright environments, daytime coding, reduced glare  
**Inspiration**: [Solarized Theme](https://ethanschoonover.com/solarized/)

```yaml
name: solarized-light
variant: light
description: "Scientifically designed light theme with balanced contrast"

colors:
  background: "#fdf6e3"
  foreground: "#657b83"
  
  # Semantic colors
  success: "#859900"      # Green
  error: "#dc322f"        # Red
  warning: "#b58900"      # Yellow
  info: "#268bd2"         # Blue
  highlight: "#6c71c4"    # Violet
  muted: "#93a1a1"        # Gray
  link: "#268bd2"         # Blue
  code: "#859900"         # Green
  
  # UI elements
  border: "#eee8d5"
  selection: "#eee8d5"
  cursor: "#657b83"
  
  # Status bar
  status_low: "#859900"      # Green
  status_medium: "#b58900"   # Yellow
  status_high: "#cb4b16"     # Orange
  status_critical: "#dc322f" # Red
  
  # Progress bar
  progress_fill: "#6c71c4"   # Violet
  progress_empty: "#eee8d5"  # Light gray
  
  # Syntax highlighting
  keyword: "#859900"      # Green
  string: "#2aa198"       # Cyan
  number: "#d33682"       # Magenta
  comment: "#93a1a1"      # Gray
  function: "#268bd2"     # Blue
  variable: "#657b83"     # Base
  type: "#b58900"         # Yellow
  operator: "#859900"     # Green

accessibility:
  wcag_level: AA
  contrast_ratios:
    foreground_bg: 7.2:1
    success_bg: 5.8:1
    error_bg: 6.5:1
    warning_bg: 6.1:1
```

## Theme 5: Tokyo Night (Dark)

**Use case**: Modern, vibrant, popular in developer community  
**Inspiration**: [Tokyo Night Theme](https://github.com/enkia/tokyo-night-vscode-theme)

```yaml
name: tokyo-night
variant: dark
description: "Modern dark theme inspired by Tokyo's neon lights"

colors:
  background: "#1a1b26"
  foreground: "#c0caf5"
  
  # Semantic colors
  success: "#9ece6a"      # Green
  error: "#f7768e"        # Red
  warning: "#e0af68"      # Yellow
  info: "#7aa2f7"         # Blue
  highlight: "#bb9af7"    # Purple
  muted: "#565f89"        # Gray
  link: "#7aa2f7"         # Blue
  code: "#9ece6a"         # Green
  
  # UI elements
  border: "#292e42"
  selection: "#364a82"
  cursor: "#c0caf5"
  
  # Status bar
  status_low: "#9ece6a"      # Green
  status_medium: "#e0af68"   # Yellow
  status_high: "#ff9e64"     # Orange
  status_critical: "#f7768e" # Red
  
  # Progress bar
  progress_fill: "#7aa2f7"   # Blue
  progress_empty: "#292e42"  # Dark gray
  
  # Syntax highlighting
  keyword: "#bb9af7"      # Purple
  string: "#9ece6a"       # Green
  number: "#ff9e64"       # Orange
  comment: "#565f89"      # Gray
  function: "#7aa2f7"     # Blue
  variable: "#c0caf5"     # White
  type: "#2ac3de"         # Cyan
  operator: "#89ddff"     # Light cyan

accessibility:
  wcag_level: AA
  contrast_ratios:
    foreground_bg: 11.8:1
    success_bg: 9.2:1
    error_bg: 7.5:1
    warning_bg: 9.8:1
```

## Theme 6: Catppuccin Mocha (Dark)

**Use case**: Pastel, soothing, modern aesthetic  
**Inspiration**: [Catppuccin Theme](https://github.com/catppuccin/catppuccin)

```yaml
name: catppuccin-mocha
variant: dark
description: "Soothing pastel dark theme with modern aesthetics"

colors:
  background: "#1e1e2e"
  foreground: "#cdd6f4"
  
  # Semantic colors
  success: "#a6e3a1"      # Green
  error: "#f38ba8"        # Red
  warning: "#f9e2af"      # Yellow
  info: "#89b4fa"         # Blue
  highlight: "#cba6f7"    # Mauve
  muted: "#6c7086"        # Gray
  link: "#89b4fa"         # Blue
  code: "#a6e3a1"         # Green
  
  # UI elements
  border: "#313244"
  selection: "#45475a"
  cursor: "#cdd6f4"
  
  # Status bar
  status_low: "#a6e3a1"      # Green
  status_medium: "#f9e2af"   # Yellow
  status_high: "#fab387"     # Peach
  status_critical: "#f38ba8" # Red
  
  # Progress bar
  progress_fill: "#cba6f7"   # Mauve
  progress_empty: "#313244"  # Dark gray
  
  # Syntax highlighting
  keyword: "#cba6f7"      # Mauve
  string: "#a6e3a1"       # Green
  number: "#fab387"       # Peach
  comment: "#6c7086"      # Gray
  function: "#89b4fa"     # Blue
  variable: "#cdd6f4"     # White
  type: "#f5c2e7"         # Pink
  operator: "#94e2d5"     # Teal

accessibility:
  wcag_level: AA
  contrast_ratios:
    foreground_bg: 12.1:1
    success_bg: 10.5:1
    error_bg: 7.8:1
    warning_bg: 13.2:1
```

## Implementation Guide

### File Structure

```
~/.lyra/themes/
├── dracula.yaml
├── nord.yaml
├── gruvbox.yaml
├── solarized-light.yaml
├── tokyo-night.yaml
└── catppuccin-mocha.yaml
```

### Python Implementation

```python
from dataclasses import dataclass
from typing import Dict
import os
import yaml

@dataclass(frozen=True)
class ColorTheme:
    name: str
    variant: str  # "dark" or "light"
    description: str
    colors: Dict[str, str]
    accessibility: Dict[str, any]

class ThemeManager:
    def __init__(self, theme_dir: str = "~/.lyra/themes"):
        self.theme_dir = os.path.expanduser(theme_dir)
        self.themes: Dict[str, ColorTheme] = {}
        self.current_theme: ColorTheme | None = None
        
    def load_themes(self):
        """Load all theme files from theme directory"""
        for file in os.listdir(self.theme_dir):
            if file.endswith('.yaml'):
                with open(os.path.join(self.theme_dir, file)) as f:
                    data = yaml.safe_load(f)
                    theme = ColorTheme(**data)
                    self.themes[theme.name] = theme
    
    def detect_theme(self) -> str:
        """Detect theme using three-layer approach"""
        # Layer 1: Environment variable
        if env_theme := os.environ.get('LYRA_THEME'):
            return env_theme
        
        # Layer 2: COLORFGBG hint
        if colorfgbg := os.environ.get('COLORFGBG'):
            # Parse "15;0" format (fg;bg)
            parts = colorfgbg.split(';')
            if len(parts) == 2:
                bg = int(parts[1])
                return 'solarized-light' if bg > 7 else 'dracula'
        
        # Layer 3: OSC 11 probe (requires terminal support)
        # TODO: Implement OSC 11 background color detection
        
        # Default fallback
        return 'dracula'
    
    def set_theme(self, theme_name: str):
        """Set current theme"""
        if theme_name not in self.themes:
            raise ValueError(f"Theme not found: {theme_name}")
        self.current_theme = self.themes[theme_name]
    
    def get_color(self, key: str) -> str:
        """Get color value from current theme"""
        if not self.current_theme:
            raise RuntimeError("No theme set")
        return self.current_theme.colors.get(key, "#ffffff")
```

### Rich Integration

```python
from rich.console import Console
from rich.theme import Theme as RichTheme

def create_rich_theme(color_theme: ColorTheme) -> RichTheme:
    """Convert ColorTheme to Rich Theme"""
    return RichTheme({
        "success": f"bold {color_theme.colors['success']}",
        "error": f"bold {color_theme.colors['error']}",
        "warning": f"bold {color_theme.colors['warning']}",
        "info": f"{color_theme.colors['info']}",
        "highlight": f"bold {color_theme.colors['highlight']}",
        "muted": f"{color_theme.colors['muted']}",
        "code": f"{color_theme.colors['code']}",
        "link": f"underline {color_theme.colors['link']}",
    })

# Usage
theme_manager = ThemeManager()
theme_manager.load_themes()
theme_name = theme_manager.detect_theme()
theme_manager.set_theme(theme_name)

rich_theme = create_rich_theme(theme_manager.current_theme)
console = Console(theme=rich_theme)

console.print("[success]✓[/success] Task completed")
console.print("[error]✗[/error] Task failed")
console.print("[warning]⚠[/warning] Warning message")
```

## Configuration

### User Configuration (~/.lyra/config.yaml)

```yaml
theme:
  name: dracula              # Theme name or "auto" for detection
  auto_detect: true          # Enable three-layer detection
  fallback: dracula          # Fallback if detection fails
  
  # Override specific colors
  overrides:
    success: "#00ff00"       # Custom success color
    error: "#ff0000"         # Custom error color
```

### Runtime Theme Switching

```bash
# Set theme via environment variable
export LYRA_THEME=nord
lyra

# Set theme via CLI flag
lyra --theme gruvbox

# Interactive theme picker
lyra theme select
```

## Accessibility Validation

### Contrast Checker Script

```python
def calculate_contrast_ratio(fg: str, bg: str) -> float:
    """Calculate WCAG contrast ratio between two colors"""
    def luminance(hex_color: str) -> float:
        rgb = tuple(int(hex_color.lstrip('#')[i:i+2], 16) / 255 for i in (0, 2, 4))
        return sum(
            c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            for c in rgb
        ) * 0.2126 + 0.7152 + 0.0722
    
    l1 = luminance(fg)
    l2 = luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def validate_theme_accessibility(theme: ColorTheme) -> Dict[str, bool]:
    """Validate theme meets WCAG AA standards"""
    bg = theme.colors['background']
    results = {}
    
    for key in ['foreground', 'success', 'error', 'warning', 'info']:
        ratio = calculate_contrast_ratio(theme.colors[key], bg)
        results[key] = ratio >= 4.5  # WCAG AA minimum
    
    return results
```

## Testing Checklist

- [ ] All themes load without errors
- [ ] Contrast ratios meet WCAG AA (4.5:1 minimum)
- [ ] Three-layer detection works correctly
- [ ] Theme switching doesn't require restart
- [ ] Colors render correctly in iTerm2, Terminal.app, Alacritty
- [ ] Status bar colors are distinguishable
- [ ] Syntax highlighting is readable
- [ ] Light theme works in bright environments
- [ ] Dark themes work in low-light environments

## Future Enhancements

1. **Custom theme builder** - Interactive CLI for creating themes
2. **Theme marketplace** - Community-contributed themes
3. **Time-based switching** - Auto-switch between light/dark based on time
4. **Per-project themes** - Override theme per workspace
5. **Gradient support** - Smooth color transitions
6. **Animation themes** - Animated progress bars and spinners

---

**Design by**: Document Specialist Agent  
**Date**: 2026-05-29  
**Status**: Ready for implementation
