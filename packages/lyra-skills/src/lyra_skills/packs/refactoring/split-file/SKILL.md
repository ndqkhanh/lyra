---
id: split-file
name: Split File
description: Split a large file into smaller, cohesive modules.
keywords:
  - split file
  - split module
  - refactor module
  - large file
  - decompose file
---

1. Review the file; group related functions, classes, and constants into candidate modules.
2. Ensure each new module has a single responsibility.
3. Move code; update imports in the new module and all consumers.
4. Check for circular imports; use late imports or restructure if needed.
5. Run tests; verify the public API is unchanged.
