"""Audio device management — enumerate, select, configure.

Provides device discovery for input/output audio hardware,
volume control, and audio format configuration.
Falls back gracefully when audio libraries are unavailable.
"""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any

__all__ = [
    "AudioDevice",
    "AudioConfig",
    "AudioError",
    "AudioManager",
]

SUPPORTED_SAMPLE_RATES: list[int] = [8000, 16000, 22050, 44100, 48000]
SUPPORTED_CHANNELS: list[int] = [1, 2]
SUPPORTED_BIT_DEPTHS: list[int] = [8, 16, 24, 32]


class AudioError(Exception):
    """Raised when audio device operations fail."""


class DeviceType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    DUPLEX = "duplex"


class DeviceState(Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    UNPLUGGED = "unplugged"
    NOT_PRESENT = "not_present"


@dataclass(frozen=True)
class AudioDevice:
    """Represents a single audio device."""

    name: str
    device_type: DeviceType
    device_id: int = -1
    state: DeviceState = DeviceState.ACTIVE
    channels: int = 2
    sample_rate: int = 44100
    max_input_channels: int = 0
    max_output_channels: int = 0

    @property
    def is_input(self) -> bool:
        return self.device_type in (DeviceType.INPUT, DeviceType.DUPLEX)

    @property
    def is_output(self) -> bool:
        return self.device_type in (DeviceType.OUTPUT, DeviceType.DUPLEX)

    @property
    def is_active(self) -> bool:
        return self.state == DeviceState.ACTIVE


@dataclass
class AudioConfig:
    """Audio recording / playback configuration."""

    sample_rate: int = 44100
    channels: int = 2
    bit_depth: int = 16
    input_device_id: int = -1
    output_device_id: int = -1
    volume: float = 1.0
    format: str = "wav"

    def __post_init__(self) -> None:
        if self.sample_rate not in SUPPORTED_SAMPLE_RATES:
            self.sample_rate = 44100
        if self.channels not in SUPPORTED_CHANNELS:
            self.channels = 2
        if self.bit_depth not in SUPPORTED_BIT_DEPTHS:
            self.bit_depth = 16
        self.volume = max(0.0, min(1.0, self.volume))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "input_device_id": self.input_device_id,
            "output_device_id": self.output_device_id,
            "volume": self.volume,
            "format": self.format,
        }


class AudioManager:
    """Manage audio input/output devices and configuration.

    Usage::

        mgr = AudioManager()
        devices = mgr.list_devices()
        mgr.set_input_device(devices[0])
        mgr.set_volume(0.8)
    """

    def __init__(self, config: AudioConfig | None = None) -> None:
        self._config = config or AudioConfig()
        self._input_device: AudioDevice | None = None
        self._output_device: AudioDevice | None = None
        self._pyaudio_available = self._check_pyaudio()

    @staticmethod
    def _check_pyaudio() -> bool:
        try:
            import pyaudio  # noqa: F401
            return True
        except ImportError:
            return False

    @property
    def config(self) -> AudioConfig:
        return self._config

    @config.setter
    def config(self, value: AudioConfig) -> None:
        self._config = value

    @property
    def pyaudio_available(self) -> bool:
        return self._pyaudio_available

    def list_devices(self, device_type: DeviceType | None = None) -> list[AudioDevice]:
        """List all available audio devices, optionally filtered by type."""
        if self._pyaudio_available:
            return self._list_devices_pyaudio(device_type)
        return self._list_devices_fallback(device_type)

    def _list_devices_pyaudio(
        self, device_type: DeviceType | None
    ) -> list[AudioDevice]:
        import pyaudio

        p = pyaudio.PyAudio()
        devices: list[AudioDevice] = []
        try:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                max_in = int(info.get("maxInputChannels", 0))
                max_out = int(info.get("maxOutputChannels", 0))

                if max_in > 0 and max_out > 0:
                    dtype = DeviceType.DUPLEX
                elif max_in > 0:
                    dtype = DeviceType.INPUT
                elif max_out > 0:
                    dtype = DeviceType.OUTPUT
                else:
                    dtype = DeviceType.NOT_PRESENT

                dev = AudioDevice(
                    name=info.get("name", f"Device {i}"),
                    device_type=dtype,
                    device_id=i,
                    channels=max(max_in, max_out),
                    sample_rate=int(info.get("defaultSampleRate", 44100)),
                    max_input_channels=max_in,
                    max_output_channels=max_out,
                )

                if device_type is None or dev.device_type == device_type:
                    devices.append(dev)
        finally:
            p.terminate()

        return devices

    def _list_devices_fallback(
        self, device_type: DeviceType | None
    ) -> list[AudioDevice]:
        """Fallback: list system audio devices using OS commands."""
        devices: list[AudioDevice] = []
        system = platform.system()

        if system == "Darwin":
            try:
                result = subprocess.run(
                    ["system_profiler", "SPAudioDataType"],
                    capture_output=True, text=True, timeout=10,
                )
                lines = result.stdout.splitlines()
                for line in lines:
                    stripped = line.strip()
                    if stripped and ":" in stripped and not stripped.startswith("Audio"):
                        name = stripped.split(":")[0].strip()
                        if name:
                            devices.append(
                                AudioDevice(
                                    name=name,
                                    device_type=DeviceType.DUPLEX,
                                    device_id=len(devices),
                                )
                            )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if not devices:
            devices.append(
                AudioDevice(
                    name="Default System Device",
                    device_type=DeviceType.DUPLEX,
                    device_id=0,
                )
            )

        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        return devices

    def set_input_device(self, device: AudioDevice) -> None:
        """Select an audio input device.

        Raises AudioError if the device does not support input.
        """
        if not device.is_input:
            raise AudioError(f"Device {device.name!r} does not support input")
        self._input_device = device
        self._config.input_device_id = device.device_id

    def set_output_device(self, device: AudioDevice) -> None:
        """Select an audio output device.

        Raises AudioError if the device does not support output.
        """
        if not device.is_output:
            raise AudioError(f"Device {device.name!r} does not support output")
        self._output_device = device
        self._config.output_device_id = device.device_id

    @property
    def input_device(self) -> AudioDevice | None:
        return self._input_device

    @property
    def output_device(self) -> AudioDevice | None:
        return self._output_device

    def set_volume(self, volume: float) -> None:
        """Set output volume (0.0 to 1.0)."""
        self._config.volume = max(0.0, min(1.0, volume))

    def set_format(self, sample_rate: int, channels: int, bit_depth: int) -> None:
        """Set audio format parameters."""
        if sample_rate in SUPPORTED_SAMPLE_RATES:
            self._config.sample_rate = sample_rate
        if channels in SUPPORTED_CHANNELS:
            self._config.channels = channels
        if bit_depth in SUPPORTED_BIT_DEPTHS:
            self._config.bit_depth = bit_depth

    def reset_config(self) -> None:
        """Reset config to defaults."""
        self._config = AudioConfig()

    def get_config_dict(self) -> dict[str, Any]:
        """Return current config as a dictionary."""
        return self._config.to_dict()
