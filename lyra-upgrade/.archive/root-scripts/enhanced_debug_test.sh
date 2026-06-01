#!/bin/zsh
echo "🔍 Enhanced Debug Test - Lyra with Full Logging"
echo "================================================"
echo ""

# Kill everything
pkill -9 -f lyra 2>/dev/null
sleep 2

# Archive old logs
mkdir -p ~/.lyra/logs/archive
mv ~/.lyra/logs/lyra_debug_*.log ~/.lyra/logs/archive/ 2>/dev/null || true

# Unset problematic keys
unset OPENAI_API_KEY

echo "✅ Environment ready"
echo ""
echo "📋 API Keys:"
env | grep -E "ANTHROPIC_API_KEY|DEEPSEEK_API_KEY" | sed 's/=.*/=***/' | sed 's/^/   /'
echo ""
echo "🚀 Starting Lyra..."
echo ""
echo "📝 Test Plan:"
echo "   1. Send: Hello"
echo "   2. Wait for response"
echo "   3. Check logs for:"
echo "      - Full prompt (should include 'ALWAYS respond in English')"
echo "      - Full response"
echo "      - Provider and model used"
echo ""
echo "🔍 Logs will be at: ~/.lyra/logs/lyra_debug_*.log"
echo ""
echo "Press Enter to start..."
read

lyra
