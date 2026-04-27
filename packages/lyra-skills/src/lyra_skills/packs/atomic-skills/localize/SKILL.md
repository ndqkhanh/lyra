---
id: localize
name: Localize
description: Find the smallest set of files / symbols relevant to a task before editing.
---

Use this skill first on any non-trivial task.

1. Read the user ask, extract 2–5 keywords.
2. Run `Grep` for each keyword; collect matching files.
3. Score candidates by (tests exist, recently edited, small module).
4. Return a ranked shortlist with 1–2 sentences each on why it's relevant.

Do NOT open every match eagerly — progressive disclosure keeps the context small.
