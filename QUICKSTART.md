# 🚀 Lyra UI - Quick Start Guide

## Prerequisites

- Node.js 18+ 
- npm 9+

## Installation & Setup

```bash
# You're already in the right directory!

# Install dependencies (use --legacy-peer-deps for React version conflicts)
npm install --legacy-peer-deps

# Build all packages
npm run build
```

## Running Lyra

### Single Run (Recommended)
```bash
npm run run --workspace=@lyra/ui-terminal
```

Runs once. Press **Ctrl+C** to exit cleanly. No auto-restart.

### Development Mode (Auto-Restart)
```bash
npm run dev --workspace=@lyra/ui-terminal
```

Watches for file changes and auto-restarts. Press **Ctrl+C** to exit.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Ctrl+C** | Exit Lyra |
| **Ctrl+\\** | Cycle display modes (minimal → standard → debug) |
| **↑** | Previous command (history) |
| **↓** | Next command (history) |
| **Enter** | Submit message |

## Display Modes

- **Minimal**: Clean, distraction-free interface
- **Standard**: Balanced view with status and metadata
- **Debug**: Full details including timestamps, IDs, and debug info

## Troubleshooting

### "Missing script: build" error
This shouldn't happen anymore - the structure has been flattened!

### Dependency conflicts
Use `--legacy-peer-deps` flag:
```bash
npm install --legacy-peer-deps
```

### Immer MapSet error
This has been fixed. Make sure you've pulled the latest changes and rebuilt:
```bash
git pull
npm run build
```

## Project Structure

```
projects/lyra/              # Main Lyra project root
├── packages/
│   ├── ui-core/           # State management + types
│   ├── ui-terminal/       # Terminal UI (Ink)
│   └── ui-transport/      # WebSocket transport
├── package.json           # Root workspace config
├── QUICKSTART.md          # This file
└── HOW_TO_RUN.md         # Complete guide
```

## Development Workflow

1. **Make changes** to source files in `packages/*/src/`
2. **Build** with `npm run build` (or use dev mode for auto-rebuild)
3. **Test** with `npm test`
4. **Run** with `npm run dev --workspace=@lyra/ui-terminal`

## Next Steps

- Read the full [README.md](README.md) for architecture details
- Check [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) for implementation status
- Explore the codebase in `packages/*/src/`

## Need Help?

- Check the main README.md for detailed documentation
- Review the implementation guide in IMPLEMENTATION_COMPLETE.md
- Examine the test files for usage examples

---

**Status**: ✅ All systems operational
**Version**: 1.0.0
**Last Updated**: 2026-05-24
