---
id: fuzz-test
name: Fuzz Test
description: Apply fuzz testing to find edge cases and crashes with random inputs.
keywords:
  - fuzz
  - fuzzing
  - fuzz test
  - random test
  - property test
  - hypothesis
  - quickcheck
---

1. Identify functions that parse, validate, or transform untrusted input.
2. Define invariants (properties) that should hold for all inputs.
3. Use a fuzzing library (hypothesis, fast-check, go-fuzz) to generate inputs.
4. Run until the first failure; minimise the failing input.
5. Add the minimised repro as a regression test.
