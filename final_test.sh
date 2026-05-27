#!/bin/zsh
echo "🧪 Final Test - Lyra with All Fixes"
echo "===================================="
echo ""

# Kill everything
echo "1. Cleaning up old processes..."
pkill -9 -f lyra 2>/dev/null
sleep 2

# Clear old logs
echo "2. Archiving old logs..."
mkdir -p ~/.lyra/logs/archive
mv ~/.lyra/logs/lyra_debug_*.log ~/.lyra/logs/archive/ 2>/dev/null || true

# Unset problematic keys
unset OPENAI_API_KEY

# Show environment
echo "3. Environment check:"
echo "   API Keys available:"
env | grep -E "ANTHROPIC_API_KEY|DEEPSEEK_API_KEY" | sed 's/=.*/=***/' | sed 's/^/   - /'
echo ""

# Start Lyra
echo "4. Starting Lyra..."
echo ""
echo "📝 Test Instructions:"
echo "   a) Send: Hello"
echo "   b) Check: Should see SINGLE response (not duplicated)"
echo "   c) Send: What model are you?"
echo "   d) Check: Should respond immediately"
echo ""
echo "🔍 After testing, check logs:"
echo "   tail -f ~/.lyra/logs/lyra_debug_*.log"
echo ""
echo "Press Enter to start Lyra..."
read

lyra
