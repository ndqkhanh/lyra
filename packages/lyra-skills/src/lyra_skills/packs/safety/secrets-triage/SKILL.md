---
id: secrets-triage
name: Secrets Triage
description: Recognise and handle credential-shaped strings during read and write.
---

On detection of an AWS key, GitHub token, private SSH/PEM material, or JWT:

- Never echo it back into the transcript.
- Replace with `<redacted:KIND>` in the transcript.
- Emit `safety.secret.detected` with file + line (not value).
- If the detection is in a user message (accidentally pasted), ask the user
  to rotate and suppress from trace.
