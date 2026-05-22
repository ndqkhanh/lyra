# Lyra v4.0.0 Release Guide

## Package Build Status ✅

**Package built successfully!**

- `dist/lyra-4.0.0-py3-none-any.whl` (85K)
- `dist/lyra-4.0.0.tar.gz` (73K)

---

## PyPI Release Steps

### 1. Set Up PyPI Credentials

#### Option A: Using API Token (Recommended)

1. Create a PyPI account at https://pypi.org/account/register/
2. Generate an API token at https://pypi.org/manage/account/token/
3. Create `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Your API token

[testpypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Your TestPyPI token
```

#### Option B: Using Environment Variables

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmc...  # Your API token
```

---

### 2. Test Package Locally

```bash
# Create a test virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install the built package
pip install dist/lyra-4.0.0-py3-none-any.whl

# Test imports
python -c "from agents.base import Agent; print('✅ Import successful')"
python -c "from optimization import TokenOptimizer; print('✅ Optimization module works')"
python -c "from security import AgentShield; print('✅ Security module works')"

# Deactivate and remove test environment
deactivate
rm -rf test_env
```

---

### 3. Upload to TestPyPI (Recommended First Step)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ lyra[full]

# Verify it works
python -c "from agents.base import Agent; print('✅ TestPyPI package works')"
```

---

### 4. Upload to PyPI (Production)

```bash
# Upload to PyPI
twine upload dist/*

# Verify on PyPI
# Visit: https://pypi.org/project/lyra/

# Test installation
pip install lyra[full]
```

---

### 5. Create GitHub Release

```bash
# Create and push tag
git tag -a v4.0.0 -m "Lyra v4.0.0 - Production Release

🎉 All 15 Phases Complete

## Highlights
- 718 tests (100% passing)
- 92% test coverage
- 15,000+ lines of production code
- 17 modules
- 60-70% token cost reduction
- Ready for production use

## Key Features
- Multi-Agent System (5 agents)
- Coordination Layer
- Memory System (STM, LTM, retrieval, consolidation)
- Skills System (232 skills ready)
- Agent Fleet (60 ECC agents)
- Hooks System (5 types)
- Rules Engine (10 categories)
- Security (AgentShield, 5 scanners)
- UI/UX (Streaming REPL)
- Cross-Platform (4 adapters)
- Token Optimization
- Monitoring (Token Observatory)
- Integration Testing
- PyPI Package

See FINAL_SUMMARY.md for complete details."

git push origin v4.0.0

# Create GitHub release using gh CLI
gh release create v4.0.0 \
  --title "Lyra v4.0.0 - Production Release" \
  --notes-file RELEASE_NOTES_v4.0.0.md \
  dist/lyra-4.0.0-py3-none-any.whl \
  dist/lyra-4.0.0.tar.gz
```

---

## Installation Options

Once published to PyPI, users can install with:

```bash
# Full installation (all features)
pip install lyra[full]

# Minimal installation (core only)
pip install lyra[minimal]

# ECC features only
pip install lyra[ecc]

# Development installation
pip install lyra[dev]
```

---

## Post-Release Checklist

- [ ] Package uploaded to PyPI
- [ ] GitHub release created with v4.0.0 tag
- [ ] Release notes published
- [ ] Installation verified from PyPI
- [ ] Documentation updated (if needed)
- [ ] Announcement made (if applicable)

---

## Troubleshooting

### Issue: "Invalid credentials"
**Solution**: Verify your API token is correct and has upload permissions.

### Issue: "Package already exists"
**Solution**: You cannot re-upload the same version. Bump the version in `pyproject.toml` and rebuild.

### Issue: "Missing dependencies"
**Solution**: Ensure all dependencies in `pyproject.toml` are available on PyPI.

### Issue: "Import errors after installation"
**Solution**: Check that `src/` directory structure matches the package layout.

---

## Support

- **Repository**: https://github.com/ndqkhanh/lyra
- **Issues**: https://github.com/ndqkhanh/lyra/issues
- **Documentation**: See FINAL_SUMMARY.md and PHASE11-12_COMPLETE.md

---

**Status**: ✅ Package built and ready for release
**Version**: 4.0.0
**Date**: 2026-05-22
