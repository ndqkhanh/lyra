"""🧬 Lyra CLI — one command to run the AGI platform."""
from __future__ import annotations
import sys, os, argparse, json

__all__ = ["main"]

BANNER = """
╔══════════════════════════════════════════════╗
║      🧬 Lyra — AGI Through Emergence        ║
║      124 packages · 20 plans · 23 waves     ║
╚══════════════════════════════════════════════╝
"""

def main():
    parser = argparse.ArgumentParser(description="🧬 Lyra — AGI Platform", prog="lyra")
    parser.add_argument("--version", "-v", action="store_true", help="Show version")
    parser.add_argument("--status", "-s", action="store_true", help="Show system status")
    parser.add_argument("--info", "-i", action="store_true", help="Show architecture info")
    parser.add_argument("--shell", action="store_true", help="Launch interactive shell")
    args = parser.parse_args()

    if args.version:
        print(f"🧬 Lyra v5.0.0 — 124 packages, 20 plans")
        return

    if args.status:
        print(BANNER)
        try:
            from lyra_core import BreakthroughIntegration, breakthrough_available
            bt = BreakthroughIntegration()
            status = bt.initialize()
            avail = sum(1 for v in status.values() if v)
            print(f"  📦 Packages: 124")
            print(f"  🧬 Subsystems: {avail}/{len(status)} initialized")
            print(f"  📋 Plans: 20")
            print(f"  📚 Research: 23 waves, 290+ papers")
            print()
        except ImportError:
            print("  ⚠ lyra-core not found. Run install.sh first.")
        return

    if args.info:
        print(BANNER)
        print("  Architecture:")
        print("    Tier 1 🧬 Foundation:        Plans 1-5  (36 packages)")
        print("    Tier 2 🚀 Breakthrough:      Plans 6-10 (28 packages)")
        print("    Tier 3 🌟 Frontier:          Plans 11-15(30 packages)")
        print("    Tier 4 ⚡ AGI Ascent:         Plans 16-20(30 packages)")
        print()
        print("  Key Capabilities:")
        print("    ⚡ Auto Mode — 2-layer permission classifier")
        print("    🔍 NLA Interpretability — reads agent activations")
        print("    🎯 Thinking/MoE Switch — adaptive compute allocation")
        print("    🌍 World Models — mental simulation before action")
        print("    🏆 Challenge Platform — competitive agent research")
        print()
        return

    # Default: show banner and status
    print(BANNER)
    try:
        from lyra_core import BreakthroughIntegration
        bt = BreakthroughIntegration()
        bt.initialize()
        print(f"  🧬 Lyra Ready — {len([k for k,v in bt.available.items() if v])} subsystems active")
        print(f"  💡 Run 'lyra --help' for options")
    except ImportError:
        print("  Installing Lyra...")
        os.system("curl -fsSL https://raw.githubusercontent.com/ndqkhanh/lyra/main/install.sh | bash")

if __name__ == "__main__":
    main()
