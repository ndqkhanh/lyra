# Adversarial Verification Panel: 3-Verifier + Skeptic with Anonymization
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/25-adversarial-panel.md) | [Code](../../src/lyra/verification/)

## Abstract
Lyra's adversarial verification panel redesigns the single-pass verifier as a multi-agent panel: 3 specialized verifiers (Correctness, Security, Reproducibility) + 1 Adversarial Skeptic tasked with refutation. Two bias corrections are mandatory: response anonymization (strip identity markers, from "When Identity Skews Debate," 2510.07517) and ReTAS dialectical alignment (Thesis-Antithesis-Synthesis, from Actor-Observer Asymmetry, 2604.19548). A finding survives only if ≥2/3 verifiers confirm after adversarial challenge. Collusion detection monitors for the "Lying with Truths" pattern (truthful evidence fragments steering beliefs, 2601.01685).

## Method
```mermaid
flowchart TD
    FINDING[Agent Finding] --> ANON[Anonymize Identity]
    ANON --> V1[Correctness Verifier]
    ANON --> V2[Security Verifier]
    ANON --> V3[Reproducibility Verifier]
    V1 --> VOTE{Vote >= 2/3?}
    V2 --> VOTE
    V3 --> VOTE
    VOTE -->|Yes| SKEPTIC[Adversarial Skeptic]
    VOTE -->|No| REJECT[Reject Finding]
    SKEPTIC --> SURVIVE{Survives Refutation?}
    SURVIVE -->|Yes| ACCEPT[Accept Finding]
    SURVIVE -->|No| REJECT
```

## Conclusion
Implemented: 3-verifier panel, Skeptic role, anonymization, voting threshold. Core: `src/lyra/verification/panel.py`. Future: collusion detection automation, dynamic panel sizing based on finding criticality.
