"""
Lyra Dynamic Workflow Engine + Adversarial Verification Protocol (AVP).

This is Lyra's "ultracode" equivalent — code-driven background workflows with
adversarial cross-checking that work across all configured providers.

Core components:
- **WorkflowEngine**: Background script executor with concurrency control,
  pause/resume serialization, and progress tracking
- **AdversarialVerifier**: 3-critic cross-model verification with mutation gating
  and consensus voting (SABER + AutoScientists patterns)
- **AutoOrchestrator**: Effort-driven workflow auto-trigger that decides whether
  a task warrants a workflow

Usage::

    from lyra_workflow import WorkflowEngine, AdversarialVerifier

    engine = WorkflowEngine()
    engine.start_workflow(script, providers={"default": "deepseek-flash"})
    # ... workflow runs in background ...
    status = engine.get_status(workflow_id)
"""

from __future__ import annotations

from .avp import (
    AdversarialVerifier,
    Claim,
    CriticVerdict,
    DecisionMatrix,
    MutationGate,
    Verdict,
)
from .engine import (
    AgentTask,
    PauseResumeSerializer,
    ScriptVM,
    WorkflowEngine,
    WorkflowPhase,
    WorkflowScript,
    WorkflowStatus,
)
from .orchestrator import AutoOrchestrator

__all__ = [
    "AdversarialVerifier",
    "AgentTask",
    "AutoOrchestrator",
    "Claim",
    "CriticVerdict",
    "DecisionMatrix",
    "MutationGate",
    "PauseResumeSerializer",
    "ScriptVM",
    "Verdict",
    "WorkflowEngine",
    "WorkflowPhase",
    "WorkflowScript",
    "WorkflowStatus",
]
