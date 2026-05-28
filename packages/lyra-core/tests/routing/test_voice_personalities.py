"""Tests for voice personality system."""
from __future__ import annotations

from lyra_cli.voice.personalities.personality_base import PersonalityTrait
from lyra_cli.voice.personalities.pirate import PiratePersonality
from lyra_cli.voice.personalities.robot import RobotPersonality
from lyra_cli.voice.personalities.butler import ButlerPersonality
from lyra_cli.voice.personalities.cowboy import CowboyPersonality
from lyra_cli.voice.personalities.zen_master import ZenMasterPersonality
from lyra_cli.voice.personalities.drill_sergeant import DrillSergeantPersonality
from lyra_cli.voice.personality_engine import PersonalityEngine, PersonalityRegistry


def _all_personalities():
    return [
        PiratePersonality(),
        RobotPersonality(),
        ButlerPersonality(),
        CowboyPersonality(),
        ZenMasterPersonality(),
        DrillSergeantPersonality(),
    ]


class TestPersonalityTraits:
    def test_trait_values_are_unique(self):
        traits = [p.trait for p in _all_personalities()]
        assert len(traits) == len(set(traits))

    def test_all_traits_in_enum(self):
        for p in _all_personalities():
            assert isinstance(p.trait, PersonalityTrait)


class TestPiratePersonality:
    def test_greeting(self):
        p = PiratePersonality()
        assert "Ahoy" in p.greeting()

    def test_farewell(self):
        p = PiratePersonality()
        assert "fair winds" in p.farewell().lower() or "Fair winds" in p.farewell()

    def test_error_message(self):
        p = PiratePersonality()
        msg = p.error_message("NullPointerException")
        assert "NullPointerException" in msg

    def test_transform_response(self):
        p = PiratePersonality()
        resp = p.transform_response("Tests pass.", "build")
        assert "Tests pass" in resp.text
        assert resp.tone == "hearty"


class TestRobotPersonality:
    def test_greeting(self):
        p = RobotPersonality()
        assert "BOOT" in p.greeting()

    def test_farewell(self):
        p = RobotPersonality()
        assert "SHUTDOWN" in p.farewell()

    def test_error_message(self):
        p = RobotPersonality()
        assert "0xDEADBEEF" in p.error_message("SIGSEGV")

    def test_transform_response(self):
        p = RobotPersonality()
        resp = p.transform_response("Build ok.", "ci")
        assert "BEEP-BOOP" in resp.text
        assert resp.tone == "monotone"


class TestButlerPersonality:
    def test_greeting(self):
        p = ButlerPersonality()
        assert "sir" in p.greeting().lower()

    def test_farewell(self):
        p = ButlerPersonality()
        assert "sir" in p.farewell().lower()

    def test_error_message(self):
        p = ButlerPersonality()
        assert "troubling" in p.error_message("500").lower()

    def test_transform_response(self):
        p = ButlerPersonality()
        resp = p.transform_response("PR merged.", "github")
        assert "Very good" in resp.text


class TestCowboyPersonality:
    def test_greeting(self):
        p = CowboyPersonality()
        assert "Howdy" in p.greeting()

    def test_farewell(self):
        p = CowboyPersonality()
        assert "Happy trails" in p.farewell()

    def test_error_message(self):
        p = CowboyPersonality()
        assert "doggone" in p.error_message("404").lower()

    def test_transform_response(self):
        p = CowboyPersonality()
        resp = p.transform_response("CI green.", "ci")
        assert "yeehaw" in resp.text.lower()


class TestZenMasterPersonality:
    def test_greeting(self):
        p = ZenMasterPersonality()
        assert "breathe" in p.greeting().lower()

    def test_farewell(self):
        p = ZenMasterPersonality()
        assert "peace" in p.farewell().lower()

    def test_error_message(self):
        p = ZenMasterPersonality()
        assert "teacher" in p.error_message("timeout")

    def test_transform_response(self):
        p = ZenMasterPersonality()
        resp = p.transform_response("Code compiles.", "build")
        assert "mind" in resp.text.lower()


class TestDrillSergeantPersonality:
    def test_greeting(self):
        p = DrillSergeantPersonality()
        assert "ATTEN-TION" in p.greeting()

    def test_farewell(self):
        p = DrillSergeantPersonality()
        assert "DIS-MISSED" in p.farewell()

    def test_error_message(self):
        p = DrillSergeantPersonality()
        assert "HOPPER" in p.error_message("segfault")

    def test_transform_response(self):
        p = DrillSergeantPersonality()
        resp = p.transform_response("All tests pass.", "test")
        assert "MAGGOT" in resp.text


class TestPersonalityRegistry:
    def test_default_personalities_registered(self):
        reg = PersonalityRegistry()
        assert len(reg.list_traits()) == 6

    def test_get_returns_personality(self):
        reg = PersonalityRegistry()
        p = reg.get(PersonalityTrait.PIRATE)
        assert p is not None
        assert p.trait == PersonalityTrait.PIRATE

    def test_get_unknown_returns_none(self):
        reg = PersonalityRegistry()

        class FakeTrait:
            value = "fake"

        assert reg.get(FakeTrait) is None

    def test_register_custom_personality(self):
        reg = PersonalityRegistry()
        pirate = PiratePersonality()
        reg.register(pirate)
        assert reg.get(PersonalityTrait.PIRATE) is pirate

    def test_list_names(self):
        reg = PersonalityRegistry()
        names = reg.list_names()
        assert "pirate" in names
        assert "robot" in names


class TestPersonalityEngine:
    def test_default_personality_is_butler(self):
        engine = PersonalityEngine()
        assert engine.active_trait == PersonalityTrait.BUTLER

    def test_set_personality(self):
        engine = PersonalityEngine()
        assert engine.set_personality(PersonalityTrait.PIRATE)
        assert engine.active_trait == PersonalityTrait.PIRATE

    def test_set_invalid_personality(self):
        engine = PersonalityEngine()

        class FakeTrait:
            value = "fake"

        assert not engine.set_personality(FakeTrait)
        assert engine.active_trait == PersonalityTrait.BUTLER

    def test_process_uses_active_personality(self):
        engine = PersonalityEngine()
        engine.set_personality(PersonalityTrait.ROBOT)
        resp = engine.process("Task done.", "general")
        assert "BEEP" in resp.text

    def test_greeting_uses_active_personality(self):
        engine = PersonalityEngine()
        engine.set_personality(PersonalityTrait.COWBOY)
        assert "Howdy" in engine.greeting()

    def test_farewell_uses_active_personality(self):
        engine = PersonalityEngine()
        engine.set_personality(PersonalityTrait.ZEN_MASTER)
        assert "peace" in engine.farewell().lower()

    def test_error_message_uses_active(self):
        engine = PersonalityEngine()
        engine.set_personality(PersonalityTrait.DRILL_SERGEANT)
        assert "MAGGOT" not in engine.error_message("oops")

    def test_different_personalities_different_responses(self):
        engine = PersonalityEngine()
        engine.set_personality(PersonalityTrait.PIRATE)
        r1 = engine.greeting()
        engine.set_personality(PersonalityTrait.ROBOT)
        r2 = engine.greeting()
        assert r1 != r2
