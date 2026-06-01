#!/bin/zsh
# Simple test - no interactive prompts

echo "🔍 Starting Lyra Test..."

# Kill old processes
pkill -9 -f lyra 2>/dev/null
sleep 1

# Clean old logs
rm -rf ~/.lyra/logs/lyra_debug_*.log 2>/dev/null

# Unset OpenAI key
unset OPENAI_API_KEY

echo "✅ Ready to start Lyra"
echo ""
echo "Run this command:"
echo "  lyra"
echo ""
echo "Then:"
echo "  1. Send: Hello"
echo "  2. Press Ctrl+C to exit"
echo "  3. Run: cat ~/.lyra/logs/lyra_debug_*.log"
