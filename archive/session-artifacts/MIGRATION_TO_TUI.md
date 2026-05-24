# Lyra CLI → TUI Migration

## Summary

Successfully replaced the simple Python CLI (Typer/Rich) with the fancy TypeScript/Ink TUI (Claude Code-style) as the default interface for Lyra.

## Changes Made

### 1. Fixed TypeScript Build Errors
- **File**: `packages/ui-terminal/src/hooks/advanced.ts`
  - Removed unused `useUIStore` import
- **File**: `packages/ui-terminal/src/modes/DebugMode.tsx`
  - Fixed type error accessing `stateMachine.state` with type assertion
- **File**: `packages/ui-terminal/tsconfig.json`
  - Excluded `__tests__` directory from build to avoid test utility export errors

### 2. Created TUI Launcher
- **File**: `packages/lyra-cli/src/lyra_cli/tui_launcher.py`
  - Python wrapper that launches the TypeScript TUI using `npx tsx`
  - Automatically finds the ui-terminal package
  - Uses `tsx` for direct TypeScript execution (no build step needed)
  - Handles errors gracefully with user-friendly messages

### 3. Updated Entry Point
- **File**: `packages/lyra-cli/src/lyra_cli/__main__.py`
  - Changed default behavior to launch TypeScript TUI
  - Made `--legacy` flag launch the old prompt_toolkit REPL
  - Updated help text to reflect new default

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  lyra command (Python entry point)                          │
│  ├─ Default: Launch TypeScript/Ink TUI via tsx              │
│  └─ --legacy: Launch old prompt_toolkit REPL                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  tui_launcher.py                                             │
│  ├─ Finds packages/ui-terminal                              │
│  ├─ Runs: npx tsx src/index.tsx                             │
│  └─ No build step needed (tsx handles TypeScript directly)  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  TypeScript/Ink TUI (Claude Code-style)                     │
│  ├─ Fancy box drawing with borders                          │
│  ├─ Status bar at bottom                                    │
│  ├─ Header with logo and model info                         │
│  ├─ Conversation view with scrolling                        │
│  └─ Input area with prompt                                  │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Default (TypeScript TUI)
```bash
lyra
```

### Legacy Python REPL
```bash
lyra --legacy
```

### Other Commands (unchanged)
```bash
lyra run <task>
lyra plan
lyra doctor
lyra session list
# ... etc
```

## Requirements

- **Node.js**: Required for running the TypeScript TUI
- **npx**: Comes with Node.js, used to run `tsx`
- **tsx**: Automatically installed via npx when needed

## Benefits

1. **No Build Step**: Uses `tsx` to run TypeScript directly
2. **Better UX**: Claude Code-style interface with boxes and status bar
3. **Backward Compatible**: Legacy REPL still available via `--legacy`
4. **Clean Architecture**: Python CLI delegates to TypeScript TUI

## Testing

The TUI launches successfully when run in an interactive terminal:
```bash
$ lyra
Launching Lyra TUI...
# Shows fancy Claude Code-style interface
```

Note: The TUI requires a TTY (interactive terminal) and will fail if stdin is piped or redirected.

## Future Work

- Add session persistence to TUI
- Implement model switching in TUI
- Add budget tracking display
- Connect TUI to actual LLM backend
- Add keyboard shortcuts documentation
