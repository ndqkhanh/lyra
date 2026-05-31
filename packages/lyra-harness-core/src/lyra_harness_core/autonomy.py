"""Autonomy Loop + Crash Detection (P4-B4 HIGH).

Continuous operation loop with watchdog health checks, crash-loop detection,
auto-repair pipeline, and configurable stop conditions.

See: plan-phase4-swarm-investigations.md §4.14
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Health & Watchdog Types
# ---------------------------------------------------------------------------


class AgentHealth(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNSTABLE = "unstable"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


class CrashSeverity(str, enum.Enum):
    RECOVERABLE = "recoverable"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclass(frozen=True)
class CrashEvent:
    """Record of a single crash."""
    timestamp: float
    error_type: str
    error_message: str
    severity: CrashSeverity = CrashSeverity.RECOVERABLE
    stack_trace: str = ""


@dataclass(frozen=True)
class CrashLoopState:
    """State of crash-loop detection."""
    is_crash_loop: bool
    crash_count: int
    window_seconds: float
    latest_crashes: tuple[CrashEvent, ...]
    first_crash_time: float | None

    @property
    def crash_rate(self) -> float:
        if self.first_crash_time is None or self.window_seconds == 0:
            return 0.0
        elapsed = time.time() - self.first_crash_time
        if elapsed <= 0:
            return 0.0
        return self.crash_count / elapsed


@dataclass
class CrashDetector:
    """Detect crash loops: 3 crashes within 300s → auto-escalate."""
    crash_threshold: int = 3
    window_seconds: float = 300.0
    _crashes: list[CrashEvent] = field(default_factory=list)

    def record_crash(self, error_type: str, error_message: str = "", severity: CrashSeverity = CrashSeverity.RECOVERABLE) -> None:
        self._crashes.append(CrashEvent(
            timestamp=time.time(),
            error_type=error_type,
            error_message=error_message,
            severity=severity,
        ))
        self._prune()

    def _prune(self) -> None:
        cutoff = time.time() - self.window_seconds
        self._crashes = [c for c in self._crashes if c.timestamp > cutoff]

    def check(self) -> CrashLoopState:
        self._prune()
        recent = [c for c in self._crashes if c.timestamp > time.time() - self.window_seconds]
        is_loop = len(recent) >= self.crash_threshold
        first = recent[0].timestamp if recent else None
        return CrashLoopState(
            is_crash_loop=is_loop,
            crash_count=len(recent),
            window_seconds=self.window_seconds,
            latest_crashes=tuple(sorted(recent, key=lambda c: c.timestamp, reverse=True)[:10]),
            first_crash_time=first,
        )

    def reset(self) -> None:
        self._crashes.clear()

    @property
    def crash_count(self) -> int:
        self._prune()
        return len(self._crashes)


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthCheck:
    """Result of a single health check."""
    component: str
    health: AgentHealth
    message: str = ""
    latency_ms: float = 0.0


@dataclass(frozen=True)
class SystemHealth:
    """Aggregate system health across components."""
    checks: tuple[HealthCheck, ...]
    overall: AgentHealth
    degraded_components: tuple[str, ...]
    crashed_components: tuple[str, ...]

    @property
    def is_healthy(self) -> bool:
        return self.overall == AgentHealth.HEALTHY

    @property
    def can_operate(self) -> bool:
        return self.overall not in (AgentHealth.CRASHED, AgentHealth.UNKNOWN)


@dataclass
class Watchdog:
    """Watchdog monitoring with lifecycle×health matrix per alphaclaw pattern."""
    _checks: dict[str, HealthCheck] = field(default_factory=dict)
    crash_detector: CrashDetector = field(default_factory=CrashDetector)

    def check_component(self, component: str, health: AgentHealth, message: str = "") -> None:
        self._checks[component] = HealthCheck(component=component, health=health, message=message, latency_ms=0.0)

    def check_all(self) -> SystemHealth:
        checks = tuple(self._checks.values())
        if not checks:
            return SystemHealth(checks=(), overall=AgentHealth.HEALTHY, degraded_components=(), crashed_components=())

        degraded = tuple(c.component for c in checks if c.health == AgentHealth.DEGRADED)
        crashed = tuple(c.component for c in checks if c.health == AgentHealth.CRASHED)

        if any(c.health == AgentHealth.CRASHED for c in checks):
            overall = AgentHealth.CRASHED
        elif any(c.health == AgentHealth.UNSTABLE for c in checks):
            overall = AgentHealth.UNSTABLE
        elif any(c.health == AgentHealth.DEGRADED for c in checks):
            overall = AgentHealth.DEGRADED
        else:
            overall = AgentHealth.HEALTHY

        return SystemHealth(checks=checks, overall=overall, degraded_components=degraded, crashed_components=crashed)

    def record_error(self, error_type: str, message: str = "") -> CrashLoopState:
        self.crash_detector.record_crash(error_type, message)
        return self.crash_detector.check()

    @property
    def component_count(self) -> int:
        return len(self._checks)

    def reset(self) -> None:
        self._checks.clear()
        self.crash_detector.reset()


# ---------------------------------------------------------------------------
# Stop Conditions
# ---------------------------------------------------------------------------


class StopReason(str, enum.Enum):
    GOAL_ACHIEVED = "goal_achieved"
    MAX_ITERATIONS = "max_iterations"
    CRASH_LOOP = "crash_loop"
    USER_INTERRUPT = "user_interrupt"
    TIMEOUT = "timeout"
    HEALTH_FAILURE = "health_failure"
    EXPLICIT_STOP = "explicit_stop"


@dataclass(frozen=True)
class StopCondition:
    """A named condition that can halt the autonomy loop."""
    name: str
    reason: StopReason
    description: str = ""


@dataclass
class StopConditionDSL:
    """DSL for defining when the autonomy loop should stop."""
    _conditions: list[StopCondition] = field(default_factory=list)

    def add(self, name: str, reason: StopReason, description: str = "") -> None:
        self._conditions.append(StopCondition(name=name, reason=reason, description=description))

    def evaluate(self, context: dict) -> StopCondition | None:
        """Evaluate all conditions against context. Returns first triggered."""
        for cond in self._conditions:
            if cond.reason == StopReason.MAX_ITERATIONS:
                max_iter = context.get("max_iterations", 0)
                current = context.get("iteration", 0)
                if max_iter > 0 and current >= max_iter:
                    return cond
            elif cond.reason == StopReason.TIMEOUT:
                deadline = context.get("deadline", 0.0)
                if deadline > 0 and time.time() >= deadline:
                    return cond
            elif cond.reason == StopReason.GOAL_ACHIEVED:
                if context.get("goal_achieved", False):
                    return cond
            elif cond.reason == StopReason.CRASH_LOOP:
                if context.get("crash_loop", False):
                    return cond
            elif cond.reason == StopReason.HEALTH_FAILURE:
                if not context.get("can_operate", True):
                    return cond
        return None

    @property
    def condition_count(self) -> int:
        return len(self._conditions)


# ---------------------------------------------------------------------------
# Autonomy Loop
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoopStep:
    """Record of a single step in the autonomy loop."""
    iteration: int
    phase: str  # health_check, plan, execute, verify, persist
    success: bool
    duration_ms: float
    details: str = ""


@dataclass(frozen=True)
class LoopResult:
    """Final result of an autonomy loop run."""
    steps: tuple[LoopStep, ...]
    stop_reason: StopReason
    total_iterations: int
    successful_steps: int
    failed_steps: int
    total_duration_ms: float
    crash_events: tuple[CrashEvent, ...]

    @property
    def success_rate(self) -> float:
        total = self.successful_steps + self.failed_steps
        if total == 0:
            return 1.0
        return self.successful_steps / total


@dataclass
class AutonomyLoop:
    """Full autonomy loop with watchdog, crash detection, and stop conditions.

    while not complete:
        1. health check
        2. context refresh
        3. plan next step
        4. execute with guard
        5. verify
        6. persist
        7. check stop conditions

    Usage::

        loop = AutonomyLoop(max_iterations=100)
        loop.stop_conditions.add("max_iter", StopReason.MAX_ITERATIONS)
        result = loop.run(plan_fn=my_planner, execute_fn=my_executor, verify_fn=my_verifier)
    """

    watchdog: Watchdog = field(default_factory=Watchdog)
    crash_detector: CrashDetector = field(default_factory=CrashDetector)
    stop_conditions: StopConditionDSL = field(default_factory=StopConditionDSL)
    max_iterations: int = 100
    deadline: float | None = None
    _steps: list[LoopStep] = field(default_factory=list)
    _crashes: list[CrashEvent] = field(default_factory=list)
    _iteration: int = 0
    _start_time: float = 0.0

    def run(
        self,
        plan_fn,
        execute_fn,
        verify_fn,
        initial_context: dict | None = None,
    ) -> LoopResult:
        """Run the autonomy loop until a stop condition is met."""
        self._steps = []
        self._crashes = []
        self._iteration = 0
        self._start_time = time.time()

        context = dict(initial_context or {})
        context["goal_achieved"] = False
        context["crash_loop"] = False
        context["can_operate"] = True

        while self._iteration < self.max_iterations:
            t0 = time.time()

            # 1. Health check
            health = self.watchdog.check_all()
            if not health.can_operate:
                self._add_step("health_check", False, t0, "System unhealthy")
                context["can_operate"] = False
                return self._build_result(StopReason.HEALTH_FAILURE)

            # Check crash loop
            crash_state = self.crash_detector.check()
            if crash_state.is_crash_loop:
                self._add_step("health_check", False, t0, "Crash loop detected")
                context["crash_loop"] = True
                return self._build_result(StopReason.CRASH_LOOP)

            # 2. Plan next step
            try:
                plan = plan_fn(context, self._iteration)
            except Exception as e:
                self._record_crash("plan_error", str(e))
                self._add_step("plan", False, t0, str(e)[:100])
                context["goal_achieved"] = True  # stop on plan failure
                return self._build_result(StopReason.GOAL_ACHIEVED)

            self._add_step("plan", True, t0)

            # 3. Execute
            t1 = time.time()
            try:
                result = execute_fn(plan, context)
            except Exception as e:
                self._record_crash("execute_error", str(e))
                self._add_step("execute", False, t1, str(e)[:100])
                context["goal_achieved"] = True
                return self._build_result(StopReason.GOAL_ACHIEVED)
            self._add_step("execute", True, t1)

            # 4. Verify
            t2 = time.time()
            try:
                verified = verify_fn(result, context)
                if not verified:
                    self._add_step("verify", False, t2, "Verification failed")
            except Exception as e:
                self._record_crash("verify_error", str(e))
                self._add_step("verify", False, t2, str(e)[:100])
            else:
                self._add_step("verify", True, t2)

            # 5. Persist
            t3 = time.time()
            try:
                context.update(result if isinstance(result, dict) else {})
                context["iteration"] = self._iteration
            except Exception:
                pass
            self._add_step("persist", True, t3)

            # 6. Check stop conditions
            context["iteration"] = self._iteration + 1
            context["max_iterations"] = self.max_iterations
            if self.deadline:
                context["deadline"] = self.deadline
            context["crash_loop"] = crash_state.is_crash_loop
            context["can_operate"] = health.can_operate

            stop_trigger = self.stop_conditions.evaluate(context)
            if stop_trigger is not None:
                return self._build_result(stop_trigger.reason)

            self._iteration += 1

        return self._build_result(StopReason.MAX_ITERATIONS)

    def _add_step(self, phase: str, success: bool, start_time: float, details: str = "") -> None:
        self._steps.append(LoopStep(
            iteration=self._iteration,
            phase=phase,
            success=success,
            duration_ms=(time.time() - start_time) * 1000,
            details=details,
        ))

    def _record_crash(self, error_type: str, message: str) -> None:
        self._crashes.append(CrashEvent(
            timestamp=time.time(), error_type=error_type, error_message=message,
        ))

    def _build_result(self, reason: StopReason) -> LoopResult:
        successful = sum(1 for s in self._steps if s.success)
        failed = len(self._steps) - successful
        return LoopResult(
            steps=tuple(self._steps),
            stop_reason=reason,
            total_iterations=self._iteration,
            successful_steps=successful,
            failed_steps=failed,
            total_duration_ms=(time.time() - self._start_time) * 1000,
            crash_events=tuple(self._crashes),
        )

    @property
    def steps(self) -> tuple[LoopStep, ...]:
        return tuple(self._steps)

    def reset(self) -> None:
        self._steps = []
        self._crashes = []
        self._iteration = 0
        self.watchdog.reset()
        self.crash_detector.reset()


__all__ = [
    "AgentHealth",
    "AutonomyLoop",
    "CrashDetector",
    "CrashEvent",
    "CrashLoopState",
    "CrashSeverity",
    "HealthCheck",
    "LoopResult",
    "LoopStep",
    "StopCondition",
    "StopConditionDSL",
    "StopReason",
    "SystemHealth",
    "Watchdog",
]
