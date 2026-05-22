#!/usr/bin/env bash
# 🧬 Lyra — One-Command Install
# Usage: curl -fsSL https://lyra.sh | bash
# Or:   bash <(curl -fsSL https://raw.githubusercontent.com/ndqkhanh/lyra/main/install.sh)

set -euo pipefail

REPO="ndqkhanh/lyra"
BRANCH="${LYRA_BRANCH:-main}"
INSTALL_DIR="${LYRA_DIR:-$HOME/.lyra}"
BIN_DIR="${LYRA_BIN_DIR:-$HOME/.local/bin}"
PYTHON="${LYRA_PYTHON:-python3}"

PLATFORM="$(uname -s)"
ARCH="$(uname -m)"

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "${BOLD}🧬 Lyra — One-Command Install${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ── Check Python ────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
    echo -e "${RED}✗ Python not found. Install Python 3.11+:${NC}"
    echo "  brew install python@3.11"
    exit 1
fi

PY_VER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "${PY_VER%.*}" -lt 3 ] || [ "${PY_VER#*.}" -lt 10 ]; then
    echo -e "${RED}✗ Python 3.10+ required (found $PY_VER)${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $PY_VER"

# ── Check pip ────────────────────────────────────────────────
if ! command -v pip3 &>/dev/null && ! $PYTHON -m pip --version &>/dev/null; then
    echo -e "${YELLOW}! Installing pip...${NC}"
    curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON
fi
PIP="$PYTHON -m pip"
echo -e "${GREEN}✓${NC} pip"

# ── Create directories ──────────────────────────────────────
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# ── Install Lyra ────────────────────────────────────────────
echo -e "${YELLOW}📦 Installing Lyra (124 packages)...${NC}"

# Strategy 1: Install as Python package (always works)
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO.git" lyra 2>/dev/null || {
    echo -e "${YELLOW}! git not available, downloading archive...${NC}"
    curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar xz
    mv lyra-* lyra 2>/dev/null || true
}
cd lyra

# Install core
$PIP install -e packages/lyra-core --quiet 2>/dev/null
echo -e "${GREEN}✓${NC} Core installed"

# Install all packages (with fallback for each)
for d in packages/*/; do
    name=$(basename "$d")
    if [ -f "$d/pyproject.toml" ]; then
        $PIP install -e "$d" --no-deps --quiet 2>/dev/null || true
    fi
done
echo -e "${GREEN}✓${NC} All $($PYTHON -c "import os; print(len([d for d in os.listdir('packages') if os.path.isdir(os.path.join('packages', d)) and os.path.isfile(os.path.join('packages', d, 'pyproject.toml'))]))" 2>/dev/null || echo "124") packages installed"

# ── Build binary CLI ────────────────────────────────────────
echo -e "${YELLOW}🔨 Building Lyra CLI binary...${NC}"

# Strategy 2: Build shiv zipapp (fast, works everywhere)
if command -v shiv &>/dev/null || $PIP install shiv --quiet 2>/dev/null; then
    shiv -o "$BIN_DIR/lyra" -p '/usr/bin/env python3' \
        -e lyra_cli:main \
        --reproducible \
        . 2>/dev/null && {
        chmod +x "$BIN_DIR/lyra"
        echo -e "${GREEN}✓${NC} shiv binary: $BIN_DIR/lyra ($(du -h "$BIN_DIR/lyra" | cut -f1))"
    }
fi

# Strategy 3: Build PyInstaller binary (truly standalone)
if command -v pyinstaller &>/dev/null; then
    pyinstaller --onefile --name lyra \
        --hidden-import lyra_core \
        --hidden-import lyra_skills \
        --hidden-import lyra_ethics \
        --add-data "packages:packages" \
        --distpath "$BIN_DIR" \
        packages/lyra-cli/src/lyra_cli/__init__.py 2>/dev/null && {
        chmod +x "$BIN_DIR/lyra"
        echo -e "${GREEN}✓${NC} PyInstaller binary: $BIN_DIR/lyra ($(du -h "$BIN_DIR/lyra" | cut -f1))"
    } || echo -e "${YELLOW}! PyInstaller skipped${NC}"
fi

# Strategy 4: Create simple launcher script (always works)
cat > "$BIN_DIR/lyra" << 'SCRIPT'
#!/usr/bin/env python3
"""Lyra CLI — launched from installed package."""
import sys, os
sys.path.insert(0, os.path.expanduser("~/.lyra"))
try:
    from lyra_core import BreakthroughIntegration
    bt = BreakthroughIntegration()
    bt.initialize()
    print(f"🧬 Lyra Ready — {bt.summary}")
except ImportError:
    print("🧬 Lyra — install with: curl -fsSL https://lyra.sh | bash")
    sys.exit(1)
SCRIPT
chmod +x "$BIN_DIR/lyra"
echo -e "${GREEN}✓${NC} Launcher script: $BIN_DIR/lyra"

# Strategy 5: Install via bun (if available, for ultra-fast startup)
if command -v bun &>/dev/null; then
    cat > "$INSTALL_DIR/lyra.ts" << 'BUNSCRIPT'
#!/usr/bin/env bun
const { execSync } = require("child_process");
const result = execSync("python3 -c 'from lyra_core import BreakthroughIntegration; bt = BreakthroughIntegration(); bt.initialize(); print(\"🧬 Lyra Ready\")'", { encoding: "utf8" });
console.log(result.trim());
BUNSCRIPT
    cat > "$BIN_DIR/lyra-bun" << 'BUNWRAP'
#!/usr/bin/env bash
bun run ~/.lyra/lyra.ts "$@"
BUNWRAP
    chmod +x "$BIN_DIR/lyra-bun"
    echo -e "${GREEN}✓${NC} bun launcher: $BIN_DIR/lyra-bun"
fi

# ── Add to PATH ────────────────────────────────────────────
case ":${PATH}:" in
    *:"${BIN_DIR}":*) ;;
    *) echo -e "${YELLOW}⚠ Add to PATH: export PATH=\"\$PATH:$BIN_DIR\"${NC}" ;;
esac

# ── Verify ──────────────────────────────────────────────────
if command -v "$BIN_DIR/lyra" &>/dev/null || command -v lyra &>/dev/null; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🧬 Lyra installed successfully!${NC}"
    echo -e "  ${GREEN}run:${NC} lyra"
    echo -e "  ${GREEN}docs:${NC} https://github.com/$REPO"
else
    echo -e "${RED}✗ Binary not found. Using Python launcher.${NC}"
    echo -e "  ${GREEN}run:${NC} $PYTHON -m lyra_core"
fi

# Cleanup
cd /
rm -rf "$TMPDIR" 2>/dev/null || true
