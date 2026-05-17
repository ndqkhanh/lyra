# Evolution Workspace

This directory contains the meta-evolution framework for Lyra.

## Structure

```
.lyra/evolution/
├── archive/           (immutable, append-only)
│   ├── candidates/    (candidate configurations)
│   ├── scores/        (evaluation results)
│   └── meta_edits/    (meta-agent edit logs)
├── workspace/         (read-write for agent)
└── evaluator/         (read-only for agent)
```

## Permissions

- **Agent**: read `archive/`, read-write `workspace/`
- **Evaluator**: write `archive/scores/`, read `evaluator/`
- **Harness**: orchestrates both, owns `archive/meta_edits/`

## Usage

See `LYRA_EVOLUTION_IMPROVEMENT_ULTRA_PLAN.md` for full implementation plan.
