#!/bin/zsh
echo "🧹 Starting Lyra with clean environment..."
echo ""

# Kill old processes
pkill -9 -f lyra 2>/dev/null
sleep 1

# Unset problematic API keys
unset OPENAI_API_KEY

# Show what we have
echo "📋 Available API keys:"
env | grep -E "ANTHROPIC_API_KEY|DEEPSEEK_API_KEY|GEMINI_API_KEY" | sed 's/=.*/=***/' || echo "   (none - will use mock mode)"
echo ""

# Start Lyra
echo "🚀 Starting Lyra..."
lyra --llm mock
