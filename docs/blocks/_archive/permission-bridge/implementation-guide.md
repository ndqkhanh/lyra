# PermissionBridge Implementation Guide

## Overview

This guide walks you through implementing PermissionBridge from scratch: step-by-step instructions, code examples, configuration, testing strategies, debugging techniques, and common pitfalls.

## Prerequisites

- Python 3.11+
- Basic understanding of authorization systems
- Familiarity with dataclasses, enums, and type hints

## Step 1: Define Core Data Structures

### 1.1 Decision Types

```python
# lyra_core/permissions/types.py
from enum import StrEnum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

class Decision(StrEnum):
    """Authorization decision outcomes."""
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"
    PARK = "park"

class PermissionMode(StrEnum):
    """Available permission modes."""
    PLAN = "plan"
    TRIAGE = "triage"
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    RED = "red"
    GREEN = "green"
    REFACTOR = "refactor"
    BYPASS = "bypass"

@dataclass
class PermissionDecision:
    """Result of authorization check."""
    decision: Decision
    reason: str
    suggestion: Optional[str] = None
    elevate_to: Optional[PermissionMode] = None
    cost_of_approval: str = "reversible"
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 1.2 Tool Call Representation

```python
# lyra_core/permissions/types.py
@dataclass(frozen=True)
class ToolCall:
    """Immutable representation of a tool invocation."""
    name: str
    args: Dict[str, Any]
    call_id: str
    timestamp: float
    session_id: str
    
    def __hash__(self) -> int:
        return hash((
            self.name,
            frozenset(self.args.items()),
            self.session_id
        ))
```

## Step 2: Build Mode Lookup Table

### 2.1 Define Mode Rules

```python
# lyra_core/permissions/modes.py
from typing import Dict, Pattern
import re

@dataclass
class ModeRule:
    """Decision rule for a (mode, tool) pair."""
    decision: Decision
    reason: str = ""
    pattern_allowlist: Optional[List[Pattern]] = None
    path_matcher: Optional[Callable[[str], bool]] = None
    
    def evaluate(self, call: ToolCall) -> PermissionDecision:
        """Evaluate this rule against a tool call."""
        # Check pattern allowlist (for Bash)
        if self.pattern_allowlist and call.name == "Bash":
            command = call.args.get("command", "")
            for pattern in self.pattern_allowlist:
                if pattern.match(command):
                    return PermissionDecision(
                        Decision.ALLOW,
                        f"{self.reason}:allowlist_match"
                    )
        
        # Check path matcher (for Edit/Write in TDD modes)
        if self.path_matcher and "path" in call.args:
            path = call.args["path"]
            if not self.path_matcher(path):
                return PermissionDecision(
                    Decision.DENY,
                    f"{self.reason}:path_mismatch"
                )
        
        return PermissionDecision(self.decision, self.reason)
```

### 2.2 Create Mode Table

```python
# lyra_core/permissions/modes.py

# Safe bash patterns
SAFE_BASH_PATTERNS = [
    re.compile(r"^pytest\b"),
    re.compile(r"^npm\s+test\b"),
    re.compile(r"^git\s+(status|log|diff|show)\b"),
    re.compile(r"^ls\b"),
    re.compile(r"^cat\b"),
]

# Destructive patterns (always deny)
DESTRUCTIVE_BASH_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/"),
    re.compile(r"rm\s+-rf\s+\$HOME"),
    re.compile(r"git\s+push\s+.*--force.*\b(main|master)\b"),
    re.compile(r":\(\)\{ :\|:& \};:"),  # fork bomb
    re.compile(r"dd\s+if=.*\s+of=/dev/"),
]

MODE_TOOL_TABLE: Dict[PermissionMode, Dict[str, ModeRule]] = {
    PermissionMode.PLAN: {
        "Read": ModeRule(Decision.ALLOW, "plan_mode_read"),
        "Grep": ModeRule(Decision.ALLOW, "plan_mode_read"),
        "Glob": ModeRule(Decision.ALLOW, "plan_mode_read"),
        "Edit": ModeRule(Decision.DENY, "plan_mode_read_only"),
        "Write": ModeRule(Decision.DENY, "plan_mode_read_only"),
        "Bash": ModeRule(Decision.DENY, "plan_mode_no_exec"),
    },
    PermissionMode.DEFAULT: {
        "Read": ModeRule(Decision.ALLOW, "default_read"),
        "Edit": ModeRule(Decision.ASK, "default_asks_writes"),
        "Write": ModeRule(Decision.ASK, "default_asks_writes"),
        "Bash": ModeRule(Decision.ASK, "default_asks_bash", 
                        pattern_allowlist=SAFE_BASH_PATTERNS),
    },
    PermissionMode.ACCEPT_EDITS: {
        "Read": ModeRule(Decision.ALLOW, "accept_edits_read"),
        "Edit": ModeRule(Decision.ALLOW, "accept_edits_write"),
        "Write": ModeRule(Decision.ALLOW, "accept_edits_write"),
        "Bash": ModeRule(Decision.ASK, "accept_edits_bash",
                        pattern_allowlist=SAFE_BASH_PATTERNS),
    },
    # Add remaining modes...
}

class ModeTable:
    """Mode × tool lookup table."""
    
    def __init__(self):
        self.table = MODE_TOOL_TABLE
        self.default_rule = ModeRule(Decision.DENY, "unknown_tool")
    
    def lookup(self, mode: PermissionMode, call: ToolCall) -> PermissionDecision:
        """Look up decision for (mode, tool)."""
        tool_rules = self.table.get(mode, {})
        rule = tool_rules.get(call.name, self.default_rule)
        
        # Check destructive patterns first (unbypassable)
        if call.name == "Bash":
            command = call.args.get("command", "")
            for pattern in DESTRUCTIVE_BASH_PATTERNS:
                if pattern.search(command):
                    return PermissionDecision(
                        Decision.DENY,
                        "destructive_pattern_detected"
                    )
        
        return rule.evaluate(call)
```

## Step 3: Implement Policy Engine

### 3.1 Policy Data Structure

```python
# lyra_core/permissions/policy.py
import yaml
from pathlib import Path
from typing import List, Optional

@dataclass
class PolicyCondition:
    """Condition that triggers a policy."""
    tools: List[str] = field(default_factory=list)
    path_glob: Optional[str] = None
    command_regex: Optional[Pattern] = None
    
    def matches(self, call: ToolCall) -> bool:
        """Check if call matches this condition."""
        # Check tool match
        if self.tools and call.name not in self.tools:
            return False
        
        # Check path glob
        if self.path_glob and "path" in call.args:
            from fnmatch import fnmatch
            if not fnmatch(call.args["path"], self.path_glob):
                return False
        
        # Check command regex
        if self.command_regex and call.name == "Bash":
            command = call.args.get("command", "")
            if not self.command_regex.search(command):
                return False
        
        return True

@dataclass
class Policy:
    """User-defined authorization policy."""
    name: str
    condition: PolicyCondition
    decision: Decision
    reason: str
    elevate_to: Optional[PermissionMode] = None
```

### 3.2 Policy Loader

```python
# lyra_core/permissions/policy.py

class PolicyEngine:
    """Loads and evaluates policies from YAML."""
    
    def __init__(self, policy_paths: List[Path]):
        self.policies: List[Policy] = []
        self._load_policies(policy_paths)
    
    def _load_policies(self, paths: List[Path]) -> None:
        """Load policies from YAML files."""
        for path in paths:
            if not path.exists():
                continue
            
            with open(path) as f:
                data = yaml.safe_load(f)
            
            for policy_data in data.get("policies", []):
                self.policies.append(self._parse_policy(policy_data))
    
    def _parse_policy(self, data: Dict[str, Any]) -> Policy:
        """Parse policy from YAML dict."""
        condition_data = data.get("when", {})
        condition = PolicyCondition(
            tools=condition_data.get("tool", []),
            path_glob=condition_data.get("path_glob"),
            command_regex=re.compile(condition_data["command_regex"]) 
                if "command_regex" in condition_data else None
        )
        
        return Policy(
            name=data["name"],
            condition=condition,
            decision=Decision(data["decision"]),
            reason=data.get("reason", ""),
            elevate_to=PermissionMode(data["elevate_to"]) 
                if "elevate_to" in data else None
        )
    
    def evaluate(self, call: ToolCall) -> Optional[PermissionDecision]:
        """Evaluate policies against a call."""
        for policy in self.policies:
            if policy.condition.matches(call):
                return PermissionDecision(
                    decision=policy.decision,
                    reason=f"policy:{policy.name}",
                    elevate_to=policy.elevate_to
                )
        return None
```

### 3.3 Example Policy File

```yaml
# .lyra/policy.yaml
version: 1
policies:
  - name: no-edits-to-generated
    when:
      tool: [Edit, Write]
      path_glob: "**/*.pb.go"
    decision: deny
    reason: "Generated files should not be manually edited"
  
  - name: prod-deploys-need-approval
    when:
      tool: Bash
      command_regex: "deploy.*--env=prod"
    decision: ask
    elevate_to: bypass
    reason: "Production deployments require explicit approval"
```

## Step 4: Build Risk Classifier

### 4.1 Rule-Based Classifier

```python
# lyra_core/permissions/risk.py

@dataclass
class RiskScore:
    """Risk assessment result."""
    score: float  # 0.0 to 1.0
    label: str
    source: str  # "rules" or "ml" or "hybrid"

class RuleBasedClassifier:
    """Deterministic risk rules."""
    
    def evaluate(self, call: ToolCall) -> float:
        """Return risk score based on rules."""
        # Destructive patterns → 1.0
        if call.name == "Bash":
            command = call.args.get("command", "")
            for pattern in DESTRUCTIVE_BASH_PATTERNS:
                if pattern.search(command):
                    return 1.0
            
            # Piped curl to bash → high risk
            if re.search(r"curl.*\|\s*bash", command):
                return 0.9
            
            # sudo commands → medium-high risk
            if command.strip().startswith("sudo"):
                return 0.7
        
        # File deletions → medium risk
        if call.name == "Delete":
            return 0.6
        
        return 0.0
```

### 4.2 ML Classifier (Simple Example)

```python
# lyra_core/permissions/risk.py
import joblib
import numpy as np

class MLClassifier:
    """Machine learning risk classifier."""
    
    def __init__(self, model_path: Path):
        self.model = joblib.load(model_path)
    
    def predict(self, call: ToolCall, session_history: List[ToolCall]) -> float:
        """Predict risk score using ML model."""
        features = self._extract_features(call, session_history)
        score = self.model.predict_proba([features])[0][1]
        return float(score)
    
    def _extract_features(self, call: ToolCall, history: List[ToolCall]) -> np.ndarray:
        """Extract feature vector from call."""
        features = []
        
        # Tool one-hot encoding (15 tools)
        tool_onehot = [1 if t == call.name else 0 
                      for t in ["Read", "Edit", "Write", "Bash", "Delete", 
                               "Grep", "Glob", "WebFetch", "Spawn"]]
        features.extend(tool_onehot)
        
        # Arg length
        features.append(len(str(call.args)))
        
        # Arg entropy
        from collections import Counter
        import math
        text = str(call.args)
        counter = Counter(text)
        entropy = -sum(
            (count / len(text)) * math.log2(count / len(text))
            for count in counter.values()
        )
        features.append(entropy)
        
        # Recent deny rate
        recent_denies = sum(
            1 for h in history[-10:] 
            if getattr(h, "decision", None) == Decision.DENY
        )
        features.append(recent_denies / 10.0)
        
        return np.array(features)
```

### 4.3 Hybrid Classifier

```python
# lyra_core/permissions/risk.py

class RiskClassifier:
    """Combined rule-based and ML classifier."""
    
    def __init__(self, ml_model_path: Optional[Path] = None):
        self.rules = RuleBasedClassifier()
        self.ml = MLClassifier(ml_model_path) if ml_model_path else None
    
    def score(self, call: ToolCall, session_history: List[ToolCall]) -> RiskScore:
        """Compute hybrid risk score."""
        # Stage 1: Rules (unbypassable)
        rule_score = self.rules.evaluate(call)
        if rule_score >= 1.0:
            return RiskScore(1.0, "destructive", "rules")
        
        # Stage 2: ML (if available)
        ml_score = 0.0
        if self.ml:
            try:
                ml_score = self.ml.predict(call, session_history)
            except Exception as e:
                logger.warning(f"ML classifier error: {e}")
                ml_score = 0.5  # Neutral on error
        
        # Combine: take maximum (fail-safe)
        final_score = max(rule_score, ml_score)
        label = self._score_to_label(final_score)
        return RiskScore(final_score, label, "hybrid")
    
    def _score_to_label(self, score: float) -> str:
        if score >= 0.85: return "critical"
        if score >= 0.4: return "elevated"
        return "low"
```

## Step 5: Assemble PermissionBridge

### 5.1 Main Bridge Implementation

```python
# lyra_core/permissions/bridge.py

class PermissionBridge:
    """Main authorization gateway."""
    
    def __init__(
        self,
        mode_table: ModeTable,
        policy_engine: PolicyEngine,
        risk_classifier: RiskClassifier,
        tracer: Optional[Tracer] = None
    ):
        self.mode_table = mode_table
        self.policy_engine = policy_engine
        self.risk_classifier = risk_classifier
        self.tracer = tracer
    
    def decide(
        self,
        call: ToolCall,
        session: Session
    ) -> PermissionDecision:
        """
        Authorize a tool call.
        Returns ALLOW, ASK, DENY, or PARK.
        """
        try:
            decision = self._decide_impl(call, session)
        except Exception as e:
            logger.error(f"PermissionBridge error: {e}", exc_info=True)
            decision = PermissionDecision(Decision.DENY, "internal_error")
        
        # Emit trace event
        if self.tracer:
            self.tracer.emit("permission.decide", {
                "call": call.name,
                "decision": decision.decision,
                "reason": decision.reason
            })
        
        return decision
    
    def _decide_impl(
        self,
        call: ToolCall,
        session: Session
    ) -> PermissionDecision:
        """Internal decision pipeline."""
        # Stage 1: Mode lookup
        mode_decision = self.mode_table.lookup(session.mode, call)
        if mode_decision.decision == Decision.DENY:
            return mode_decision
        
        # Stage 2: Policy check
        policy_decision = self.policy_engine.evaluate(call)
        if policy_decision and policy_decision.decision == Decision.DENY:
            return policy_decision
        
        # Stage 3: Risk classification
        risk_score = self.risk_classifier.score(call, session.history)
        
        if risk_score.score >= session.config.risk_deny_threshold:
            return PermissionDecision(
                Decision.DENY,
                f"risk:{risk_score.label}"
            )
        
        if risk_score.score >= session.config.risk_ask_threshold:
            if mode_decision.decision == Decision.ALLOW:
                mode_decision = PermissionDecision(
                    Decision.ASK,
                    f"risk_elevated:{risk_score.label}"
                )
        
        # Stage 4: Parking (DAG Teams only)
        if (mode_decision.decision == Decision.ASK and 
            session.harness == "dag-teams" and
            session.config.dag_teams.park_on_ask):
            return PermissionDecision(
                Decision.PARK,
                mode_decision.reason,
                elevate_to=mode_decision.elevate_to
            )
        
        return mode_decision
```

## Step 6: Configuration

### 6.1 Session Config

```python
# lyra_core/permissions/config.py

@dataclass
class SessionConfig:
    """Configuration for permission system."""
    risk_ask_threshold: float = 0.4
    risk_deny_threshold: float = 0.85
    policy_paths: List[Path] = field(default_factory=list)
    dag_teams: DagTeamsConfig = field(default_factory=lambda: DagTeamsConfig())

@dataclass
class DagTeamsConfig:
    """DAG Teams specific config."""
    park_on_ask: bool = True
    max_parked: int = 100
    park_timeout_seconds: int = 3600
```

### 6.2 Load from File

```python
# Example: ~/.lyra/config.toml
"""
[permissions]
risk_ask_threshold = 0.4
risk_deny_threshold = 0.85

[permissions.dag_teams]
park_on_ask = true
max_parked = 100
"""

import toml

def load_config(config_path: Path) -> SessionConfig:
    """Load config from TOML file."""
    data = toml.load(config_path)
    perm_config = data.get("permissions", {})
    
    return SessionConfig(
        risk_ask_threshold=perm_config.get("risk_ask_threshold", 0.4),
        risk_deny_threshold=perm_config.get("risk_deny_threshold", 0.85),
        dag_teams=DagTeamsConfig(**perm_config.get("dag_teams", {}))
    )
```

## Step 7: Testing

### 7.1 Unit Tests

```python
# tests/test_permission_bridge.py
import unittest

class TestPermissionBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = PermissionBridge(
            mode_table=ModeTable(),
            policy_engine=PolicyEngine([]),
            risk_classifier=RiskClassifier()
        )
        self.session = Session(
            session_id="test",
            mode=PermissionMode.DEFAULT,
            config=SessionConfig()
        )
    
    def test_deny_in_plan_mode(self):
        """Edit should be denied in plan mode."""
        session = Session(
            session_id="test",
            mode=PermissionMode.PLAN,
            config=SessionConfig()
        )
        call = ToolCall(
            name="Edit",
            args={"path": "test.py"},
            call_id="1",
            timestamp=time.time(),
            session_id="test"
        )
        
        decision = self.bridge.decide(call, session)
        
        self.assertEqual(decision.decision, Decision.DENY)
        self.assertIn("plan_mode", decision.reason)
    
    def test_destructive_pattern_denied(self):
        """Destructive bash patterns always denied."""
        call = ToolCall(
            name="Bash",
            args={"command": "rm -rf /"},
            call_id="2",
            timestamp=time.time(),
            session_id="test"
        )
        
        decision = self.bridge.decide(call, self.session)
        
        self.assertEqual(decision.decision, Decision.DENY)
        self.assertIn("destructive", decision.reason)
```

## Step 8: Debugging

### 8.1 Enable Verbose Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("lyra.permissions")
```

### 8.2 Decision Explainer

```python
def explain_decision(bridge: PermissionBridge, call: ToolCall, session: Session):
    """Explain why a decision was made."""
    print(f"\n=== Explaining decision for {call.name} ===")
    
    # Stage 1: Mode
    mode_decision = bridge.mode_table.lookup(session.mode, call)
    print(f"1. Mode check ({session.mode}): {mode_decision.decision}")
    if mode_decision.decision == Decision.DENY:
        print(f"   STOPPED: {mode_decision.reason}")
        return
    
    # Stage 2: Policy
    policy_decision = bridge.policy_engine.evaluate(call)
    if policy_decision:
        print(f"2. Policy match: {policy_decision.reason}")
        if policy_decision.decision == Decision.DENY:
            print(f"   STOPPED: Policy denies")
            return
    else:
        print("2. No policy match")
    
    # Stage 3: Risk
    risk = bridge.risk_classifier.score(call, session.history)
    print(f"3. Risk score: {risk.score:.2f} ({risk.label})")
    
    # Final
    final = bridge.decide(call, session)
    print(f"\nFinal decision: {final.decision}")
    print(f"Reason: {final.reason}")
```

## Common Pitfalls

### Pitfall 1: Mutable ToolCall

```python
# WRONG: Mutable call can be modified after decision
@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any]

# RIGHT: Frozen dataclass prevents modification
@dataclass(frozen=True)
class ToolCall:
    name: str
    args: Dict[str, Any]
```

### Pitfall 2: Not Handling Exceptions

```python
# WRONG: Let exceptions escape
def decide(call, session):
    return self._decide_impl(call, session)

# RIGHT: Fail closed on any error
def decide(call, session):
    try:
        return self._decide_impl(call, session)
    except Exception:
        return PermissionDecision(Decision.DENY, "internal_error")
```

### Pitfall 3: Forgetting to Check Destructive Patterns

```python
# WRONG: Only check mode
if session.mode == "bypass":
    return Decision.ALLOW

# RIGHT: Always check destructive patterns
if is_destructive(call):
    return Decision.DENY
if session.mode == "bypass":
    return Decision.ALLOW
```

## Next Steps

1. Read [Deep Dive](./deep-dive.md) for advanced patterns
2. Study [Architecture Tradeoffs](./architecture-tradeoffs.md) for design decisions
3. Review [System Design](./system-design.md) for abstractions

## References

- [PermissionBridge architecture](./architecture.md)
- [SemaClaw paper](../../../../docs/54-semaclaw-general-purpose-agent.md)
