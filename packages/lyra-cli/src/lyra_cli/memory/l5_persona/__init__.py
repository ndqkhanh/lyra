"""L5 Persona layer — identity, style, and preference modeling."""

from .identity_traits import IdentityModel, IdentityTrait, TraitCategory
from .persona_store import PersonaSnapshot, PersonaStore
from .preference_accumulator import AccumulatedPreference, PreferenceAccumulator, PreferenceSource
from .style_learner import StyleDimension, StyleLearner, StylePreference

__all__ = [
    "AccumulatedPreference",
    "IdentityModel",
    "IdentityTrait",
    "PersonaSnapshot",
    "PersonaStore",
    "PreferenceAccumulator",
    "PreferenceSource",
    "StyleDimension",
    "StyleLearner",
    "StylePreference",
    "TraitCategory",
]
