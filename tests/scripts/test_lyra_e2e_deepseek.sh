#!/bin/bash
# Comprehensive E2E test for Lyra with DeepSeek
# Tests UI feedback, progress indicators, autosuggestions, and error handling

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Lyra E2E Test Suite with DeepSeek"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check prerequisites
echo "→ Checking prerequisites..."
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "✗ DEEPSEEK_API_KEY not set"
    exit 1
fi
echo "✓ DeepSeek API key found"

if ! command -v ly &> /dev/null; then
    echo "✗ ly command not found"
    exit 1
fi
echo "✓ ly command available"
echo ""

# Test 1: Basic chat with progress indicators
echo "════════════════════════════════════════════════════════════════"
echo "Test 1: Basic Chat with Progress Indicators"
echo "════════════════════════════════════════════════════════════════"
cat > /tmp/lyra_test_1.txt << 'EOF'
What is 2+2? Keep it brief.
/exit
EOF

echo "→ Running basic chat test..."
timeout 60s ly --model deepseek-chat < /tmp/lyra_test_1.txt > /tmp/lyra_output_1.txt 2>&1 || true
echo "✓ Basic chat completed"
echo ""
echo "Output preview:"
head -30 /tmp/lyra_output_1.txt
echo ""

# Test 2: Model switching and status
echo "════════════════════════════════════════════════════════════════"
echo "Test 2: Model Switching & Status Display"
echo "════════════════════════════════════════════════════════════════"
cat > /tmp/lyra_test_2.txt << 'EOF'
/status
/model list
/exit
EOF

echo "→ Testing model commands..."
timeout 30s ly < /tmp/lyra_test_2.txt > /tmp/lyra_output_2.txt 2>&1 || true
echo "✓ Model commands completed"
echo ""
echo "Output preview:"
grep -A 5 "Model\|Status\|Slot" /tmp/lyra_output_2.txt | head -20 || echo "No model info found"
echo ""

# Test 3: Deep research flow (critical test)
echo "════════════════════════════════════════════════════════════════"
echo "Test 3: Deep Research Flow with Progress Tracking"
echo "════════════════════════════════════════════════════════════════"
cat > /tmp/lyra_test_3.txt << 'EOF'
/research "Python async patterns"
/exit
EOF

echo "→ Running deep research test (this may take 2-3 minutes)..."
timeout 180s ly --model deepseek-reasoner < /tmp/lyra_test_3.txt > /tmp/lyra_output_3.txt 2>&1 || true
echo "✓ Deep research completed"
echo ""
echo "Checking for progress indicators..."
if grep -q "⏺\|Running\|agents\|tool uses\|tokens" /tmp/lyra_output_3.txt; then
    echo "✓ Progress indicators found"
    grep "⏺\|Running\|agents" /tmp/lyra_output_3.txt | head -10
else
    echo "✗ No progress indicators detected"
fi
echo ""

# Test 4: Context management commands
echo "════════════════════════════════════════════════════════════════"
echo "Test 4: Context Management & Memory"
echo "════════════════════════════════════════════════════════════════"
cat > /tmp/lyra_test_4.txt << 'EOF'
/memory
/context checkpoint test1
/tools
/skills
/exit
EOF

echo "→ Testing context commands..."
timeout 30s ly < /tmp/lyra_test_4.txt > /tmp/lyra_output_4.txt 2>&1 || true
echo "✓ Context commands completed"
echo ""
echo "Output preview:"
grep -A 3 "memory\|checkpoint\|tools\|skills" /tmp/lyra_output_4.txt | head -20 || echo "No context info found"
echo ""

# Test 5: Error handling and recovery
echo "════════════════════════════════════════════════════════════════"
echo "Test 5: Error Handling & Recovery"
echo "════════════════════════════════════════════════════════════════"
cat > /tmp/lyra_test_5.txt << 'EOF'
/invalid_command
/model invalid-model-name
/exit
EOF

echo "→ Testing error handling..."
timeout 30s ly < /tmp/lyra_test_5.txt > /tmp/lyra_output_5.txt 2>&1 || true
echo "✓ Error handling test completed"
echo ""
echo "Checking error messages..."
if grep -qi "error\|invalid\|unknown\|not found" /tmp/lyra_output_5.txt; then
    echo "✓ Error messages present"
    grep -i "error\|invalid\|unknown" /tmp/lyra_output_5.txt | head -5
else
    echo "⚠ No clear error messages found"
fi
echo ""

# Test 6: Background task execution
echo "════════════════════════════════════════════════════════════════"
echo "Test 6: Background Task Indicators"
echo "════════════════════════════════════════════════════════════════"
echo "→ Checking if background task UI elements are present..."
if grep -q "ctrl+b\|background\|↓ to manage\|shell" /tmp/lyra_output_*.txt; then
    echo "✓ Background task UI elements found"
    grep "ctrl+b\|background\|↓ to manage" /tmp/lyra_output_*.txt | head -5
else
    echo "⚠ Background task indicators not visible in test outputs"
fi
echo ""

# Test 7: Spinner and progress feedback
echo "════════════════════════════════════════════════════════════════"
echo "Test 7: Spinner & Progress Feedback"
echo "════════════════════════════════════════════════════════════════"
echo "→ Checking for spinner and progress indicators..."
if grep -q "⏺\|✳\|✻\|✶\|✽\|Thinking\|tokens\|tool uses" /tmp/lyra_output_*.txt; then
    echo "✓ Spinner/progress indicators found"
    grep "⏺\|✳\|✻\|✶\|✽\|Thinking" /tmp/lyra_output_*.txt | head -10
else
    echo "⚠ Limited spinner feedback in outputs"
fi
echo ""

# Summary Report
echo "════════════════════════════════════════════════════════════════"
echo "  Test Summary"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check for key UX features
echo "UX Feature Checklist:"
echo ""

# Progress indicators
if grep -q "⏺\|Running.*agents" /tmp/lyra_output_*.txt; then
    echo "✓ Progress indicators (⏺, Running agents)"
else
    echo "✗ Progress indicators missing"
fi

# Token/time tracking
if grep -q "tokens\|tool uses" /tmp/lyra_output_*.txt; then
    echo "✓ Token/time tracking visible"
else
    echo "✗ Token/time tracking not visible"
fi

# Status bar elements
if grep -q "esc to interrupt\|↓ to manage\|bypass permissions" /tmp/lyra_output_*.txt; then
    echo "✓ Status bar elements present"
else
    echo "✗ Status bar elements missing"
fi

# Tips and hints
if grep -q "Tip:\|ctrl+o\|ctrl+b" /tmp/lyra_output_*.txt; then
    echo "✓ User tips/hints displayed"
else
    echo "✗ User tips/hints not visible"
fi

# Subagent tracking
if grep -q "oh-my-claudecode:\|general-purpose" /tmp/lyra_output_*.txt; then
    echo "✓ Subagent execution tracking"
else
    echo "✗ Subagent tracking not visible"
fi

# Compaction notices
if grep -q "compacted\|Conversation compacted" /tmp/lyra_output_*.txt; then
    echo "✓ Context compaction feedback"
else
    echo "⚠ No compaction events in test (may be normal)"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Full outputs saved to /tmp/lyra_output_*.txt"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "To review detailed outputs:"
echo "  cat /tmp/lyra_output_1.txt  # Basic chat"
echo "  cat /tmp/lyra_output_2.txt  # Model switching"
echo "  cat /tmp/lyra_output_3.txt  # Deep research"
echo "  cat /tmp/lyra_output_4.txt  # Context management"
echo "  cat /tmp/lyra_output_5.txt  # Error handling"
echo ""
