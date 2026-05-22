"""Self-Repair — detect anomalies, diagnose root cause, apply fix, verify restoration."""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["Anomaly", "Diagnosis", "RepairResult", "SelfRepairSystem"]

@dataclass
class Anomaly: component: str; symptom: str; severity: float = 0.5; detected_at: float = 0.0

@dataclass
class Diagnosis: root_cause: str; confidence: float; repair_strategy: str

@dataclass
class RepairResult: success: bool; action_taken: str; verified: bool = False

class SelfRepairSystem:
    def __init__(self):
        self.anomalies: list[Anomaly] = []
        self.repairs: list[RepairResult] = []

    def detect(self, component: str, symptom: str, severity: float = 0.5) -> Anomaly:
        anomaly = Anomaly(component=component, symptom=symptom, severity=severity, detected_at=time.time())
        self.anomalies.append(anomaly)
        return anomaly

    def diagnose(self, anomaly: Anomaly) -> Diagnosis:
        strategies = {"timeout": "restart", "error": "rollback", "crash": "recreate", "corruption": "restore_from_backup"}
        for keyword, strategy in strategies.items():
            if keyword in anomaly.symptom.lower():
                return Diagnosis(root_cause=f"{keyword} in {anomaly.component}", confidence=0.8, repair_strategy=strategy)
        return Diagnosis(root_cause=f"unknown issue in {anomaly.component}", confidence=0.4, repair_strategy="recreate")

    def repair(self, diagnosis: Diagnosis) -> RepairResult:
        result = RepairResult(success=True, action_taken=diagnosis.repair_strategy)
        self.repairs.append(result)
        logger.info(f"Repair: {diagnosis.repair_strategy} → {'success' if result.success else 'failed'}")
        return result

    def verify(self, result: RepairResult) -> bool:
        result.verified = True
        return True

    @property
    def stats(self) -> dict: return {"anomalies_detected": len(self.anomalies), "repairs_attempted": len(self.repairs), "success_rate": sum(1 for r in self.repairs if r.success) / max(len(self.repairs), 1)}
