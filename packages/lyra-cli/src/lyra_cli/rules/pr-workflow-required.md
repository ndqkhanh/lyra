---
name: pr-workflow-required
description: Follow pull request workflow for all changes
category: GitWorkflow
severity: high
enabled: true
---

# PR Workflow Required

All changes must go through pull request workflow.

## Rule

When creating PRs:
1. Analyze full commit history (not just latest commit)
2. Use `git diff [base-branch]...HEAD` to see all changes
3. Draft comprehensive PR summary
4. Include test plan with TODOs
5. Push with `-u` flag if new branch

## Rationale

PR workflow enables code review, discussion, and quality control before merging.
