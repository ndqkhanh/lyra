# hello-tdd — a 30-second tour of Lyra primitives

A minimal, fully runnable demo that exercises four kernel features **without starting an LLM**:

1. **`RedProof` validation** — prove a test *actually* failed.
2. **Impact map** — given an edited source file, find the tests that should re-run.
3. **Coverage regression gate** — block a "fix" that silently drops coverage.
4. **Eval runner** — run the golden corpus with a deterministic stub policy.

Everything here ships green in the base install. It is meant for:

- Onboarding new contributors: "what even are these modules?"
- CI sanity: `python run_demo.py` is what the contrib docs ask PRs to run locally.
- Integrators: copy-paste the patterns into your own runner.

## Layout

```
examples/hello-tdd/
├── README.md               (this file)
├── run_demo.py             (end-to-end driver)
├── SOUL.md                 (toy persona)
├── src/greet/__init__.py   (the code under test)
└── tests/test_greet.py     (red → green test)
```

## Usage

```bash
cd projects/lyra
python -m pip install -e packages/lyra-core -e packages/lyra-evals
python examples/hello-tdd/run_demo.py
```

Expected output (exact text may drift with version):

```
[1/4] RedProof validated            ok
[2/4] Impact map for greet/__init__.py -> ['tests/test_greet.py']
[3/4] Coverage delta 71.0% -> 72.5%  (tolerance 1.0%)   ok
[4/4] Golden-corpus smoke            success_rate=1.00  drift_gate_tripped=False
hello-tdd demo passed.
```

## Why no LLM in the demo?

The TDD gate, the impact map, the coverage gate, and the eval runner are all **deterministic**. They are what stop an agent (LLM or human) from lying about tests. If you need to see the LLM loop, run the real CLI: `lyra plan "add foo" --auto-approve --llm mock`.
