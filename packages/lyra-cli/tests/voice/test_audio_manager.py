"""Tests for AudioManager, AudioDevice, AudioConfig, and DeviceType."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from lyra_cli.voice.audio_manager import (
    AudioConfig,
    AudioDevice,
    AudioError,
    AudioManager,
    DeviceState,
    DeviceType,
)


class TestAudioDevice:
    def test_default_values(self):
        dev = AudioDevice(name="Test Device", device_type=DeviceType.OUTPUT)
        assert dev.name == "Test Device"
        assert dev.device_type == DeviceType.OUTPUT
        assert dev.device_id == -1
        assert dev.state == DeviceState.ACTIVE
        assert dev.sample_rate == 44100

    def test_is_input_output(self):
        input_dev = AudioDevice(name="In", device_type=DeviceType.INPUT)
        output_dev = AudioDevice(name="Out", device_type=DeviceType.OUTPUT)
        duplex_dev = AudioDevice(name="Both", device_type=DeviceType.DUPLEX)

        assert input_dev.is_input and not input_dev.is_output
        assert output_dev.is_output and not output_dev.is_input
        assert duplex_dev.is_input and duplex_dev.is_output

    def test_is_active(self):
        active = AudioDevice(name="A", device_type=DeviceType.INPUT)
        disabled = AudioDevice(name="B", device_type=DeviceType.INPUT, state=DeviceState.DISABLED)
        assert active.is_active
        assert not disabled.is_active

    def test_frozen(self):
        dev = AudioDevice(name="Test", device_type=DeviceType.INPUT)
        with pytest.raises((AttributeError, TypeError)):
            dev.name = "New Name"  # type: ignore[misc]


class TestAudioConfig:
    def test_default_values(self):
        cfg = AudioConfig()
        assert cfg.sample_rate == 44100
        assert cfg.channels == 2
        assert cfg.bit_depth == 16
        assert cfg.volume == 1.0
        assert cfg.format == "wav"

    def test_invalid_values_clamped(self):
        cfg = AudioConfig(sample_rate=9999, channels=5, bit_depth=64, volume=2.5)
        assert cfg.sample_rate == 44100
        assert cfg.channels == 2
        assert cfg.bit_depth == 16
        assert cfg.volume == 1.0

    def test_to_dict(self):
        cfg = AudioConfig(sample_rate=16000, channels=1, volume=0.5)
        d = cfg.to_dict()
        assert d["sample_rate"] == 16000
        assert d["channels"] == 1
        assert d["volume"] == 0.5
        assert d["format"] == "wav"


class TestAudioManager:
    def test_default_config(self):
        mgr = AudioManager()
        assert mgr.config.sample_rate == 44100
        assert mgr.pyaudio_available is False  # pyaudio not installed

    def test_custom_config(self):
        cfg = AudioConfig(sample_rate=16000, volume=0.5)
        mgr = AudioManager(config=cfg)
        assert mgr.config.sample_rate == 16000
        assert mgr.config.volume == 0.5

    def test_set_volume(self):
        mgr = AudioManager()
        mgr.set_volume(0.3)
        assert mgr.config.volume == 0.3
        mgr.set_volume(2.0)
        assert mgr.config.volume == 1.0
        mgr.set_volume(-1.0)
        assert mgr.config.volume == 0.0

    def test_set_format(self):
        mgr = AudioManager()
        mgr.set_format(16000, 1, 8)
        assert mgr.config.sample_rate == 16000
        assert mgr.config.channels == 1
        assert mgr.config.bit_depth == 8

        mgr.set_format(9999, 5, 64)
        assert mgr.config.sample_rate == 16000  # unchanged
        assert mgr.config.channels == 1  # unchanged

    def test_set_input_device(self):
        mgr = AudioManager()
        dev = AudioDevice(name="Mic", device_type=DeviceType.INPUT, device_id=1)
        mgr.set_input_device(dev)
        assert mgr.input_device == dev
        assert mgr.config.input_device_id == 1

    def test_set_input_device_not_input(self):
        mgr = AudioManager()
        dev = AudioDevice(name="Speaker", device_type=DeviceType.OUTPUT)
        with pytest.raises(AudioError, match="does not support input"):
            mgr.set_input_device(dev)

    def test_set_output_device(self):
        mgr = AudioManager()
        dev = AudioDevice(name="Speaker", device_type=DeviceType.OUTPUT, device_id=2)
        mgr.set_output_device(dev)
        assert mgr.output_device == dev
        assert mgr.config.output_device_id == 2

    def test_set_output_device_not_output(self):
        mgr = AudioManager()
        dev = AudioDevice(name="Mic", device_type=DeviceType.INPUT)
        with pytest.raises(AudioError, match="does not support output"):
            mgr.set_output_device(dev)

    def test_reset_config(self):
        mgr = AudioManager()
        mgr.set_volume(0.3)
        mgr.set_format(16000, 1, 8)
        mgr.reset_config()
        assert mgr.config.volume == 1.0
        assert mgr.config.sample_rate == 44100

    def test_get_config_dict(self):
        mgr = AudioManager()
        d = mgr.get_config_dict()
        assert "sample_rate" in d
        assert "volume" in d

    def test_list_devices_fallback(self):
        mgr = AudioManager()
        devices = mgr.list_devices()
        assert len(devices) >= 1
        assert all(isinstance(d, AudioDevice) for d in devices)

    def test_list_devices_pyaudio(self):
        expected = [
            AudioDevice(name="Mic", device_type=DeviceType.INPUT, device_id=0, sample_rate=44100),
            AudioDevice(name="Speaker", device_type=DeviceType.OUTPUT, device_id=1, sample_rate=48000),
        ]
        mgr = AudioManager()
        mgr._pyaudio_available = True
        with patch.object(mgr, "_list_devices_pyaudio", return_value=expected):
            devices = mgr.list_devices()
            assert len(devices) == 2
            assert devices[0].device_type == DeviceType.INPUT
            assert devices[1].device_type == DeviceType.OUTPUT
