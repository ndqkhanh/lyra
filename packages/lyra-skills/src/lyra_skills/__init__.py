"""lyra-skills: loader, router, extractor, shipped packs, ledger."""
from __future__ import annotations

from .extractor import ExtractorInput, ExtractorOutput, extract_candidate
from .ledger import (
    OUTCOME_FAILURE,
    OUTCOME_NEUTRAL,
    OUTCOME_SUCCESS,
    SkillLedger,
    SkillOutcome,
    SkillStats,
    default_ledger_path,
    load_ledger,
    record_outcome,
    save_ledger,
    top_n as ledger_top_n,
    utility_score,
)
from .loader import SkillLoaderError, SkillManifest, load_skills
from .packs import shipped_pack_roots
from .router import SkillRouter

__version__ = "0.1.0"

__all__ = [
    "ExtractorInput",
    "ExtractorOutput",
    "OUTCOME_FAILURE",
    "OUTCOME_NEUTRAL",
    "OUTCOME_SUCCESS",
    "SkillLedger",
    "SkillLoaderError",
    "SkillManifest",
    "SkillOutcome",
    "SkillRouter",
    "SkillStats",
    "default_ledger_path",
    "extract_candidate",
    "ledger_top_n",
    "load_ledger",
    "load_skills",
    "record_outcome",
    "save_ledger",
    "shipped_pack_roots",
    "utility_score",
]
