#!/bin/zsh
echo "🔄 Reinstalling Lyra with ALL fixes..."
echo ""

# Kill old processes
pkill -9 -f lyra 2>/dev/null
sleep 1

# Reinstall development version
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/packages/lyra-cli
echo "📦 Installing development version..."
pip install -e . --force-reinstall --quiet

# Verify installation
echo ""
echo "✅ Verifying fixes are installed:"
grep -q "ALWAYS respond in English" /Users/khanhnguyen/miniconda3/lib/python3.11/site-packages/lyra_cli/interactive/session.py && echo "   ✅ English fix installed" || echo "   ❌ English fix NOT installed"
grep -q "debug_logger" /Users/khanhnguyen/miniconda3/lib/python3.11/site-packages/lyra_cli/providers/openai_compatible.py && echo "   ✅ Debug logging installed" || echo "   ❌ Debug logging NOT installed"

echo ""
echo "🚀 Ready to test! Run:"
echo "   ./final_test.sh"
