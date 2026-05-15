# Hotfix Report - CSS Error Fixed

## Issue

**Error:** Lyra failed to start with CSS parsing error
```
Invalid CSS property 'font-style'. Did you mean 'text-style'?
```

**Location:** `packages/lyra-cli/src/lyra_cli/tui_v2/sidebar/agents_tab.py:17`

---

## Root Cause

Textual CSS uses `text-style` instead of standard CSS `font-style`.

**Incorrect:**
```css
AgentsTab .agents-empty {
    color: $fg_muted;
    font-style: italic;  /* ❌ Wrong property */
}
```

**Correct:**
```css
AgentsTab .agents-empty {
    color: $fg_muted;
    text-style: italic;  /* ✅ Correct property */
}
```

---

## Fix Applied

**Commit:** `ce35f60b`
**File:** `packages/lyra-cli/src/lyra_cli/tui_v2/sidebar/agents_tab.py`
**Change:** Line 17 - Changed `font-style` to `text-style`

---

## Verification

✅ `ly --version` works
✅ `ly --help` works
✅ No other CSS issues found
✅ Hotfix pushed to GitHub

---

## Prevention Measures

### 1. Add CSS Linting

Create `.textual-lint.py`:
```python
"""Lint Textual CSS for common errors."""
import re
import sys
from pathlib import Path

INVALID_PROPERTIES = {
    'font-style': 'text-style',
    'font-weight': 'text-style',
    'font-size': 'text-style',
}

def lint_file(path: Path) -> list[str]:
    errors = []
    content = path.read_text()
    
    for line_num, line in enumerate(content.splitlines(), 1):
        for invalid, valid in INVALID_PROPERTIES.items():
            if invalid in line and 'DEFAULT_CSS' in content:
                errors.append(
                    f"{path}:{line_num}: Use '{valid}' instead of '{invalid}'"
                )
    
    return errors

if __name__ == '__main__':
    errors = []
    for py_file in Path('packages/lyra-cli/src').rglob('*.py'):
        errors.extend(lint_file(py_file))
    
    if errors:
        print('\n'.join(errors))
        sys.exit(1)
    print('✅ No CSS errors found')
```

### 2. Add Pre-commit Hook

Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: textual-css-lint
      name: Textual CSS Linter
      entry: python .textual-lint.py
      language: system
      pass_filenames: false
```

### 3. Add CI Check

Add to `.github/workflows/ci.yml`:
```yaml
- name: Lint Textual CSS
  run: python .textual-lint.py
```

### 4. Documentation

Add to `CONTRIBUTING.md`:
```markdown
## Textual CSS Guidelines

When writing Textual CSS in Python files:

**Use Textual properties:**
- ✅ `text-style: italic` (not `font-style`)
- ✅ `text-style: bold` (not `font-weight`)
- ✅ Use Textual's text-style for all text formatting

**Common mistakes:**
- ❌ `font-style: italic` → ✅ `text-style: italic`
- ❌ `font-weight: bold` → ✅ `text-style: bold`
- ❌ `font-size: 14px` → ✅ Use Textual's sizing system
```

---

## Testing Checklist

- [x] Fix applied
- [x] `ly --version` works
- [x] `ly --help` works
- [x] No other CSS issues found
- [x] Hotfix committed
- [x] Hotfix pushed to GitHub
- [ ] Add CSS linting (recommended)
- [ ] Add pre-commit hook (recommended)
- [ ] Update documentation (recommended)

---

## Summary

**Issue:** CSS property error preventing Lyra from starting
**Fix:** Changed `font-style` to `text-style` in AgentsTab
**Status:** ✅ Fixed and pushed
**Prevention:** Recommend adding CSS linting

**Commit:** `ce35f60b`
**Repository:** https://github.com/ndqkhanh/lyra
