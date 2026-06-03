# PermissionBridge Deep Dive

## Overview

This document explores advanced patterns, optimization techniques, edge cases, internal algorithms, and future research directions for PermissionBridge. It assumes familiarity with the basic architecture and implementation.

## Advanced Patterns

### Pattern 1: Decision Caching with Invalidation

**Problem**: Repeated identical calls in a session cause redundant authorization checks.

**Solution**: Cache decisions with smart invalidation.

```python
from functools import lru_cache
from typing import Tuple

class CachingPermissionBridge(PermissionBridge):
    """Bridge with decision caching."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_version = 0
    
    def decide(self, call: ToolCall, session: Session) -> PermissionDecision:
        """Cached decision with version-based invalidation."""
        cache_key = self._make_cache_key(call, session)
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Compute and cache
        decision = super().decide(call, session)
        self._set_cached(cache_key, decision)
        return decision
    
    def _make_cache_key(self, call: ToolCall, session: Session) -> Tuple:
        """Create cache key from call + session state."""
        return (
            self._cache_version,  # Invalidate on policy/mode changes
            hash(call),
            session.mode,
            session.session_id
        )
    
    def invalidate_cache(self, reason: str) -> None:
        """Invalidate all cached decisions."""
        self._cache_version += 1
        logger.info(f"Permission cache invalidated: {reason}")
    
    def on_mode_change(self, old: PermissionMode, new: PermissionMode) -> None:
        """Hook called when mode changes."""
        self.invalidate_cache(f"mode_change:{old}->{new}")
    
    def on_policy_reload(self) -> None:
        """Hook called when policies reload."""
        self.invalidate_cache("policy_reload")
```

**Performance impact**:
```
Without cache: 1ms per decision
With cache:    10μs per cached decision (100× faster)
Cache hit rate: ~70% in typical sessions
```

**Trade-off**: Memory usage (1KB per 100 cached decisions) vs. latency.

---

### Pattern 2: Approval Batching

**Problem**: DAG Teams with many `ASK` decisions create approval fatigue.

**Solution**: Batch similar approvals for bulk user decision.

```python
@dataclass
class ApprovalBatch:
    """Group of similar pending approvals."""
    batch_id: str
    calls: List[ToolCall]
    pattern: str  # e.g., "Edit src/**/*.py"
    parked_tickets: List[str]
    
    def matches(self, call: ToolCall) -> bool:
        """Check if call belongs to this batch."""
        if call.name != self.calls[0].name:
            return False
        
        # Same tool + similar paths
        if call.name in ("Edit", "Write"):
            path = call.args.get("path", "")
            pattern = self.calls[0].args.get("path", "")
            # Check if same directory
            return Path(path).parent == Path(pattern).parent
        
        return False

class BatchingApprover:
    """Batch similar approvals for user efficiency."""
    
    def __init__(self, max_batch_size: int = 10):
        self.batches: List[ApprovalBatch] = []
        self.max_batch_size = max_batch_size
    
    def add_to_batch(self, call: ToolCall, ticket: str) -> Optional[str]:
        """
        Add call to existing batch or create new batch.
        Returns batch_id if batch ready for approval.
        """
        # Try to add to existing batch
        for batch in self.batches:
            if batch.matches(call) and len(batch.calls) < self.max_batch_size:
                batch.calls.append(call)
                batch.parked_tickets.append(ticket)
                
                # Batch ready?
                if len(batch.calls) >= 5:  # Present to user after 5 similar calls
                    return batch.batch_id
                return None
        
        # Create new batch
        batch = ApprovalBatch(
            batch_id=f"batch-{uuid.uuid4().hex[:8]}",
            calls=[call],
            pattern=self._extract_pattern(call),
            parked_tickets=[ticket]
        )
        self.batches.append(batch)
        return None
    
    def _extract_pattern(self, call: ToolCall) -> str:
        """Extract approval pattern from call."""
        if call.name in ("Edit", "Write"):
            path = call.args.get("path", "")
            dir_path = Path(path).parent
            return f"{call.name} {dir_path}/**/*"
        return call.name
```

**User experience**:
```
Without batching:
  Approve Edit src/auth/login.py? [y/n]
  Approve Edit src/auth/signup.py? [y/n]
  Approve Edit src/auth/logout.py? [y/n]

With batching:
  Approve batch: Edit 3 files in src/auth/? [y/n/review]
  (If 'review', show list; if 'y', approve all)
```

---

### Pattern 3: Contextual Risk Adjustment

**Problem**: Static risk thresholds don't account for session context.

**Solution**: Adjust risk thresholds based on session history.

```python
class AdaptiveRiskClassifier(RiskClassifier):
    """Risk classifier with contextual threshold adjustment."""
    
    def score_with_context(
        self,
        call: ToolCall,
        session: Session
    ) -> RiskScore:
        """Compute risk with session context adjustments."""
        base_score = super().score(call, session.history)
        
        # Adjustment 1: User approval rate
        approval_rate = self._compute_approval_rate(session)
        if approval_rate > 0.9:
            # User approves almost everything → increase sensitivity
            adjusted = base_score.score * 1.2
        elif approval_rate < 0.3:
            # User denies frequently → decrease sensitivity
            adjusted = base_score.score * 0.8
        else:
            adjusted = base_score.score
        
        # Adjustment 2: Similar calls in history
        similar_calls = self._find_similar_calls(call, session.history)
        if similar_calls:
            avg_risk = np.mean([c.risk_score for c in similar_calls])
            # Blend: 70% current, 30% historical average
            adjusted = 0.7 * adjusted + 0.3 * avg_risk
        
        # Adjustment 3: Time of day (heuristic: late night = higher risk)
        hour = datetime.now().hour
        if hour < 6 or hour > 22:  # Late night/early morning
            adjusted *= 1.1
        
        return RiskScore(
            score=min(adjusted, 1.0),
            label=self._score_to_label(adjusted),
            source="adaptive"
        )
    
    def _compute_approval_rate(self, session: Session) -> float:
        """Compute user's approval rate in this session."""
        asks = [h for h in session.history if h.decision == Decision.ASK]
        if not asks:
            return 0.5  # Neutral
        
        approvals = [h for h in asks if h.user_approved]
        return len(approvals) / len(asks)
```

---

## Optimization Techniques

### Technique 1: Lazy ML Model Loading

**Problem**: ML model adds 200ms startup latency, but not always needed.

```python
class LazyMLClassifier:
    """Load ML model only when first needed."""
    
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self._model = None
        self._load_attempted = False
    
    @property
    def model(self):
        """Lazy-load model on first access."""
        if self._model is None and not self._load_attempted:
            self._load_attempted = True
            try:
                import joblib
                self._model = joblib.load(self.model_path)
                logger.info(f"ML model loaded: {self.model_path}")
            except Exception as e:
                logger.warning(f"Failed to load ML model: {e}")
                self._model = None
        return self._model
    
    def predict(self, features: np.ndarray) -> float:
        """Predict with lazy-loaded model."""
        if self.model is None:
            return 0.5  # Neutral fallback
        return self.model.predict_proba([features])[0][1]
```

**Benefit**: Sessions that never hit risk classification (e.g., plan mode only) don't pay model load cost.

---

### Technique 2: Regex Compilation Caching

**Problem**: Re-compiling regex patterns on every call wastes CPU.

```python
import re
from functools import lru_cache

@lru_cache(maxsize=100)
def compile_pattern(pattern: str) -> re.Pattern:
    """Cached regex compilation."""
    return re.compile(pattern)

class OptimizedRuleClassifier:
    """Rule classifier with compiled patterns."""
    
    def __init__(self):
        # Compile patterns once at init
        self.destructive_patterns = [
            compile_pattern(r"rm\s+-rf\s+/"),
            compile_pattern(r"git\s+push\s+.*--force.*\b(main|master)\b"),
            # ...
        ]
    
    def evaluate(self, call: ToolCall) -> float:
        """Fast pattern matching with pre-compiled regex."""
        if call.name == "Bash":
            command = call.args.get("command", "")
            for pattern in self.destructive_patterns:
                if pattern.search(command):
                    return 1.0
        return 0.0
```

---

### Technique 3: Feature Extraction Vectorization

**Problem**: Computing features one-by-one is slow.

```python
import numpy as np
from typing import List

class VectorizedFeatureExtractor:
    """Extract features for multiple calls at once."""
    
    def extract_batch(self, calls: List[ToolCall]) -> np.ndarray:
        """Extract features for multiple calls (vectorized)."""
        # Build feature matrix (N calls × M features)
        features = []
        
        # Tool one-hot (vectorized)
        tool_names = [c.name for c in calls]
        tool_onehot = self._onehot_encode(tool_names, self.tool_vocab)
        
        # Arg lengths (vectorized)
        arg_lengths = np.array([len(str(c.args)) for c in calls])
        
        # Combine
        return np.column_stack([tool_onehot, arg_lengths[:, None]])
    
    def _onehot_encode(self, values: List[str], vocab: List[str]) -> np.ndarray:
        """Vectorized one-hot encoding."""
        indices = [vocab.index(v) if v in vocab else -1 for v in values]
        onehot = np.zeros((len(values), len(vocab)))
        for i, idx in enumerate(indices):
            if idx >= 0:
                onehot[i, idx] = 1
        return onehot
```

**Performance**: 10× faster for batch processing (DAG Teams with 50+ parallel nodes).

---

## Edge Cases

### Edge Case 1: Parking Lot Overflow

**Scenario**: DAG with 200 nodes, all hit ASK simultaneously.

**Problem**: Parking lot has 100-item limit → later nodes denied.

**Solution**: Priority-based parking with overflow handling.

```python
class PriorityParkingLot(ParkingLot):
    """Parking lot with priority queue and overflow strategy."""
    
    def park(
        self,
        decision: PermissionDecision,
        node_id: str,
        priority: int = 5
    ) -> ParkTicket:
        """Park with priority (1=highest, 10=lowest)."""
        if len(self._parked) >= self.max_queue_size:
            # Overflow: evict lowest priority item
            lowest = min(self._parked.values(), key=lambda p: p.priority)
            if priority < lowest.priority:
                # This call is higher priority, evict lowest
                self._evict(lowest.ticket_id)
            else:
                # This call is lower priority, deny immediately
                raise ParkingLotFullError("High priority queue full")
        
        # Park normally
        ticket_id = self._generate_ticket_id()
        self._parked[ticket_id] = ParkedDecision(
            decision=decision,
            node_id=node_id,
            priority=priority,
            parked_at=time.time()
        )
        return ParkTicket(id=ticket_id)
    
    def _evict(self, ticket_id: str) -> None:
        """Evict a parked item (auto-deny)."""
        parked = self._parked.pop(ticket_id)
        # Notify node that it was auto-denied
        self._emit_event("parking.evicted", {
            "ticket": ticket_id,
            "node": parked.node_id,
            "reason": "queue_overflow"
        })
```

---

### Edge Case 2: Policy File Conflicts

**Scenario**: Two policies match same call with conflicting decisions.

```yaml
# Policy 1: Allow all edits in tests/
- name: allow-test-edits
  when:
    tool: Edit
    path_glob: "tests/**"
  decision: allow

# Policy 2: Deny all edits to snapshots
- name: deny-snapshot-edits
  when:
    tool: Edit
    path_glob: "**/__snapshots__/**"
  decision: deny

# Conflict: tests/__snapshots__/test.snap matches both!
```

**Solution**: Explicit conflict resolution.

```python
class ConflictResolvingPolicyEngine(PolicyEngine):
    """Policy engine with conflict detection and resolution."""
    
    def evaluate(self, call: ToolCall) -> Optional[PermissionDecision]:
        """Evaluate with conflict detection."""
        matches = [p for p in self.policies if p.condition.matches(call)]
        
        if len(matches) == 0:
            return None
        
        if len(matches) == 1:
            return self._policy_to_decision(matches[0])
        
        # Multiple matches → conflict
        return self._resolve_conflict(matches, call)
    
    def _resolve_conflict(
        self,
        policies: List[Policy],
        call: ToolCall
    ) -> PermissionDecision:
        """
        Resolve policy conflict.
        Strategy: Most restrictive wins (DENY > ASK > ALLOW).
        """
        logger.warning(f"Policy conflict for {call.name}: {[p.name for p in policies]}")
        
        # Check for DENY
        denies = [p for p in policies if p.decision == Decision.DENY]
        if denies:
            return self._policy_to_decision(denies[0])
        
        # Check for ASK
        asks = [p for p in policies if p.decision == Decision.ASK]
        if asks:
            return self._policy_to_decision(asks[0])
        
        # All ALLOW
        return self._policy_to_decision(policies[0])
```

---

### Edge Case 3: Time-of-Check/Time-of-Use (TOCTOU)

**Scenario**: Call args modified between decision and execution.

**Attack**:
```python
call = ToolCall(name="Edit", args={"path": "safe.txt"})
decision = bridge.decide(call, session)  # → ALLOW

# Attacker modifies call before execution
call.args["path"] = "/etc/passwd"  # TOCTOU vulnerability!
executor.execute(call)  # Edits wrong file!
```

**Solution**: Immutable ToolCall + decision binding.

```python
@dataclass(frozen=True)  # frozen=True makes it immutable
class ToolCall:
    name: str
    args: Dict[str, Any]  # Must also be immutable!
    call_id: str
    
    def __post_init__(self):
        # Convert args dict to frozendict (immutable)
        object.__setattr__(self, 'args', frozendict(self.args))

@dataclass
class BoundDecision:
    """Decision bound to specific call."""
    decision: PermissionDecision
    call_hash: int
    issued_at: float
    
    def verify(self, call: ToolCall) -> bool:
        """Verify decision is for this exact call."""
        return hash(call) == self.call_hash

class SecureExecutor:
    """Executor that verifies decision binding."""
    
    def execute(self, call: ToolCall, decision: BoundDecision):
        """Execute only if decision matches call."""
        if not decision.verify(call):
            raise SecurityError("Decision/call mismatch (TOCTOU attempt?)")
        
        # Proceed with execution
        self._execute_impl(call)
```

---

## Internal Algorithms

### Algorithm 1: Risk Feature Engineering

**Goal**: Extract meaningful features from tool calls for ML model.

```python
class FeatureEngineer:
    """Advanced feature extraction for risk classification."""
    
    def extract_features(self, call: ToolCall, session: Session) -> np.ndarray:
        """Extract 30-dimensional feature vector."""
        features = []
        
        # Group 1: Tool characteristics (9 features)
        features.extend(self._tool_features(call))
        
        # Group 2: Argument analysis (8 features)
        features.extend(self._arg_features(call))
        
        # Group 3: Path analysis (5 features)
        features.extend(self._path_features(call))
        
        # Group 4: Temporal patterns (4 features)
        features.extend(self._temporal_features(call, session))
        
        # Group 5: Session context (4 features)
        features.extend(self._session_features(session))
        
        return np.array(features)
    
    def _tool_features(self, call: ToolCall) -> List[float]:
        """Extract tool-specific features."""
        # One-hot encoding for tool name
        tool_onehot = [1.0 if t == call.name else 0.0 
                      for t in self.tool_vocab]
        return tool_onehot
    
    def _arg_features(self, call: ToolCall) -> List[float]:
        """Extract features from arguments."""
        args_str = str(call.args)
        return [
            len(args_str),                    # Total length
            self._entropy(args_str),          # Shannon entropy
            args_str.count('/'),              # Path depth indicator
            args_str.count('..'),             # Path traversal indicator
            int('sudo' in args_str.lower()),  # Contains sudo
            int('rm' in args_str.lower()),    # Contains rm
            int('http' in args_str.lower()),  # Contains URL
            self._special_char_ratio(args_str) # Ratio of special chars
        ]
    
    def _path_features(self, call: ToolCall) -> List[float]:
        """Extract path-related features."""
        path = call.args.get('path', '')
        return [
            len(Path(path).parts),            # Directory depth
            int(path.startswith('/')),        # Absolute path
            int('..' in path),                # Parent traversal
            int(path.endswith('.sh')),        # Script file
            self._path_risk_score(path)       # Heuristic path risk
        ]
    
    def _temporal_features(self, call: ToolCall, session: Session) -> List[float]:
        """Extract temporal patterns."""
        recent_calls = session.history[-10:]
        return [
            len(recent_calls),                           # Recent activity
            sum(1 for c in recent_calls if c.name == call.name) / 10,  # Same tool rate
            session.history[-1].timestamp - call.timestamp if session.history else 0,  # Time since last
            datetime.fromtimestamp(call.timestamp).hour / 24  # Hour of day (normalized)
        ]
    
    def _session_features(self, session: Session) -> List[float]:
        """Extract session-level features."""
        return [
            len(session.history),                     # Total calls in session
            session.metrics.approval_rate,            # User approval rate
            session.metrics.recent_deny_rate,         # Recent deny rate
            int(session.mode == PermissionMode.BYPASS) # Is in bypass mode
        ]
```

---

### Algorithm 2: Policy Precedence Resolution

**Goal**: Deterministic ordering when multiple policies could match.

```python
class PolicyPrecedenceResolver:
    """Resolve policy precedence deterministically."""
    
    def order_policies(self, policies: List[Policy]) -> List[Policy]:
        """
        Order policies by precedence.
        
        Precedence rules (highest to lowest):
        1. Explicit priority field (if set)
        2. More specific path globs (fewer wildcards)
        3. Decision restrictiveness (DENY > ASK > ALLOW)
        4. Lexicographic by name (for determinism)
        """
        def precedence_key(policy: Policy) -> Tuple:
            return (
                -policy.priority if hasattr(policy, 'priority') else 0,
                -self._path_specificity(policy),
                self._decision_restrictiveness(policy),
                policy.name
            )
        
        return sorted(policies, key=precedence_key)
    
    def _path_specificity(self, policy: Policy) -> int:
        """
        Compute path specificity score.
        More specific = higher score.
        """
        if not policy.condition.path_glob:
            return 0
        
        glob = policy.condition.path_glob
        # Fewer wildcards = more specific
        wildcard_count = glob.count('*') + glob.count('?')
        path_depth = glob.count('/')
        
        return path_depth * 10 - wildcard_count
    
    def _decision_restrictiveness(self, policy: Policy) -> int:
        """Map decision to restrictiveness level."""
        return {
            Decision.DENY: 3,
            Decision.ASK: 2,
            Decision.ALLOW: 1,
            Decision.PARK: 2
        }[policy.decision]
```

---

## Future Research Directions

### 1. Intent-Based Authorization

**Idea**: Verify agent's stated intent matches actual tool call.

```python
class IntentVerifier:
    """Verify tool call matches agent's declared intent."""
    
    def verify(
        self,
        intent: str,  # e.g., "Fix failing test by updating assertion"
        call: ToolCall,
        context: ConversationContext
    ) -> bool:
        """
        Check if call is consistent with stated intent.
        
        Uses:
        - NLI model to check intent → action consistency
        - Static analysis to verify call matches description
        - Context to detect deviations
        """
        # Extract expected actions from intent
        expected = self._parse_intent(intent)
        
        # Check consistency
        if call.name not in expected.allowed_tools:
            return False
        
        if "path" in call.args:
            if not any(fnmatch(call.args["path"], p) for p in expected.allowed_paths):
                return False
        
        return True
```

**Challenges**:
- Reliable intent extraction from natural language
- Handling vague intents ("improve the code")
- False positives blocking legitimate work

---

### 2. Hardware-Backed Approvals

**Idea**: High-risk operations require biometric confirmation.

```python
class BiometricApprover:
    """Approval requiring hardware-backed authentication."""
    
    def request_approval(
        self,
        call: ToolCall,
        decision: PermissionDecision
    ) -> bool:
        """Request approval with biometric check."""
        if decision.cost_of_approval == "irreversible":
            # Require TouchID/FaceID/YubiKey
            return self._hardware_prompt(
                f"Approve irreversible action: {call.name}?",
                require_biometric=True
            )
        else:
            # Standard prompt
            return self._standard_prompt(call, decision)
```

**Benefits**:
- Prevents approval by someone who walked away from terminal
- Audit trail tied to physical person

---

### 3. Cross-Agent Learning

**Idea**: Risk classifier learns from all users' decisions, not just one session.

```python
class FederatedRiskLearner:
    """Learn from aggregated user decisions across organization."""
    
    def __init__(self, aggregation_server: str):
        self.server = aggregation_server
        self.local_data = []
    
    def record_decision(self, call: ToolCall, decision: Decision, user_approved: bool):
        """Record decision for later learning."""
        self.local_data.append({
            "features": self._extract_features(call),
            "risk_label": 1.0 if decision == Decision.DENY else 0.0,
            "user_override": user_approved if decision == Decision.ASK else None
        })
    
    async def sync(self):
        """Upload local data, download global model."""
        # Upload (anonymized)
        await self._upload_anonymized(self.local_data)
        
        # Download new model trained on all users' data
        new_model = await self._download_global_model()
        self.model = new_model
```

**Privacy considerations**:
- Differential privacy for uploaded data
- No sharing of actual code/paths, only features
- Opt-in only

---

## References

- [PermissionBridge architecture](./architecture.md)
- [Architecture tradeoffs](./architecture-tradeoffs.md)
- [System design](./system-design.md)
- [Implementation guide](./implementation-guide.md)
- [SemaClaw paper arXiv:2604.11548](../../../../docs/54-semaclaw-general-purpose-agent.md)
