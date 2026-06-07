"""
Audio Player - Cross-platform audio playback.

Features:
- Platform detection
- Async playback
- Volume control
"""

import platform
import shutil
import subprocess
import threading
from pathlib import Path


class AudioPlayer:
    """
    Cross-platform audio player.

    Features:
    - Platform detection (macOS, Linux, Windows)
    - Synchronous and asynchronous playback
    - Volume control
    """

    def __init__(self):
        """Initialize audio player."""
        self.platform = platform.system()
        self.player_cmd = self._detect_player()

    def _detect_player(self) -> str | None:
        """
        Detect available audio player.

        Returns:
            Player command or None
        """
        if self.platform == "Darwin":  # macOS
            return "afplay"
        elif self.platform == "Linux":
            # Try multiple players in order of preference
            for player in ["aplay", "paplay", "ffplay"]:
                if shutil.which(player):
                    return player
            return None
        elif self.platform == "Windows":
            return "winsound"
        return None

    def play(self, sound_path: str, volume: float = 1.0, blocking: bool = True):
        """
        Play audio file.

        Args:
            sound_path: Path to audio file
            volume: Volume level (0.0 to 1.0)
            blocking: Wait for playback to complete
        """
        if not self.player_cmd:
            return  # No player available

        path = Path(sound_path).expanduser()
        if not path.exists():
            return  # File doesn't exist

        try:
            if self.platform == "Darwin":  # macOS
                cmd = ["afplay"]
                if volume < 1.0:
                    cmd.extend(["-v", str(volume)])
                cmd.append(str(path))

                if blocking:
                    subprocess.run(cmd, check=False, capture_output=True)
                else:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            elif self.platform == "Linux":
                if self.player_cmd == "aplay":
                    cmd = ["aplay", "-q", str(path)]
                elif self.player_cmd == "paplay":
                    cmd = ["paplay", str(path)]
                elif self.player_cmd == "ffplay":
                    cmd = ["ffplay", "-nodisp", "-autoexit", "-v", "0", str(path)]
                else:
                    return

                if blocking:
                    subprocess.run(cmd, check=False, capture_output=True)
                else:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            elif self.platform == "Windows":
                # Use winsound for Windows
                import winsound

                flags = winsound.SND_FILENAME
                if not blocking:
                    flags |= winsound.SND_ASYNC

                winsound.PlaySound(str(path), flags)

        except (subprocess.SubprocessError, ImportError, OSError):
            pass  # Fail silently

    def play_async(self, sound_path: str, volume: float = 1.0):
        """
        Play audio file asynchronously.

        Args:
            sound_path: Path to audio file
            volume: Volume level (0.0 to 1.0)
        """
        thread = threading.Thread(
            target=self.play, args=(sound_path, volume, False), daemon=True
        )
        thread.start()

    def is_available(self) -> bool:
        """Check if audio player is available."""
        return self.player_cmd is not None

    def get_platform(self) -> str:
        """Get current platform."""
        return self.platform
