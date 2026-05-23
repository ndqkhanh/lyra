# 🚀 How to Run Lyra UI

## Important: Directory Structure

The Lyra UI rebuild is located at:
```
/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/projects/lyra/
```

## Quick Start

```bash
# Navigate to the NEW UI directory (note the nested projects/lyra)
cd projects/lyra

# Install dependencies
npm install --legacy-peer-deps

# Build all packages
npm run build

# Run Lyra (single execution, no auto-restart)
npm run run --workspace=@lyra/ui-terminal
```

## Run Options

### Option 1: Single Run (Recommended)
```bash
npm run run --workspace=@lyra/ui-terminal
```
- Runs once
- Press **Ctrl+C** to exit
- No auto-restart on file changes

### Option 2: Development Mode (Auto-Restart)
```bash
npm run dev --workspace=@lyra/ui-terminal
```
- Watches for file changes
- Auto-restarts when you edit code
- Press **Ctrl+C** to exit

### Option 3: Production Build
```bash
npm run build
npm run start --workspace=@lyra/ui-terminal
```
- Runs the compiled version from `dist/`
- Fastest startup

## Keyboard Controls

| Key | Action |
|-----|--------|
| **Ctrl+C** | Exit Lyra |
| **Ctrl+\\** | Cycle display modes (minimal → standard → debug) |
| **↑** | Previous command in history |
| **↓** | Next command in history |
| **Enter** | Submit message |

## Troubleshooting

### "Missing script: build" error
You're in the wrong directory! Make sure you're in:
```bash
cd projects/lyra  # The nested one!
pwd  # Should show: .../projects/lyra/projects/lyra
```

### "No workspaces found" error
Same issue - wrong directory. Use `cd projects/lyra` from the main Lyra directory.

### Dependency conflicts
Use the `--legacy-peer-deps` flag:
```bash
npm install --legacy-peer-deps
```

## Project Structure

```
projects/lyra/                    # Main Lyra project (Python)
└── projects/lyra/                # NEW UI rebuild (TypeScript/React)
    ├── packages/
    │   ├── ui-core/              # State management
    │   ├── ui-terminal/          # Terminal UI
    │   └── ui-transport/         # WebSocket transport
    ├── package.json              # Workspace config
    ├── QUICKSTART.md             # Quick start guide
    ├── HOW_TO_RUN.md             # Complete guide
    └── README.md                 # Full documentation
```

## What You'll See

When you run Lyra, you'll see:
- **Header** with Lyra branding
- **Conversation view** showing messages
- **Input area** at the bottom
- **Status bar** with current status

## Next Steps

1. Run the UI: `npm run run --workspace=@lyra/ui-terminal`
2. Test keyboard shortcuts
3. Try different display modes (Ctrl+\\)
4. Read the full documentation in README.md

---

**Built with**: React + Ink + TypeScript + Zustand
**Status**: ✅ Ready to run
**Date**: 2026-05-24
