#!/bin/bash
# E2E Test for Lyra Deep Research with Team Orchestration

# Don't exit on error - we want to run all tests
set +e

echo "=========================================="
echo "LYRA E2E DEEP RESEARCH TEST"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# 1. Check Lyra installation
echo "1. Checking Lyra installation..."
if ly --version > /dev/null 2>&1; then
    VERSION=$(ly --version)
    test_result 0 "Lyra installed: $VERSION"
else
    test_result 1 "Lyra not installed"
    exit 1
fi
echo ""

# 2. Check DeepSeek configuration
echo "2. Checking DeepSeek configuration..."
if [ -z "$DEEPSEEK_API_KEY" ]; then
    test_result 1 "DEEPSEEK_API_KEY not set"
    echo -e "${YELLOW}⚠ Please export DEEPSEEK_API_KEY${NC}"
    exit 1
else
    test_result 0 "DEEPSEEK_API_KEY configured"
fi
echo ""

# 3. Check doctor output
echo "3. Running Lyra doctor..."
if ly doctor > /tmp/lyra_doctor.txt 2>&1; then
    test_result 0 "Lyra doctor passed"
    echo "Doctor output:"
    cat /tmp/lyra_doctor.txt | head -20
else
    test_result 1 "Lyra doctor failed"
fi
echo ""

# 4. Test research command via interactive session
echo "4. Testing /research command..."
cat > /tmp/lyra_research_test.txt << 'EOF'
/research Python async patterns --depth quick
/exit
EOF

echo "Running: ly --model deepseek < /tmp/lyra_research_test.txt"
if ly --model deepseek < /tmp/lyra_research_test.txt > /tmp/lyra_research_output.txt 2>&1; then
    if grep -q "Research complete\|Sources analyzed\|Report" /tmp/lyra_research_output.txt; then
        test_result 0 "Research command executed"
        echo "Research output preview:"
        grep -A 5 "Research complete\|Sources analyzed" /tmp/lyra_research_output.txt | head -10
    else
        test_result 1 "Research command did not complete"
        echo "Output:"
        tail -20 /tmp/lyra_research_output.txt
    fi
else
    test_result 1 "Research command timed out or failed"
    echo "Output:"
    tail -20 /tmp/lyra_research_output.txt
fi
echo ""

# 5. Test team orchestration
echo "5. Testing /team command..."
cat > /tmp/lyra_team_test.txt << 'EOF'
/team
/exit
EOF

echo "Running: ly --model deepseek < /tmp/lyra_team_test.txt"
if ly --model deepseek < /tmp/lyra_team_test.txt > /tmp/lyra_team_output.txt 2>&1; then
    if grep -q "team\|role\|LEAD\|RESEARCHER" /tmp/lyra_team_output.txt; then
        test_result 0 "Team command available"
        echo "Team output preview:"
        grep -i "team\|role" /tmp/lyra_team_output.txt | head -10
    else
        test_result 1 "Team command not found"
        echo "Output:"
        tail -20 /tmp/lyra_team_output.txt
    fi
else
    test_result 1 "Team command timed out or failed"
fi
echo ""

# 6. Check skills system
echo "6. Checking skills system..."
if ly skill list > /tmp/lyra_skills.txt 2>&1; then
    test_result 0 "Skills system available"
    echo "Installed skills:"
    cat /tmp/lyra_skills.txt | head -10
else
    test_result 1 "Skills system failed"
fi
echo ""

# 7. Check memory system
echo "7. Checking memory system..."
if ly memory --help > /tmp/lyra_memory.txt 2>&1; then
    test_result 0 "Memory system available"
else
    test_result 1 "Memory system failed"
fi
echo ""

# Summary
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}⚠ Some tests failed${NC}"
    exit 1
fi
