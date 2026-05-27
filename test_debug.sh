#!/bin/bash
echo "🔍 Lyra Debug Test Script"
echo "========================"
echo ""

# Kill old processes
echo "1. Killing old Lyra processes..."
pkill -f lyra 2>/dev/null
sleep 1

# Check if logs directory exists
echo "2. Checking logs directory..."
mkdir -p ~/.lyra/logs
echo "   ✅ Logs will be saved to: ~/.lyra/logs/"

# Show current logs
echo ""
echo "3. Current log files:"
ls -lht ~/.lyra/logs/ 2>/dev/null | head -5 || echo "   (no logs yet)"

echo ""
echo "4. Ready to test!"
echo ""
echo "Next steps:"
echo "  a) Run: lyra --llm mock"
echo "  b) Type: Hello, test message"
echo "  c) Check logs: tail -f ~/.lyra/logs/lyra_debug_*.log"
echo ""
echo "The logs will show EXACTLY what's happening! 🎯"
