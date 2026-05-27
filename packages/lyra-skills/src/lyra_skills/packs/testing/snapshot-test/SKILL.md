---
id: snapshot-test
name: Snapshot Test
description: Use snapshot testing to catch unintended changes in output structures.
keywords:
  - snapshot
  - snapshot test
  - regression test
  - visual diff
  - output test
---

1. Identify stable output structures (API responses, rendered components, serialized data).
2. Generate a snapshot on the first run; commit it to version control.
3. On subsequent runs, compare output to the snapshot; fail on mismatch.
4. Review snapshot diffs carefully before updating; snapshots are part of the review.
5. Keep snapshots small and focused; avoid snapshotting large, volatile structures.
