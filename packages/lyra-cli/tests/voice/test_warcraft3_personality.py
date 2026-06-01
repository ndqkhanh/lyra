"""Tests for Warcraft III Peon voice personality."""

from __future__ import annotations

from lyra_cli.voice.personalities.personality_base import (
    PersonalityTrait,
    VoiceResponse,
)
from lyra_cli.voice.personalities.warcraft3_peon import (
    Warcraft3PeonPersonality,
)
from lyra_cli.voice.sound_notifications import (
    THEME_PRESETS,
    WARCRAFT3_THEME_PRESETS,
)


class TestWarcraft3PeonPersonality:
    def setup_method(self) -> None:
        self.personality = Warcraft3PeonPersonality()

    def test_trait(self):
        assert self.personality.trait == PersonalityTrait.WARCRAFT3_PEON

    def test_metadata(self):
        assert self.personality.name == "Warcraft III Peon"
        assert self.personality.theme == "warcraft3"
        assert self.personality.icon == "\U0001fa97"

    def test_transform_response(self):
        result = self.personality.transform_response(
            "Build order completed", "task_complete"
        )
        assert isinstance(result, VoiceResponse)
        assert "Work work!" in result.text
        assert "Something need doing?" in result.text
        assert result.tone == "gruff"
        assert "grunt" in result.effects

    def test_greeting(self):
        greeting = self.personality.greeting()
        assert "Zug zug" in greeting or "Ready to work" in greeting
        assert isinstance(greeting, str)

    def test_farewell(self):
        farewell = self.personality.farewell()
        assert "Zug zug" in farewell
        assert isinstance(farewell, str)

    def test_error_message(self):
        error_msg = self.personality.error_message("Network timeout")
        assert "I'm not ready!" in error_msg or "Me not that kind of orc!" in error_msg
        assert "Network timeout" in error_msg
        assert isinstance(error_msg, str)

    def test_get_response_startup(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "startup"},
        )
        assert isinstance(result, VoiceResponse)
        assert result.tone == "gruff"
        assert "grunt" in result.effects

    def test_get_response_task_complete(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "task_complete"},
        )
        assert isinstance(result, VoiceResponse)
        assert "Work complete" in result.text or "More work" in result.text

    def test_get_response_error(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "error"},
        )
        assert isinstance(result, VoiceResponse)
        assert "not ready" in result.text.lower() or "orc" in result.text.lower()

    def test_get_response_wake(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "wake"},
        )
        assert isinstance(result, VoiceResponse)
        assert "milord" in result.text.lower() or "what you want" in result.text.lower()

    def test_get_response_sleep(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "sleep"},
        )
        assert isinstance(result, VoiceResponse)
        assert "need sleep" in result.text.lower()

    def test_get_response_cost_warning(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "cost_warning"},
        )
        assert isinstance(result, VoiceResponse)
        assert "gold" in result.text.lower()

    def test_get_response_agent_spawn(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "agent_spawn"},
        )
        assert isinstance(result, VoiceResponse)
        assert "Ready to work" in result.text

    def test_get_response_task_start(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "task_start"},
        )
        assert isinstance(result, VoiceResponse)
        assert "Job's done" in result.text

    def test_get_response_unknown_event_falls_back(self):
        result = self.personality.get_response(
            PersonalityTrait.WARCRAFT3_PEON,
            {"event": "unknown_event"},
        )
        assert isinstance(result, VoiceResponse)


class TestWarcraft3ThemeRegistration:
    def test_theme_presets_registered(self):
        assert "warcraft3" in THEME_PRESETS
        presets = THEME_PRESETS["warcraft3"]
        assert presets is WARCRAFT3_THEME_PRESETS

    def test_warcraft3_presets_have_correct_theme(self):
        for state, config in WARCRAFT3_THEME_PRESETS.items():
            assert config.theme == "warcraft3"

    def test_warcraft3_presets_have_low_frequency(self):
        for config in WARCRAFT3_THEME_PRESETS.values():
            assert config.frequency <= 250

    def test_warcraft3_presets_cover_all_agent_states(self):
        from lyra_cli.voice.sound_notifications import AgentState

        for state in AgentState:
            assert state in WARCRAFT3_THEME_PRESETS


class TestSoundPackConfiguration:
    def test_warcraft3_sound_effects_pack(self):
        from lyra_cli.sound_effects import SoundEvent, get_sound_manager

        mgr = get_sound_manager()
        assert "warcraft3" in mgr.available_packs
        loaded = mgr.load_pack("warcraft3")
        assert loaded
