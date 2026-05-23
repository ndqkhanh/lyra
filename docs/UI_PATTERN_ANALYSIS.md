# Claude Code UI Pattern Analysis for Lyra

## Pattern 1: Welcome Banner

### Claude Code Pattern
```
╭─── Claude Code v2.1.148 ────────────────────────────────────────────────────────
 ▐▛███▜▌   Claude Code v2.1.148
▝▜█████▛▘  Opus 4.7 (1M context) with xhigh effort · API Usage Billing
  ▘▘ ▝▝    ~/Downloads/MyCV/research/harness-engineering
```

### Key Elements
1. **Top border**: `╭─── [Title] ───...`
2. **ASCII Art**: Crab logo (left-aligned)
3. **Info lines**: Version, model, effort, billing, path
4. **Layout**: 3-4 lines, compact, informative

### Lyra Adaptation

**Lyra Symbol Options**:
- 🦅 Eagle (vision, intelligence, soaring high)
- 🎵 Lyre (musical instrument, Lyra constellation)
- ⭐ Star (Lyra constellation reference)
- 🎼 Musical notes (Lyra = Lyre)

**ASCII Art for Lyra** (Lyre/Harp):
```
  ╱╲
 ╱  ╲
╱╱╱╱╱╲
║║║║║║
╚╩╩╩╩╝
```

Or simpler:
```
╦  ╦ ╦ ╦═╗ ╔═╗
║  ╚╦╝ ╠╦╝ ╠═╣
╩═╝ ╩  ╩╚═ ╩ ╩
```

**Proposed Lyra Welcome**:
```
╭─── Lyra v0.1.0 ─────────────────────────────────────────────────────────────────
  ╦  ╦ ╦ ╦═╗ ╔═╗   Lyra v0.1.0
  ║  ╚╦╝ ╠╦╝ ╠═╣   Opus 4.7 (1M context) · xhigh effort · Anthropic API
  ╩═╝ ╩  ╩╚═ ╩ ╩   ~/Downloads/MyCV/research/harness-engineering
```

---

## Pattern 2: Model Selection Menu

### Claude Code Pattern

**Structure**:
```
──────────────────────────────────────────────────────────────────────────────────
  Select model
  [Description paragraph]

  ❯ 1. Option ✔  Description · Pricing
    2. Option    Description · Pricing
    3. Option    Description · Pricing

  ◉ Setting (default) ←/→ to adjust

  [Additional info line]

  Enter to confirm · d to set as default · Esc to cancel
──────────────────────────────────────────────────────────────────────────────────
```

**Key Elements**:
1. **Full-width dividers**: `────` (repeated to terminal width)
2. **Title**: 2-space indent, bold
3. **Description**: 2-space indent, dim, wrapped
4. **Blank line** after description
5. **Options**: 4-space indent
   - Current selection: `❯` prefix
   - Active item: `✔` suffix
   - Number + dot + name + description + pricing
6. **Settings**: `◉` for radio, `←/→` for adjustment
7. **Blank line** before footer
8. **Footer**: Action hints (Enter/d/Esc)

### Lyra Adaptation

**Multi-Provider Model Selection**:
```
──────────────────────────────────────────────────────────────────────────────────
  Select model
  Switch between models from multiple providers. Applies to this session only.

  ❯ 1. Claude Opus 4.7 ✔         Most capable · Anthropic · $5/$25 per Mtok
    2. Claude Sonnet 4.6          Best for everyday · Anthropic · $3/$15 per Mtok
    3. Claude Haiku 4.5           Fastest · Anthropic · $1/$5 per Mtok
    4. GPT-4 Turbo                OpenAI flagship · OpenAI · $10/$30 per Mtok
    5. GPT-4o                     Multimodal · OpenAI · $5/$15 per Mtok
    6. Gemini 1.5 Pro             Long context · Google · $3.50/$10.50 per Mtok

  ◉ High effort (default) ←/→ to adjust

  Enter to confirm · d to set as default · Esc to cancel
──────────────────────────────────────────────────────────────────────────────────
```

---

## Implementation Plan

### Phase 1: Welcome Banner
1. Create ASCII art for Lyra (lyre/harp)
2. Update welcome display function
3. Show: version, model, effort, provider, path
4. Use Claude Code border style

### Phase 2: Model Selection Menu
1. Create model registry with providers
2. Implement selection UI with ❯ cursor
3. Add keyboard navigation (↑/↓/Enter/Esc)
4. Support multiple providers (Anthropic, OpenAI, Google)
5. Show pricing information
6. Add effort level adjustment (←/→)

### Phase 3: Integration
1. Hook `/model` command to show menu
2. Update chat.py to use new welcome
3. Add model switching logic
4. Persist default model selection

---

## Data Structure

### Model Registry
```python
@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    description: str
    input_price: float  # per Mtok
    output_price: float  # per Mtok
    context_window: int
    capabilities: list[str]

MODELS = [
    ModelInfo(
        id="claude-opus-4-20250514",
        name="Claude Opus 4.7",
        provider="Anthropic",
        description="Most capable",
        input_price=5.0,
        output_price=25.0,
        context_window=1_000_000,
        capabilities=["thinking", "vision", "tools"]
    ),
    # ... more models
]
```

### Effort Levels
```python
EFFORT_LEVELS = [
    "low",
    "medium", 
    "high",
    "xhigh"
]
```

---

## UI Components Needed

### 1. WelcomeBanner
```python
class WelcomeBanner:
    def render(self, version: str, model: str, effort: str, 
               provider: str, path: str) -> str:
        # Render Lyra welcome banner
```

### 2. ModelSelectionMenu
```python
class ModelSelectionMenu:
    def __init__(self, models: list[ModelInfo], current: str):
        self.models = models
        self.current_index = 0
        self.effort_index = 2  # default: high
        
    def render(self) -> str:
        # Render selection menu
        
    def handle_key(self, key: str) -> str | None:
        # Handle keyboard input
        # Returns selected model ID or None
```

### 3. InteractiveMenu
```python
class InteractiveMenu:
    def show(self, menu: ModelSelectionMenu) -> str | None:
        # Show menu and handle interaction
        # Returns selected model ID or None if cancelled
```

---

## Keyboard Handling

### Navigation
- `↑` / `k`: Move up
- `↓` / `j`: Move down
- `←` / `h`: Decrease effort
- `→` / `l`: Increase effort
- `Enter`: Confirm selection
- `d`: Set as default and confirm
- `Esc` / `q`: Cancel

### Implementation
```python
def handle_key_press(key: str) -> Action:
    if key in ['↑', 'k']:
        return Action.MOVE_UP
    elif key in ['↓', 'j']:
        return Action.MOVE_DOWN
    elif key in ['←', 'h']:
        return Action.DECREASE_EFFORT
    elif key in ['→', 'l']:
        return Action.INCREASE_EFFORT
    elif key == '\r':  # Enter
        return Action.CONFIRM
    elif key == 'd':
        return Action.SET_DEFAULT
    elif key in ['\x1b', 'q']:  # Esc
        return Action.CANCEL
```

---

## Rendering Details

### Divider
```python
def render_divider(width: int) -> str:
    return "─" * width
```

### Option Line
```python
def render_option(
    index: int,
    model: ModelInfo,
    is_selected: bool,
    is_current: bool
) -> str:
    # Format: "  ❯ 1. Name ✔  Description · Provider · $X/$Y per Mtok"
    prefix = "  ❯ " if is_selected else "    "
    number = f"{index + 1}. "
    checkmark = " ✔" if is_current else ""
    
    name = f"{model.name}{checkmark}"
    desc = model.description
    provider = model.provider
    pricing = f"${model.input_price}/${model.output_price} per Mtok"
    
    # Pad name to align descriptions
    name_width = 30
    padded_name = name.ljust(name_width)
    
    return f"{prefix}{number}{padded_name}{desc} · {provider} · {pricing}"
```

### Effort Selector
```python
def render_effort_selector(current_effort: str) -> str:
    symbol = "◉"
    return f"  {symbol} {current_effort.capitalize()} effort (default) ←/→ to adjust"
```

---

## Color Scheme

Following Claude Code pattern:
- **Title**: Cyan/bold
- **Description**: Dim
- **Selected option**: Default (white)
- **Unselected option**: Dim
- **Checkmark**: Green
- **Cursor**: Yellow/bright
- **Footer**: Dim
- **Divider**: Dim/cyan

---

## Files to Create/Modify

### New Files
1. `ui/welcome_banner.py` - Welcome banner component
2. `ui/model_menu.py` - Model selection menu
3. `ui/interactive_menu.py` - Interactive menu handler
4. `cli/models.py` - Model registry and definitions

### Modified Files
1. `cli/commands/chat.py` - Use new welcome, handle /model
2. `ui/fixed_layout.py` - Add menu overlay support

---

## Next Steps

1. Implement WelcomeBanner with Lyra ASCII art
2. Create ModelInfo registry with multi-provider support
3. Implement ModelSelectionMenu with keyboard navigation
4. Integrate with /model command
5. Test interactive menu in fixed bottom layout
6. Add default model persistence

Ready to implement?
