# Lyra Privacy - Privacy-Preserving Agent Inference

## Overview

Privacy-preserving module for Lyra that enables confidential computing, differential privacy, and federated knowledge sharing across agents.

## Features

### 1. Confidential Inference (TEE)
- TEE attestation proof generation and verification
- Simulated SGX/TDX enclave execution
- SHA-256 based cryptographic binding of results

### 2. Differential Privacy (DP)
- Epsilon/Delta budget tracking
- Gaussian noise mechanism
- Per-user privacy accounting
- Automatic budget depletion enforcement

### 3. Federated Knowledge Sharing
- DP-protected knowledge deltas from individual agents
- Secure aggregation with convergence scoring
- Configurable minimum contributor thresholds

## Quick Start

```python
from lyra_privacy import PrivacyPreservingAgent

# Create agent with default privacy config
agent = PrivacyPreservingAgent(agent_id="my-agent")

# Confidential inference
result = agent.secure_infer("What is the capital of France?")
proof = agent.generate_attestation(result)
assert agent.verify_attestation(proof)

# Differentially private query
dp_result = agent.query_with_dp("SELECT count(*) FROM users", "dataset-1")

# Federated knowledge sharing
update = agent.create_federated_update({"confidence": 0.95})
```

## Testing

```bash
pytest tests/ -v
```

## Version

Current version: **0.1.0**

## License

MIT License
