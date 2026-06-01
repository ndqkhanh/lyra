# 01 - Design System

**Complete design foundation for Lyra's UI/UX**

---

## 🎨 Color System

### Base Theme: Catppuccin Mocha

**Background Colors**
```python
BASE = "#1e1e2e"        # Main background
MANTLE = "#181825"      # Darker background
CRUST = "#11111b"       # Darkest background
SURFACE_0 = "#313244"   # Elevated surface
SURFACE_1 = "#45475a"   # More elevated
SURFACE_2 = "#585b70"   # Highest elevation
```

**Text Colors**
```python
TEXT = "#cdd6f4"        # Primary text (high contrast)
SUBTEXT_1 = "#bac2de"   # Secondary text
SUBTEXT_0 = "#a6adc8"   # Tertiary text
OVERLAY_2 = "#9399b2"   # Muted text
OVERLAY_1 = "#7f849c"   # Very muted
OVERLAY_0 = "#6c7086"   # Disabled text
```

**Semantic Colors**
```python
# Success (Green)
GREEN = "#a6e3a1"       # Success, completed, active
GREEN_DIM = "#40a02b"   # Muted success

# Warning (Yellow)
YELLOW = "#f9e2af"      # Warning, pending, in-progress
YELLOW_DIM = "#df8e1d"  # Muted warning

# Error (Red)
RED = "#f38ba8"         # Error, failed, critical
RED_DIM = "#d20f39"     # Muted error

# Info (Blue)
BLUE = "#89b4fa"        # Info, running, neutral
BLUE_DIM = "#1e66f5"    # Muted info

# Special (Purple)
MAUVE = "#cba6f7"       # Highlights, special
MAUVE_DIM = "#8839ef"   # Muted special
```

**Brand Colors (Lyra Identity)**
```python
# Primary - Vega Gold
PRIMARY = "#FACC15"         # Main brand color
PRIMARY_HOVER = "#EAB308"   # Hover state
PRIMARY_MUTED = "#A16207"   # Muted/disabled

# Accent - Plum Purple
ACCENT = "#C084FC"          # Accent color
ACCENT_HOVER = "#A855F7"    # Hover state
ACCENT_MUTED = "#7C3AED"    # Muted/disabled
```

### Color Usage Guidelines

**Text on Background**
- Primary text: `TEXT` on `BASE` (contrast 12:1)
- Secondary text: `SUBTEXT_1` on `BASE` (contrast 8:1)
- Muted text: `OVERLAY_2` on `BASE` (contrast 4.5:1)

**Interactive Elements**
- Links: `ACCENT` (hover: `ACCENT_HOVER`)
- Buttons: `PRIMARY` background, `BASE` text
- Focus rings: `ACCENT` 2px outline

**Status Indicators**
- Success: `GREEN` icon + text
- Warning: `YELLOW` icon + text
- Error: `RED` icon + text
- Info: `BLUE` icon + text

---

## 📝 Typography

### Font Stack
```css
monospace: "JetBrains Mono", "Fira Code", "Cascadia Code", 
           "SF Mono", "Consolas", monospace
```

### Type Scale
```python
# Sizes (in terminal cells/lines)
TITLE = "24px bold"      # Major headings
H1 = "20px bold"         # Section headings
H2 = "18px bold"         # Subsection headings
H3 = "16px bold"         # Minor headings
BODY = "14px regular"    # Body text
SMALL = "12px regular"   # Small text
TINY = "10px dim"        # Metadata, timestamps
```

### Font Weights
```python
REGULAR = 400
MEDIUM = 500
SEMIBOLD = 600
BOLD = 700
```

### Line Heights
```python
TIGHT = 1.2      # Headings
NORMAL = 1.5     # Body text
RELAXED = 1.8    # Long-form content
```

---

## 📏 Spacing System

### Base Unit: 4px

```python
SPACE_0 = 0      # None
SPACE_1 = 4      # xs - Tight spacing
SPACE_2 = 8      # sm - Compact spacing
SPACE_3 = 12     # md-sm - Small spacing
SPACE_4 = 16     # md - Default spacing
SPACE_5 = 20     # md-lg - Medium spacing
SPACE_6 = 24     # lg - Large spacing
SPACE_8 = 32     # xl - Extra large
SPACE_10 = 40    # xxl - Huge spacing
SPACE_12 = 48    # xxxl - Maximum spacing
```

### Usage Guidelines
- **Component padding**: `SPACE_4` (16px)
- **Section spacing**: `SPACE_6` (24px)
- **Major sections**: `SPACE_8` (32px)
- **Inline spacing**: `SPACE_2` (8px)
- **Icon-text gap**: `SPACE_2` (8px)

---

## 🎭 Icons & Symbols

### Emoji Icons (Universal)
```python
# Status
SUCCESS = "✅"
WARNING = "⚠️"
ERROR = "❌"
INFO = "ℹ️"
PENDING = "⏳"
RUNNING = "🔄"

# Actions
SEARCH = "🔍"
EDIT = "✏️"
DELETE = "🗑️"
SAVE = "💾"
COPY = "📋"
DOWNLOAD = "⬇️"
UPLOAD = "⬆️"

# Objects
FILE = "📄"
FOLDER = "📁"
CODE = "💻"
TERMINAL = "⚡"
ROBOT = "🤖"
USER = "👤"
SETTINGS = "⚙️"
PACKAGE = "📦"

# Indicators
STAR = "⭐"
FIRE = "🔥"
ROCKET = "🚀"
SPARKLES = "✨"
TROPHY = "🏆"
TARGET = "🎯"
```

### Unicode Box Drawing
```python
# Borders
TOP_LEFT = "╭"
TOP_RIGHT = "╮"
BOTTOM_LEFT = "╰"
BOTTOM_RIGHT = "╯"
HORIZONTAL = "─"
VERTICAL = "│"

# Connectors
T_DOWN = "┬"
T_UP = "┴"
T_RIGHT = "├"
T_LEFT = "┤"
CROSS = "┼"

# Arrows
ARROW_RIGHT = "→"
ARROW_LEFT = "←"
ARROW_UP = "↑"
ARROW_DOWN = "↓"
ARROW_DOUBLE = "⇒"

# Bullets
BULLET = "•"
CIRCLE = "○"
SQUARE = "□"
DIAMOND = "◆"
TRIANGLE = "▸"
```

---

## 🎨 Component Patterns

### Box Styles

**Standard Box**
```
╭─────────────────────────╮
│ Content here            │
╰─────────────────────────╯
```

**Titled Box**
```
╭─ Title ─────────────────╮
│ Content here            │
╰─────────────────────────╯
```

**Nested Box**
```
╭─ Outer ─────────────────╮
│ ┌─ Inner ─────────────┐ │
│ │ Content             │ │
│ └─────────────────────┘ │
╰─────────────────────────╯
```

### Dividers

**Section Divider**
```
───────────────────────────────────────
```

**Subtle Divider**
```
· · · · · · · · · · · · · · · · · · ·
```

**Labeled Divider**
```
─────────── Section Name ───────────
```

---

## 📐 Layout Grid

### Terminal Width Breakpoints
```python
NARROW = 80      # Minimum supported
MEDIUM = 100     # Comfortable
WIDE = 120       # Spacious
ULTRA = 160      # Maximum
```

### Content Width
```python
MAX_CONTENT = 100    # Maximum readable width
SIDEBAR = 30         # Sidebar width
MAIN = 70            # Main content area
```

---

## 🎯 Accessibility

### Contrast Ratios (WCAG AA)
- Normal text: 4.5:1 minimum
- Large text (18px+): 3:1 minimum
- UI components: 3:1 minimum

### Focus Indicators
- 2px solid outline
- Color: `ACCENT`
- Offset: 2px

### Screen Reader Support
- Semantic HTML structure
- ARIA labels where needed
- Keyboard navigation support

---

**Next**: [02-COMPONENT_LIBRARY.md](02-COMPONENT_LIBRARY.md)
