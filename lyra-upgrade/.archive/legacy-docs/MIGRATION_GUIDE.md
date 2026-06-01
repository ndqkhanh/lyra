# Lyra CLI Migration Guide

**From**: TUI v2 (Textual-based)  
**To**: New CLI (Rich + Typer)  
**Date**: 2026-05-23

---

## Overview

Lyra has migrated from a complex Textual-based TUI (16,300+ lines) to a clean, simple CLI using Rich and Typer (~1,500 lines). This guide helps you transition to the new interface.

---

## What Changed

### Removed
- ❌ TUI v2 (Textual-based full-screen interface)
- ❌ harness-tui dependency
- ❌ textual dependency
- ❌ 90 TUI widget files
- ❌ 14 modal dialogs
- ❌ 6 sidebar components
- ❌ LYRA_TUI environment variable

### Added
- ✅ New CLI with Rich formatting
- ✅ Interactive prompt with history
- ✅ Streaming agent responses
- ✅ Clean status messages
- ✅ Slash command completion

---

## Quick Start

### Before (TUI v2)
```bash
# Launch TUI
lyra

# Or force legacy REPL
LYRA_TUI=legacy lyra
```

### After (New CLI)
```bash
# Launch new CLI (default)
lyra

# Or use legacy REPL
lyra --legacy
```

---

## Feature Mapping

| TUI v2 Feature | New CLI Equivalent | Notes |
|----------------|-------------------|-------|
| Welcome screen | Welcome panel | Box-drawn with logo |
| Chat log | Scrolling output | Natural terminal scrolling |
| Input composer | Interactive prompt | With history & completion |
| Status bar | Status messages | Inline spinners (⏺ ✻ ✶) |
| Command palette | Slash commands | `/help`, `/config`, etc. |
| Model picker | `--model` flag | `lyra --model opus` |
| Session manager | `/session` command | List/switch sessions |
| Sidebar | Not needed | CLI doesn't need sidebar |
| Modals | Commands | `/config`, `/session`, etc. |
| Theme switcher | Not implemented | Future enhancement |

---

## Commands

### Interactive Mode

```bash
# Start interactive chat
lyra

# With specific model
lyra --model opus
lyra --model sonnet
lyra --model haiku
```

### Single Message

```bash
# Send one message
lyra chat "Explain quantum computing"

# With model selection
lyra --model sonnet chat "Quick question"
```

### Slash Commands

Available in interactive mode:

- `/help` - Show help
- `/exit` or `/quit` - Exit
- `/clear` - Clear screen
- `/config` - Configuration (coming soon)
- `/session` - Session management (coming soon)
- `/skills` - Skills management (coming soon)

### Keyboard Shortcuts

- `↑/↓` - Command history
- `Tab` - Command completion
- `Ctrl+C` - Interrupt
- `Ctrl+D` - Exit

---

## Configuration

### Environment Variables

```bash
# Set API key
export ANTHROPIC_API_KEY=your_key

# Enable debug mode
export DEBUG=1
```

### Config File

Location: `~/.lyra/config.toml` (coming in Phase 6)

```toml
[general]
model = "opus"
organization = "Claude Max"

[display]
show_tokens = true
show_timing = true
```

---

## Migration Steps

### 1. Update Dependencies

```bash
cd packages/lyra-cli
pip install -e .
```

This will:
- Remove `harness-tui`
- Remove `textual`
- Add `rich>=13.7`
- Add `prompt_toolkit>=3.0`

### 2. Test New CLI

```bash
# Test basic functionality
python test_new_cli.py

# Test agent integration
python test_agent_integration.py

# Try interactive mode
lyra
```

### 3. Update Scripts

If you have scripts that launch Lyra:

**Before**:
```bash
LYRA_TUI=tui lyra
```

**After**:
```bash
lyra  # New CLI is now default
```

### 4. Update Workflows

If you use Lyra in CI/CD:

**Before**:
```bash
LYRA_TUI=legacy lyra run --task "..."
```

**After**:
```bash
lyra run --task "..."  # Works the same
```

---

## Troubleshooting

### Issue: "new CLI not available"

**Cause**: Missing dependencies

**Solution**:
```bash
pip install rich>=13.7 prompt_toolkit>=3.0
```

### Issue: "ANTHROPIC_API_KEY not set"

**Cause**: API key not configured

**Solution**:
```bash
export ANTHROPIC_API_KEY=your_key
```

### Issue: Want old TUI back

**Cause**: Prefer TUI interface

**Solution**: TUI v2 has been removed. Use legacy REPL:
```bash
lyra --legacy
```

### Issue: Missing features

**Cause**: Some TUI features not yet in CLI

**Solution**: Check roadmap below for planned features

---

## Roadmap

### Implemented ✅
- ✅ Welcome screen
- ✅ Interactive prompt
- ✅ Streaming responses
- ✅ Status messages
- ✅ Slash commands
- ✅ Command history
- ✅ Token usage display
- ✅ Agent integration

### Coming Soon 🔄
- 🔄 Session management
- 🔄 Configuration commands
- 🔄 Skills management
- 🔄 Debug commands
- 🔄 Theme support

### Future Enhancements 💡
- 💡 Multi-line input with editor
- 💡 Syntax highlighting
- 💡 Image display (iTerm2, Kitty)
- 💡 Mouse support
- 💡 Custom themes

---

## FAQ

### Q: Why remove TUI v2?

**A**: TUI v2 was complex (16,300 lines), unstable (immediate exit bugs), and hard to maintain. The new CLI is simpler (1,500 lines), more stable, and easier to extend.

### Q: Will TUI v2 come back?

**A**: No. The new CLI is the future. It's simpler, more stable, and follows Claude Code patterns.

### Q: Can I still use the old REPL?

**A**: Yes, use `lyra --legacy` for the prompt_toolkit REPL.

### Q: What about the sidebar?

**A**: CLI doesn't need a sidebar. Use commands instead:
- `/agents` - List agents
- `/debug status` - System status

### Q: How do I change themes?

**A**: Theme support coming soon. For now, use terminal color schemes.

### Q: Where are my sessions?

**A**: Sessions are still in `.lyra/sessions/`. Use `/session list` to view them.

---

## Getting Help

### Documentation
- [CLI Interface Spec](CLI_INTERFACE_SPEC.md)
- [CLI Patterns](CLI_PATTERNS.md)
- [Testing Report](TESTING_REPORT.md)

### Commands
```bash
# Show help
lyra --help

# Show command help
lyra chat --help
```

### Issues
Report issues at: https://github.com/ndqkhanh/lyra/issues

---

## Feedback

We'd love to hear your feedback on the new CLI!

**What we want to know**:
- What features do you miss from TUI v2?
- What do you like about the new CLI?
- What could be improved?

**How to provide feedback**:
- GitHub Issues
- Pull Requests
- Discussions

---

**Migration Complete!** 🎉

Enjoy the new, simpler Lyra CLI!
