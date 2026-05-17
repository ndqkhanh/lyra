# Evolution Permission Model

## Overview

The evolution harness enforces capability boundaries through permission splits to prevent reward hacking and ensure safe meta-evolution.

## Permission Layers

### Agent Layer
**Capabilities:**
- Read from `archive/candidates/`, `archive/scores/`, `archive/meta_edits/`
- Read-write access to `workspace/`
- Submit candidates via harness API (write-only)

**Restrictions:**
- Cannot read `evaluator/` internals
- Cannot modify `archive/` (append-only via harness)
- Cannot read back submitted scores

### Evaluator Layer
**Capabilities:**
- Read from `evaluator/` (test cases, ground truth)
- Write to `archive/scores/` (evaluation results)

**Restrictions:**
- Cannot access `workspace/`
- Cannot read candidate implementations directly

### Harness Layer
**Capabilities:**
- Full orchestration authority
- Write to `archive/meta_edits/` (audit trail)
- Mediate all agent-evaluator interactions

**Restrictions:**
- None (trusted component)

## Implementation Strategy

### Phase 1 (Current)
- Logical separation via path validation
- Harness enforces boundaries in code

### Phase 2 (Future)
- OS-level permissions (file system ACLs)
- Separate user accounts for agent/evaluator
- Sandboxed execution (Docker/chroot)

## Verification

To verify permission boundaries:
1. Agent attempts to read `evaluator/` → should fail
2. Agent attempts to write `archive/scores/` → should fail
3. Agent attempts to read submitted score → should fail
4. Evaluator attempts to read `workspace/` → should fail

## Security Notes

- Current implementation uses path validation (not OS-level enforcement)
- Suitable for development and testing
- Production deployment should use OS-level sandboxing
- See AEVO paper (arXiv:2605.13821) for threat model
