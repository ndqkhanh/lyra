# Contributing to Lyra Reasoning

Thank you for your interest in contributing to Lyra Reasoning! This document provides guidelines and instructions for contributing.

## 🌟 Ways to Contribute

- **Bug Reports**: Report bugs through GitHub Issues
- **Feature Requests**: Suggest new features or improvements
- **Code Contributions**: Submit pull requests with bug fixes or new features
- **Documentation**: Improve documentation and examples
- **Testing**: Add or improve test coverage
- **Performance**: Optimize performance and efficiency

## 🚀 Getting Started

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/lyra.git
   cd lyra/projects/lyra/packages/lyra-reasoning
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/benchmarks/

# Run with coverage
pytest --cov=lyra_reasoning --cov-report=html

# Run with verbose output
pytest -v -s
```

### Code Style

We use:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **pylint** for linting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type check
mypy src/

# Lint
pylint src/
```

## 📝 Pull Request Process

1. **Fork the repository** and create a new branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Add tests** for new functionality

4. **Update documentation** if needed

5. **Run tests** to ensure everything passes
   ```bash
   pytest
   black --check src/ tests/
   mypy src/
   ```

6. **Commit your changes** with clear messages
   ```bash
   git commit -m "Add feature: description of your changes"
   ```

7. **Push to your fork** and submit a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

## 🎯 Coding Standards

### Python Style

- Follow PEP 8
- Use type hints for all functions
- Write docstrings for all public APIs
- Keep functions focused and small
- Use meaningful variable names

### Example

```python
from typing import List, Optional

def calculate_verification_score(
    steps: List[ReasoningStep],
    threshold: float = 0.7,
) -> float:
    """
    Calculate overall verification score from reasoning steps.
    
    Args:
        steps: List of reasoning steps to verify
        threshold: Minimum acceptable score (default: 0.7)
        
    Returns:
        Overall verification score between 0.0 and 1.0
        
    Raises:
        ValueError: If steps list is empty
    """
    if not steps:
        raise ValueError("Steps list cannot be empty")
    
    scores = [step.verification_score for step in steps]
    return sum(scores) / len(scores)
```

### Documentation

- Use Google-style docstrings
- Include type hints
- Provide examples for complex functions
- Keep documentation up-to-date with code changes

### Testing

- Write unit tests for all new functions
- Add integration tests for new features
- Maintain > 80% code coverage
- Use descriptive test names

```python
def test_verification_score_calculation():
    """Test that verification scores are calculated correctly."""
    steps = [
        ReasoningStep(content="Step 1", verification_score=0.8),
        ReasoningStep(content="Step 2", verification_score=0.9),
    ]
    
    score = calculate_verification_score(steps)
    
    assert score == 0.85
```

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Minimal code to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: Python version, OS, package versions
6. **Logs**: Relevant error messages or logs

### Bug Report Template

```markdown
**Description**
A clear description of the bug.

**To Reproduce**
```python
from lyra_reasoning import DeepReasoningAgent

agent = DeepReasoningAgent()
result = agent.reason(task="...", strategy="cot")
# Bug occurs here
```

**Expected Behavior**
What should happen.

**Actual Behavior**
What actually happens.

**Environment**
- Python version: 3.11
- OS: macOS 14.0
- lyra-reasoning version: 1.0.0

**Additional Context**
Any other relevant information.
```

## 💡 Feature Requests

When requesting features, please include:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other approaches you've considered
4. **Examples**: Code examples of how it would be used

### Feature Request Template

```markdown
**Use Case**
Describe the problem or need this feature addresses.

**Proposed Solution**
How should this feature work?

**Example Usage**
```python
# Example of how the feature would be used
agent = DeepReasoningAgent()
result = agent.new_feature(...)
```

**Alternatives**
Other approaches you've considered.

**Additional Context**
Any other relevant information.
```

## 🏗️ Architecture Guidelines

### Adding New Reasoning Engines

1. Create a new engine class in `src/lyra_reasoning/engines/`
2. Inherit from base engine interface
3. Implement required methods
4. Add tests in `tests/unit/test_engines.py`
5. Update documentation

```python
from .base import BaseReasoningEngine

class MyNewEngine(BaseReasoningEngine):
    """My new reasoning engine."""
    
    def reason(
        self,
        task: str,
        budget: ComputeBudget,
        config: ReasoningConfig,
    ) -> ReasoningTrace:
        """Execute reasoning."""
        # Implementation
        pass
```

### Adding New Verification Methods

1. Create verifier in `src/lyra_reasoning/verification/`
2. Implement verification logic
3. Integrate with VerificationSystem
4. Add tests
5. Update documentation

### Adding New Memory Features

1. Extend ReasoningMemory class
2. Add persistence logic
3. Update retrieval methods
4. Add tests
5. Update documentation

## 📚 Documentation

### Updating Documentation

- Keep README.md up-to-date
- Update API reference for new features
- Add examples for new functionality
- Update CHANGELOG.md

### Writing Examples

- Create clear, runnable examples
- Include comments explaining key concepts
- Show both basic and advanced usage
- Test examples to ensure they work

## 🔄 Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release tag
5. Build and publish to PyPI

## 🤝 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other unprofessional conduct

## 📞 Getting Help

- **Documentation**: Check the README and examples first
- **GitHub Issues**: Search existing issues
- **Discussions**: Ask questions in GitHub Discussions
- **Email**: contact@lyra-ai.dev

## 🙏 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for contributing to Lyra Reasoning! 🎉
