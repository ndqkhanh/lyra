"""
Audio Player

Cross-platform audio playback for sound notifications.
"""

import platform
import subprocess
from pathlib import Path
from typing import Optional
from enum import Enum


class AudioBackend(Enum):
    """Audio playback backends"""
    AFPLAY = "afplay"      # macOS
    APLAY = "aplay"        # Linux (ALSA)
    PAPLAY = "paplay"      # Linux (PulseAudio)
    POWERSHELL = "powershell"  # Windows


class AudioPlayer:
    """
    Cross-platform audio player

    Automatically detects platform and uses appropriate audio backend.
    """

    def __init__(self):
        self.backend = self._detect_backend()

    def _detect_backend(self) -> AudioBackend:
        """Detect appropriate audio backend for current platform"""
        system = platform.system()

        if system == "Darwin":
            return AudioBackend.AFPLAY
        elif system == "Linux":
            # Check if paplay is available (PulseAudio)
            if self._command_exists("paplay"):
                return AudioBackend.PAPLAY
            return AudioBackend.APLAY
        elif system == "Windows":
            return AudioBackend.POWERSHELL
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

    def _command_exists(self, command: str) -> bool:
        """Check if command exists in PATH"""
        try:
            subprocess.run([command, "--version"],
                         capture_output=True,
                         timeout=1)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def play(self, sound_path: Path, volume: float = 1.0,
             background: bool = True) -> Optional[subprocess.Popen]:
        """
        Play sound file

        Args:
            sound_path: Path to sound file
            volume: Volume level (0.0 to 1.0)
            background: Run in background (non-blocking)

        Returns:
            Process handle if background=True, None otherwise
        """
        if not sound_path.exists():
            raise FileNotFoundError(f"Sound file not found: {sound_path}")

        command = self._build_command(sound_path, volume)

        if background:
            # Run in background, don't wait
            return subprocess.Popen(command,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        else:
            # Run and wait for completion
            subprocess.run(command,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
            return None

    def _build_command(self, sound_path: Path, volume: float) -> list:
        """Build platform-specific audio command"""
        if self.backend == AudioBackend.AFPLAY:
            # macOS: afplay -v <volume> <file>
            return ["afplay", "-v", str(volume), str(sound_path)]

        elif self.backend == AudioBackend.PAPLAY:
            # Linux PulseAudio: paplay --volume <0-65536> <file>
            pa_volume = int(volume * 65536)
            return ["paplay", "--volume", str(pa_volume), str(sound_path)]

        elif self.backend == AudioBackend.APLAY:
            # Linux ALSA: aplay <file>
            # Note: ALSA doesn't support volume in command
            return ["aplay", str(sound_path)]

        elif self.backend == AudioBackend.POWERSHELL:
            # Windows PowerShell
            ps_command = f'(New-Object Media.SoundPlayer "{sound_path}").PlaySync()'
            return ["powershell.exe", "-c", ps_command]

        raise RuntimeError(f"Unsupported backend: {self.backend}")
