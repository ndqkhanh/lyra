---
id: rename-symbol
name: Rename Symbol
description: Rename a variable, function, or class for clarity across the entire codebase.
keywords:
  - rename
  - rename symbol
  - rename variable
  - rename function
  - refactor name
---

1. Identify the symbol with an unclear or misleading name.
2. Choose a name that describes what the symbol represents, not how it's used.
3. Use the IDE/LSP rename refactoring to propagate across all references.
4. Update any documentation or comments that reference the old name.
5. Run the full test suite to catch any missed references.
