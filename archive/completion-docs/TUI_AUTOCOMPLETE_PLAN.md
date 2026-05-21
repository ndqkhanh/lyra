# Lyra TUI Autocomplete Implementation Plan

## Executive Summary

**Current Status:**
- ✅ **Lyra REPL** - World-class autocomplete (on par with Claude Code)
- ❌ **Lyra TUI v2** - NO autocomplete (critical gap)

**Root Cause:** Textual's TextArea doesn't support suggesters natively

**Solution:** Implement custom dropdown widgets and command palette

---

## Gap Analysis

### Lyra REPL (prompt_toolkit) ✅

**Features:**
- ✅ Slash command dropdown with descriptions
- ✅ Ghost-text suggestions (history + registry)
- ✅ File path completion (`@file`)
- ✅ Skill completion (`#skill`)
- ✅ Subcommand completion
- ✅ Command palette (`Ctrl-K`)
- ✅ Argument completion

**Implementation:**
- `SlashCompleter` - Full-featured completer
- `CommandAutoSuggest` - Ghost-text preview
- `CommandPalette` - Fuzzy search modal
- 8-row dropdown menu
- Accept with `→` or `Ctrl-E`

### Lyra TUI v2 (Textual) ❌

**Current:**
- ❌ NO inline autocomplete
- ❌ NO slash command dropdown
- ❌ NO ghost-text suggestions
- ❌ NO file path completion
- ❌ NO command palette
- ✅ Modal pickers (separate screens)

**Implementation:**
- Plain `TextArea` widget
- No suggester attached
- Modal pickers only (Alt+P for models)

---

## Implementation Roadmap

### Phase 1: Command Palette (Week 1) - QUICK WIN

**Priority:** CRITICAL
**Effort:** 2-3 days
**Impact:** HIGH (discoverability)

**Tasks:**
1. Create `CommandPaletteModal` extending `LyraPickerModal`
2. Port fuzzy filter logic from REPL
3. Bind to `Ctrl-K` in app
4. Show all slash commands with descriptions
5. Test keyboard navigation

**Code:**
```python
# tui_v2/modals/command_palette.py
from ..modals.base import LyraPickerModal, Entry
from lyra_cli.interactive.command_palette import fuzzy_filter

class CommandPaletteModal(LyraPickerModal):
    picker_title = "Command Palette"
    
    def entries(self) -> list[Entry]:
        return [
            Entry(
                key=spec.name,
                label=f"/{spec.name}",
                description=spec.description,
                meta={"category": spec.category}
            )
            for spec in COMMAND_REGISTRY
        ]
```

**Acceptance Criteria:**
- [ ] `Ctrl-K` opens command palette
- [ ] Fuzzy search works
- [ ] Shows command descriptions
- [ ] Enter inserts command into composer
- [ ] Esc closes palette

---

### Phase 2: Slash Command Dropdown (Weeks 2-3) - CORE FEATURE

**Priority:** CRITICAL
**Effort:** 1-2 weeks
**Impact:** CRITICAL (core UX)

**Tasks:**
1. Create `SlashDropdown` widget
2. Position below Composer cursor
3. Trigger on `/` character
4. Implement fuzzy matching
5. Handle keyboard navigation (↑↓ Enter Esc)
6. Integrate with Composer key events
7. Show command descriptions
8. Auto-hide when not needed

**Code:**
```python
# tui_v2/widgets/slash_dropdown.py
from textual.widgets import ListView, ListItem, Static
from textual.containers import Vertical

class SlashDropdown(Vertical):
    DEFAULT_CSS = """
    SlashDropdown {
        height: auto;
        max-height: 8;
        background: $surface;
        border: tall $primary;
        layer: overlay;
    }
    """
    
    def __init__(self, commands: list[dict]):
        super().__init__()
        self.commands = commands
        
    def compose(self):
        items = []
        for cmd in self.commands:
            label = f"/{cmd['name']}"
            desc = cmd.get('description', '')
            items.append(
                ListItem(Static(f"{label} - {desc}"))
            )
        yield ListView(*items)
    
    def filter(self, query: str):
        # Fuzzy filter commands
        pass
```

**Composer Integration:**
```python
# Extend Composer to show dropdown
class ComposerWithAutocomplete(Composer):
    def __init__(self):
        super().__init__()
        self.dropdown = None
        
    async def _on_key(self, event):
        await super()._on_key(event)
        
        text = self.text
        cursor_pos = self.cursor_position
        
        # Check for slash trigger
        if self._should_show_slash_dropdown(text, cursor_pos):
            await self._show_slash_dropdown()
        elif self.dropdown and self.dropdown.is_mounted:
            await self._update_or_hide_dropdown()
    
    def _should_show_slash_dropdown(self, text, cursor_pos):
        # Check if cursor is after '/' at start of line or after space
        line_start = text.rfind('\n', 0, cursor_pos) + 1
        line_text = text[line_start:cursor_pos]
        return line_text.strip().startswith('/')
```

**Acceptance Criteria:**
- [ ] Dropdown appears when typing `/`
- [ ] Shows matching commands as you type
- [ ] ↑↓ navigate, Enter selects
- [ ] Esc closes dropdown
- [ ] Auto-completes command name
- [ ] Shows descriptions
- [ ] Positioned correctly below cursor

---

### Phase 3: File Path Completion (Week 4) - HIGH VALUE

**Priority:** HIGH
**Effort:** 3-4 days
**Impact:** HIGH (file mentions)

**Tasks:**
1. Create `FileDropdown` widget
2. Trigger on `@` character
3. Reuse `_walk_repo` from REPL
4. Add fuzzy filtering
5. Show file paths with icons
6. Handle large repos (lazy loading)

**Code:**
```python
# tui_v2/widgets/file_dropdown.py
class FileDropdown(Vertical):
    def __init__(self, repo_root: Path):
        super().__init__()
        self.repo_root = repo_root
        self.files = self._walk_repo()
    
    def _walk_repo(self) -> list[Path]:
        # Reuse logic from REPL completer
        from lyra_cli.interactive.completer import _walk_repo
        return _walk_repo(self.repo_root)
    
    def filter(self, query: str) -> list[Path]:
        # Fuzzy match file paths
        pass
```

**Acceptance Criteria:**
- [ ] Dropdown appears when typing `@`
- [ ] Shows matching file paths
- [ ] Fuzzy search works
- [ ] Handles large repos (>1000 files)
- [ ] Shows relative paths
- [ ] Enter inserts file path

---

### Phase 4: Ghost-Text Suggestions (Week 5) - POLISH

**Priority:** MEDIUM
**Effort:** 1 week
**Impact:** MEDIUM (polish)

**Tasks:**
1. Add suggestion layer to Composer
2. Render dim text overlay
3. Implement history lookup
4. Handle `→` accept key
5. Show command registry suggestions
6. Prioritize recent history

**Code:**
```python
# Add ghost text rendering
class ComposerWithGhostText(ComposerWithAutocomplete):
    def __init__(self):
        super().__init__()
        self.ghost_text = ""
        
    def render_line(self, y: int) -> Strip:
        # Render normal line
        strip = super().render_line(y)
        
        # Add ghost text if at cursor line
        if y == self.cursor_position[0] and self.ghost_text:
            # Render dim text after cursor
            pass
        
        return strip
    
    def _update_ghost_text(self):
        text = self.text
        # Look up suggestion from history + registry
        self.ghost_text = self._get_suggestion(text)
```

**Acceptance Criteria:**
- [ ] Ghost text appears as you type
- [ ] Dim grey color
- [ ] `→` accepts suggestion
- [ ] History-based suggestions
- [ ] Command registry fallback
- [ ] Updates in real-time

---

### Phase 5: Subcommand & Skill Completion (Week 6) - ENHANCED

**Priority:** MEDIUM
**Effort:** 3-4 days
**Impact:** MEDIUM (power users)

**Tasks:**
1. Subcommand completion (e.g., `/mode plan|build|run`)
2. Skill completion (`#skill`)
3. Argument completion (e.g., `/model <slug>`)
4. Context-aware suggestions

**Acceptance Criteria:**
- [ ] Subcommands complete after space
- [ ] `#` triggers skill dropdown
- [ ] Arguments complete for known commands
- [ ] Context-aware filtering

---

## Technical Architecture

### Component Diagram

```mermaid
graph TB
    COMPOSER[Composer TextArea<br/>User Input]
    
    subgraph "Autocomplete System"
        DETECTOR[Input Detector<br/>Detect triggers]
        SLASH[SlashDropdown<br/>/ commands]
        FILE[FileDropdown<br/>@ files]
        SKILL[SkillDropdown<br/># skills]
        GHOST[GhostText Layer<br/>Suggestions]
        PALETTE[CommandPalette<br/>Ctrl-K modal]
    end
    
    REGISTRY[Command Registry<br/>Slash commands]
    HISTORY[Session History<br/>Recent commands]
    REPO[Repository Files<br/>File tree]
    SKILLS[Skill Library<br/>Available skills]
    
    COMPOSER --> DETECTOR
    DETECTOR -->|/| SLASH
    DETECTOR -->|@| FILE
    DETECTOR -->|#| SKILL
    DETECTOR -->|text| GHOST
    
    SLASH --> REGISTRY
    FILE --> REPO
    SKILL --> SKILLS
    GHOST --> HISTORY
    GHOST --> REGISTRY
    
    COMPOSER -.Ctrl-K.-> PALETTE
    PALETTE --> REGISTRY
    
    style COMPOSER fill:#14532d,stroke:#4ade80,color:#fff
    style DETECTOR fill:#422006,stroke:#f97316,color:#fff
    style SLASH fill:#1e3a5f,stroke:#60a5fa,color:#fff
    style FILE fill:#3b0764,stroke:#c084fc,color:#fff
    style SKILL fill:#164e63,stroke:#22d3ee,color:#fff
    style GHOST fill:#0c4a6e,stroke:#38bdf8,color:#fff
    style PALETTE fill:#831843,stroke:#f472b6,color:#fff
```

### Key Classes

```python
# Core autocomplete system
class AutocompleteManager:
    """Manages all autocomplete dropdowns and suggestions."""
    
    def __init__(self, composer: Composer):
        self.composer = composer
        self.active_dropdown = None
        self.ghost_text = ""
        
    async def on_text_change(self, text: str, cursor_pos: int):
        """Handle text changes and show appropriate dropdown."""
        trigger = self._detect_trigger(text, cursor_pos)
        
        if trigger == '/':
            await self._show_slash_dropdown()
        elif trigger == '@':
            await self._show_file_dropdown()
        elif trigger == '#':
            await self._show_skill_dropdown()
        else:
            await self._hide_dropdown()
            self._update_ghost_text(text)
    
    def _detect_trigger(self, text: str, cursor_pos: int) -> str | None:
        """Detect autocomplete trigger character."""
        pass
```

---

## Testing Strategy

### Unit Tests
```python
def test_slash_dropdown_filtering():
    dropdown = SlashDropdown(commands)
    dropdown.filter("mod")
    assert "model" in dropdown.visible_commands
    assert "mode" in dropdown.visible_commands

def test_file_dropdown_fuzzy_match():
    dropdown = FileDropdown(repo_root)
    dropdown.filter("src/ut")
    assert "src/utils.py" in dropdown.visible_files
```

### Integration Tests
```python
async def test_composer_slash_autocomplete():
    app = LyraHarnessApp(config)
    composer = app.shell.composer
    
    # Type slash
    await composer.insert_text("/")
    assert composer.dropdown is not None
    assert composer.dropdown.is_mounted
    
    # Type more
    await composer.insert_text("mod")
    assert "model" in composer.dropdown.visible_commands
```

### E2E Tests
- Manual testing with real TUI
- Keyboard navigation testing
- Performance testing with large repos
- Comparison with REPL behavior

---

## Performance Considerations

### File Path Completion
- **Problem:** Large repos (10,000+ files)
- **Solution:** 
  - Lazy loading (load on demand)
  - Limit results to 100
  - Cache file tree
  - Background indexing

### Dropdown Rendering
- **Problem:** Lag when typing fast
- **Solution:**
  - Debounce updates (50ms)
  - Virtual scrolling for long lists
  - Async filtering

### Ghost Text
- **Problem:** Flicker on every keystroke
- **Solution:**
  - Throttle updates (100ms)
  - Cache suggestions
  - Async lookup

---

## Success Metrics

1. **Discoverability:** 80% of users find commands without `/help`
2. **Speed:** Autocomplete appears <100ms
3. **Accuracy:** Top suggestion correct >80% of time
4. **Adoption:** TUI v2 usage increases 50%
5. **Parity:** Feature set matches REPL

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| TextArea limitations | HIGH | Use overlay widgets |
| Positioning complexity | MEDIUM | Study Textual examples |
| Performance (large repos) | MEDIUM | Limit results, lazy load |
| Keyboard conflicts | LOW | Document bindings |
| Framework updates | LOW | Pin Textual version |

---

## Timeline

**Total:** 6 weeks for full feature parity

| Phase | Duration | Priority | Status |
|-------|----------|----------|--------|
| 1. Command Palette | 2-3 days | CRITICAL | 📋 Planned |
| 2. Slash Dropdown | 1-2 weeks | CRITICAL | 📋 Planned |
| 3. File Completion | 3-4 days | HIGH | 📋 Planned |
| 4. Ghost Text | 1 week | MEDIUM | 📋 Planned |
| 5. Enhanced Features | 3-4 days | MEDIUM | 📋 Planned |

---

## Next Steps

### Immediate (This Week)
1. Create `tui_v2/widgets/autocomplete/` directory
2. Implement `CommandPaletteModal`
3. Bind `Ctrl-K` in app
4. Test with existing commands

### Short-term (Next 2 Weeks)
1. Implement `SlashDropdown` widget
2. Integrate with Composer
3. Add fuzzy filtering
4. Test keyboard navigation

### Medium-term (Next Month)
1. Add file path completion
2. Implement ghost-text suggestions
3. Add subcommand completion
4. Performance optimization

---

## Conclusion

**Current State:**
- Lyra REPL has world-class autocomplete
- TUI v2 has NO autocomplete (critical gap)

**Solution:**
- Implement custom dropdown widgets
- Port REPL logic to Textual
- 6-week implementation plan

**Impact:**
- Massive UX improvement
- Feature parity with Claude Code
- Increased TUI v2 adoption

**Recommendation:** Start with Phase 1 (Command Palette) for quick win, then Phase 2 (Slash Dropdown) for core feature.
