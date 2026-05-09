---
id: edit
name: Edit
description: Apply the smallest diff that makes a failing test pass.
---

1. Confirm a RED proof exists for the behaviour you're about to implement.
2. Read the current implementation; identify the single spot that needs to change.
3. Emit a diff that is smaller than the test (rule of thumb).
4. Run the focused test; iterate if it fails.
5. Run the surrounding module's tests before declaring GREEN.
