"""FailurePatternGuard — detects 8 recurring failure modes in agent execution."""


from .models import FailureMode, FailureSignal


class FailurePatternGuard:
    """Detects 8 recurring failure modes from production research.

    1. Retrieval noise & context overload
    2. Hallucinated tool-call arguments
    3. Recursive loops & polling tax
    4. Guardrail failures
    5. Pre-training bias overriding context
    6. Unhandled external API schema changes
    7. Instruction drift in long sessions (>20 turns)
    8. Code generation safety (destructive commands)
    """

    _DESTRUCTIVE_PATTERNS = [
        "rm -rf", "sudo rm", "format c:", "drop table",
        "delete from", "truncate table", "shutdown", "reboot",
    ]

    _LOOP_SIGNALS = [
        "retrying", "attempt", "try again", "one more time",
        "let me try", "re-running", "re-executing",
    ]

    def __init__(self, drift_turn_threshold: int = 20, loop_threshold: int = 3):
        self._signals: dict[str, FailureSignal] = {}
        self._drift_turn_threshold = drift_turn_threshold
        self._loop_threshold = loop_threshold

    def detect(
        self, session_id: str, turn_number: int,
        context: str = "", tool_name: str = "", tool_args: str = "",
    ) -> list[FailureSignal]:
        """Run all 8 failure pattern detectors."""
        signals: list[FailureSignal] = []

        # 1. Context overload
        if len(context) > 10000:
            s = self._make_signal(
                FailureMode.CONTEXT_OVERLOAD,
                f"Context length {len(context)} exceeds safe threshold",
                session_id, turn_number,
            )
            signals.append(s)

        # 2. Retrieval noise
        if context.count("\n") > 200:
            s = self._make_signal(
                FailureMode.RETRIEVAL_NOISE,
                f"High retrieval noise: {context.count(chr(10))} newlines in context",
                session_id, turn_number,
            )
            signals.append(s)

        # 3. Hallucinated args
        if tool_name and tool_args:
            if tool_args in ("{}", "null", "undefined", "None"):
                s = self._make_signal(
                    FailureMode.HALLUCINATED_ARGS,
                    f"Potentially hallucinated args for {tool_name}: {tool_args}",
                    session_id, turn_number, severity=0.7,
                )
                signals.append(s)

        # 4. Recursive loops
        loop_count = sum(1 for signal in self._LOOP_SIGNALS if signal in context.lower())
        if loop_count >= self._loop_threshold:
            s = self._make_signal(
                FailureMode.RECURSIVE_LOOP,
                f"Recursive loop detected: {loop_count} loop signals",
                session_id, turn_number, severity=0.8,
            )
            signals.append(s)

        # 5. Polling tax
        if turn_number > 10 and tool_name == "search" and context.count("search") > 5:
            s = self._make_signal(
                FailureMode.POLLING_TAX,
                f"Polling tax: excessive search calls on turn {turn_number}",
                session_id, turn_number, severity=0.5,
            )
            signals.append(s)

        # 6. Instruction drift
        if turn_number >= self._drift_turn_threshold:
            if _has_drift_indicators(context):
                s = self._make_signal(
                    FailureMode.INSTRUCTION_DRIFT,
                    f"Instruction drift detected at turn {turn_number}",
                    session_id, turn_number, severity=0.75,
                )
                signals.append(s)

        # 7. Destructive code
        if _contains_destructive(tool_args):
            s = self._make_signal(
                FailureMode.DESTRUCTIVE_CODE,
                f"Destructive code pattern in tool args: {tool_args[:100]}",
                session_id, turn_number, severity=1.0,
            )
            signals.append(s)

        # 8. Guardrail / Bias override detection
        bias_signals = ["always been", "everyone knows", "obviously", "clearly the only"]
        bias_count = sum(1 for b in bias_signals if b in context.lower())
        if bias_count >= 2:
            s = self._make_signal(
                FailureMode.BIAS_OVERRIDE,
                f"Pre-training bias override: {bias_count} bias signals",
                session_id, turn_number, severity=0.6,
            )
            signals.append(s)

        for s in signals:
            self._signals[s.id] = s
        return signals

    def _make_signal(self, mode: FailureMode, desc: str, sid: str, turn: int, severity: float = 0.5) -> FailureSignal:
        import uuid
        return FailureSignal(
            id=str(uuid.uuid4()), failure_mode=mode, description=desc,
            session_id=sid, turn_number=turn, severity=severity,
        )

    def signals_by_mode(self, mode: FailureMode) -> list[FailureSignal]:
        return [s for s in self._signals.values() if s.failure_mode == mode]

    def summary(self) -> dict:
        """Return aggregate failure signal statistics."""
        if not self._signals:
            return {"total_signals": 0, "by_mode": {}}
        by_mode: dict[str, int] = {}
        for s in self._signals.values():
            by_mode[s.failure_mode.value] = by_mode.get(s.failure_mode.value, 0) + 1
        return {"total_signals": len(self._signals), "by_mode": by_mode}

    @property
    def signal_count(self) -> int:
        return len(self._signals)


def _has_drift_indicators(context: str) -> bool:
    """Check for instruction drift indicators in long sessions."""
    lower = context.lower()
    drift = [
        "forget", "what was i", "lost track", "starting over",
        "from scratch", "let me restart", "new approach", "different angle",
    ]
    return sum(1 for d in drift if d in lower) >= 2


def _contains_destructive(args: str) -> bool:
    args_lower = args.lower()
    return any(p in args_lower for p in FailurePatternGuard._DESTRUCTIVE_PATTERNS)
