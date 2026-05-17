---
name: git-workflow
description: Git workflow patterns and best practices
origin: ECC
tags: [git, workflow, version-control]
triggers: [git, commit, branch]
---

# Git Workflow

## Commit Message Format

```
<type>: <description>

<optional body>
```

Types: feat, fix, refactor, docs, test, chore, perf, ci

## Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Urgent production fixes

## Best Practices

- Commit often, push regularly
- Write clear commit messages
- Keep commits focused (one logical change)
- Review diffs before committing
- Never commit secrets
- Use `.gitignore` properly

## Pull Request Workflow

1. Create feature branch
2. Make changes and commit
3. Push to remote
4. Create PR with description
5. Address review comments
6. Merge when approved
