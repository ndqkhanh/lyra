"""Integrated Agent — governance, learning, and eval hooks wrapped around AgentLoop.

Pre-turn safety check → pre-tool anti-pattern check → post-turn experience
capture → halt/resume with crash-loop detection.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_core.agent.loop import AgentLoop, TurnResult
from lyra_core.evaluation.pipeline import EvalPipeline, EvalTrigger
from lyra_core.experience.anti_pattern import AntiPatternRegistry
from lyra_core.experience.extractor import ExperienceExtractor, ExperienceRecord
from lyra_core.experience.learning_loop import LearningLoop
from lyra_core.safety.governance import PolicyEngine, PolicyVerdict


class HaltReason(str, Enum):
    SAFETY_DENY = "safety_deny"
    CRASH_LOOP = "crash_loop"
    MANUAL = "manual"
    COOLDOWN = "cooldown"
    RECOVERY_EXHAUSTED = "recovery_exhausted"


class AgentStatus(str, Enum):
    RUNNING = "running"
    HALTED = "halted"
    COOLDOWN = "cooldown"
    RECOVERING = "recovering"
    DEGRADED = "degraded"
    STOPPED = "stopped"


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for IntegratedAgent."""

    max_turns: int = 100
    cooldown_seconds: float = 5.0
    max_recovery_attempts: int = 3
    crash_loop_threshold: int = 5
    learning_cycle_interval: int = 50
    auto_eval_after_turns: int = 20
    block_on_anti_pattern: bool = True
    safety_strict: bool = False


@dataclass(frozen=True)
class AgentSafetyContext:
    """Snapshot of the safety state at a point in time."""

    policy_verdict: PolicyVerdict
    blocked_tools: tuple[str, ...]
    anti_pattern_matches: tuple[str, ...]
    last_check_time: float
    override_active: bool = False


@dataclass
class HaltResumeController:
    """Manages halt/resume lifecycle with crash-loop detection.

    Usage::

        ctrl = HaltResumeController()
        ctrl.halt(HaltReason.SAFETY_DENY)
        ctrl.begin_recovery()
        # ... recovery actions ...
        ctrl.resume()
    """

    max_recovery_attempts: int = 3
    crash_loop_threshold: int = 5
    cooldown_seconds: float = 5.0

    status: AgentStatus = AgentStatus.RUNNING
    halt_reason: HaltReason | None = None
    halted_at: float | None = None
    recovery_attempts: int = 0
    crash_count: int = 0
    last_crash_time: float | None = None
    total_halt_count: int = 0
    total_resume_count: int = 0

    def halt(self, reason: HaltReason) -> None:
        """Halt the agent. Sets cooldown timer."""
        self.status = AgentStatus.HALTED
        self.halt_reason = reason
        self.halted_at = time.time()
        self.total_halt_count += 1

    def begin_recovery(self) -> bool:
        """Begin recovery from a halted state. Returns False if recovery exhausted."""
        if self.recovery_attempts >= self.max_recovery_attempts:
            self.status = AgentStatus.STOPPED
            self.halt_reason = HaltReason.RECOVERY_EXHAUSTED
            return False

        self.status = AgentStatus.RECOVERING
        self.recovery_attempts += 1
        return True

    def resume(self) -> bool:
        """Resume from recovery. Returns False if cooldown not expired."""
        if self.status != AgentStatus.RECOVERING:
            return False

        now = time.time()
        if self.halted_at is not None and (now - self.halted_at) < self.cooldown_seconds:
            self.status = AgentStatus.COOLDOWN
            self.halt_reason = HaltReason.COOLDOWN
            return False

        self.status = AgentStatus.RUNNING
        self.halt_reason = None
        self.halted_at = None
        self.recovery_attempts = 0
        self.total_resume_count += 1
        return True

    def record_crash(self) -> bool:
        """Record a crash. Returns True if crash loop detected."""
        now = time.time()
        if self.last_crash_time is not None and (now - self.last_crash_time) < 60:
            self.crash_count += 1
        else:
            self.crash_count = 1

        self.last_crash_time = now

        if self.crash_count >= self.crash_loop_threshold:
            self.halt(HaltReason.CRASH_LOOP)
            return True
        return False

    def is_running(self) -> bool:
        return self.status == AgentStatus.RUNNING

    def is_halted(self) -> bool:
        return self.status in (AgentStatus.HALTED, AgentStatus.STOPPED)

    def reset(self) -> None:
        self.status = AgentStatus.RUNNING
        self.halt_reason = None
        self.halted_at = None
        self.recovery_attempts = 0
        self.crash_count = 0
        self.last_crash_time = None


@dataclass
class IntegratedAgent:
    """AgentLoop wrapped with governance, learning, and eval hooks.

    Usage::

        agent = IntegratedAgent(
            loop=AgentLoop(llm=..., tools=..., store=...),
        )
        result = agent.run_conversation("analyze this code", session_id="s1")
        print(agent.health_report())
    """

    loop: AgentLoop
    config: AgentConfig = field(default_factory=AgentConfig)
    policy_engine: PolicyEngine = field(default_factory=PolicyEngine)
    anti_pattern_registry: AntiPatternRegistry = field(default_factory=AntiPatternRegistry)
    learning_loop: LearningLoop = field(default_factory=LearningLoop)
    eval_pipeline: EvalPipeline = field(default_factory=EvalPipeline)
    halt_controller: HaltResumeController = field(default_factory=HaltResumeController)
    experience_extractor: ExperienceExtractor = field(default_factory=ExperienceExtractor)

    _turn_count: int = 0
    _last_safety_check: float = 0.0
    _current_safety_context: AgentSafetyContext | None = None

    def run_conversation(self, user_text: str, *, session_id: str = "") -> TurnResult:
        """Run a conversation turn with pre-flight safety checks."""
        if not session_id:
            session_id = f"s-{uuid.uuid4().hex[:12]}"

        if not self.halt_controller.is_running():
            return self._halted_result()

        # Pre-turn safety check
        safety_ctx = self._pre_turn_check(user_text, session_id)
        self._current_safety_context = safety_ctx

        if safety_ctx.policy_verdict == PolicyVerdict.DENY:
            self.halt_controller.halt(HaltReason.SAFETY_DENY)
            return TurnResult(
                final_text="Action denied by safety policy.",
                stopped_by="safety_deny",
            )

        try:
            result = self.loop.run_conversation(user_text, session_id=session_id)
            self._turn_count += 1
        except Exception:
            crash_loop = self.halt_controller.record_crash()
            if crash_loop:
                return TurnResult(
                    final_text="Agent halted: crash loop detected.",
                    stopped_by="crash_loop",
                )
            raise

        # Post-turn experience capture
        self._post_turn_capture(user_text, result, session_id)

        # Periodic learning cycle
        if self._turn_count % self.config.learning_cycle_interval == 0:
            self._run_async(self.learning_loop.run_cycle())

        # Periodic eval
        if self._turn_count % self.config.auto_eval_after_turns == 0:
            self.eval_pipeline.run(EvalTrigger.SCHEDULED)

        return result

    def _pre_turn_check(self, user_text: str, session_id: str) -> AgentSafetyContext:
        """Run safety checks before processing a turn."""
        ctx = {"action": "run_conversation", "user_text": user_text, "session_id": session_id}
        verdict = self.policy_engine.evaluate("run_conversation", ctx)

        anti_matches = self.anti_pattern_registry.match(user_text)
        blocked: list[str] = []
        if self.config.block_on_anti_pattern:
            blocked = [m.anti_pattern.name for m in anti_matches if m.matched]

        self._last_safety_check = time.time()

        return AgentSafetyContext(
            policy_verdict=verdict,
            blocked_tools=tuple(blocked),
            anti_pattern_matches=tuple(m.anti_pattern.name for m in anti_matches),
            last_check_time=self._last_safety_check,
        )

    def _post_turn_capture(self, user_text: str, result: TurnResult, session_id: str) -> None:
        """Capture experience after a completed turn."""
        is_success = result.stopped_by == "end_turn" and not result.final_text.startswith(
            "Action denied"
        )
        effective_outcome = (
            "success"
            if is_success
            else ("failure" if result.stopped_by != "end_turn" else "partial")
        )

        record = ExperienceRecord(
            id=f"exp-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            task_signature=user_text[:100],
            outcome=effective_outcome,
            turn_count=result.iterations,
            tool_calls=len(result.tool_calls),
            final_artefact=result.final_text[:500] if result.final_text else "",
            error_message="" if is_success else result.stopped_by,
            duration_ms=0,
        )
        self._run_async(self.learning_loop.submit_record(record))

    def halt(self, reason: HaltReason) -> None:
        """Manually halt the agent."""
        self.halt_controller.halt(reason)

    def resume(self) -> bool:
        """Attempt to resume from a halted state."""
        if self.halt_controller.begin_recovery():
            return self.halt_controller.resume()
        return False

    def health_report(self) -> dict[str, Any]:
        """Aggregate health report from all subsystems."""
        safety = self._current_safety_context
        return {
            "status": self.halt_controller.status.value,
            "turn_count": self._turn_count,
            "halt_count": self.halt_controller.total_halt_count,
            "resume_count": self.halt_controller.total_resume_count,
            "crash_count": self.halt_controller.crash_count,
            "recovery_attempts": self.halt_controller.recovery_attempts,
            "safety_verdict": safety.policy_verdict.value if safety else "unknown",
            "blocked_tools": list(safety.blocked_tools) if safety else [],
            "anti_pattern_matches": list(safety.anti_pattern_matches) if safety else [],
            "policies_active": self.policy_engine.policy_count,
            "anti_patterns_registered": self.anti_pattern_registry.count,
            "learning_records_pending": len(self.learning_loop.get_pending_records()),
            "eval_runs": self.eval_pipeline.run_count,
            "last_overall_score": self.eval_pipeline.last_overall_score,
        }

    def _halted_result(self) -> TurnResult:
        reason_val = (
            self.halt_controller.halt_reason.value
            if self.halt_controller.halt_reason
            else "unknown"
        )
        return TurnResult(
            final_text=f"Agent is {self.halt_controller.status.value}: {reason_val}",
            stopped_by=(
                self.halt_controller.halt_reason.value
                if self.halt_controller.halt_reason
                else "halted"
            ),
        )

    @property
    def is_running(self) -> bool:
        return self.halt_controller.is_running()

    @property
    def is_halted(self) -> bool:
        return self.halt_controller.is_halted()

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @staticmethod
    def _run_async(coro: Any) -> None:
        """Run a coroutine, scheduling on running loop or standalone."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    def reset(self) -> None:
        """Reset the agent to initial state."""
        self._turn_count = 0
        self._last_safety_check = 0.0
        self._current_safety_context = None
        self.halt_controller.reset()
        self.eval_pipeline.clear_history()
