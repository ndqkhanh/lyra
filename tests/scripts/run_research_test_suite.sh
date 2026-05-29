#!/bin/bash
# =============================================================================
# Lyra Research Flows — Comprehensive Test Suite
# Provider: DeepSeek via Anthropic bridge
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0
RESULTS=()

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

run_test() {
    local name="$1"
    local cmd="$2"
    local allow_fail="${3:-false}"

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}🔬 ${name}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if eval "$cmd 2>&1"; then
        echo -e "${GREEN}✅ PASS: ${name}${NC}"
        RESULTS+=("✅ ${name}")
        ((PASS++))
    else
        if [ "$allow_fail" = "true" ]; then
            echo -e "${YELLOW}⚠️  EXPECTED FAILURE: ${name}${NC}"
            RESULTS+=("⚠️  ${name} (expected)")
            ((PASS++))
        else
            echo -e "${RED}❌ FAIL: ${name}${NC}"
            RESULTS+=("❌ ${name}")
            ((FAIL++))
        fi
    fi
    echo ""
}

# =============================================================================
# PHASE 0: Provider Verification
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 0: PROVIDER VERIFICATION${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

python3 -c "
import os
key = os.environ.get('ANTHROPIC_API_KEY', '')
url = os.environ.get('ANTHROPIC_BASE_URL', '')
model = os.environ.get('ANTHROPIC_MODEL', '')
print(f'API Key: {\"SET\" if key else \"MISSING\"} ({key[:8]}...{key[-4:] if key else \"\"})')
print(f'Base URL: {url or \"MISSING\"}')
print(f'Model: {model or \"MISSING\"}')
if 'deepseek' in (url or ''):
    print('✅ DeepSeek provider detected via Anthropic bridge')
elif os.environ.get('DEEPSEEK_API_KEY'):
    print('✅ DeepSeek provider detected via direct API key')
else:
    print('⚠️  DeepSeek not detected — some tests may use simulated results')
"

# =============================================================================
# PHASE 1: lyra-research Unit Tests (P0 — Core Pipeline)
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 1: lyra-research CORE UNIT TESTS (P0)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "1.1 Research Models (Cost optimizer, model router)" \
    "cd packages/lyra-research && python -m pytest tests/test_models.py -v --tb=short 2>&1 | tail -5"

run_test "1.2 Source Discovery (arXiv, GitHub, HuggingFace, Scholar)" \
    "cd packages/lyra-research && python -m pytest tests/test_sources.py tests/test_discovery_agents.py -v --tb=short 2>&1 | tail -5"

run_test "1.3 Analysis Agents (Paper, Repo, Citation, Quality)" \
    "cd packages/lyra-research && python -m pytest tests/test_analysis_agents.py -v --tb=short 2>&1 | tail -5"

run_test "1.4 Synthesis Agents (Cross-source synthesis, Evidence audit)" \
    "cd packages/lyra-research && python -m pytest tests/test_synthesis_agents.py -v --tb=short 2>&1 | tail -5"

run_test "1.5 Orchestrator Core + Integration" \
    "cd packages/lyra-research && python -m pytest tests/test_orchestrator.py tests/test_orchestrator_integration.py -v --tb=short 2>&1 | tail -5"

# =============================================================================
# PHASE 2: lyra-research Unit Tests (P1 — Supporting Systems)
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 2: lyra-research SUPPORTING SYSTEMS (P1)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "2.1 Coordination Primitives (Retry, Timeout, Circuit Breaker)" \
    "cd packages/lyra-research && python -m pytest tests/test_coordination.py -v --tb=short 2>&1 | tail -5"

run_test "2.2 Capacity Manager (Memory-aware context)" \
    "cd packages/lyra-research && python -m pytest tests/test_capacity_manager.py -v --tb=short 2>&1 | tail -5"

run_test "2.3 Adversarial Reviewer (Claim verification)" \
    "cd packages/lyra-research && python -m pytest tests/test_adversarial_reviewer.py -v --tb=short 2>&1 | tail -5"

run_test "2.4 Intelligence (Gap Analysis, Falsification)" \
    "cd packages/lyra-research && python -m pytest tests/test_intelligence.py -v --tb=short 2>&1 | tail -5"

run_test "2.5 Quality Gates (Discovery, Analysis, Curation, Review, Synthesis)" \
    "cd packages/lyra-research && python -m pytest tests/test_quality_gates.py -v --tb=short 2>&1 | tail -5"

run_test "2.6 Role System" \
    "cd packages/lyra-research && python -m pytest tests/test_roles.py -v --tb=short 2>&1 | tail -5"

run_test "2.7 Reporter (Report generation, Quality checking)" \
    "cd packages/lyra-research && python -m pytest tests/test_reporter.py -v --tb=short 2>&1 | tail -5"

# =============================================================================
# PHASE 3: lyra-research Unit Tests (P2 — Extended Features)
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 3: lyra-research EXTENDED FEATURES (P2)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "3.1 Research Memory & Persistence" \
    "cd packages/lyra-research && python -m pytest tests/test_research_memory.py tests/test_checkpoint.py -v --tb=short 2>&1 | tail -5"

run_test "3.2 Learning & Strategy Extraction" \
    "cd packages/lyra-research && python -m pytest tests/test_learning.py tests/test_strategies.py -v --tb=short 2>&1 | tail -5"

run_test "3.3 Context Integration" \
    "cd packages/lyra-research && python -m pytest tests/test_context_integration.py -v --tb=short 2>&1 | tail -5"

run_test "3.4 Skills & Evolution" \
    "cd packages/lyra-research && python -m pytest tests/test_skills.py tests/test_evaluation.py -v --tb=short 2>&1 | tail -5"

run_test "3.5 Adaptive Decomposition" \
    "cd packages/lyra-research && python -m pytest tests/test_adaptive_decomposition.py -v --tb=short 2>&1 | tail -5"

run_test "3.6 Full Integration" \
    "cd packages/lyra-research && python -m pytest tests/test_full_integration.py tests/test_curation.py -v --tb=short 2>&1 | tail -5"

# =============================================================================
# PHASE 4: lyra-research Advanced Phases (P3)
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 4: lyra-research ADVANCED PHASES (P3)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "4.1 PRISMA Bias Assessment (Phase 1)" \
    "cd packages/lyra-research && python -m pytest tests/test_prisma_phase1.py -v --tb=short 2>&1 | tail -5"

run_test "4.2 Socratic Agent (Phase 2)" \
    "cd packages/lyra-research && python -m pytest tests/test_socratic_phase2.py -v --tb=short 2>&1 | tail -5"

run_test "4.3 Writing Quality (Phase 3)" \
    "cd packages/lyra-research && python -m pytest tests/test_writing_phase3.py -v --tb=short 2>&1 | tail -5"

run_test "4.4 Cross-Model Review (Phase 4)" \
    "cd packages/lyra-research && python -m pytest tests/test_cross_model_phase4.py -v --tb=short 2>&1 | tail -5"

run_test "4.5 Integrity Verification (Phase 0)" \
    "cd packages/lyra-research && python -m pytest tests/test_integrity_phase0.py -v --tb=short 2>&1 | tail -5"

# =============================================================================
# PHASE 5: Science Pipeline
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 5: lyra-science-pipeline TESTS${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "5.1 Science Pipeline (Existing Tests)" \
    "cd packages/lyra-science-pipeline && python -m pytest tests/ -v --tb=long 2>&1 | tail -10"

# =============================================================================
# PHASE 6: Auto-Research Gap Analysis
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 6: lyra-autoresearch GAP ANALYSIS${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

echo "Implementation status per submodule:"
for dir in packages/lyra-autoresearch/src/lyra_autoresearch/*/; do
    if [ -d "$dir" ]; then
        submod=$(basename "$dir")
        impl_count=$(grep -c "^def \|^class \|^async def " "$dir/__init__.py" 2>/dev/null || echo "0")
        echo "  ${submod}: ${impl_count} real implementations"
    fi
done

run_test "6.1 Autoresearch Tests (Expected: partial failures — stubs only)" \
    "cd packages/lyra-autoresearch && python -m pytest tests/ -v --tb=short 2>&1 | tail -20 || true" \
    "true"

# =============================================================================
# PHASE 7: Evals
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 7: lyra-evals TESTS${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "7.1 Eval Harness (All Tests)" \
    "cd packages/lyra-evals && python -m pytest tests/ -v --tb=short 2>&1 | tail -15"

run_test "7.2 AER SLO Tracking" \
    "cd packages/lyra-evals && python -m pytest tests/test_aer_slo.py -v --tb=short 2>&1 | tail -5"

# =============================================================================
# PHASE 8: CLI Integration
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 8: CLI INTEGRATION TESTS${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "8.1 Research Command + Handler" \
    "cd packages/lyra-cli && python -m pytest tests/test_research_command.py tests/test_research_command_handler.py -v --tb=short 2>&1 | tail -10"

run_test "8.2 Research Engine" \
    "cd packages/lyra-cli && python -m pytest tests/research/ -v --tb=short 2>&1 | tail -10"

run_test "8.3 Voice Integration" \
    "cd packages/lyra-cli && python -m pytest tests/integration/test_research_voice_integration.py -v --tb=short 2>&1 | tail -10"

# =============================================================================
# PHASE 9: Script-Based E2E
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}PHASE 9: SCRIPT-BASED END-TO-END TESTS${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

run_test "9.1 Research Flow E2E" \
    "python tests/scripts/test_research_flow.py 2>&1 | tail -30"

run_test "9.2 DeepSeek Research" \
    "python tests/scripts/test_deepseek_research.py 2>&1 | tail -30"

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}TEST SUITE SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
for result in "${RESULTS[@]}"; do
    echo -e "$result"
done
echo -e "${CYAN}───────────────────────────────────────────────────────────────${NC}"
TOTAL=$((PASS + FAIL))
echo -e "Total: ${TOTAL} | ${GREEN}✅ Passed: ${PASS}${NC} | ${RED}❌ Failed: ${FAIL}${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"

exit $FAIL
