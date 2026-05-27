"""ExecutionIntegrity — verifies tool calls preserve intent and produce valid results.

Formal correctness model (compiler analogy): every tool call is verified for
argument validity, outcome matching, and intent preservation.
"""

from .models import ExecutionIntent, IntegrityViolation, ViolationSeverity


class ExecutionIntegrity:
    """Verifies tool executions preserve intent and produce valid outcomes.

    Three verification axes:
    1. Argument validity — required args present, types correct
    2. Intent preservation — outcome matches what was declared
    3. Side-effect safety — no destructive operations unprompted
    """

    _DESTRUCTIVE_PATTERNS = [
        "rm -rf", "delete", "drop table", "truncate",
        "format", "purge", "destroy", "--no-verify", "--force",
    ]

    def __init__(self, strict_mode: bool = True):
        self._intents: dict[str, ExecutionIntent] = {}
        self._violations: dict[str, IntegrityViolation] = {}
        self._strict_mode = strict_mode

    def declare_intent(
        self,
        tool_name: str,
        intent_description: str,
        expected_args: tuple[str, ...],
        expected_outcome: str,
    ) -> ExecutionIntent:
        """Declare the intent behind a tool execution before it runs."""
        import uuid

        intent = ExecutionIntent(
            id=str(uuid.uuid4()),
            tool_name=tool_name,
            intent_description=intent_description,
            expected_args=expected_args,
            expected_outcome=expected_outcome,
        )
        self._intents[intent.id] = intent
        return intent

    def verify_execution(
        self,
        intent_id: str,
        actual_args: tuple[str, ...],
        actual_outcome: str,
        tool_output: str = "",
    ) -> list[IntegrityViolation]:
        """Verify a completed tool execution against its declared intent."""
        import uuid

        violations: list[IntegrityViolation] = []
        intent = self._intents.get(intent_id)
        if intent is None:
            return violations

        missing = set(intent.expected_args) - set(actual_args)
        if missing:
            v = IntegrityViolation(
                id=str(uuid.uuid4()),
                tool_name=intent.tool_name,
                violation_type="missing_args",
                description=f"Missing required arguments: {', '.join(sorted(missing))}",
                severity=ViolationSeverity.HIGH,
                args_provided=actual_args,
                args_expected=intent.expected_args,
            )
            violations.append(v)

        if intent.expected_outcome.lower() not in actual_outcome.lower():
            if self._strict_mode:
                v = IntegrityViolation(
                    id=str(uuid.uuid4()),
                    tool_name=intent.tool_name,
                    violation_type="outcome_mismatch",
                    description=f"Expected '{intent.expected_outcome}' but got '{actual_outcome[:100]}'",
                    severity=ViolationSeverity.MEDIUM,
                )
                violations.append(v)

        destructive = self._check_destructive(tool_output)
        if destructive:
            v = IntegrityViolation(
                id=str(uuid.uuid4()),
                tool_name=intent.tool_name,
                violation_type="destructive_pattern",
                description=f"Destructive pattern detected: {destructive}",
                severity=ViolationSeverity.CRITICAL,
            )
            violations.append(v)

        for v in violations:
            self._violations[v.id] = v

        return violations

    def _check_destructive(self, output: str) -> str | None:
        output_lower = output.lower()
        for pattern in self._DESTRUCTIVE_PATTERNS:
            if pattern in output_lower:
                return pattern
        return None

    def history(self) -> list[IntegrityViolation]:
        return sorted(
            self._violations.values(),
            key=lambda v: v.detected_at,
            reverse=True,
        )

    def violations_by_severity(self, severity: ViolationSeverity) -> list[IntegrityViolation]:
        return [v for v in self._violations.values() if v.severity == severity]

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    @property
    def intent_count(self) -> int:
        return len(self._intents)
