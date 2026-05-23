# 🚀 Lyra UI - Quick Start Guide

## Prerequisites

- Node.js 18+ 
- npm 9+

## Installation & Setup

```bash
# Navigate to the Lyra UI project
cd projects/lyra

# Install dependencies (use --legacy-peer-deps for React version conflicts)
npm install --legacy-peer-deps

# Build all packages
npm run build
```

## Running Lyra

### Development Mode (Recommended)
```bash
npm run dev --workspace=@lyra/ui-terminal
```

This starts the UI with hot reload. Press **Ctrl+C** to exit.

### Production Mode
```bash
# Build first (if not already done)
npm run build

# Run the built version
npm run start --workspace=@lyra/ui-terminal
```

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
Make sure you're in the correct directory:
```bash
cd projects/lyra  # Not just projects/
```

### "No workspaces found" error
The workspace structure requires being in the root `projects/lyra` directory.

### Dependency conflicts
Use `--legacy-peer-deps` flag:
```bash
npm install --legacy-peer-deps
```

### Immer MapSet error
This has been fixed in the latest commit. Make sure you've pulled the latest changes and rebuilt:
```bash
git pull
npm run build
```

## Project Structure

```
projects/lyra/
├── packages/
│   ├── ui-core/        # State management + types
│   ├── ui-terminal/    # Terminal UI (Ink)
│   └── ui-transport/   # WebSocket transport
├── package.json        # Root workspace config
└── README.md          # Full documentation
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
