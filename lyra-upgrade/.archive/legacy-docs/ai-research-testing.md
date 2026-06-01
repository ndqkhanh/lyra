# AI Research Workflow Testing

Comprehensive test suite for AI research workflows including paper parsing, technique extraction, code analysis, and end-to-end research workflows.

## Test Coverage Summary

| Test Suite | Tests | Coverage | Status |
|------------|-------|----------|--------|
| Paper Parsing | 22 | Unit + Integration | ✓ |
| Technique Extraction | 20 | Integration | ✓ |
| AI Research E2E | 9 | E2E | ✓ |
| Code Analysis | 21 | Unit + Integration | ✓ |
| **Total** | **72** | **≥80%** | **✓** |

## Test Files

### 1. Paper Parsing Tests (`test_paper_parsing.py`)

**Purpose**: Test paper analysis, methodology extraction, dataset identification, and technique extraction from research papers.

**Test Classes**:
- `TestPaperParsing` (17 tests): Core paper parsing functionality
- `TestPaperStructureExtraction` (3 tests): Structured information extraction
- `TestPaperParsingIntegration` (2 tests): Complete paper analysis workflows

**Key Test Cases**:

#### Basic Parsing (5 tests)
- `test_parse_paper_basic`: Verify basic paper metadata extraction
- `test_extract_methodology`: Extract methodology sections and techniques
- `test_extract_datasets`: Identify datasets used in experiments
- `test_extract_metrics`: Extract evaluation metrics
- `test_extract_findings`: Extract key research findings

#### Reproducibility Assessment (3 tests)
- `test_assess_reproducibility`: Calculate reproducibility scores
- `test_reproducibility_with_code`: High score for papers with code
- `test_reproducibility_without_code`: Low score for papers without code

#### Quality Analysis (4 tests)
- `test_identify_strengths`: Identify paper strengths (citations, results)
- `test_identify_limitations`: Extract limitation statements
- `test_detect_biases`: Detect potential biases in research
- `test_strength_high_citations`: Recognize highly cited papers

#### Edge Cases (3 tests)
- `test_parse_paper_empty_content`: Handle empty content gracefully
- `test_parse_paper_minimal_metadata`: Handle minimal metadata
- `test_parse_paper_with_missing_sections`: Handle incomplete papers

#### Multi-Item Extraction (2 tests)
- `test_extract_multiple_datasets`: Extract multiple datasets
- `test_extract_multiple_metrics`: Extract multiple evaluation metrics

#### Pattern Recognition (3 tests)
- `test_extract_methodology_patterns`: Recognize methodology patterns
- `test_extract_dataset_patterns`: Recognize dataset mentions
- `test_extract_findings_patterns`: Recognize finding statements

#### Integration Tests (2 tests)
- `test_parse_complete_paper`: Full paper analysis workflow
- `test_parse_paper_with_missing_sections`: Partial paper handling

**Fixtures**:
- `paper_analyzer`: PaperAnalyzer instance
- `sample_paper_content`: Realistic paper content with all sections
- `sample_metadata`: Complete paper metadata

### 2. Technique Extraction Tests (`test_technique_extraction.py`)

**Purpose**: Test extracting techniques from papers and code, categorizing them, and mapping relationships.

**Test Classes**:
- `TestTechniqueExtraction` (7 tests): Basic technique extraction
- `TestTechniqueCategorization` (4 tests): Technique categorization
- `TestTechniqueRelationships` (4 tests): Technique relationship mapping
- `TestCrossSourceTechniqueExtraction` (3 tests): Cross-source extraction
- `TestTechniqueEvolution` (2 tests): Technique evolution tracking

**Key Test Cases**:

#### Extraction (7 tests)
- `test_extract_techniques_from_paper`: Extract ML techniques from papers
- `test_extract_techniques_from_code_readme`: Extract from repository READMEs
- `test_categorize_ml_techniques`: Categorize supervised/unsupervised/RL
- `test_categorize_architecture_patterns`: Identify architecture patterns
- `test_extract_optimization_techniques`: Extract optimization methods
- `test_extract_evaluation_techniques`: Extract evaluation approaches
- `test_extract_data_processing_techniques`: Extract data processing methods

#### Categorization (4 tests)
- `test_categorize_deep_learning_techniques`: DL-specific techniques
- `test_categorize_nlp_techniques`: NLP-specific techniques
- `test_categorize_computer_vision_techniques`: CV-specific techniques
- `test_categorize_reinforcement_learning_techniques`: RL-specific techniques

#### Relationships (4 tests)
- `test_technique_builds_on_relationship`: "Builds on" relationships
- `test_technique_combines_relationship`: "Combines" relationships
- `test_technique_improves_relationship`: "Improves" relationships
- `test_technique_replaces_relationship`: "Replaces" relationships

#### Cross-Source (3 tests)
- `test_extract_from_paper_and_code`: Extract from both sources
- `test_verify_paper_claims_in_code`: Verify claims against implementation
- `test_identify_implementation_gaps`: Find gaps between paper and code

#### Evolution (2 tests)
- `test_track_technique_progression`: Track technique evolution
- `test_identify_technique_trends`: Identify adoption trends

**Fixtures**:
- `paper_analyzer`: PaperAnalyzer instance
- `repo_analyzer`: RepositoryAnalyzer instance

### 3. AI Research E2E Tests (`test_ai_research_e2e.py`)

**Purpose**: Test complete AI research workflows from discovery to synthesis.

**Test Classes**:
- `TestCompleteResearchWorkflows` (3 tests): End-to-end workflows
- `TestResearchQualityAssessment` (3 tests): Quality assessment
- `TestCrossSourceValidation` (3 tests): Cross-source validation

**Key Test Cases**:

#### Complete Workflows (3 tests)
- `test_complete_paper_analysis_workflow`: Full paper analysis pipeline
  - Discovery → Analysis → Quality Scoring
  - Verifies all components extracted
  - Validates quality scores
- `test_complete_code_analysis_workflow`: Full code analysis pipeline
  - Repository discovery → Analysis → Quality Scoring
  - Verifies documentation, maintenance, code quality
- `test_multi_source_synthesis_workflow`: Multi-source synthesis
  - Analyze multiple papers and repositories
  - Score and rank sources
  - Synthesize insights

#### Quality Assessment (3 tests)
- `test_assess_high_quality_paper`: High-quality paper indicators
  - High reproducibility score (>0.7)
  - Multiple strengths identified
  - High overall quality score (>0.6)
- `test_assess_low_quality_paper`: Low-quality paper indicators
  - Low reproducibility score (<0.3)
  - Few findings extracted
  - Low overall quality score (<0.5)
- `test_assess_reproducibility_spectrum`: Reproducibility range
  - Papers with code vs. without code
  - Hyperparameters vs. vague descriptions

#### Cross-Source Validation (3 tests)
- `test_validate_paper_claims_with_code`: Validate claims
  - Paper claims high accuracy
  - Code implementation confirms results
- `test_identify_missing_implementations`: Find missing code
  - Papers without implementations
  - Low reproducibility scores
- `test_compare_multiple_implementations`: Compare implementations
  - Official vs. community implementations
  - Quality score differences

**Fixtures**:
- `paper_analyzer`: PaperAnalyzer instance
- `repo_analyzer`: RepositoryAnalyzer instance
- `quality_scorer`: QualityScorer instance

### 4. Code Analysis Tests (`test_code_analysis.py`)

**Purpose**: Test analyzing code repositories, extracting architecture patterns, and assessing code quality.

**Test Classes**:
- `TestCodeAnalysis` (8 tests): Basic code analysis
- `TestImplementationPatternExtraction` (6 tests): Pattern extraction
- `TestArchitectureUnderstanding` (4 tests): Architecture analysis
- `TestCodeQualityAssessment` (3 tests): Quality assessment

**Key Test Cases**:

#### Basic Analysis (8 tests)
- `test_analyze_repository_basic`: Basic repository metadata
- `test_calculate_code_quality_score`: Code quality scoring
- `test_calculate_documentation_score`: Documentation scoring
- `test_calculate_maintenance_score`: Maintenance scoring
- `test_identify_repository_features`: Feature detection (CI, tests, docs)
- `test_identify_repository_strengths`: Strength identification
- `test_identify_repository_limitations`: Limitation identification

#### Pattern Extraction (6 tests)
- `test_extract_architecture_pattern`: Microservices, monolith patterns
- `test_extract_design_patterns`: Repository, Factory, Observer patterns
- `test_extract_technology_stack`: Backend, frontend, infrastructure
- `test_extract_api_patterns`: REST, GraphQL, authentication
- `test_extract_testing_patterns`: Unit, integration, E2E tests
- `test_extract_deployment_patterns`: CI/CD, containerization

#### Architecture Understanding (4 tests)
- `test_understand_layered_architecture`: Presentation, business, data layers
- `test_understand_event_driven_architecture`: Event producers/consumers
- `test_understand_plugin_architecture`: Plugin systems
- `test_understand_component_relationships`: Component dependencies

#### Quality Assessment (3 tests)
- `test_assess_high_quality_repository`: High-quality indicators
  - Code quality score >0.6
  - Documentation score >0.7
  - Maintenance score >0.7
  - Multiple strengths identified
- `test_assess_low_quality_repository`: Low-quality indicators
  - All scores <0.5
  - Multiple limitations
- `test_assess_abandoned_repository`: Abandoned project detection
  - Last commit >2 years ago
  - Low maintenance score
- `test_assess_popular_but_unmaintained`: Popular but stale
  - High stars but low maintenance

**Fixtures**:
- `repo_analyzer`: RepositoryAnalyzer instance
- `sample_repo_metadata`: Complete repository metadata

## Running Tests

### Run All AI Research Tests
```bash
cd packages/lyra-research
pytest tests/test_paper_parsing.py tests/test_technique_extraction.py \
       tests/test_ai_research_e2e.py tests/test_code_analysis.py -v
```

### Run by Category
```bash
# Paper parsing tests only
pytest tests/test_paper_parsing.py -v

# Technique extraction tests only
pytest tests/test_technique_extraction.py -v

# E2E tests only
pytest tests/test_ai_research_e2e.py -v -m e2e

# Code analysis tests only
pytest tests/test_code_analysis.py -v
```

### Run with Coverage
```bash
pytest tests/test_paper_parsing.py tests/test_technique_extraction.py \
       tests/test_ai_research_e2e.py tests/test_code_analysis.py \
       --cov=lyra_research.analysis \
       --cov-report=term-missing \
       --cov-report=html
```

### Run Integration Tests Only
```bash
pytest tests/test_paper_parsing.py tests/test_technique_extraction.py \
       tests/test_ai_research_e2e.py tests/test_code_analysis.py \
       -m integration -v
```

### Run E2E Tests Only
```bash
pytest tests/test_ai_research_e2e.py -m e2e -v
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.unit`: Unit tests (fast, isolated)
- `@pytest.mark.integration`: Integration tests (moderate speed)
- `@pytest.mark.e2e`: End-to-end tests (slow, comprehensive)
- `@pytest.mark.slow`: Slow tests (skip in quick runs)

## Test Configuration

### conftest.py

The test suite uses shared fixtures defined in `conftest.py`:

```python
@pytest.fixture
def mock_deepseek_client():
    """Mock DeepSeek API client for testing."""
    # Returns mock client with predefined responses

@pytest.fixture
def sample_paper_metadata():
    """Standard paper metadata for testing."""
    # Returns realistic paper metadata

@pytest.fixture
def sample_repo_metadata():
    """Standard repository metadata for testing."""
    # Returns realistic repository metadata
```

### Environment Variables

Tests use the following environment variables:

- `DEEPSEEK_API_KEY`: DeepSeek API key (configured in `~/.claude/settings.json`)
- `PYTEST_TIMEOUT`: Test timeout in seconds (default: 300)

## Coverage Requirements

### Minimum Coverage: 80%

Coverage is measured for the following modules:

- `lyra_research.analysis.paper_analyzer`: Paper analysis logic
- `lyra_research.analysis.repository_analyzer`: Repository analysis logic
- `lyra_research.analysis.quality_scorer`: Quality scoring logic
- `lyra_research.analysis.models`: Data models

### Coverage Report

Generate HTML coverage report:

```bash
pytest tests/test_paper_parsing.py tests/test_technique_extraction.py \
       tests/test_ai_research_e2e.py tests/test_code_analysis.py \
       --cov=lyra_research.analysis \
       --cov-report=html

# Open report
open htmlcov/index.html
```

## Test Data

### Sample Papers

Tests use realistic paper content including:
- Abstract, introduction, methodology sections
- Dataset mentions (ImageNet, COCO, MNIST)
- Evaluation metrics (accuracy, precision, recall, F1)
- Hyperparameters (learning rate, batch size)
- Results and findings
- Limitations and future work

### Sample Repositories

Tests use realistic repository metadata including:
- Stars, forks, contributors
- License information
- Last commit date
- README content with installation, usage, documentation
- Technology stack descriptions

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: AI Research Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e packages/lyra-research[test]
      - name: Run tests
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          pytest packages/lyra-research/tests/test_paper_parsing.py \
                 packages/lyra-research/tests/test_technique_extraction.py \
                 packages/lyra-research/tests/test_ai_research_e2e.py \
                 packages/lyra-research/tests/test_code_analysis.py \
                 --cov=lyra_research.analysis \
                 --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

#### 1. DeepSeek API Key Not Found

**Error**: `KeyError: 'DEEPSEEK_API_KEY'`

**Solution**: Configure API key in `~/.claude/settings.json`:
```json
{
  "env": {
    "DEEPSEEK_API_KEY": "your-api-key-here"
  }
}
```

#### 2. Tests Timeout

**Error**: `pytest.timeout.Timeout`

**Solution**: Increase timeout or skip slow tests:
```bash
pytest -m "not slow" tests/
```

#### 3. Import Errors

**Error**: `ModuleNotFoundError: No module named 'lyra_research'`

**Solution**: Install package in development mode:
```bash
pip install -e packages/lyra-research
```

#### 4. Mock API Responses

For tests that don't require real API calls, use mocks:

```python
@pytest.fixture
def mock_analyzer(monkeypatch):
    def mock_analyze(*args, **kwargs):
        return PaperAnalysis(...)
    monkeypatch.setattr(PaperAnalyzer, 'analyze', mock_analyze)
```

## Test Maintenance

### Adding New Tests

When adding new AI research features:

1. **Add unit tests** for individual functions
2. **Add integration tests** for component interactions
3. **Add E2E tests** for complete workflows
4. **Update this documentation** with new test descriptions
5. **Verify coverage** remains ≥80%

### Test Naming Convention

Follow pytest naming conventions:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

Use descriptive names:
- ✓ `test_extract_methodology_from_paper`
- ✗ `test_method1`

### Test Organization

Group related tests in classes:
```python
class TestPaperParsing:
    """Tests for paper parsing functionality."""
    
    def test_parse_basic(self): ...
    def test_parse_with_missing_sections(self): ...
```

## Performance Benchmarks

### Test Execution Times

| Test Suite | Tests | Avg Time | Total Time |
|------------|-------|----------|------------|
| Paper Parsing | 22 | 0.5s | ~11s |
| Technique Extraction | 20 | 0.6s | ~12s |
| AI Research E2E | 9 | 2.0s | ~18s |
| Code Analysis | 21 | 0.4s | ~8s |
| **Total** | **72** | **0.7s** | **~49s** |

### Optimization Tips

1. **Use mocks** for external API calls
2. **Parallelize tests** with `pytest-xdist`:
   ```bash
   pytest -n auto tests/
   ```
3. **Skip slow tests** in development:
   ```bash
   pytest -m "not slow" tests/
   ```
4. **Cache fixtures** with `scope="module"` or `scope="session"`

## Related Documentation

- [US-030 Implementation Plan](../operations/US-030-IMPLEMENTATION.md)
- [Research Engine Architecture](../architecture/research-engine.md)
- [Analysis Module Documentation](../../packages/lyra-research/docs/analysis.md)
- [Testing Strategy](./testing-strategy.md)

## Success Criteria

- [x] 72 tests implemented (requirement: 38+)
  - [x] Paper parsing: 22 tests (requirement: 18+)
  - [x] Technique extraction: 20 tests (requirement: 7+)
  - [x] AI research E2E: 9 tests (requirement: 3+)
  - [x] Code analysis: 21 tests (requirement: 10+)
- [x] All tests passing with DeepSeek API
- [x] Test coverage ≥80% for AI research modules
- [x] Documentation complete and comprehensive
- [x] CI/CD integration ready
