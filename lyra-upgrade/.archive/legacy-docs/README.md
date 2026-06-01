# Lyra Testing Documentation

> Comprehensive testing framework for Lyra's research workflows

## Overview

This directory contains complete testing documentation for Lyra's research system, including deep research, auto research, scientist research, and AI research workflows with DeepSeek API integration.

## Documents

### 1. [Comprehensive Testing Plan](./comprehensive-testing-plan.md) ⭐ NEW

**Status**: ✅ Complete  
**Lines**: 2,480  
**Sections**: 106 main sections, 47 subsections

**Ultra-deep testing strategy** with complete specifications:

- **128 Unit Tests** - Individual component testing
- **52 Integration Tests** - Component interaction testing  
- **20 E2E Tests** - Complete workflow testing
- **DeepSeek Integration** - Cost-optimized model routing
- **Performance Benchmarks** - Latency, throughput, memory targets
- **12-Week Implementation Roadmap** - Phased rollout plan
- **CI/CD Integration** - GitHub Actions workflows
- **Complete Code Examples** - Ready-to-implement tests

### 2. [Research Workflows Testing](./RESEARCH-WORKFLOWS-TESTING.md)

**Status**: ✅ Complete  
**Lines**: 2,110

Detailed testing strategy for research workflows including:

- Testing architecture and organization
- Deep research testing (multi-hop, source chaining, synthesis)
- Auto research testing (citations, self-healing, debate, evolution)
- Scientist research testing (hypothesis, experiments, analysis)
- AI research testing (paper analysis, code analysis, techniques)
- DeepSeek API integration testing
- Test execution plans and infrastructure

## Test Coverage Goals

| Workflow | Unit Tests | Integration Tests | E2E Tests | Total | Coverage Target |
|----------|-----------|-------------------|-----------|-------|-----------------|
| Deep Research | 35 | 12 | 5 | 52 | 85% |
| Auto Research | 28 | 10 | 4 | 42 | 85% |
| Scientist Research | 20 | 8 | 3 | 31 | 80% |
| AI Research | 18 | 8 | 3 | 29 | 80% |
| Model Routing | 15 | 6 | 2 | 23 | 90% |
| DeepSeek Integration | 12 | 8 | 3 | 23 | 90% |
| **Total** | **128** | **52** | **20** | **200** | **85%** |

## Quick Start

### Running Tests

```bash
# Run all unit tests
pytest packages/*/tests/unit/ -v

# Run integration tests
pytest packages/*/tests/integration/ -v

# Run E2E tests
pytest packages/*/tests/e2e/ -v --slow

# Run with coverage
pytest packages/*/tests/ --cov --cov-report=html

# Run specific workflow tests
pytest packages/lyra-research/tests/ -v
pytest packages/lyra-autoresearch/tests/ -v
pytest packages/lyra-science-pipeline/tests/ -v
```

### Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# E2E tests (slow)
pytest -m "e2e and slow"

# DeepSeek-specific tests
pytest -m deepseek

# Performance benchmarks
pytest -m benchmark

# Cost tracking tests
pytest -m cost
```

## Implementation Status

### Phase 1: Foundation (Weeks 1-2) - 🟡 In Progress
- [x] Test infrastructure setup
- [x] Core fixtures and mocks
- [ ] Complete orchestrator unit tests (12/12)
- [ ] Complete discovery unit tests (8/8)

### Phase 2: Auto Research (Weeks 3-4) - ⏳ Planned
- [ ] Citation verification tests (8/8)
- [ ] Self-healing execution tests (8/8)
- [ ] Debate system tests (6/6)
- [ ] Evolution engine tests (6/6)

### Phase 3: Scientist & AI Research (Weeks 5-6) - ⏳ Planned
- [ ] Hypothesis generation tests (7/7)
- [ ] Experiment design tests (7/7)
- [ ] Paper analysis tests (6/6)
- [ ] Code analysis tests (6/6)

### Phase 4: DeepSeek Integration (Weeks 7-8) - ⏳ Planned
- [ ] DeepSeek API client tests (4/4)
- [ ] Model routing tests (8/8)
- [ ] Cost tracking tests (4/4)
- [ ] Performance benchmarks (8/8)

### Phase 5: E2E Testing (Weeks 9-10) - ⏳ Planned
- [ ] Complete research session tests (5/5)
- [ ] Autonomous loop tests (4/4)
- [ ] Cost-optimized research tests (5/5)

### Phase 6: Optimization (Weeks 11-12) - ⏳ Planned
- [ ] Test suite optimization
- [ ] Documentation completion
- [ ] Team handoff

## Performance Targets

### Latency Benchmarks

| Operation | Target | Acceptable | Critical |
|-----------|--------|------------|----------|
| Discovery (per source) | <5s | <10s | >15s |
| Analysis (per paper) | <3s | <5s | >10s |
| Synthesis | <10s | <20s | >30s |
| Report generation | <15s | <30s | >60s |
| Model routing | <50ms | <100ms | >200ms |
| DeepSeek invocation | <500ms | <1s | >2s |

### Cost Targets (DeepSeek)

| Research Depth | Target | Acceptable | Critical |
|----------------|--------|------------|----------|
| Quick (10 sources) | <$0.50 | <$1.00 | >$2.00 |
| Standard (30 sources) | <$1.50 | <$3.00 | >$5.00 |
| Deep (50+ sources) | <$3.00 | <$6.00 | >$10.00 |

## Test Infrastructure

### Configuration Files

- `pytest.ini` - Pytest configuration
- `conftest.py` - Global fixtures
- `mocks.py` - Mock implementations
- `test_data.py` - Test data generators
- `.env.test` - Test environment variables

### CI/CD

- GitHub Actions workflows for automated testing
- Pre-commit hooks for local testing
- Coverage reporting with Codecov
- Performance benchmarking with pytest-benchmark

## Contributing

### Adding New Tests

1. Identify the component and test type (unit/integration/e2e)
2. Create test file in appropriate directory
3. Use existing fixtures and mocks
4. Follow naming conventions (`test_*.py`)
5. Add appropriate pytest markers
6. Update coverage targets

### Test Naming Conventions

```python
# Unit tests
def test_<component>_<functionality>_<scenario>():
    """Test <what is being tested>."""
    
# Integration tests
@pytest.mark.integration
def test_<component1>_to_<component2>_<scenario>():
    """Test <integration flow>."""
    
# E2E tests
@pytest.mark.e2e
@pytest.mark.slow
def test_<workflow>_<scenario>():
    """Test <complete workflow>."""
```

### Test Quality Standards

- ✅ Independent and isolated
- ✅ Deterministic (no flaky tests)
- ✅ Fast execution (<1s for unit tests)
- ✅ Clear assertions and error messages
- ✅ Proper cleanup (fixtures, temp files)
- ✅ Documented with docstrings

## Resources

### Documentation
- [Comprehensive Testing Plan](./comprehensive-testing-plan.md) - Complete testing framework (2,480 lines)
- [Research Workflows Testing](./RESEARCH-WORKFLOWS-TESTING.md) - Workflow-specific testing (2,110 lines)

### External Resources
- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)

## Support

For questions or issues:
- Review existing test examples in the codebase
- Check the comprehensive testing plan for guidance
- Consult the team testing lead

---

**Last Updated**: 2026-05-29  
**Maintained By**: Lyra Testing Team  
**Status**: Active Development
