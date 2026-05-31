# lyra-workflow — Dynamic Workflow Engine + AVP

Lyra's "ultracode" equivalent. Code-driven background workflows with adversarial cross-checking.

| Component | Purpose |
|-----------|---------|
| `WorkflowEngine` | Background executor, 16-concurrent cap, pause/resume |
| `ScriptVM` | Static analysis for workflow script safety |
| `AdversarialVerifier` | 3-critic cross-model verification (SABER + AutoScientists patterns) |
| `AutoOrchestrator` | Effort-driven workflow auto-trigger |

[Plan: plans/19-ultracode-replication.md](../../lyra-upgrade/plans/19-ultracode-replication.md)
