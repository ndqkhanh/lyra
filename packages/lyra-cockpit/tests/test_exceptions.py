"""Tests for the exceptions module."""

from __future__ import annotations

import pytest

from lyra_cockpit.exceptions import (
    BudgetError,
    CockpitError,
    ConfigError,
    IAAEngineError,
    MonitorError,
    TransparencyError,
    VoiceNotifyError,
)


class TestExceptions:
    def test_cockpit_error_base(self) -> None:
        assert issubclass(IAAEngineError, CockpitError)
        assert issubclass(TransparencyError, CockpitError)
        assert issubclass(MonitorError, CockpitError)
        assert issubclass(BudgetError, CockpitError)
        assert issubclass(VoiceNotifyError, CockpitError)
        assert issubclass(ConfigError, CockpitError)

    def test_cockpit_error_message(self) -> None:
        err = CockpitError("test message")
        assert str(err) == "test message"

    def test_iaa_engine_error_message(self) -> None:
        err = IAAEngineError("preview failed")
        assert str(err) == "preview failed"

    def test_transparency_error_message(self) -> None:
        err = TransparencyError("no metrics")
        assert str(err) == "no metrics"

    def test_monitor_error_message(self) -> None:
        err = MonitorError("agent not found")
        assert str(err) == "agent not found"

    def test_budget_error_message(self) -> None:
        err = BudgetError("over limit")
        assert str(err) == "over limit"

    def test_voice_notify_error_message(self) -> None:
        err = VoiceNotifyError("disabled")
        assert str(err) == "disabled"

    def test_config_error_message(self) -> None:
        err = ConfigError("invalid config")
        assert str(err) == "invalid config"

    def test_all_exceptions_are_cockpit_errors(self) -> None:
        errors = [
            IAAEngineError("test"),
            TransparencyError("test"),
            MonitorError("test"),
            BudgetError("test"),
            VoiceNotifyError("test"),
            ConfigError("test"),
        ]
        for err in errors:
            assert isinstance(err, CockpitError)
