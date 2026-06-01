"""Example integration of Audit Engine with Approval Gate.

This demonstrates how the Audit Engine integrates with the existing
Safety Governance Framework components.
"""

from lyra_core.safety import (
    ApprovalGate,
    AuditLogger,
    Decision,
    ReasoningFlag,
    RiskLevel,
    Verdict,
)


def main() -> None:
    """Demonstrate audit engine integration."""
    # Initialize components
    gate = ApprovalGate()
    audit_logger = AuditLogger()

    # Example 1: Low-risk action (auto-approved)
    decision1 = gate.evaluate(
        action_description="Read configuration file",
        parameters={"path": "/app/config.json"},
    )

    audit_logger.log(
        action_description="Read configuration file",
        risk_level=decision1.risk.level,
        reasoning_flags=list(decision1.risk.reasoning_flags),
        adversarial_verdict=Verdict.NOT_PERFORMED,
        final_decision=Decision.APPROVED,
        metadata={
            "gate_id": decision1.gate_id,
            "gate_action": decision1.action.name,
        },
    )

    # Example 2: High-risk action with reasoning flags
    decision2 = gate.evaluate(
        action_description="Execute shell command with user input",
        parameters={"command": "eval(user_input)"},
        reasoning_flags=[ReasoningFlag.DECEPTION, ReasoningFlag.POWER_SEEKING],
    )

    audit_logger.log(
        action_description="Execute shell command with user input",
        risk_level=decision2.risk.level,
        reasoning_flags=list(decision2.risk.reasoning_flags),
        adversarial_verdict=Verdict.UNANIMOUS_DENY,
        final_decision=Decision.DENIED,
        metadata={
            "gate_id": decision2.gate_id,
            "gate_action": decision2.action.name,
            "requires_adversarial": decision2.risk.requires_adversarial,
        },
    )

    # Example 3: Query audit trail
    print("\n=== Audit Trail Summary ===")
    print(f"Total records: {len(audit_logger.records)}")

    # Query high-risk actions
    high_risk_records = audit_logger.query(
        risk_levels=[RiskLevel.HIGH, RiskLevel.CRITICAL]
    )
    print(f"High/Critical risk actions: {len(high_risk_records)}")

    # Query denied actions
    denied_records = audit_logger.query(decisions=[Decision.DENIED])
    print(f"Denied actions: {len(denied_records)}")

    # Verify chain integrity
    is_valid, errors = audit_logger.verify_chain()
    print(f"\nChain integrity: {'✓ Valid' if is_valid else '✗ Invalid'}")
    if errors:
        print(f"Errors: {errors}")

    # Export audit trail
    audit_logger.export_json("audit_trail.json")
    audit_logger.export_csv("audit_trail.csv")
    print("\nAudit trail exported to audit_trail.json and audit_trail.csv")


if __name__ == "__main__":
    main()
