# Terminal Color Themes Catalog

A comprehensive catalog of beautiful terminal color themes for CLI applications, with complete color palettes, design principles, and implementation guidance for Lyra.

## Table of Contents

1. [Theme Catalog](#theme-catalog)
2. [Theme Comparison](#theme-comparison)
3. [Implementation Guide](#implementation-guide)
4. [Theme System Architecture](#theme-system-architecture)
5. [Hot Reload & Live Switching](#hot-reload--live-switching)
6. [References](#references)

---

## Theme Catalog

### 1. Tokyo Night

**Philosophy**: Inspired by Tokyo's nighttime cityscape with deep indigo skies, electric blue signage, soft purple neon, and warm amber streetlights.

**Variants**: Storm (default), Night, Day

**Tokyo Night Storm**:
```json
{
  "name": "Tokyo Night Storm",
  "type": "dark",
  "colors": {
    "background": "#24283B",
    "foreground": "#A9B1D6",
    "cursor": "#C0CAF5",
    "selection": "#414868",
    "black": "#414868",
    "red": "#F7768E",
    "green": "#73DACA",
    "yellow": "#E0AF68",
    "blue": "#7AA2F7",
    "magenta": "#BB9AF7",
    "cyan": "#7DCFFF",
    "white": "#C0CAF5",
    "brightBlack": "#565F89",
    "brightRed": "#F76373",
    "brightGreen": "#87FFEC",
    "brightYellow": "#FFC776",
    "brightBlue": "#448CFF",
    "brightMagenta": "#9F6DFF",
    "brightCyan": "#4AD4FF",
    "brightWhite": "#D6DEFF"
  }
}
```

**Use Cases**: Modern development, night coding sessions, vibrant UI elements

---

### 2. Dracula

**Philosophy**: Dark theme with carefully selected colors for reduced eye strain and improved readability. Created by Zeno Rocha in 2013.

**Variants**: Dracula (dark), Alucard (light)

**Dracula Classic**:
```json
{
  "name": "Dracula",
  "type": "dark",
  "colors": {
    "background": "#282A36",
    "foreground": "#F8F8F2",
    "cursor": "#F8F8F2",
    "selection": "#44475A",
    "comment": "#6272A4",
    "black": "#21222C",
    "red": "#FF5555",
    "green": "#50FA7B",
    "yellow": "#F1FA8C",
    "blue": "#BD93F9",
    "magenta": "#FF79C6",
    "cyan": "#8BE9FD",
    "white": "#F8F8F2",
    "brightBlack": "#6272A4",
    "brightRed": "#FF6E6E",
    "brightGreen": "#69FF94",
    "brightYellow": "#FFFFA5",
    "brightBlue": "#D6ACFF",
    "brightMagenta": "#FF92DF",
    "brightCyan": "#A4FFFF",
    "brightWhite": "#FFFFFF"
  },
  "syntax": {
    "keywords": "#FF79C6",
    "functions": "#50FA7B",
    "classes": "#8BE9FD",
    "strings": "#F1FA8C",
    "numbers": "#FFB86C",
    "errors": "#FF5555"
  }
}
```

**Use Cases**: General purpose, long coding sessions, high contrast needs

---

### 3. Nord

**Philosophy**: Arctic, north-bluish color palette designed for optimal focus and beautiful, elegant appearance.

**Variants**: Nord (single palette, works for both dark and light)

**Nord Theme**:
```json
{
  "name": "Nord",
  "type": "dark",
  "colors": {
    "background": "#2E3440",
    "foreground": "#D8DEE9",
    "cursor": "#D8DEE9",
    "selection": "#434C5E",
    "black": "#3B4252",
    "red": "#BF616A",
    "green": "#A3BE8C",
    "yellow": "#EBCB8B",
    "blue": "#81A1C1",
    "magenta": "#B48EAD",
    "cyan": "#88C0D0",
    "white": "#E5E9F0",
    "brightBlack": "#4C566A",
    "brightRed": "#BF616A",
    "brightGreen": "#A3BE8C",
    "brightYellow": "#EBCB8B",
    "brightBlue": "#81A1C1",
    "brightMagenta": "#B48EAD",
    "brightCyan": "#8FBCBB",
    "brightWhite": "#ECEFF4"
  },
  "palette": {
    "polarNight": ["#2E3440", "#3B4252", "#434C5E", "#4C566A"],
    "snowStorm": ["#D8DEE9", "#E5E9F0", "#ECEFF4"],
    "frost": ["#8FBCBB", "#88C0D0", "#81A1C1", "#5E81AC"],
    "aurora": ["#BF616A", "#D08770", "#EBCB8B", "#A3BE8C", "#B48EAD"]
  }
}
```

**Use Cases**: Clean, professional environments, documentation, minimal distraction

---

### 4. Gruvbox

**Philosophy**: Retro groove color scheme with warm, earthy tones designed for long-term use without eye strain.

**Variants**: Dark (hard, medium, soft), Light (hard, medium, soft)

**Gruvbox Dark Medium**:
```json
{
  "name": "Gruvbox Dark",
  "type": "dark",
  "colors": {
    "background": "#282828",
    "foreground": "#EBDBB2",
    "cursor": "#EBDBB2",
    "selection": "#504945",
    "black": "#282828",
    "red": "#CC241D",
    "green": "#98971A",
    "yellow": "#D79921",
    "blue": "#458588",
    "magenta": "#B16286",
    "cyan": "#689D6A",
    "white": "#A89984",
    "brightBlack": "#928374",
    "brightRed": "#FB4934",
    "brightGreen": "#B8BB26",
    "brightYellow": "#FABD2F",
    "brightBlue": "#83A598",
    "brightMagenta": "#D3869B",
    "brightCyan": "#8EC07C",
    "brightWhite": "#EBDBB2"
  }
}
```

**Use Cases**: Warm, comfortable coding, retro aesthetics, reduced blue light

---

### 5. Catppuccin

**Philosophy**: Soothing pastel theme with four distinct flavors, each offering a unique aesthetic while maintaining consistency.

**Variants**: Latte (light), Frappé (dark muted), Macchiato (dark medium), Mocha (dark vibrant)

**Catppuccin Mocha**:
```json
{
  "name": "Catppuccin Mocha",
  "type": "dark",
  "colors": {
    "background": "#1E1E2E",
    "foreground": "#CDD6F4",
    "cursor": "#F5E0DC",
    "selection": "#585B70",
    "black": "#45475A",
    "red": "#F38BA8",
    "green": "#A6E3A1",
    "yellow": "#F9E2AF",
    "blue": "#89B4FA",
    "magenta": "#F5C2E7",
    "cyan": "#94E2D5",
    "white": "#BAC2DE",
    "brightBlack": "#585B70",
    "brightRed": "#F38BA8",
    "brightGreen": "#A6E3A1",
    "brightYellow": "#F9E2AF",
    "brightBlue": "#89B4FA",
    "brightMagenta": "#F5C2E7",
    "brightCyan": "#94E2D5",
    "brightWhite": "#A6ADC8"
  },
  "extended": {
    "rosewater": "#F5E0DC",
    "flamingo": "#F2CDCD",
    "pink": "#F5C2E7",
    "mauve": "#CBA6F7",
    "maroon": "#EBA0AC",
    "peach": "#FAB387",
    "teal": "#94E2D5",
    "sky": "#89DCEB",
    "sapphire": "#74C7EC",
    "lavender": "#B4BEFE"
  }
}
```

**Use Cases**: Soft, pastel aesthetics, reduced contrast, gentle on eyes

---

### 6. Solarized

**Philosophy**: Precision color scheme with scientifically calibrated CIELAB lightness relationships for optimal readability.

**Variants**: Dark, Light

**Solarized Dark**:
```json
{
  "name": "Solarized Dark",
  "type": "dark",
  "colors": {
    "background": "#002B36",
    "foreground": "#839496",
    "cursor": "#839496",
    "selection": "#073642",
    "black": "#073642",
    "red": "#DC322F",
    "green": "#859900",
    "yellow": "#B58900",
    "blue": "#268BD2",
    "magenta": "#D33682",
    "cyan": "#2AA198",
    "white": "#EEE8D5",
    "brightBlack": "#002B36",
    "brightRed": "#CB4B16",
    "brightGreen": "#586E75",
    "brightYellow": "#657B83",
    "brightBlue": "#839496",
    "brightMagenta": "#6C71C4",
    "brightCyan": "#93A1A1",
    "brightWhite": "#FDF6E3"
  }
}
```

**Use Cases**: Scientific precision, accessibility, dual light/dark workflow

---

### 7. One Dark

**Philosophy**: Atom editor's iconic dark theme with balanced colors and excellent syntax highlighting.

**Variants**: One Dark (dark), One Light (light)

**One Dark**:
```json
{
  "name": "One Dark",
  "type": "dark",
  "colors": {
    "background": "#282C34",
    "foreground": "#ABB2BF",
    "cursor": "#ABB2BF",
    "selection": "#3E4451",
    "black": "#3F4451",
    "red": "#E05561",
    "green": "#8CC265",
    "yellow": "#D18F52",
    "blue": "#4AA5F0",
    "magenta": "#C162DE",
    "cyan": "#42B3C2",
    "white": "#E6E6E6",
    "brightBlack": "#4F5666",
    "brightRed": "#FF616E",
    "brightGreen": "#A5E075",
    "brightYellow": "#F0A45D",
    "brightBlue": "#4DC4FF",
    "brightMagenta": "#DE73FF",
    "brightCyan": "#4CD1E0",
    "brightWhite": "#FFFFFF"
  }
}
```

**Use Cases**: Familiar Atom/VS Code users, balanced contrast, modern development

---

### 8. Monokai

**Philosophy**: Classic theme with vibrant colors on dark background, originally created for Sublime Text.

**Variants**: Monokai (original), Monokai Pro (refined)

**Monokai**:
```json
{
  "name": "Monokai",
  "type": "dark",
  "colors": {
    "background": "#272822",
    "foreground": "#F8F8F2",
    "cursor": "#F8F8F0",
    "selection": "#49483E",
    "black": "#272822",
    "red": "#F92672",
    "green": "#A6E22E",
    "yellow": "#F4BF75",
    "blue": "#66D9EF",
    "magenta": "#AE81FF",
    "cyan": "#A1EFE4",
    "white": "#F8F8F2",
    "brightBlack": "#75715E",
    "brightRed": "#F92672",
    "brightGreen": "#A6E22E",
    "brightYellow": "#F4BF75",
    "brightBlue": "#66D9EF",
    "brightMagenta": "#AE81FF",
    "brightCyan": "#A1EFE4",
    "brightWhite": "#F9F8F5"
  }
}
```

**Use Cases**: High contrast, vibrant colors, Sublime Text users

---

### 9. Material Theme

**Philosophy**: Google's Material Design principles applied to terminal themes with clean, modern aesthetics.

**Variants**: Material Ocean, Material Palenight, Material Darker, Material Lighter

**Material Palenight**:
```json
{
  "name": "Material Palenight",
  "type": "dark",
  "colors": {
    "background": "#292D3E",
    "foreground": "#959DCB",
    "cursor": "#FFCC00",
    "selection": "#717CB4",
    "black": "#292D3E",
    "red": "#FF5370",
    "green": "#C3E88D",
    "yellow": "#FFCB6B",
    "blue": "#82AAFF",
    "magenta": "#C792EA",
    "cyan": "#89DDFF",
    "white": "#959DCB",
    "brightBlack": "#676E95",
    "brightRed": "#FF5370",
    "brightGreen": "#C3E88D",
    "brightYellow": "#FFCB6B",
    "brightBlue": "#82AAFF",
    "brightMagenta": "#C792EA",
    "brightCyan": "#89DDFF",
    "brightWhite": "#FFFFFF"
  }
}
```

**Material Ocean**:
```json
{
  "name": "Material Ocean",
  "type": "dark",
  "colors": {
    "background": "#0F111A",
    "foreground": "#8F93A2",
    "cursor": "#FFCC00",
    "selection": "#1F2233",
    "black": "#0F111A",
    "red": "#F07178",
    "green": "#C3E88D",
    "yellow": "#FFCB6B",
    "blue": "#82AAFF",
    "magenta": "#C792EA",
    "cyan": "#89DDFF",
    "white": "#B0BEC5",
    "brightBlack": "#546E7A",
    "brightRed": "#F07178",
    "brightGreen": "#C3E88D",
    "brightYellow": "#FFCB6B",
    "brightBlue": "#82AAFF",
    "brightMagenta": "#C792EA",
    "brightCyan": "#89DDFF",
    "brightWhite": "#EEFFFF"
  }
}
```

**Use Cases**: Material Design fans, modern UI, clean aesthetics

---

### 10. Rosé Pine

**Philosophy**: All natural pine, faux fur and a bit of soho vibes for the classy minimalist.

**Variants**: Rosé Pine (main), Rosé Pine Moon, Rosé Pine Dawn (light)

**Rosé Pine Main**:
```json
{
  "name": "Rosé Pine",
  "type": "dark",
  "colors": {
    "background": "#191724",
    "foreground": "#E0DEF4",
    "cursor": "#E0DEF4",
    "selection": "#403D52",
    "black": "#26233A",
    "red": "#EB6F92",
    "green": "#31748F",
    "yellow": "#F6C177",
    "blue": "#9CCFD8",
    "magenta": "#C4A7E7",
    "cyan": "#EBBCBA",
    "white": "#E0DEF4",
    "brightBlack": "#6E6A86",
    "brightRed": "#EB6F92",
    "brightGreen": "#31748F",
    "brightYellow": "#F6C177",
    "brightBlue": "#9CCFD8",
    "brightMagenta": "#C4A7E7",
    "brightCyan": "#EBBCBA",
    "brightWhite": "#E0DEF4"
  },
  "extended": {
    "love": "#EB6F92",
    "gold": "#F6C177",
    "rose": "#EBBCBA",
    "pine": "#31748F",
    "foam": "#9CCFD8",
    "iris": "#C4A7E7"
  }
}
```

**Rosé Pine Dawn (Light)**:
```json
{
  "name": "Rosé Pine Dawn",
  "type": "light",
  "colors": {
    "background": "#FAF4ED",
    "foreground": "#575279",
    "cursor": "#575279",
    "selection": "#DFDAD9",
    "black": "#F2E9E1",
    "red": "#B4637A",
    "green": "#286983",
    "yellow": "#EA9D34",
    "blue": "#56949F",
    "magenta": "#907AA9",
    "cyan": "#D7827E",
    "white": "#575279",
    "brightBlack": "#9893A5",
    "brightRed": "#B4637A",
    "brightGreen": "#286983",
    "brightYellow": "#EA9D34",
    "brightBlue": "#56949F",
    "brightMagenta": "#907AA9",
    "brightCyan": "#D7827E",
    "brightWhite": "#575279"
  }
}
```

**Use Cases**: Elegant minimalism, soft colors, unique aesthetic

---

### 11. Everforest

**Philosophy**: Comfortable and pleasant green-based color scheme designed to be warm and soft for eye comfort.

**Variants**: Dark (hard, medium, soft), Light (hard, medium, soft)

**Everforest Dark Medium**:
```json
{
  "name": "Everforest Dark",
  "type": "dark",
  "colors": {
    "background": "#2D353B",
    "foreground": "#D3C6AA",
    "cursor": "#D3C6AA",
    "selection": "#543A48",
    "black": "#475258",
    "red": "#E67E80",
    "green": "#A7C080",
    "yellow": "#DBBC7F",
    "blue": "#7FBBB3",
    "magenta": "#D699B6",
    "cyan": "#83C092",
    "white": "#D3C6AA",
    "brightBlack": "#56635F",
    "brightRed": "#E67E80",
    "brightGreen": "#A7C080",
    "brightYellow": "#DBBC7F",
    "brightBlue": "#7FBBB3",
    "brightMagenta": "#D699B6",
    "brightCyan": "#83C092",
    "brightWhite": "#D3C6AA"
  }
}
```

**Everforest Light Medium**:
```json
{
  "name": "Everforest Light",
  "type": "light",
  "colors": {
    "background": "#FDF6E3",
    "foreground": "#5C6A72",
    "cursor": "#5C6A72",
    "selection": "#EAEDC8",
    "black": "#5C6A72",
    "red": "#F85552",
    "green": "#8DA101",
    "yellow": "#DFA000",
    "blue": "#3A94C5",
    "magenta": "#DF69BA",
    "cyan": "#35A77C",
    "white": "#F4F0D9",
    "brightBlack": "#A6B0A0",
    "brightRed": "#F85552",
    "brightGreen": "#8DA101",
    "brightYellow": "#DFA000",
    "brightBlue": "#3A94C5",
    "brightMagenta": "#DF69BA",
    "brightCyan": "#35A77C",
    "brightWhite": "#FFFBEF"
  }
}
```

**Use Cases**: Nature-inspired, warm tones, comfortable long sessions

---

### 12. Ayu

**Philosophy**: Simple, bright and elegant theme with three variants for different lighting conditions.

**Variants**: Dark, Mirage, Light

**Ayu Mirage**:
```json
{
  "name": "Ayu Mirage",
  "type": "dark",
  "colors": {
    "background": "#1F2430",
    "foreground": "#CBCCC6",
    "cursor": "#FFCC66",
    "selection": "#33415E",
    "black": "#191E2A",
    "red": "#ED8274",
    "green": "#A6CC70",
    "yellow": "#FAD07B",
    "blue": "#6DCBFA",
    "magenta": "#CFBAFA",
    "cyan": "#90E1C6",
    "white": "#C7C7C7",
    "brightBlack": "#686868",
    "brightRed": "#F28779",
    "brightGreen": "#BAE67E",
    "brightYellow": "#FFD580",
    "brightBlue": "#73D0FF",
    "brightMagenta": "#D4BFFF",
    "brightCyan": "#95E6CB",
    "brightWhite": "#FFFFFF"
  }
}
```

**Ayu Light**:
```json
{
  "name": "Ayu Light",
  "type": "light",
  "colors": {
    "background": "#FAFAFA",
    "foreground": "#5C6166",
    "cursor": "#FF6A00",
    "selection": "#F0EEE4",
    "black": "#000000",
    "red": "#F07171",
    "green": "#86B300",
    "yellow": "#F2AE49",
    "blue": "#399EE6",
    "magenta": "#A37ACC",
    "cyan": "#4CBF99",
    "white": "#FAFAFA",
    "brightBlack": "#686868",
    "brightRed": "#F07171",
    "brightGreen": "#86B300",
    "brightYellow": "#F2AE49",
    "brightBlue": "#399EE6",
    "brightMagenta": "#A37ACC",
    "brightCyan": "#4CBF99",
    "brightWhite": "#FFFFFF"
  }
}
```

**Use Cases**: Clean design, multiple lighting conditions, Sublime Text users

---

### 13. Kanagawa

**Philosophy**: Inspired by Katsushika Hokusai's "The Great Wave off Kanagawa" painting, featuring deep blues and warm accents.

**Variants**: Kanagawa (wave), Kanagawa Dragon, Kanagawa Lotus

**Kanagawa Wave**:
```json
{
  "name": "Kanagawa",
  "type": "dark",
  "colors": {
    "background": "#1F1F28",
    "foreground": "#DCD7BA",
    "cursor": "#C8C093",
    "selection": "#2D4F67",
    "black": "#090618",
    "red": "#C34043",
    "green": "#76946A",
    "yellow": "#C0A36E",
    "blue": "#7E9CD8",
    "magenta": "#957FB8",
    "cyan": "#6A9589",
    "white": "#C8C093",
    "brightBlack": "#727169",
    "brightRed": "#E82424",
    "brightGreen": "#98BB6C",
    "brightYellow": "#E6C384",
    "brightBlue": "#7FB4CA",
    "brightMagenta": "#938AA9",
    "brightCyan": "#7AA89F",
    "brightWhite": "#DCD7BA"
  }
}
```

**Use Cases**: Artistic aesthetic, Japanese-inspired, unique color harmony

---

### 14. GitHub Theme

**Philosophy**: GitHub's official color schemes matching the web interface for seamless workflow integration.

**Variants**: Dark, Dark Dimmed, Dark High Contrast, Light, Light High Contrast

**GitHub Dark**:
```json
{
  "name": "GitHub Dark",
  "type": "dark",
  "colors": {
    "background": "#0D1117",
    "foreground": "#C9D1D9",
    "cursor": "#C9D1D9",
    "selection": "#264F78",
    "black": "#484F58",
    "red": "#FF7B72",
    "green": "#3FB950",
    "yellow": "#D29922",
    "blue": "#58A6FF",
    "magenta": "#BC8CFF",
    "cyan": "#39C5CF",
    "white": "#B1BAC4",
    "brightBlack": "#6E7681",
    "brightRed": "#FFA198",
    "brightGreen": "#56D364",
    "brightYellow": "#E3B341",
    "brightBlue": "#79C0FF",
    "brightMagenta": "#D2A8FF",
    "brightCyan": "#56D4DD",
    "brightWhite": "#F0F6FC"
  }
}
```

**Use Cases**: GitHub integration, familiar interface, web-to-terminal consistency

---

### 15. Nightfox

**Philosophy**: Highly customizable theme family with multiple variants inspired by different fox species.

**Variants**: Nightfox, Dayfox, Dawnfox, Duskfox, Nordfox, Terafox, Carbonfox

**Nightfox**:
```json
{
  "name": "Nightfox",
  "type": "dark",
  "colors": {
    "background": "#192330",
    "foreground": "#CDCECF",
    "cursor": "#CDCECF",
    "selection": "#2B3B51",
    "black": "#393B44",
    "red": "#C94F6D",
    "green": "#81B29A",
    "yellow": "#DBC074",
    "blue": "#719CD6",
    "magenta": "#9D79D6",
    "cyan": "#63CDCF",
    "white": "#DFDFE0",
    "brightBlack": "#575860",
    "brightRed": "#D16983",
    "brightGreen": "#8EBAA4",
    "brightYellow": "#E0C989",
    "brightBlue": "#86ABDC",
    "brightMagenta": "#BAA1E2",
    "brightCyan": "#7AD4D6",
    "brightWhite": "#E4E4E5"
  }
}
```

**Use Cases**: Customization enthusiasts, multiple mood options, fox theme fans

---

## Theme Comparison

### By Contrast Level

| Theme | Contrast | Best For |
|-------|----------|----------|
| Dracula | High | Long sessions, clear distinction |
| Tokyo Night | Medium-High | Modern development, vibrant UI |
| Nord | Medium | Professional, minimal distraction |
| Gruvbox | Medium | Warm, comfortable coding |
| Catppuccin | Low-Medium | Soft, pastel aesthetics |
| Solarized | Scientifically Calibrated | Accessibility, dual mode |
| Rosé Pine | Low-Medium | Elegant minimalism |

### By Color Temperature

| Warm | Neutral | Cool |
|------|---------|------|
| Gruvbox | One Dark | Nord |
| Everforest | Dracula | Tokyo Night |
| Ayu Light | Monokai | Material Ocean |
| Kanagawa | GitHub | Nightfox |

### By Use Case

**Long Coding Sessions**: Gruvbox, Everforest, Nord, Solarized
**High Contrast Needs**: Dracula, Monokai, One Dark
**Soft/Pastel Preference**: Catppuccin, Rosé Pine
**Modern/Vibrant**: Tokyo Night, Material Palenight
**Professional/Clean**: Nord, GitHub, Ayu
**Artistic/Unique**: Kanagawa, Rosé Pine, Nightfox

---

## Implementation Guide

### Theme File Format

Lyra should support JSON-based theme files with the following structure:

```json
{
  "name": "Theme Name",
  "type": "dark" | "light",
  "author": "Author Name",
  "version": "1.0.0",
  "colors": {
    "background": "#RRGGBB",
    "foreground": "#RRGGBB",
    "cursor": "#RRGGBB",
    "selection": "#RRGGBB",
    "black": "#RRGGBB",
    "red": "#RRGGBB",
    "green": "#RRGGBB",
    "yellow": "#RRGGBB",
    "blue": "#RRGGBB",
    "magenta": "#RRGGBB",
    "cyan": "#RRGGBB",
    "white": "#RRGGBB",
    "brightBlack": "#RRGGBB",
    "brightRed": "#RRGGBB",
    "brightGreen": "#RRGGBB",
    "brightYellow": "#RRGGBB",
    "brightBlue": "#RRGGBB",
    "brightMagenta": "#RRGGBB",
    "brightCyan": "#RRGGBB",
    "brightWhite": "#RRGGBB"
  },
  "ui": {
    "border": "#RRGGBB",
    "highlight": "#RRGGBB",
    "error": "#RRGGBB",
    "warning": "#RRGGBB",
    "info": "#RRGGBB",
    "success": "#RRGGBB"
  },
  "syntax": {
    "keywords": "#RRGGBB",
    "functions": "#RRGGBB",
    "strings": "#RRGGBB",
    "numbers": "#RRGGBB",
    "comments": "#RRGGBB",
    "operators": "#RRGGBB"
  }
}
```

### Directory Structure

```
~/.config/lyra/themes/
├── builtin/
│   ├── tokyo-night.json
│   ├── dracula.json
│   ├── nord.json
│   ├── gruvbox-dark.json
│   ├── gruvbox-light.json
│   ├── catppuccin-mocha.json
│   ├── catppuccin-latte.json
│   ├── solarized-dark.json
│   ├── solarized-light.json
│   ├── one-dark.json
│   ├── monokai.json
│   └── ...
├── custom/
│   └── my-theme.json
└── active.json (symlink to current theme)
```

### Theme Loading System

```typescript
// theme-manager.ts
interface Theme {
  name: string;
  type: 'dark' | 'light';
  author?: string;
  version?: string;
  colors: ThemeColors;
  ui?: UIColors;
  syntax?: SyntaxColors;
}

interface ThemeColors {
  background: string;
  foreground: string;
  cursor: string;
  selection: string;
  black: string;
  red: string;
  green: string;
  yellow: string;
  blue: string;
  magenta: string;
  cyan: string;
  white: string;
  brightBlack: string;
  brightRed: string;
  brightGreen: string;
  brightYellow: string;
  brightBlue: string;
  brightMagenta: string;
  brightCyan: string;
  brightWhite: string;
}

class ThemeManager {
  private themes: Map<string, Theme> = new Map();
  private activeTheme: Theme | null = null;
  
  async loadThemes(): Promise<void> {
    // Load builtin themes
    const builtinDir = path.join(configDir, 'themes', 'builtin');
    const builtinThemes = await this.loadThemesFromDir(builtinDir);
    
    // Load custom themes
    const customDir = path.join(configDir, 'themes', 'custom');
    const customThemes = await this.loadThemesFromDir(customDir);
    
    // Merge themes (custom overrides builtin)
    for (const theme of [...builtinThemes, ...customThemes]) {
      this.themes.set(theme.name, theme);
    }
  }
  
  async setTheme(name: string): Promise<void> {
    const theme = this.themes.get(name);
    if (!theme) {
      throw new Error(`Theme not found: ${name}`);
    }
    
    this.activeTheme = theme;
    await this.applyTheme(theme);
    await this.saveActiveTheme(name);
  }
  
  private async applyTheme(theme: Theme): Promise<void> {
    // Apply ANSI colors
    this.applyANSIColors(theme.colors);
    
    // Apply UI colors
    if (theme.ui) {
      this.applyUIColors(theme.ui);
    }
    
    // Emit theme change event
    this.emit('themeChanged', theme);
  }
}
```

---

## Theme System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Theme System                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Theme      │    │   Theme      │    │   Theme      │  │
│  │   Loader     │───▶│   Manager    │───▶│   Renderer   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   File       │    │   Cache      │    │   ANSI       │  │
│  │   System     │    │   Layer      │    │   Renderer   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Theme Loader

Responsible for discovering and loading theme files:

```typescript
class ThemeLoader {
  async loadThemesFromDir(dir: string): Promise<Theme[]> {
    const files = await fs.readdir(dir);
    const themes: Theme[] = [];
    
    for (const file of files) {
      if (file.endsWith('.json')) {
        const content = await fs.readFile(path.join(dir, file), 'utf-8');
        const theme = this.parseTheme(content);
        themes.push(theme);
      }
    }
    
    return themes;
  }
  
  private parseTheme(content: string): Theme {
    const data = JSON.parse(content);
    
    // Validate theme structure
    this.validateTheme(data);
    
    return data as Theme;
  }
  
  private validateTheme(data: any): void {
    const required = ['name', 'type', 'colors'];
    for (const field of required) {
      if (!(field in data)) {
        throw new Error(`Missing required field: ${field}`);
      }
    }
    
    // Validate color format
    const colorRegex = /^#[0-9A-Fa-f]{6}$/;
    for (const [key, value] of Object.entries(data.colors)) {
      if (!colorRegex.test(value as string)) {
        throw new Error(`Invalid color format for ${key}: ${value}`);
      }
    }
  }
}
```

### Theme Cache

Improves performance by caching parsed themes:

```typescript
class ThemeCache {
  private cache: Map<string, Theme> = new Map();
  private timestamps: Map<string, number> = new Map();
  
  get(name: string): Theme | null {
    return this.cache.get(name) || null;
  }
  
  set(name: string, theme: Theme): void {
    this.cache.set(name, theme);
    this.timestamps.set(name, Date.now());
  }
  
  invalidate(name: string): void {
    this.cache.delete(name);
    this.timestamps.delete(name);
  }
  
  clear(): void {
    this.cache.clear();
    this.timestamps.clear();
  }
}
```

### ANSI Color Renderer

Applies theme colors using ANSI escape codes:

```typescript
class ANSIRenderer {
  private colorMap: Map<string, number> = new Map([
    ['black', 0],
    ['red', 1],
    ['green', 2],
    ['yellow', 3],
    ['blue', 4],
    ['magenta', 5],
    ['cyan', 6],
    ['white', 7],
  ]);
  
  applyColors(colors: ThemeColors): void {
    // Set background color
    this.setBackgroundColor(colors.background);
    
    // Set foreground color
    this.setForegroundColor(colors.foreground);
    
    // Set ANSI palette colors
    this.setPaletteColor(0, colors.black);
    this.setPaletteColor(1, colors.red);
    this.setPaletteColor(2, colors.green);
    this.setPaletteColor(3, colors.yellow);
    this.setPaletteColor(4, colors.blue);
    this.setPaletteColor(5, colors.magenta);
    this.setPaletteColor(6, colors.cyan);
    this.setPaletteColor(7, colors.white);
    this.setPaletteColor(8, colors.brightBlack);
    this.setPaletteColor(9, colors.brightRed);
    this.setPaletteColor(10, colors.brightGreen);
    this.setPaletteColor(11, colors.brightYellow);
    this.setPaletteColor(12, colors.brightBlue);
    this.setPaletteColor(13, colors.brightMagenta);
    this.setPaletteColor(14, colors.brightCyan);
    this.setPaletteColor(15, colors.brightWhite);
  }
  
  private setBackgroundColor(color: string): void {
    const rgb = this.hexToRgb(color);
    process.stdout.write(`\x1b]11;rgb:${rgb.r}/${rgb.g}/${rgb.b}\x07`);
  }
  
  private setForegroundColor(color: string): void {
    const rgb = this.hexToRgb(color);
    process.stdout.write(`\x1b]10;rgb:${rgb.r}/${rgb.g}/${rgb.b}\x07`);
  }
  
  private setPaletteColor(index: number, color: string): void {
    const rgb = this.hexToRgb(color);
    process.stdout.write(`\x1b]4;${index};rgb:${rgb.r}/${rgb.g}/${rgb.b}\x07`);
  }
  
  private hexToRgb(hex: string): { r: string; g: string; b: string } {
    const r = parseInt(hex.slice(1, 3), 16).toString(16).padStart(2, '0');
    const g = parseInt(hex.slice(3, 5), 16).toString(16).padStart(2, '0');
    const b = parseInt(hex.slice(5, 7), 16).toString(16).padStart(2, '0');
    return { r, g, b };
  }
}
```

---

## Hot Reload & Live Switching

### Theme Switching Mechanism

```typescript
class ThemeSwitcher {
  private manager: ThemeManager;
  private renderer: ANSIRenderer;
  
  async switchTheme(themeName: string): Promise<void> {
    const theme = await this.manager.getTheme(themeName);
    
    if (!theme) {
      throw new Error(`Theme not found: ${themeName}`);
    }
    
    // Apply theme immediately
    this.renderer.applyColors(theme.colors);
    
    // Update configuration
    await this.updateConfig(themeName);
    
    // Notify all active sessions
    this.notifyActiveSessions(theme);
  }
  
  private async updateConfig(themeName: string): Promise<void> {
    const configPath = path.join(configDir, 'config.json');
    const config = await this.loadConfig(configPath);
    config.theme = themeName;
    await fs.writeFile(configPath, JSON.stringify(config, null, 2));
  }
  
  private notifyActiveSessions(theme: Theme): void {
    // Send theme change signal to all active Lyra sessions
    // This allows hot reload without restarting
    process.emit('theme:changed', theme);
  }
}
```

### Live Preview System

```typescript
class ThemePreview {
  private originalTheme: Theme;
  
  async preview(themeName: string): Promise<void> {
    // Save current theme
    this.originalTheme = await this.manager.getActiveTheme();
    
    // Apply preview theme temporarily
    await this.switchTheme(themeName);
    
    // Show preview UI
    this.showPreviewUI();
  }
  
  async confirm(): Promise<void> {
    // Keep the previewed theme
    const currentTheme = await this.manager.getActiveTheme();
    await this.manager.setTheme(currentTheme.name);
    this.originalTheme = null;
  }
  
  async cancel(): Promise<void> {
    // Restore original theme
    if (this.originalTheme) {
      await this.switchTheme(this.originalTheme.name);
      this.originalTheme = null;
    }
  }
  
  private showPreviewUI(): void {
    console.log('\n╭─────────────────────────────────────╮');
    console.log('│  Theme Preview Mode                 │');
    console.log('├─────────────────────────────────────┤');
    console.log('│  Press Enter to confirm             │');
    console.log('│  Press Esc to cancel                │');
    console.log('╰─────────────────────────────────────╯\n');
    
    // Show color samples
    this.showColorSamples();
  }
  
  private showColorSamples(): void {
    const colors = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'];
    
    console.log('Normal colors:');
    for (const color of colors) {
      process.stdout.write(`\x1b[3${colors.indexOf(color)}m█████\x1b[0m `);
    }
    console.log('\n');
    
    console.log('Bright colors:');
    for (const color of colors) {
      process.stdout.write(`\x1b[9${colors.indexOf(color)}m█████\x1b[0m `);
    }
    console.log('\n');
  }
}
```

### CLI Commands

```bash
# List available themes
lyra theme list

# Show current theme
lyra theme current

# Switch theme
lyra theme set <theme-name>

# Preview theme (with confirmation)
lyra theme preview <theme-name>

# Create custom theme
lyra theme create <theme-name>

# Edit theme
lyra theme edit <theme-name>

# Export theme
lyra theme export <theme-name> --output <file>

# Import theme
lyra theme import <file>

# Show theme info
lyra theme info <theme-name>
```

### Configuration File

```json
{
  "theme": {
    "active": "tokyo-night",
    "autoDetect": true,
    "lightTheme": "catppuccin-latte",
    "darkTheme": "tokyo-night",
    "previewTimeout": 30000
  }
}
```

### Auto Theme Detection

```typescript
class ThemeAutoDetector {
  async detectSystemTheme(): Promise<'light' | 'dark'> {
    // macOS
    if (process.platform === 'darwin') {
      const result = await exec('defaults read -g AppleInterfaceStyle');
      return result.includes('Dark') ? 'dark' : 'light';
    }
    
    // Linux (GNOME)
    if (process.platform === 'linux') {
      const result = await exec('gsettings get org.gnome.desktop.interface color-scheme');
      return result.includes('dark') ? 'dark' : 'light';
    }
    
    // Windows
    if (process.platform === 'win32') {
      // Check Windows registry for theme preference
      const result = await exec('reg query HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v AppsUseLightTheme');
      return result.includes('0x0') ? 'dark' : 'light';
    }
    
    return 'dark'; // Default
  }
  
  async applyAutoTheme(): Promise<void> {
    const systemTheme = await this.detectSystemTheme();
    const config = await this.loadConfig();
    
    const themeName = systemTheme === 'dark' 
      ? config.theme.darkTheme 
      : config.theme.lightTheme;
    
    await this.manager.setTheme(themeName);
  }
  
  watchSystemTheme(): void {
    // Watch for system theme changes
    setInterval(async () => {
      const currentSystemTheme = await this.detectSystemTheme();
      const lastSystemTheme = this.lastDetectedTheme;
      
      if (currentSystemTheme !== lastSystemTheme) {
        this.lastDetectedTheme = currentSystemTheme;
        await this.applyAutoTheme();
      }
    }, 5000); // Check every 5 seconds
  }
}
```

---

## User Customization Patterns

### Custom Theme Creation

```typescript
class ThemeBuilder {
  async createTheme(name: string, baseTheme?: string): Promise<void> {
    let theme: Theme;
    
    if (baseTheme) {
      // Clone existing theme
      const base = await this.manager.getTheme(baseTheme);
      theme = JSON.parse(JSON.stringify(base));
      theme.name = name;
    } else {
      // Create from scratch
      theme = this.getDefaultTheme(name);
    }
    
    // Open in editor
    const themePath = path.join(configDir, 'themes', 'custom', `${name}.json`);
    await fs.writeFile(themePath, JSON.stringify(theme, null, 2));
    
    // Launch editor
    await this.openInEditor(themePath);
  }
  
  private getDefaultTheme(name: string): Theme {
    return {
      name,
      type: 'dark',
      author: 'User',
      version: '1.0.0',
      colors: {
        background: '#1E1E1E',
        foreground: '#D4D4D4',
        cursor: '#D4D4D4',
        selection: '#264F78',
        black: '#000000',
        red: '#CD3131',
        green: '#0DBC79',
        yellow: '#E5E510',
        blue: '#2472C8',
        magenta: '#BC3FBC',
        cyan: '#11A8CD',
        white: '#E5E5E5',
        brightBlack: '#666666',
        brightRed: '#F14C4C',
        brightGreen: '#23D18B',
        brightYellow: '#F5F543',
        brightBlue: '#3B8EEA',
        brightMagenta: '#D670D6',
        brightCyan: '#29B8DB',
        brightWhite: '#FFFFFF'
      }
    };
  }
}
```

### Theme Inheritance

```json
{
  "name": "My Custom Theme",
  "extends": "tokyo-night",
  "type": "dark",
  "colors": {
    "background": "#1A1B26",
    "red": "#FF0000"
  }
}
```

```typescript
class ThemeInheritance {
  async resolveTheme(theme: Theme): Promise<Theme> {
    if (!theme.extends) {
      return theme;
    }
    
    const baseTheme = await this.manager.getTheme(theme.extends);
    if (!baseTheme) {
      throw new Error(`Base theme not found: ${theme.extends}`);
    }
    
    // Merge themes (child overrides parent)
    return {
      ...baseTheme,
      ...theme,
      colors: {
        ...baseTheme.colors,
        ...theme.colors
      },
      ui: {
        ...baseTheme.ui,
        ...theme.ui
      },
      syntax: {
        ...baseTheme.syntax,
        ...theme.syntax
      }
    };
  }
}
```

### Theme Variables

Support for dynamic color generation:

```json
{
  "name": "Dynamic Theme",
  "type": "dark",
  "variables": {
    "primary": "#7AA2F7",
    "secondary": "#BB9AF7",
    "background": "#1A1B26"
  },
  "colors": {
    "background": "$background",
    "foreground": "$primary",
    "blue": "$primary",
    "magenta": "$secondary",
    "selection": "lighten($background, 10%)",
    "cursor": "brighten($primary, 20%)"
  }
}
```

---

## Recommendations for Lyra

### Default Theme Selection

**Recommended defaults**:
1. **Dark**: Tokyo Night Storm (modern, vibrant, popular)
2. **Light**: Catppuccin Latte (soft, pleasant, easy on eyes)
3. **Alternative Dark**: Nord (professional, minimal)
4. **Alternative Light**: Rosé Pine Dawn (elegant, unique)

### Bundled Themes

Include these 12 themes by default:
1. Tokyo Night (Storm, Night, Day)
2. Dracula
3. Nord
4. Gruvbox (Dark, Light)
5. Catppuccin (Mocha, Latte)
6. One Dark
7. Solarized (Dark, Light)
8. Material Palenight

### Theme System Features

**Must-have**:
- JSON-based theme files
- Hot reload/live switching
- Theme preview with confirmation
- Auto theme detection (system preference)
- Custom theme creation
- Theme inheritance

**Nice-to-have**:
- Theme variables and color functions
- Theme marketplace/repository
- Theme export/import
- Theme validation and linting
- Color contrast checker
- Accessibility mode

---

## References

### Sources

- [Tokyo Night Theme](https://github.com/tokyo-night/tokyo-night-vscode-theme)
- [Dracula Theme Specification](https://draculatheme.com/spec)
- [Nord Theme Documentation](https://www.nordtheme.com/docs/colors-and-palettes/)
- [Gruvbox Color Guide](https://github.com/vanzsh/gruvbox-color-guide)
- [Catppuccin Palette](https://catppuccin.com/palette)
- [Solarized Official Site](https://ethanschoonover.com/solarized/)
- [Rosé Pine Theme](https://rosepinetheme.com/palette/ingredients/)
- [Everforest Palette](https://github.com/sainnhe/everforest/blob/master/palette.md)
- [Material Theme Documentation](https://material-theme.com/docs/reference/color-palette/)
- [One Dark Terminal](https://github.com/nathanbuchar/atom-one-dark-terminal)
- [Monokai Terminal Colors](https://github.com/stephenway/monokai.terminal)
- [Ayu Theme](https://github.com/dempfi/ayu)
- [Kanagawa Theme](https://github.com/rebelot/kanagawa.nvim)
- [Nightfox Theme](https://github.com/edeneast/nightfox.nvim)
- [GitHub Theme](https://brand.github.com/foundations/color)

### Tools & Resources

- [Terminal Colors](https://terminalcolors.com/) - Theme downloads for multiple terminals
- [AnsiColor](https://ansicolor.com/) - ANSI palette picker
- [Gogh](https://github.com/Gogh-Co/Gogh) - Terminal color scheme collection
- [Shellshade](https://github.com/Contra-Collective/shellshade) - Cross-platform theme manager
- [ANSI Escape Codes Reference](https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797)

### Implementation References

- [Windows Terminal Themes](https://learn.microsoft.com/en-us/windows/terminal/customize-settings/themes)
- [iTerm2 Color Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes)
- [Alacritty Themes](https://github.com/alacritty/alacritty-theme)
- [Kitty Themes](https://github.com/dexpota/kitty-themes)

---

**Document Version**: 1.0.0  
**Last Updated**: 2026-05-26  
**Author**: Research Agent (a18ad6fd973438320)
