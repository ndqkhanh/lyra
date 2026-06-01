# 06. Brand Identity - Lyra UI/UX Plan

**Version**: 1.0  
**Status**: ✅ Complete  
**Last Updated**: 2026-05-21

---

## Overview

This document defines Lyra's brand identity, visual language, and personality. It ensures consistent brand expression across all touchpoints and creates a memorable, distinctive experience.

---

## Brand Essence

### Brand Name: Lyra

**Origin**: Named after the constellation Lyra, home to Vega, one of the brightest stars in the night sky.

**Symbolism**:
- ✨ **Brightness**: Illuminating the path forward
- 🎵 **Harmony**: The lyre (musical instrument) represents harmony between human and AI
- 🌟 **Guidance**: Like a star, Lyra guides developers through complex tasks
- 🚀 **Aspiration**: Reaching for the stars, pushing boundaries

### Brand Promise

**"Illuminate Your Development"**

Lyra brings clarity to complex development tasks, guiding you with intelligence and precision.

---

## Brand Personality

### Core Traits

**1. Intelligent** 🧠
- Knowledgeable and capable
- Understands context deeply
- Makes smart decisions
- Learns and improves

**2. Reliable** 🛡️
- Consistent and dependable
- Safe and secure
- Transparent about limitations
- Honest about capabilities

**3. Efficient** ⚡
- Fast and responsive
- Focused on results
- No wasted effort
- Streamlined workflows

**4. Friendly** 😊
- Approachable and warm
- Helpful, not condescending
- Supportive, not patronizing
- Professional but personable

**5. Innovative** 🚀
- Cutting-edge technology
- Forward-thinking
- Continuously evolving
- Pushing boundaries

### Voice and Tone

**Voice** (Consistent across all contexts):
- Clear and direct
- Professional but approachable
- Confident but humble
- Technical but accessible

**Tone** (Adapts to context):

| Context | Tone | Example |
|---------|------|---------|
| Success | Encouraging | "✅ Done! Your tests are passing." |
| Error | Supportive | "⚠️ File not found. Let me help you locate it." |
| Warning | Cautious | "⚠️ This will delete 50 files. Continue?" |
| Info | Informative | "ℹ️ Reading 3 files (2.4 KB total)" |
| Progress | Motivating | "🔄 Almost there... 80% complete" |

---

## Visual Identity

### Logo and Icon

**Primary Logo**:
```
🌟 Lyra
```

**Icon Only**:
```
🌟
```

**ASCII Logo** (for terminals without emoji):
```
 _
| |   _   _ _ __ __ _
| |  | | | | '__/ _` |
| |__| |_| | | | (_| |
|_____\__, |_|  \__,_|
      |___/
```

**Usage Guidelines**:
- Use 🌟 emoji in modern terminals
- Use ASCII logo in limited terminals
- Always pair with "Lyra" text
- Maintain clear space around logo

### Color Palette

**Primary Colors**:

```python
# Vega Gold (Primary Brand Color)
PRIMARY = "#FACC15"      # Bright, warm gold
PRIMARY_DARK = "#CA8A04" # Darker gold for contrast
PRIMARY_LIGHT = "#FDE68A" # Light gold for highlights

# Plum Purple (Accent Color)
ACCENT = "#C084FC"       # Vibrant purple
ACCENT_DARK = "#9333EA"  # Deep purple
ACCENT_LIGHT = "#E9D5FF" # Soft purple
```

**Semantic Colors** (Catppuccin Mocha):

```python
# Base Colors
BASE = "#1e1e2e"         # Background
SURFACE = "#313244"      # Elevated surfaces
OVERLAY = "#45475a"      # Overlays
TEXT = "#cdd6f4"         # Primary text
SUBTEXT = "#a6adc8"      # Secondary text
MUTED = "#6c7086"        # Muted text

# Status Colors
SUCCESS = "#a6e3a1"      # Green - success, completion
WARNING = "#f9e2af"      # Yellow - warnings, caution
ERROR = "#f38ba8"        # Red - errors, failures
INFO = "#89b4fa"         # Blue - information, neutral
```

**Usage Guidelines**:
- Primary (Vega Gold): Brand elements, highlights, CTAs
- Accent (Plum Purple): Secondary actions, decorative elements
- Semantic: Status indicators, feedback, UI states
- Base: Backgrounds, surfaces, text

### Typography

**Font Family**:
```python
FONT_FAMILY = [
    "JetBrains Mono",    # Primary (best for code)
    "Fira Code",         # Fallback 1
    "Cascadia Code",     # Fallback 2
    "SF Mono",           # Fallback 3 (macOS)
    "Consolas",          # Fallback 4 (Windows)
    "monospace"          # System fallback
]
```

**Type Scale**:
```python
# Font Sizes (in terminal rows/columns)
TITLE = 24      # Large headers
H1 = 20         # Section headers
H2 = 16         # Subsection headers
BODY = 14       # Default text
SMALL = 12      # Secondary text
TINY = 10       # Metadata, timestamps
```

**Font Weights**:
```python
REGULAR = 400   # Body text
MEDIUM = 500    # Emphasis
BOLD = 700      # Headers, strong emphasis
```

**Usage Guidelines**:
- Use monospace fonts for consistency
- Prefer JetBrains Mono for best readability
- Use bold for headers and emphasis
- Use regular weight for body text

### Iconography

**Icon Style**: Emoji + Unicode

**Primary Icons**:
```python
# Brand
LOGO = "🌟"              # Lyra logo
STAR = "⭐"              # Highlight, favorite

# Status
SUCCESS = "✅"           # Success, completion
ERROR = "❌"             # Error, failure
WARNING = "⚠️"           # Warning, caution
INFO = "ℹ️"              # Information
LOADING = "⏳"           # Loading, waiting
PROGRESS = "🔄"          # In progress

# Actions
SEARCH = "🔍"            # Search
EDIT = "✏️"              # Edit
DELETE = "🗑️"            # Delete
SAVE = "💾"              # Save
COPY = "📋"              # Copy

# Entities
USER = "👤"              # User
AGENT = "🤖"             # AI agent
FILE = "📄"              # File
FOLDER = "📁"            # Folder
CODE = "💻"              # Code
MEMORY = "🧠"            # Memory
SKILL = "🔧"             # Skill
TOOL = "🛠️"              # Tool

# Communication
CHAT = "💬"              # Chat mode
GOAL = "🎯"              # Goal mode
MESSAGE = "💌"           # Message
NOTIFICATION = "🔔"      # Notification

# Navigation
BACK = "←"               # Back
FORWARD = "→"            # Forward
UP = "↑"                 # Up
DOWN = "↓"               # Down
```

**Usage Guidelines**:
- Use emoji for visual appeal in modern terminals
- Provide text alternatives for accessibility
- Use Unicode symbols for basic shapes
- Maintain consistent icon usage

### Box Drawing Characters

**Border Styles**:
```python
# Rounded Corners (Primary)
TOP_LEFT = "╭"
TOP_RIGHT = "╮"
BOTTOM_LEFT = "╰"
BOTTOM_RIGHT = "╯"
HORIZONTAL = "─"
VERTICAL = "│"

# Sharp Corners (Secondary)
TOP_LEFT_SHARP = "┌"
TOP_RIGHT_SHARP = "┐"
BOTTOM_LEFT_SHARP = "└"
BOTTOM_RIGHT_SHARP = "┘"

# Heavy Borders (Emphasis)
TOP_LEFT_HEAVY = "┏"
TOP_RIGHT_HEAVY = "┓"
BOTTOM_LEFT_HEAVY = "┗"
BOTTOM_RIGHT_HEAVY = "┛"
HORIZONTAL_HEAVY = "━"
VERTICAL_HEAVY = "┃"

# Connectors
T_DOWN = "┬"
T_UP = "┴"
T_RIGHT = "├"
T_LEFT = "┤"
CROSS = "┼"
```

**Usage Guidelines**:
- Use rounded corners for primary panels (friendly)
- Use sharp corners for secondary panels (technical)
- Use heavy borders for emphasis (important)
- Maintain consistent border style within views

---

## Brand Applications

### Header Design

**Primary Header**:
```
╭─────────────────────────────────────────────────────────────╮
│ 🌟 Lyra v3.14.0                              💬 Chat Mode │
╰─────────────────────────────────────────────────────────────╯
```

**Components**:
- Logo (🌟) + Brand name (Lyra)
- Version number (v3.14.0)
- Current mode icon + text
- Vega Gold accent color for logo

### Message Bubbles

**User Message**:
```
┌─ 👤 You ───────────────────────────────────────────────────┐
│ Fix the authentication bug in src/auth.py                  │
└─────────────────────────────────────────────────────────────┘
```
- Blue border (INFO color)
- User icon (👤)
- Clear attribution

**Assistant Message**:
```
┌─ 🤖 Assistant ──────────────────────────────────────────────┐
│ I'll analyze and fix the authentication bug.               │
└─────────────────────────────────────────────────────────────┘
```
- Green border (SUCCESS color)
- Agent icon (🤖)
- Friendly, helpful tone

**System Message**:
```
┌─ ⚙️ System ─────────────────────────────────────────────────┐
│ Goal mode activated. Budget: $5.00, Time: 10 minutes       │
└─────────────────────────────────────────────────────────────┘
```
- Yellow border (WARNING color)
- System icon (⚙️)
- Informative, neutral tone

### Status Indicators

**Success**:
```
✅ Done! Tests are passing.
```
- Green checkmark
- Positive, encouraging message
- Brief and clear

**Error**:
```
❌ Error: File not found
   Path: src/auth.py
   Suggestion: Check the file path
```
- Red X
- Clear error description
- Helpful suggestion

**Warning**:
```
⚠️ Warning: Approaching budget limit (80% used)
```
- Yellow warning triangle
- Cautionary message
- Actionable information

**Info**:
```
ℹ️ Reading 3 files (2.4 KB total)
```
- Blue info icon
- Neutral, informative
- Concise details

### Progress Indicators

**Spinner**:
```
⠋ Processing request...
```
- Animated spinner
- Action description
- Vega Gold color

**Progress Bar**:
```
[████████████████░░░░░░░░░░░░░░░░░░░░] 40%
```
- Filled portion in Vega Gold
- Empty portion in muted gray
- Percentage indicator

**Step Progress**:
```
Step 3 of 7: Analyzing code
```
- Current step highlighted
- Total steps shown
- Clear progress indication

---

## Brand Messaging

### Taglines

**Primary Tagline**:
> "Illuminate Your Development"

**Secondary Taglines**:
> "Your AI Development Partner"
> "Intelligent. Reliable. Efficient."
> "Code with Confidence"

### Value Propositions

**For Individual Developers**:
> "Lyra accelerates your development workflow with intelligent assistance, letting you focus on what matters: building great software."

**For Teams**:
> "Empower your team with AI-powered development tools that enhance productivity, maintain code quality, and reduce time-to-market."

**For Open Source**:
> "Join the community building the most advanced open-source AI development assistant. Transparent, extensible, and community-driven."

### Key Messages

**Intelligence**:
> "Lyra understands your codebase, learns from your patterns, and provides contextually relevant assistance."

**Reliability**:
> "Built with safety and transparency in mind. Lyra is honest about its capabilities and limitations."

**Efficiency**:
> "From simple edits to complex refactoring, Lyra streamlines your workflow and saves you time."

**Community**:
> "Open-source and community-driven. Contribute, extend, and shape the future of AI-assisted development."

---

## Brand Guidelines

### Do's

✅ **Do**:
- Use Vega Gold (#FACC15) for brand elements
- Use emoji icons in modern terminals
- Maintain friendly, professional tone
- Be clear and concise
- Provide helpful suggestions
- Show progress and status
- Use consistent terminology
- Support accessibility

### Don'ts

❌ **Don't**:
- Use off-brand colors for primary elements
- Overuse animations or decorations
- Be condescending or patronizing
- Use jargon without explanation
- Hide errors or limitations
- Overwhelm with information
- Change terminology inconsistently
- Ignore accessibility needs

### Tone Examples

**Good Examples**:
```
✅ "Done! Your tests are passing."
✅ "I found 3 potential issues. Let me show you."
✅ "This will delete 50 files. Want to proceed?"
✅ "I'm analyzing your code. This may take a moment."
```

**Bad Examples**:
```
❌ "Operation completed successfully with no errors detected."
❌ "Obviously, you need to fix these issues first."
❌ "Deleting files..."
❌ "Please wait while the system processes your request."
```

---

## Brand Touchpoints

### 1. CLI Interface

**Primary Brand Expression**:
- Header with logo and brand name
- Vega Gold accents
- Friendly, helpful messages
- Clear status indicators

**Brand Elements**:
- 🌟 Logo in header
- Vega Gold for highlights
- Consistent typography
- Emoji icons

### 2. Documentation

**Brand Expression**:
- Clear, accessible writing
- Helpful examples
- Visual consistency
- Professional but friendly

**Brand Elements**:
- Lyra logo on pages
- Code examples with syntax highlighting
- Consistent formatting
- Helpful tips and notes

### 3. GitHub Repository

**Brand Expression**:
- Professional README
- Clear contribution guidelines
- Welcoming community
- Transparent roadmap

**Brand Elements**:
- Lyra logo in README
- Consistent formatting
- Helpful issue templates
- Clear documentation

### 4. Community

**Brand Expression**:
- Welcoming and inclusive
- Helpful and supportive
- Transparent and honest
- Collaborative and open

**Brand Elements**:
- Consistent messaging
- Professional communication
- Helpful responses
- Community guidelines

---

## Brand Evolution

### Current State (v3.x)

**Strengths**:
- ✅ Functional and reliable
- ✅ Good tool coverage
- ✅ Active development

**Opportunities**:
- ⚠️ Visual identity needs refinement
- ⚠️ Brand personality not fully expressed
- ⚠️ Inconsistent messaging

### Target State (v4.0)

**Goals**:
- ✅ Strong, distinctive visual identity
- ✅ Consistent brand personality
- ✅ Clear, unified messaging
- ✅ Memorable user experience

**Improvements**:
- Implement Vega Gold color scheme
- Consistent emoji icon usage
- Refined typography
- Polished UI components
- Clear brand voice

---

## Brand Assets

### Logo Variations

**Full Logo**:
```
🌟 Lyra
```

**Logo + Tagline**:
```
🌟 Lyra
Illuminate Your Development
```

**ASCII Logo**:
```
 _
| |   _   _ _ __ __ _
| |  | | | | '__/ _` |
| |__| |_| | | | (_| |
|_____\__, |_|  \__,_|
      |___/
```

**Minimal**:
```
🌟
```

### Color Swatches

```python
# Primary Palette
VEGA_GOLD = "#FACC15"
PLUM_PURPLE = "#C084FC"

# Catppuccin Mocha Base
MOCHA_BASE = "#1e1e2e"
MOCHA_TEXT = "#cdd6f4"

# Semantic Colors
SUCCESS_GREEN = "#a6e3a1"
WARNING_YELLOW = "#f9e2af"
ERROR_RED = "#f38ba8"
INFO_BLUE = "#89b4fa"
```

### Typography Samples

```
Title (24px):     Lyra - Illuminate Your Development
Heading 1 (20px): Getting Started with Lyra
Heading 2 (16px): Installation
Body (14px):      Lyra is an AI-powered development assistant...
Small (12px):     Version 3.14.0 | Last updated: 2 hours ago
Tiny (10px):      © 2026 Lyra Project
```

### Icon Set

```
🌟 ⭐ ✅ ❌ ⚠️ ℹ️ ⏳ 🔄 🔍 ✏️ 🗑️ 💾 📋
👤 🤖 📄 📁 💻 🧠 🔧 🛠️ 💬 🎯 💌 🔔
← → ↑ ↓ ▶ ▼ ○ ● ◐ ◑ □ ■ ◆ ◇
```

---

## Brand Checklist

### Visual Identity
- ✅ Logo defined (🌟 Lyra)
- ✅ Color palette established (Vega Gold + Catppuccin Mocha)
- ✅ Typography system defined (JetBrains Mono)
- ✅ Icon set created (Emoji + Unicode)
- ✅ Box drawing characters specified

### Brand Personality
- ✅ Core traits defined (Intelligent, Reliable, Efficient, Friendly, Innovative)
- ✅ Voice and tone guidelines established
- ✅ Messaging framework created
- ✅ Do's and don'ts documented

### Brand Applications
- ✅ Header design specified
- ✅ Message bubble styles defined
- ✅ Status indicators designed
- ✅ Progress indicators created

### Brand Touchpoints
- ✅ CLI interface guidelines
- ✅ Documentation standards
- ✅ GitHub repository guidelines
- ✅ Community guidelines

---

## Summary

This brand identity provides:
- ✅ Clear brand essence (Lyra = Illuminate Your Development)
- ✅ Distinctive personality (Intelligent, Reliable, Efficient, Friendly, Innovative)
- ✅ Comprehensive visual identity (Vega Gold + Catppuccin Mocha)
- ✅ Consistent voice and tone guidelines
- ✅ Complete brand asset library
- ✅ Application guidelines for all touchpoints

**Key Elements**:
- 🌟 Logo: Star emoji representing Vega
- 🎨 Colors: Vega Gold (#FACC15) + Plum Purple (#C084FC)
- 🔤 Typography: JetBrains Mono
- 😊 Personality: Professional but friendly
- 💬 Voice: Clear, direct, helpful

**Next**: See 08-TESTING_VALIDATION.md for testing and validation strategies.
