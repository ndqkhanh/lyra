"""Common Sense Knowledge Base — everyday world knowledge, physical reasoning, social conventions."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["CommonSenseFact", "CommonSenseKB"]

@dataclass
class CommonSenseFact:
    statement: str; domain: str; certainty: float = 0.9

class CommonSenseKB:
    def __init__(self):
        self.facts: dict[str, CommonSenseFact] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        defaults = [
            ("water_freezes_at_32f", "Water freezes at 32°F or 0°C", "physics", 0.99),
            ("objects_fall_down", "Objects fall down when dropped", "physics", 0.99),
            ("people_need_food", "People need food and water to survive", "biology", 0.99),
            ("fire_burns", "Fire is hot and can burn", "physics", 0.99),
            ("sleep_is_necessary", "Humans need sleep daily", "biology", 0.95),
            ("gravity_exists", "What goes up must come down", "physics", 0.99),
            ("time_moves_forward", "Time only moves forward", "physics", 0.99),
            ("cause_before_effect", "Cause happens before effect", "logic", 0.99),
            ("if_rain_wet", "If it rains, the ground gets wet", "physics", 0.95),
            ("day_after_night", "Day follows night", "astronomy", 0.99),
        ]
        for key, stmt, domain, certainty in defaults:
            self.facts[key] = CommonSenseFact(statement=stmt, domain=domain, certainty=certainty)

    def query(self, statement: str) -> Optional[CommonSenseFact]:
        stmt_lower = statement.lower()
        for fact in self.facts.values():
            if any(w in stmt_lower for w in fact.statement.lower().split()):
                if fact.certainty > 0.8:
                    return fact
        return None

    def add_fact(self, key: str, statement: str, domain: str, certainty: float = 0.8) -> CommonSenseFact:
        fact = CommonSenseFact(statement=statement, domain=domain, certainty=certainty)
        self.facts[key] = fact
        return fact

    @property
    def stats(self) -> dict: return {"facts": len(self.facts), "domains": list(set(f.domain for f in self.facts.values()))}
