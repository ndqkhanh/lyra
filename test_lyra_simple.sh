#!/bin/bash
# Simple E2E test for Lyra with DeepSeek (macOS compatible)

echo "════════════════════════════════════════════════════════════════"
echo "  Lyra E2E Test with DeepSeek"
echo "════════════════════════════════════════════════════════════════"

# Test 1: Basic chat
echo ""
echo "Test 1: Basic Chat"
echo "→ Running..."
cat > /tmp/test1.txt << 'EOF'
What is 2+2? Answer briefly.
/exit
EOF

ly --model deepseek-chat < /tmp/test1.txt > /tmp/out1.txt 2>&1 &
PID=$!
sleep 30
kill $PID 2>/dev/null || true
wait $PID 2>/dev/null

echo "✓ Output saved to /tmp/out1.txt"
echo "Preview:"
head -50 /tmp/out1.txt
echo ""

# Test 2: Status check
echo "Test 2: Status & Model Info"
echo "→ Running..."
cat > /tmp/test2.txt << 'EOF'
/status
/exit
EOF

ly < /tmp/test2.txt > /tmp/out2.txt 2>&1 &
PID=$!
sleep 15
kill $PID 2>/dev/null || true
wait $PID 2>/dev/null

echo "✓ Output saved to /tmp/out2.txt"
grep -i "model\|status\|slot" /tmp/out2.txt | head -10
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "Full outputs: /tmp/out1.txt, /tmp/out2.txt"
echo "════════════════════════════════════════════════════════════════"
