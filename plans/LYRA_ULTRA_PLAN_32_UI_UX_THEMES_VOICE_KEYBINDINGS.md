# Lyra Ultra Plan 32: UI/UX, Color Themes, Voice System & Keybindings

**Status**: RESEARCH COMPLETE → PLANNING
**Wave**: 3 — Ultra Deep Research
**Focus**: UI/UX Upgrade — Themes, Voice, Keybindings, Interaction Design
**Timeline**: 8 Weeks (2 Phases × 4 weeks)
**Inspiration**: Claude Code Interactive Mode, Warp Terminal, tmux, cmux, Hermes Agent, iTerm2, Catppuccin, Tokyo Night, Nord, Dracula, Gruvbox

---

## Executive Summary

This plan delivers a comprehensive UI/UX upgrade covering four dimensions: (1) **12+ professionally designed color themes** with exact hex palettes for every terminal role; (2) **40+ keybindings** spanning general controls, text editing (vim mode), conversation navigation, and agent management; (3) a **configurable voice/sound effects system** with 8 event-triggered sounds and cross-platform audio support; (4) **interaction design upgrades** including block-based output, slash-command autocomplete, session checkpointing, task list overlay, context visualization, and transcript viewer.

---

## Phase 32.1: Color Theme System + Interaction Design (Weeks 1-4)

### 32.1.1 Theme Architecture

```python
class Theme:
    """Complete terminal color theme with semantic role mapping."""

    name: str
    variant: str  # dark, light, midnight
    metadata: ThemeMetadata  # author, license, source

    # Base
    background: str        # Main bg
    foreground: str        # Primary text
    cursor: str            # Cursor color
    selection: str         # Selection bg

    # Surfaces
    surface0: str          # Card backgrounds
    surface1: str          # Hover states
    surface2: str          # Inactive elements

    # Text hierarchy
    text: str              # Primary text
    subtext0: str          # Secondary text
    subtext1: str          # Less important text
    comment: str           # Comments, muted

    # Semantic colors
    accent: str            # Primary accent
    red: str               # Errors, deletions
    green: str             # Success, additions
    yellow: str            # Warnings, modifications
    blue: str              # Functions, links
    purple: str            # Keywords, constants
    cyan: str              # Types, classes
    orange: str            # Numbers, variables

    # Status bar
    status_bg: str
    status_fg: str
    status_error: str
    status_warning: str
    status_success: str
```

### 32.1.2 12 Built-in Themes with Exact Hex Palettes

**1. Catppuccin Mocha** — Warm, muted lavender. Most popular community theme.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#1E1E2E` | Surface 0 | `#313244` |
| Foreground | `#CDD6F4` | Subtext 0 | `#A6ADC8` |
| Accent (Mauve) | `#CBA6F7` | Red | `#F38BA8` |
| Green | `#A6E3A1` | Yellow | `#F9E2AF` |
| Blue | `#89B4FA` | Cyan (Teal) | `#94E2D5` |
| Orange (Peach) | `#FAB387` | Comment | `#6C7086` |

**2. Tokyo Night Storm** — Blue-tinted dark, vibrant saturated accents.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#24283B` | Selection | `#343A52` |
| Foreground | `#A9B1D6` | Comment | `#444B6A` |
| Red | `#F7768E` | Orange | `#FF9E64` |
| Yellow | `#E0AF68` | Green | `#41A6B5` |
| Cyan | `#7DCFFF` | Blue | `#7AA2F7` |
| Purple | `#BB9AF7` | Darker bg | `#1A1B26` |

**3. Nord** — Arctic, north-bluish, calm and highly readable.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background (nord0) | `#2E3440` | Surface (nord1) | `#3B4252` |
| Selection (nord2) | `#434C5E` | Comment (nord3) | `#4C566A` |
| Text (nord4) | `#D8DEE9` | Subtext (nord5) | `#E5E9F0` |
| Red (nord11) | `#BF616A` | Orange (nord12) | `#D08770` |
| Yellow (nord13) | `#EBCB8B` | Green (nord14) | `#A3BE8C` |
| Purple (nord15) | `#B48EAD` | Blue (nord9) | `#81A1C1` |
| Cyan (nord8) | `#88C0D0` | Teal (nord7) | `#8FBCBB` |

**4. Dracula** — High-contrast dark, distinctive vibrant palette.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#282A36` | Selection | `#44475A` |
| Foreground | `#F8F8F2` | Comment | `#6272A4` |
| Cyan | `#8BE9FD` | Green | `#50FA7B` |
| Orange | `#FFB86C` | Pink | `#FF79C6` |
| Purple | `#BD93F9` | Red | `#FF5555` |
| Yellow | `#F1FA8C` | Current line | `#44475A` |

**5. One Dark** — The iconic Atom editor theme.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#282C34` | Selection | `#3E4452` |
| Foreground | `#ABB2BF` | Comment | `#5C6370` |
| Red | `#E06C75` | Orange | `#D19A66` |
| Yellow | `#E5C07B` | Green | `#98C379` |
| Cyan | `#56B6C2` | Blue | `#61AFEF` |
| Purple | `#C678DD` | Line highlight | `#2C313C` |

**6. Gruvbox Dark Medium** — Retro, earthy, warm. Most comfortable for long sessions.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background (bg0) | `#282828` | Surface (bg1) | `#3C3836` |
| Selection (bg2) | `#504945` | Comment (fg3) | `#BDAE93` |
| Bright (fg0) | `#FBF1C7` | Text (fg1) | `#EBDDB2` |
| Subtext (fg2) | `#D5C4A1` | Red | `#CC241D` |
| Green | `#98971A` | Yellow | `#D79921` |
| Blue | `#458588` | Purple | `#B16286` |
| Aqua | `#689D6A` | Orange | `#D65D0E` |

**7. Selenized Dark** — Perceptually uniform (CIE Lab based).

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#1A1A2E` | Foreground | `#B9B9B9` |
| Red | `#ED4A46` | Green | `#70B433` |
| Yellow | `#DBB32D` | Blue | `#368AEB` |
| Magenta | `#EB6EB7` | Cyan | `#3FC5B7` |
| Orange | `#E67F43` | Violet | `#A580E1` |

**8. Everforest Dark** — Soft green-tinted, easy on the eyes.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#2D353B` | Foreground | `#D3C6AA` |
| Red | `#E67E80` | Green | `#A7C080` |
| Yellow | `#DBBC7F` | Blue | `#7FBBB3` |
| Purple | `#D699B6` | Aqua | `#83C092` |
| Orange | `#E69875` | Gray | `#859289` |

**9. Ayu Dark** — Warm amber/wheat tones on deep charcoal.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#0A0E14` | Foreground | `#B3B1AD` |
| Comment | `#3D424D` | Red | `#FF3333` |
| Green | `#B8CC52` | Yellow | `#E7C547` |
| Blue | `#59C2FF` | Cyan | `#95E6CB` |
| Magenta | `#D2A6FF` | Orange | `#FF8F40` |

**10. Rose Pine Moon** — Soft, warm rose-tinted dark.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#232136` | Surface | `#2A2740` |
| Overlay | `#383255` | Text | `#E0DEF4` |
| Subtle | `#908CAA` | Rose | `#EBBCBA` |
| Pine | `#31748F` | Foam | `#9CCFD8` |
| Gold | `#F6C177` | Iris | `#C4A7E7` |
| Love | `#EB6F92` | Comment | `#6E6A86` |

**11. SilkCircuit Neon** — Electric cyberpunk purple/cyan.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#0A0A0F` | Foreground | `#E0E0E0` |
| Purple | `#E135FF` | Pink | `#FF79C6` |
| Cyan | `#80FFEA` | Green | `#50FA7B` |
| Yellow | `#F1FA8C` | Orange | `#FFB86C` |

**12. Sentry Sentinel Dark** — Purple/pink professional.

| Role | Hex | Role | Hex |
|------|-----|------|-----|
| Background | `#181225` | Foreground | `#E0E0E0` |
| Keywords | `#9E86FF` | Strings | `#83DA90` |
| Functions | `#226DFC` | Types | `#FF45A8` |
| Numbers | `#FDB81B` | Comments | `#898294` |

### 32.1.3 Theme Manager

```python
class ThemeManager:
    """Load, apply, preview, and customize themes."""

    def __init__(self, themes_dir: Path):
        self.themes: dict[str, Theme] = {}
        self.active: Optional[Theme] = None
        self._load_builtin_themes(themes_dir)

    def apply(self, theme_name: str) -> ApplyResult:
        """Apply theme to all terminal components."""
        theme = self.themes.get(theme_name)
        if not theme:
            raise ThemeNotFoundError(f"Theme '{theme_name}' not found")

        self.active = theme
        self._emit_ansi_colors(theme)
        self._update_status_bar(theme)
        self._update_syntax_highlighting(theme)

        return ApplyResult(theme=theme, components_updated=[
            "terminal", "status_bar", "syntax_highlighting",
            "diff_view", "block_headers"
        ])

    def preview(self, theme_name: str) -> str:
        """Generate preview with all semantic colors rendered."""
        theme = self.themes[theme_name]
        return self._render_preview_card(theme)

    def customize(self, theme_name: str, overrides: dict[str, str]) -> Theme:
        """Create a custom variant of an existing theme."""
        base = self.themes[theme_name]
        custom = base.copy(update=overrides)
        custom.name = f"{theme_name}-custom"
        self.themes[custom.name] = custom
        return custom

    def list_themes(self) -> list[ThemePreview]:
        """List all installed themes with palette previews."""
        return [
            ThemePreview(
                name=t.name,
                variant=t.variant,
                palette=[t.background, t.foreground, t.accent,
                         t.red, t.green, t.blue, t.purple],
                is_active=(t == self.active)
            )
            for t in self.themes.values()
        ]


# CLI integration
# /theme list           — show all themes with palette previews
# /theme apply nord     — apply Nord theme
# /theme preview dracula — preview Dracula palette
# /theme customize catppuccin bg=#000000 accent=#FF0000
```

### 32.1.4 Block-Based Output Rendering

Each agent response turn is wrapped in a navigable, collapsible block with metadata.

```python
class ConversationBlock:
    """One turn of agent interaction rendered as a navigable block."""

    id: str
    timestamp: datetime
    model: str
    role: str  # user | agent | system
    content: str
    tool_calls: list[ToolCall]  # Collapsible
    metadata: BlockMetadata  # tokens, duration, cost

    def render(self, theme: Theme) -> BlockOutput:
        """Render block with header, body, collapsible tools, footer."""
        header = self._render_header(theme)
        body = self._render_body(theme)
        tools = self._render_collapsible_tools(theme)
        footer = self._render_footer(theme)
        return BlockOutput(header, body, tools, footer)

    def _render_header(self, theme: Theme) -> str:
        """Timestamp | Model | Token Count | Duration"""
        return f"{theme.comment}[{self.timestamp:%H:%M:%S}]{theme.reset} " \
               f"{theme.accent}{self.model}{theme.reset} " \
               f"{theme.subtext0}{self.metadata.tokens}T {self.metadata.duration}s{theme.reset}"
```

### 32.1.5 Status Bar

```python
class StatusBar:
    """
    Bottom status bar showing session info.
    Color-coded segments with customizable format string.
    """

    DEFAULT_FORMAT = (
        "{session_name} | {git_branch} | "
        "Context: {context_pct}% | "
        "{task_count} tasks | "
        "{model} | {time}"
    )

    def render(self, state: SessionState, theme: Theme) -> str:
        context_color = self._context_color(state.context_pct, theme)
        return (
            f"{theme.surface0} {state.session_name} {theme.reset}|"
            f" {theme.accent}{state.git_branch}{theme.reset} |"
            f" {context_color}Context: {state.context_pct}%{theme.reset} |"
            f" {state.task_count} tasks |"
            f" {theme.blue}{state.model}{theme.reset} |"
            f" {state.time:%H:%M}"
        )

    def _context_color(self, pct: float, theme: Theme) -> str:
        if pct < 40:
            return theme.green
        elif pct < 60:
            return theme.yellow
        elif pct < 80:
            return theme.orange
        else:
            return theme.red
```

### 32.1.6 Slash-Command Autocomplete

```python
class SlashCommandAutocomplete:
    """
    '/' triggers filtered command menu with fuzzy search.
    Shows: command name, description, namespace, keyboard shortcut.
    """

    def __init__(self, commands: CommandRegistry):
        self.commands = commands

    def get_suggestions(self, partial: str, limit: int = 8) -> list[Suggestion]:
        """Fuzzy match partial input against all commands."""
        if not partial.startswith("/"):
            return []

        query = partial[1:]  # Strip leading '/'
        all_commands = self.commands.get_slash_menu()

        if not query:
            # Show all commands, most-used first
            return sorted(all_commands, key=lambda c: c.usage_count, reverse=True)[:limit]

        # Fuzzy match
        scored = []
        for cmd in all_commands:
            score = self._fuzzy_score(query, cmd.name)
            if score > 0:
                scored.append((score, cmd))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [cmd for _, cmd in scored[:limit]]

    def _fuzzy_score(self, query: str, target: str) -> float:
        """Simple fuzzy matching score."""
        query = query.lower()
        target = target.lower()

        if query == target:
            return 1.0
        if target.startswith(query):
            return 0.8
        if query in target:
            return 0.5

        # Character-by-character match
        qi = 0
        for tc in target:
            if qi < len(query) and tc == query[qi]:
                qi += 1
        return qi / len(query) if qi > 0 else 0
```

---

## Phase 32.2: Voice System + Keybindings + Session Management (Weeks 5-8)

### 32.2.1 Voice/Sound Effects System

```python
class SoundSystem:
    """
    Configurable audio feedback for session events.
    Cross-platform: afplay (macOS), paplay (Linux), PowerShell (Windows).
    """

    EVENTS = {
        "session_start":      SoundEvent("startup.mp3",    "<1s", "Ascending chime"),
        "prompt_submit":      SoundEvent("submit.mp3",     "<0.3s", "Click acknowledgment"),
        "response_complete":  SoundEvent("complete.mp3",   "<1s", "Gentle completion chime"),
        "error":              SoundEvent("error.mp3",      "<0.5s", "Brief error buzz"),
        "context_compact":    SoundEvent("compact.mp3",    "<1s", "Transformation sound"),
        "long_task_done":     SoundEvent("fanfare.mp3",    "<2s", "Fanfare notification"),
        "permission_prompt":  SoundEvent("prompt.mp3",     "<0.5s", "Attention bell"),
        "tool_failure":       SoundEvent("tool_error.mp3", "<0.3s", "Soft error tone"),
    }

    def __init__(self, config: SoundConfig):
        self.config = config
        self.enabled = config.enabled
        self.volume = config.volume  # 0.0 - 1.0
        self.sound_dir = Path(config.sound_dir).expanduser()
        self.player = self._detect_player()

    def _detect_player(self) -> str:
        """Detect platform-appropriate audio player."""
        if sys.platform == "darwin":
            return "afplay"
        elif sys.platform == "linux":
            return "paplay" if shutil.which("paplay") else "aplay"
        elif sys.platform == "win32":
            return "powershell.exe"
        raise UnsupportedPlatformError(f"No audio player for {sys.platform}")

    async def play(self, event_name: str):
        """Play sound for event. Always backgrounded — never blocks."""
        if not self.enabled:
            return

        event = self.EVENTS.get(event_name)
        if not event:
            return

        sound_file = self.sound_dir / event.filename
        if not sound_file.exists():
            return

        cmd = self._build_command(sound_file)
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

    def _build_command(self, sound_file: Path) -> str:
        """Build platform-specific playback command with volume."""
        if self.player == "afplay":
            return f"afplay -v {self.volume} '{sound_file}' &"
        elif self.player == "paplay":
            return f"paplay --volume={int(self.volume * 65536)} '{sound_file}' &"
        elif self.player == "aplay":
            return f"aplay -q '{sound_file}' &"
        elif self.player == "powershell.exe":
            return (
                f'powershell.exe -c "'
                f'(New-Object Media.SoundPlayer \\"{sound_file}\\").Play();"'
            )
        return ""

    def set_event_sound(self, event_name: str, sound_file: str):
        """Customize sound for a specific event."""
        if event_name not in self.EVENTS:
            raise ValueError(f"Unknown event: {event_name}")
        self.EVENTS[event_name].filename = sound_file
```

### 32.2.2 Hook Integration

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python -m lyra.sound session_start &"}]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python -m lyra.sound response_complete &"}]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python -m lyra.sound context_compact &"}]
      }
    ],
    "PostToolUseFailure": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python -m lyra.sound tool_failure &"}]
      }
    ]
  }
}
```

### 32.2.3 Keybindings — Complete Mapping

**General Controls**

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | First press: clear input. Second press: interrupt operation |
| `Ctrl+D` | Exit session (EOF) |
| `Ctrl+L` | Redraw terminal screen |
| `Ctrl+R` | Reverse search command history |
| `Ctrl+O` | Toggle transcript viewer |
| `Ctrl+T` | Toggle task list overlay |
| `Ctrl+B` | Background current command |
| `Ctrl+G` | Open prompt in `$EDITOR` for external editing |
| `Option+P` | Switch model (cycle available models) |
| `Option+T` | Toggle extended thinking |
| `Option+O` | Toggle fast mode |
| `Shift+Tab` | Cycle permission modes (default/acceptEdits/plan/auto) |
| `Esc` | Interrupt mid-turn, stop current response |
| `Esc` `Esc` | Open rewind menu (empty input) |

**Text Editing**

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Move cursor to line start |
| `Ctrl+E` | Move cursor to line end |
| `Ctrl+K` | Delete to end of line |
| `Ctrl+U` | Delete from cursor to line start |
| `Ctrl+W` | Delete previous word |
| `Ctrl+Y` | Paste deleted text |
| `Alt+Y` | Cycle paste history (after Ctrl+Y) |
| `Alt+B` | Move cursor back one word |
| `Alt+F` | Move cursor forward one word |
| `\` + `Enter` | Quick multiline escape |
| `Option+Enter` | Multiline input |
| `Ctrl+J` | Multiline input (universal) |

**Multimodal Input**

| Input | Action |
|-------|--------|
| `/` at prompt start | Open slash-command menu with autocomplete |
| `!` at prompt start | Shell mode (passthrough to bash) |
| `@` in prompt | File path autocomplete from project |
| `Ctrl+V` / `Cmd+V` | Paste image from clipboard |

**Block/Conversation Navigation**

| Shortcut | Action |
|----------|--------|
| `Ctrl+Up` | Previous conversation block |
| `Ctrl+Down` | Next conversation block |
| `{` | Jump to previous prompt (transcript viewer) |
| `}` | Jump to next prompt (transcript viewer) |

**Agent Management**

| Shortcut | Action |
|----------|--------|
| `Shift+Down` | Cycle through active agent teammates |
| `Ctrl+X Ctrl+K` (2x) | Kill all background tasks |

**Transcript Viewer (Ctrl+O)**

| Shortcut | Action |
|----------|--------|
| `?` | Toggle keyboard shortcut help |
| `Ctrl+E` | Toggle show all content |
| `[` | Write conversation to terminal scrollback |
| `v` | Open conversation in `$VISUAL`/`$EDITOR` |
| `q` / `Ctrl+C` / `Esc` | Exit transcript viewer |

### 32.2.4 Vim Mode

```python
class VimInputMode:
    """
    Full vim keybindings for input area.
    Toggle via /vim or /config.
    """

    MODES = ["normal", "insert", "visual", "visual_line"]

    NORMAL_BINDINGS = {
        "h": "cursor_left",
        "j": "cursor_down",
        "k": "cursor_up",
        "l": "cursor_right",
        "w": "next_word_start",
        "b": "prev_word_start",
        "e": "next_word_end",
        "0": "line_start",
        "$": "line_end",
        "gg": "input_start",
        "G": "input_end",
        "f{char}": "jump_forward_to",
        "F{char}": "jump_backward_to",
        "x": "delete_char",
        "dd": "delete_line",
        "D": "delete_to_line_end",
        "yy": "yank_line",
        "Y": "yank_to_line_end",
        "p": "paste_after",
        "P": "paste_before",
        "u": "undo",
        ".": "repeat_last_change",
        ">>": "indent",
        "<<": "dedent",
        "J": "join_lines",
        "i": "enter_insert",
        "I": "insert_at_line_start",
        "a": "insert_after_cursor",
        "A": "insert_at_line_end",
        "o": "insert_newline_below",
        "O": "insert_newline_above",
        "v": "enter_visual_char",
        "V": "enter_visual_line",
        "/{pattern}": "search_forward",
    }

    VISUAL_BINDINGS = {
        "h/j/k/l": "extend_selection",
        "w/b/e": "word_selection",
        "0/$": "extend_to_line_bounds",
        "gg/G": "extend_to_bounds",
        "x/d": "delete_selection",
        "y": "yank_selection",
        "p/P": "replace_with_register",
        ">/<": "indent_selection",
    }
```

### 32.2.5 Session Checkpointing

```python
class SessionCheckpointManager:
    """
    Auto-save state before each edit.
    Supports rewind: restore conversation, code, or both.
    30-day TTL.
    """

    def __init__(self, checkpoint_dir: Path):
        self.dir = checkpoint_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    async def save_checkpoint(self, session: Session) -> Checkpoint:
        """Save checkpoint before each edit operation."""
        cp = Checkpoint(
            id=f"cp-{uuid4().hex[:8]}",
            session_id=session.id,
            timestamp=datetime.now(),
            prompt_index=session.prompt_count,
            conversation_snapshot=session.conversation.serialize(),
            file_states=self._capture_file_states(session.touched_files),
            git_commit=self._get_git_commit(),
        )
        self._write_checkpoint(cp)
        return cp

    async def rewind(self, session: Session) -> RewindMenu:
        """Build rewind menu with actions per checkpoint."""
        checkpoints = self._list_checkpoints(session.id)
        actions = []
        for cp in checkpoints:
            actions.extend([
                RewindAction(cp, "restore_all",
                    "Restore code and conversation", self._restore_all),
                RewindAction(cp, "restore_code",
                    "Restore code only", self._restore_code),
                RewindAction(cp, "restore_conversation",
                    "Restore conversation only", self._restore_conversation),
                RewindAction(cp, "summarize_from",
                    "Summarize conversation from here", self._summarize_from),
                RewindAction(cp, "fork_from",
                    "Fork new session from here", self._fork_from),
            ])
        return RewindMenu(actions=actions)

    async def _restore_all(self, cp: Checkpoint):
        """Full rollback: restore files + conversation."""
        await self._restore_files(cp.file_states)
        self.session.conversation = Conversation.deserialize(cp.conversation_snapshot)

    async def _restore_code(self, cp: Checkpoint):
        """Revert files only, keep conversation."""
        await self._restore_files(cp.file_states)

    async def _restore_conversation(self, cp: Checkpoint):
        """Revert conversation only, keep file changes."""
        self.session.conversation = Conversation.deserialize(cp.conversation_snapshot)
```

### 32.2.6 Context Usage Visualization

```python
class ContextVisualizer:
    """
    Real-time context window usage with color-coded zones.
    Green <40%, Yellow 40-60%, Orange 60-80%, Red >80%.
    """

    def render(self, used_tokens: int, total_tokens: int, theme: Theme) -> str:
        pct = used_tokens / total_tokens
        bar_width = 30
        filled = int(bar_width * pct)
        empty = bar_width - filled

        color = self._color_for_pct(pct, theme)
        bar = f"{color}{'█' * filled}{theme.comment}{'░' * empty}{theme.reset}"

        return f"Context: {bar} {used_tokens:,}/{total_tokens:,} ({pct:.0%})"

    def _color_for_pct(self, pct: float, theme: Theme) -> str:
        if pct < 0.4:
            return theme.green
        elif pct < 0.6:
            return theme.yellow
        elif pct < 0.8:
            return theme.orange
        else:
            return theme.red

    def get_warning(self, pct: float) -> Optional[str]:
        """Return warning message if context is getting full."""
        if pct > 0.85:
            return "Context nearly full. Consider /compact."
        if pct > 0.70:
            return "Context usage high."
        return None
```

---

## Sound Configuration Reference

```json
{
  "lyra": {
    "sound": {
      "enabled": true,
      "volume": 0.5,
      "soundDir": "~/.lyra/sounds",
      "events": {
        "sessionStart": "startup.mp3",
        "promptSubmit": "submit.mp3",
        "responseComplete": "complete.mp3",
        "error": "error.mp3",
        "compact": "compact.mp3",
        "longTaskDone": "fanfare.mp3",
        "permissionPrompt": "prompt.mp3",
        "toolFailure": "tool_error.mp3"
      }
    },
    "theme": {
      "active": "catppuccin-mocha",
      "customizations": {}
    },
    "keybindings": {
      "vimMode": false,
      "customBindings": {}
    },
    "ui": {
      "blockMode": true,
      "statusBar": true,
      "contextBar": true,
      "promptSuggestions": true
    }
  }
}
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Themes available | 12+ built-in | Theme list count |
| Theme apply latency | <50ms | Apply timing |
| Keybindings coverage | 40+ shortcuts | Binding registry count |
| Sound event types | 8 events | Event catalog count |
| Sound playback latency | <100ms (background) | Play timing |
| Slash-command menu latency | <10ms (fuzzy search) | Autocomplete timing |
| Block navigation latency | <30ms | Navigation timing |
| Checkpoint save latency | <100ms | Save timing |
| Rewind restore latency | <500ms | Restore timing |
| Context bar refresh rate | Every turn | Integration check |

---

## Innovation Lineage

| Feature | Source | Reference |
|---------|--------|-----------|
| Block-Based Output | Warp Terminal | warp.dev |
| Catppuccin Theme | Catppuccin Community | hexdocs.pm/catppuccin |
| Tokyo Night Theme | folke/tokyonight.nvim | github.com/folke/tokyonight.nvim |
| Nord Theme | Arctic Ice Studio | nordtheme.com |
| Dracula Theme | Zeno Rocha | draculatheme.com |
| Gruvbox Theme | Pavel Pertsev | github.com/morhetz/gruvbox |
| Selenized Theme | Jan Warchoł | github.com/jan-warchol/selenized |
| Everforest Theme | Sainnhe | github.com/sainnhe/everforest |
| SilkCircuit Theme | hyperb1iss | github.com/hyperb1iss/silkcircuit |
| Sentry Sentinel | Getsentry | github.com/getsentry/sentinel |
| Slash-Command Autocomplete | Claude Code Interactive Mode | code.claude.com/docs/en/interactive-mode |
| Vim Mode | Claude Code | code.claude.com/docs/en/interactive-mode |
| Session Checkpointing | Claude Code | code.claude.com/docs/en/checkpointing |
| Transcript Viewer (Ctrl+O) | Claude Code | code.claude.com/docs/en/interactive-mode |
| Task List Overlay | Claude Code | code.claude.com/docs/en/interactive-mode |
| Sound Effects via Hooks | alexop.dev Community | alexop.dev/posts/how-i-added-sound-effects |
| Status Bar Design | tmux | github.com/tmux/tmux |
| Notification Rings | cmux (Manaflow) | github.com/manaflow-ai/cmux |
| Context Visualization | Claude Code Status Line | code.claude.com/docs/en/interactive-mode |
| Multiline Input Editor | Warp Terminal | warp.dev |
