# Lyra v4.0 Safety & Governance Design

**Version**: 1.0  
**Status**: 🚧 Draft  
**Last Updated**: 2026-05-21

---

## Overview

The Safety & Governance system ensures Lyra operates safely, transparently, and under user control. This document details the multi-layer safety architecture, budget management, audit mechanisms, and control systems.

---

## Design Goals

### 1. Safety
- Prevent harmful actions
- Validate all operations
- Fail safely

### 2. Transparency
- Explain all decisions
- Visible reasoning
- Complete audit trail

### 3. Control
- User oversight
- Approval workflows
- Emergency stop

### 4. Accountability
- Track all actions
- Attribution clear
- Compliance ready

### 5. Efficiency
- Minimal overhead
- Fast validation
- Smart defaults

---

## System Architecture

```
Safety & Governance System
│
├── Safety Layer
│   ├── Input Validator
│   ├── Action Validator
│   ├── Output Validator
│   └── Risk Assessor
│
├── Budget Manager
│   ├── Cost Tracker
│   ├── Resource Monitor
│   ├── Budget Enforcer
│   └── Alert System
│
├── Audit System
│   ├── Operation Logger
│   ├── Decision Tracker
│   ├── Audit Trail
│   └── Compliance Reporter
│
└── Control System
    ├── Approval Workflow
    ├── User Override
    ├── Emergency Stop
    └── Rollback Manager
```

---

## Safety Layer

### Multi-Layer Validation

```
Request Flow:
    ↓
[Input Validation]
    ↓
[Intent Analysis]
    ↓
[Risk Assessment]
    ↓
[Action Validation]
    ↓
[Execution]
    ↓
[Output Validation]
    ↓
Response
```

### Input Validator

```python
class InputValidator:
    """Validate user input"""
    
    async def validate(self, input_text: str) -> ValidationResult:
        """Validate input"""
        issues = []
        
        # Check for injection attempts
        if self.contains_injection(input_text):
            issues.append(SecurityIssue(
                severity="high",
                type="injection_attempt",
                description="Input contains potential injection patterns"
            ))
        
        # Check for malicious patterns
        if self.contains_malicious_patterns(input_text):
            issues.append(SecurityIssue(
                severity="high",
                type="malicious_pattern",
                description="Input contains suspicious patterns"
            ))
        
        # Check length
        if len(input_text) > 10000:
            issues.append(ValidationIssue(
                severity="medium",
                type="length_exceeded",
                description="Input exceeds maximum length"
            ))
        
        return ValidationResult(
            valid=len([i for i in issues if i.severity == "high"]) == 0,
            issues=issues
        )
    
    def contains_injection(self, text: str) -> bool:
        """Check for injection attempts"""
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"system\s+prompt",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
            r"###\s+Instruction",
        ]
        
        import re
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in injection_patterns
        )
```

### Action Validator

```python
class ActionValidator:
    """Validate actions before execution"""
    
    async def validate(self, action: Action) -> ValidationResult:
        """Validate action"""
        issues = []
        
        # Check action type
        if action.type in self.dangerous_actions:
            risk = await self.assess_risk(action)
            if risk.level == "high":
                issues.append(SafetyIssue(
                    severity="high",
                    type="dangerous_action",
                    description=f"Action {action.type} is high-risk",
                    requires_approval=True
                ))
        
        # Check permissions
        if not self.has_permission(action):
            issues.append(PermissionIssue(
                severity="high",
                type="insufficient_permissions",
                description=f"No permission for {action.type}"
            ))
        
        # Check resource limits
        if not self.within_limits(action):
            issues.append(ResourceIssue(
                severity="medium",
                type="resource_limit",
                description="Action exceeds resource limits"
            ))
        
        return ValidationResult(
            valid=len([i for i in issues if i.severity == "high"]) == 0,
            issues=issues,
            requires_approval=any(
                getattr(i, "requires_approval", False)
                for i in issues
            )
        )
    
    dangerous_actions = {
        "delete_file",
        "delete_directory",
        "execute_shell",
        "modify_system",
        "network_request",
        "database_write"
    }
```

### Risk Assessor

```python
class RiskAssessor:
    """Assess risk of actions"""
    
    async def assess_risk(self, action: Action) -> RiskAssessment:
        """Assess action risk"""
        factors = []
        
        # Reversibility
        reversibility = self.assess_reversibility(action)
        factors.append(("reversibility", reversibility))
        
        # Impact scope
        impact = self.assess_impact(action)
        factors.append(("impact", impact))
        
        # Data sensitivity
        sensitivity = self.assess_sensitivity(action)
        factors.append(("sensitivity", sensitivity))
        
        # Historical safety
        history = await self.check_history(action)
        factors.append(("history", history))
        
        # Calculate overall risk
        risk_score = self.calculate_risk_score(factors)
        risk_level = self.determine_risk_level(risk_score)
        
        return RiskAssessment(
            action=action,
            score=risk_score,
            level=risk_level,
            factors=factors,
            recommendations=self.generate_recommendations(risk_level)
        )
    
    def assess_reversibility(self, action: Action) -> float:
        """Assess how easily action can be reversed (0-1)"""
        if action.type in ["read_file", "list_directory"]:
            return 1.0  # Fully reversible (no changes)
        elif action.type in ["write_file", "edit_file"]:
            return 0.8  # Mostly reversible (can restore)
        elif action.type in ["delete_file"]:
            return 0.3  # Partially reversible (may have backup)
        elif action.type in ["execute_shell"]:
            return 0.1  # Rarely reversible
        else:
            return 0.5  # Unknown
    
    def assess_impact(self, action: Action) -> float:
        """Assess potential impact scope (0-1)"""
        if action.type in ["read_file"]:
            return 0.1  # Single file
        elif action.type in ["write_file", "edit_file"]:
            return 0.3  # Single file modification
        elif action.type in ["delete_directory"]:
            return 0.8  # Multiple files
        elif action.type in ["execute_shell"]:
            return 0.9  # System-wide
        else:
            return 0.5  # Unknown
    
    def calculate_risk_score(self, factors: list[tuple[str, float]]) -> float:
        """Calculate overall risk score"""
        weights = {
            "reversibility": -0.3,  # Negative because higher is better
            "impact": 0.4,
            "sensitivity": 0.2,
            "history": -0.1
        }
        
        score = 0.5  # Baseline
        for name, value in factors:
            if name in weights:
                score += weights[name] * value
        
        return max(0.0, min(1.0, score))
    
    def determine_risk_level(self, score: float) -> str:
        """Determine risk level from score"""
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "medium"
        else:
            return "high"
```

---

## Budget Management

### Budget Structure

```python
class Budget:
    # Cost limits
    max_cost_usd: float | None
    current_cost_usd: float
    
    # Time limits
    max_time_seconds: float | None
    current_time_seconds: float
    
    # Token limits
    max_tokens: int | None
    current_tokens: int
    
    # Turn limits
    max_turns: int | None
    current_turns: int
    
    # Alerts
    alert_thresholds: dict[str, float]  # e.g., {"cost": 0.8, "time": 0.9}
    alerts_sent: set[str]

class BudgetStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"
```

### Budget Manager

```python
class BudgetManager:
    """Manage resource budgets"""
    
    def __init__(self):
        self.budgets: dict[str, Budget] = {}
        self.alert_system = AlertSystem()
    
    async def check_budget(self, goal_id: str, action: Action) -> BudgetCheck:
        """Check if action is within budget"""
        budget = self.budgets.get(goal_id)
        if not budget:
            return BudgetCheck(allowed=True, status=BudgetStatus.OK)
        
        # Estimate action cost
        estimated = await self.estimate_cost(action)
        
        # Check each limit
        issues = []
        
        # Cost check
        if budget.max_cost_usd:
            projected_cost = budget.current_cost_usd + estimated.cost_usd
            if projected_cost > budget.max_cost_usd:
                issues.append(BudgetIssue(
                    type="cost",
                    current=budget.current_cost_usd,
                    limit=budget.max_cost_usd,
                    projected=projected_cost
                ))
        
        # Time check
        if budget.max_time_seconds:
            projected_time = budget.current_time_seconds + estimated.time_seconds
            if projected_time > budget.max_time_seconds:
                issues.append(BudgetIssue(
                    type="time",
                    current=budget.current_time_seconds,
                    limit=budget.max_time_seconds,
                    projected=projected_time
                ))
        
        # Token check
        if budget.max_tokens:
            projected_tokens = budget.current_tokens + estimated.tokens
            if projected_tokens > budget.max_tokens:
                issues.append(BudgetIssue(
                    type="tokens",
                    current=budget.current_tokens,
                    limit=budget.max_tokens,
                    projected=projected_tokens
                ))
        
        # Determine status
        if issues:
            status = BudgetStatus.EXCEEDED
            allowed = False
        else:
            # Check warning thresholds
            status = self.check_thresholds(budget)
            allowed = True
            
            # Send alerts if needed
            if status == BudgetStatus.WARNING:
                await self.send_alerts(goal_id, budget)
        
        return BudgetCheck(
            allowed=allowed,
            status=status,
            issues=issues
        )
    
    def check_thresholds(self, budget: Budget) -> BudgetStatus:
        """Check if approaching limits"""
        max_usage = 0.0
        
        if budget.max_cost_usd:
            cost_usage = budget.current_cost_usd / budget.max_cost_usd
            max_usage = max(max_usage, cost_usage)
        
        if budget.max_time_seconds:
            time_usage = budget.current_time_seconds / budget.max_time_seconds
            max_usage = max(max_usage, time_usage)
        
        if budget.max_tokens:
            token_usage = budget.current_tokens / budget.max_tokens
            max_usage = max(max_usage, token_usage)
        
        if max_usage >= 1.0:
            return BudgetStatus.EXCEEDED
        elif max_usage >= 0.9:
            return BudgetStatus.CRITICAL
        elif max_usage >= 0.7:
            return BudgetStatus.WARNING
        else:
            return BudgetStatus.OK
    
    async def record_usage(
        self,
        goal_id: str,
        cost_usd: float,
        time_seconds: float,
        tokens: int
    ):
        """Record resource usage"""
        budget = self.budgets.get(goal_id)
        if not budget:
            return
        
        budget.current_cost_usd += cost_usd
        budget.current_time_seconds += time_seconds
        budget.current_tokens += tokens
        budget.current_turns += 1
        
        # Check status
        status = self.check_thresholds(budget)
        
        # Send alerts if needed
        if status in [BudgetStatus.WARNING, BudgetStatus.CRITICAL]:
            await self.send_alerts(goal_id, budget)
```

### Cost Estimator

```python
class CostEstimator:
    """Estimate action costs"""
    
    def __init__(self):
        # Token costs per model (per 1M tokens)
        self.token_costs = {
            "claude-opus-4": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4": {"input": 3.0, "output": 15.0},
            "claude-haiku-4": {"input": 0.25, "output": 1.25}
        }
    
    async def estimate_cost(self, action: Action) -> CostEstimate:
        """Estimate action cost"""
        # Estimate tokens
        input_tokens = self.estimate_input_tokens(action)
        output_tokens = self.estimate_output_tokens(action)
        
        # Calculate cost
        model = action.model or "claude-sonnet-4"
        cost_usd = (
            input_tokens / 1_000_000 * self.token_costs[model]["input"] +
            output_tokens / 1_000_000 * self.token_costs[model]["output"]
        )
        
        # Estimate time
        time_seconds = self.estimate_time(action)
        
        return CostEstimate(
            cost_usd=cost_usd,
            time_seconds=time_seconds,
            tokens=input_tokens + output_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
    
    def estimate_input_tokens(self, action: Action) -> int:
        """Estimate input tokens"""
        # Base context
        base_tokens = 1000
        
        # Action-specific
        if action.type == "read_file":
            # Estimate file size
            file_size = action.params.get("size", 1000)
            base_tokens += file_size // 4  # ~4 chars per token
        elif action.type == "web_search":
            base_tokens += 500  # Search results
        
        return base_tokens
    
    def estimate_output_tokens(self, action: Action) -> int:
        """Estimate output tokens"""
        if action.type in ["write_file", "edit_file"]:
            return 2000  # Code generation
        elif action.type == "analyze":
            return 1000  # Analysis
        else:
            return 500  # Default
```

---

## Audit System

### Operation Logger

```python
class OperationLogger:
    """Log all operations"""
    
    def __init__(self):
        self.db = AuditDatabase()
    
    async def log_operation(self, operation: Operation):
        """Log operation"""
        record = AuditRecord(
            id=generate_id(),
            timestamp=datetime.now(),
            operation_type=operation.type,
            operation_data=operation.to_dict(),
            user_id=operation.user_id,
            session_id=operation.session_id,
            goal_id=operation.goal_id,
            agent_id=operation.agent_id,
            result=operation.result,
            success=operation.success,
            duration=operation.duration,
            cost=operation.cost
        )
        
        await self.db.insert(record)
    
    async def query_operations(
        self,
        filters: dict,
        limit: int = 100
    ) -> list[AuditRecord]:
        """Query operation history"""
        return await self.db.query(filters, limit)
```

### Decision Tracker

```python
class DecisionTracker:
    """Track decision-making process"""
    
    async def track_decision(self, decision: Decision):
        """Track a decision"""
        record = DecisionRecord(
            id=generate_id(),
            timestamp=datetime.now(),
            decision_type=decision.type,
            context=decision.context,
            options=decision.options,
            selected_option=decision.selected,
            reasoning=decision.reasoning,
            confidence=decision.confidence,
            factors=decision.factors
        )
        
        await self.db.insert(record)
    
    async def get_decision_chain(self, goal_id: str) -> list[DecisionRecord]:
        """Get all decisions for a goal"""
        return await self.db.query({"goal_id": goal_id})
```

### Audit Trail

```python
class AuditTrail:
    """Complete audit trail"""
    
    async def generate_trail(self, goal_id: str) -> Trail:
        """Generate audit trail for goal"""
        # Get all operations
        operations = await self.operation_logger.query_operations(
            {"goal_id": goal_id}
        )
        
        # Get all decisions
        decisions = await self.decision_tracker.get_decision_chain(goal_id)
        
        # Get budget usage
        budget = await self.budget_manager.get_budget(goal_id)
        
        # Generate timeline
        timeline = self.create_timeline(operations, decisions)
        
        return Trail(
            goal_id=goal_id,
            operations=operations,
            decisions=decisions,
            budget=budget,
            timeline=timeline,
            summary=self.generate_summary(operations, decisions, budget)
        )
    
    def create_timeline(
        self,
        operations: list[AuditRecord],
        decisions: list[DecisionRecord]
    ) -> list[TimelineEvent]:
        """Create chronological timeline"""
        events = []
        
        # Add operations
        for op in operations:
            events.append(TimelineEvent(
                timestamp=op.timestamp,
                type="operation",
                data=op
            ))
        
        # Add decisions
        for dec in decisions:
            events.append(TimelineEvent(
                timestamp=dec.timestamp,
                type="decision",
                data=dec
            ))
        
        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        
        return events
```

---

## Control System

### Approval Workflow

```python
class ApprovalWorkflow:
    """Manage approval workflows"""
    
    def __init__(self):
        self.pending_approvals: dict[str, Approval] = {}
    
    async def request_approval(
        self,
        action: Action,
        reason: str
    ) -> ApprovalRequest:
        """Request user approval"""
        request = ApprovalRequest(
            id=generate_id(),
            action=action,
            reason=reason,
            risk_assessment=await self.risk_assessor.assess_risk(action),
            requested_at=datetime.now(),
            status="pending"
        )
        
        self.pending_approvals[request.id] = request
        
        # Notify user
        await self.notify_user(request)
        
        return request
    
    async def wait_for_approval(
        self,
        request_id: str,
        timeout: float = 300.0
    ) -> ApprovalResponse:
        """Wait for user approval"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            request = self.pending_approvals.get(request_id)
            
            if request.status == "approved":
                return ApprovalResponse(
                    approved=True,
                    modifications=request.modifications
                )
            elif request.status == "rejected":
                return ApprovalResponse(
                    approved=False,
                    reason=request.rejection_reason
                )
            
            await asyncio.sleep(1.0)
        
        # Timeout
        return ApprovalResponse(
            approved=False,
            reason="Approval timeout"
        )
    
    async def approve(
        self,
        request_id: str,
        modifications: dict | None = None
    ):
        """Approve request"""
        request = self.pending_approvals.get(request_id)
        if request:
            request.status = "approved"
            request.modifications = modifications
            request.approved_at = datetime.now()
    
    async def reject(self, request_id: str, reason: str):
        """Reject request"""
        request = self.pending_approvals.get(request_id)
        if request:
            request.status = "rejected"
            request.rejection_reason = reason
            request.rejected_at = datetime.now()
```

### Emergency Stop

```python
class EmergencyStop:
    """Emergency stop mechanism"""
    
    def __init__(self):
        self.stopped = False
        self.stop_reason: str | None = None
    
    def trigger(self, reason: str):
        """Trigger emergency stop"""
        self.stopped = True
        self.stop_reason = reason
        
        # Log event
        logger.critical(f"EMERGENCY STOP: {reason}")
        
        # Notify all agents
        self.notify_all_agents()
        
        # Save state
        self.save_state()
    
    def check(self):
        """Check if stopped"""
        if self.stopped:
            raise EmergencyStopError(self.stop_reason)
    
    def reset(self):
        """Reset emergency stop"""
        self.stopped = False
        self.stop_reason = None
```

### Rollback Manager

```python
class RollbackManager:
    """Manage operation rollback"""
    
    def __init__(self):
        self.checkpoints: dict[str, Checkpoint] = {}
    
    async def create_checkpoint(self, goal_id: str) -> str:
        """Create rollback checkpoint"""
        checkpoint = Checkpoint(
            id=generate_id(),
            goal_id=goal_id,
            timestamp=datetime.now(),
            state=await self.capture_state(goal_id)
        )
        
        self.checkpoints[checkpoint.id] = checkpoint
        return checkpoint.id
    
    async def rollback(self, checkpoint_id: str):
        """Rollback to checkpoint"""
        checkpoint = self.checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        # Restore state
        await self.restore_state(checkpoint.state)
        
        # Log rollback
        logger.info(f"Rolled back to checkpoint {checkpoint_id}")
    
    async def capture_state(self, goal_id: str) -> dict:
        """Capture current state"""
        return {
            "goal": await self.get_goal_state(goal_id),
            "plan": await self.get_plan_state(goal_id),
            "memory": await self.get_memory_state(goal_id),
            "files": await self.get_file_checksums(goal_id)
        }
    
    async def restore_state(self, state: dict):
        """Restore state from checkpoint"""
        # Restore goal
        await self.restore_goal_state(state["goal"])
        
        # Restore plan
        await self.restore_plan_state(state["plan"])
        
        # Restore memory
        await self.restore_memory_state(state["memory"])
        
        # Restore files (if possible)
        await self.restore_files(state["files"])
```

---

## Safety Policies

### Policy Engine

```python
class PolicyEngine:
    """Enforce safety policies"""
    
    def __init__(self):
        self.policies: list[Policy] = []
        self.load_default_policies()
    
    def load_default_policies(self):
        """Load default safety policies"""
        self.policies = [
            Policy(
                name="no_destructive_without_approval",
                description="Destructive actions require approval",
                rule=lambda action: (
                    action.type not in ["delete_file", "delete_directory"]
                    or action.approved
                )
            ),
            Policy(
                name="no_external_network_without_approval",
                description="External network requests require approval",
                rule=lambda action: (
                    action.type != "network_request"
                    or action.target.startswith("http://localhost")
                    or action.approved
                )
            ),
            Policy(
                name="respect_budget_limits",
                description="Must stay within budget limits",
                rule=lambda action: (
                    self.budget_manager.check_budget(
                        action.goal_id,
                        action
                    ).allowed
                )
            )
        ]
    
    async def check_policies(self, action: Action) -> PolicyCheck:
        """Check action against policies"""
        violations = []
        
        for policy in self.policies:
            if not await policy.evaluate(action):
                violations.append(PolicyViolation(
                    policy=policy.name,
                    description=policy.description,
                    severity=policy.severity
                ))
        
        return PolicyCheck(
            allowed=len(violations) == 0,
            violations=violations
        )
```

---

## Monitoring & Alerts

### Alert System

```python
class AlertSystem:
    """Send alerts to users"""
    
    async def send_alert(self, alert: Alert):
        """Send alert"""
        # Log alert
        logger.warning(f"ALERT: {alert.type} - {alert.message}")
        
        # Notify user
        await self.notify_user(alert)
        
        # Store alert
        await self.store_alert(alert)
    
    async def notify_user(self, alert: Alert):
        """Notify user of alert"""
        if alert.severity == "critical":
            # Immediate notification
            await self.send_immediate_notification(alert)
        else:
            # Queue for next interaction
            await self.queue_notification(alert)
```

### Health Monitor

```python
class HealthMonitor:
    """Monitor system health"""
    
    async def check_health(self) -> HealthStatus:
        """Check overall system health"""
        checks = {
            "memory": await self.check_memory_health(),
            "agents": await self.check_agent_health(),
            "budget": await self.check_budget_health(),
            "safety": await self.check_safety_health()
        }
        
        # Determine overall status
        if any(c.status == "critical" for c in checks.values()):
            overall = "critical"
        elif any(c.status == "warning" for c in checks.values()):
            overall = "warning"
        else:
            overall = "healthy"
        
        return HealthStatus(
            overall=overall,
            checks=checks,
            timestamp=datetime.now()
        )
```

---

## Summary

Safety & Governance provides:
- ✅ **Multi-layer safety**: Input, action, output validation
- ✅ **Risk assessment**: Comprehensive risk evaluation
- ✅ **Budget management**: Cost, time, token limits
- ✅ **Complete audit trail**: All operations logged
- ✅ **User control**: Approval workflows, overrides
- ✅ **Emergency stop**: Immediate halt capability
- ✅ **Rollback**: Checkpoint and restore
- ✅ **Policy enforcement**: Configurable safety policies

**Key Features**:
- Safe by default
- Transparent operations
- User in control
- Complete accountability
- Efficient validation

**Architecture Complete**: All 5 v4.0 architecture documents created! 🎉

---

**Related Documents**:
- `01-ARCHITECTURE_OVERVIEW.md`: System overview
- `02-MEMORY_SYSTEM.md`: Memory architecture
- `03-MULTI_AGENT_ORCHESTRATION.md`: Multi-agent design
- `04-PLANNING_REASONING.md`: Planning system
