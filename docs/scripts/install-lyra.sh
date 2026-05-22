#!/usr/bin/env bash
# install-lyra.sh — make `lyra` (and alias `ly`) work from any shell.
#
# 1. Editable-install the five lyra packages so `python3 -m lyra_cli` works.
# 2. Locate the entry-point shims that pip created (`lyra`, `ly`).
# 3. Symlink them into a writable directory on $PATH (default: prefer
#    /opt/homebrew/bin → /usr/local/bin → ~/.local/bin → ~/bin).
#
# Usage:
#   ./scripts/install-lyra.sh                 # auto-detect target on PATH
#   ./scripts/install-lyra.sh --bindir DIR    # force a specific bindir
#   ./scripts/install-lyra.sh --skip-pip      # don't reinstall, just symlink
#   ./scripts/install-lyra.sh --uninstall     # remove symlinks
#
# Exit codes:
#   0 success, 1 unrecoverable error (no writable PATH dir / pip failed).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LYRA_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-python3}"

PACKAGES=(
  "$LYRA_ROOT/packages/lyra-core"
  "$LYRA_ROOT/packages/lyra-skills"
  "$LYRA_ROOT/packages/lyra-mcp"
  "$LYRA_ROOT/packages/lyra-evals"
  "$LYRA_ROOT/packages/lyra-cli"
)

BINDIR=""
SKIP_PIP=0
UNINSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bindir)    BINDIR="$2"; shift 2 ;;
    --skip-pip)  SKIP_PIP=1;  shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)
      sed -n '2,18p' "$0"; exit 0 ;;
    *)
      echo "unknown flag: $1" >&2; exit 1 ;;
  esac
done

resolve_bindir() {
  if [[ -n "$BINDIR" ]]; then
    echo "$BINDIR"; return
  fi
  for candidate in /opt/homebrew/bin /usr/local/bin "$HOME/.local/bin" "$HOME/bin"; do
    if [[ ":$PATH:" == *":$candidate:"* && -d "$candidate" && -w "$candidate" ]]; then
      echo "$candidate"; return
    fi
  done
  echo ""
}

resolve_user_base_bin() {
  "$PYTHON" - <<'PY'
import site, sys, os
base = site.USER_BASE
print(os.path.join(base, "Scripts" if sys.platform.startswith("win") else "bin"))
PY
}

if [[ "$UNINSTALL" -eq 1 ]]; then
  bindir="$(resolve_bindir)"
  if [[ -z "$bindir" ]]; then
    echo "no bindir on PATH; pass --bindir explicitly" >&2
    exit 1
  fi
  removed=0
  for name in lyra ly; do
    if [[ -L "$bindir/$name" ]]; then
      rm "$bindir/$name"
      echo "removed $bindir/$name"
      removed=$((removed + 1))
    fi
  done
  echo "uninstalled $removed symlink(s)."
  exit 0
fi

if [[ "$SKIP_PIP" -ne 1 ]]; then
  echo "→ editable install of lyra packages with $PYTHON"
  pip_args=()
  for pkg in "${PACKAGES[@]}"; do
    pip_args+=("-e" "$pkg")
  done
  "$PYTHON" -m pip install --user --quiet "${pip_args[@]}"
fi

USER_BASE_BIN="$(resolve_user_base_bin)"
SRC_LYRA="$USER_BASE_BIN/lyra"
SRC_LY="$USER_BASE_BIN/ly"

if [[ ! -x "$SRC_LYRA" ]]; then
  echo "expected entry-point shim at $SRC_LYRA but did not find it" >&2
  echo "run: $PYTHON -m pip install -e $LYRA_ROOT/packages/lyra-cli" >&2
  exit 1
fi

bindir="$(resolve_bindir)"
if [[ -z "$bindir" ]]; then
  echo "no writable directory on \$PATH found." >&2
  echo "either pass --bindir DIR or add this line to ~/.zshrc:" >&2
  echo "  export PATH=\"$USER_BASE_BIN:\$PATH\"" >&2
  exit 1
fi

ln -sf "$SRC_LYRA" "$bindir/lyra"
ln -sf "$SRC_LY"   "$bindir/ly"

echo "✓ symlinked  $bindir/lyra  →  $SRC_LYRA"
echo "✓ symlinked  $bindir/ly    →  $SRC_LY"
echo
echo "now available globally:"
echo "  lyra --version"
echo "  lyra doctor"
echo "  lyra run \"hello\""
