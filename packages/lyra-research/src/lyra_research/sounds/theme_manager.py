"""
Theme Manager

Manages sound themes for different event types.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SoundTheme:
    """Sound theme definition"""
    name: str
    description: str
    sounds: Dict[str, str]  # event -> sound_file mapping


class ThemeManager:
    """
    Manages sound themes

    Built-in themes:
    - warcraft: Warcraft III peon sounds
    - aoe: Age of Empires sounds
    - memes: Internet meme sounds
    - minimal: Subtle notification sounds
    """

    def __init__(self, sounds_dir: Path = None):
        self.sounds_dir = sounds_dir or Path(__file__).parent / "assets"
        self.themes = self._load_builtin_themes()

    def _load_builtin_themes(self) -> Dict[str, SoundTheme]:
        """Load built-in sound themes"""
        return {
            "warcraft": SoundTheme(
                name="warcraft",
                description="Warcraft III peon voice lines",
                sounds={
                    "session_start": "warcraft/zug_zug.mp3",
                    "task_start": "warcraft/ready_to_work.mp3",
                    "task_complete": "warcraft/job_done.mp3",
                    "error": "warcraft/something_need_doing.mp3",
                    "syntax_error": "warcraft/me_not_that_kind_orc.mp3",
                    "logic_error": "warcraft/that_not_possible.mp3",
                    "rate_limit": "warcraft/me_tired.mp3",
                    "milestone": "warcraft/for_the_horde.mp3",
                    "compact": "warcraft/work_work.mp3"
                }
            ),
            "aoe": SoundTheme(
                name="aoe",
                description="Age of Empires villager sounds",
                sounds={
                    "session_start": "aoe/horn.mp3",
                    "task_start": "aoe/yes.mp3",
                    "task_complete": "aoe/allhail.mp3",
                    "error": "aoe/no.mp3",
                    "compact": "aoe/wololo.mp3",
                    "milestone": "aoe/victory.mp3"
                }
            ),
            "memes": SoundTheme(
                name="memes",
                description="Internet meme sounds",
                sounds={
                    "session_start": "memes/hello_there.mp3",
                    "task_start": "memes/lets_go.mp3",
                    "task_complete": "memes/nice.mp3",
                    "error": "memes/bruh.mp3",
                    "syntax_error": "memes/windows_error.mp3",
                    "rate_limit": "memes/sad_trombone.mp3",
                    "milestone": "memes/airhorn.mp3",
                    "compact": "memes/thanos_snap.mp3"
                }
            ),
            "minimal": SoundTheme(
                name="minimal",
                description="Subtle notification sounds",
                sounds={
                    "session_start": "minimal/chime.mp3",
                    "task_start": "minimal/click.mp3",
                    "task_complete": "minimal/ding.mp3",
                    "error": "minimal/error.mp3",
                    "compact": "minimal/whoosh.mp3"
                }
            )
        }

    def get_theme(self, theme_name: str) -> Optional[SoundTheme]:
        """Get theme by name"""
        return self.themes.get(theme_name)

    def list_themes(self) -> List[str]:
        """List available theme names"""
        return list(self.themes.keys())

    def get_sound_path(self, theme_name: str, event: str) -> Optional[Path]:
        """
        Get full path to sound file for event

        Args:
            theme_name: Theme name
            event: Event name

        Returns:
            Path to sound file, or None if not found
        """
        theme = self.get_theme(theme_name)
        if not theme:
            return None

        sound_file = theme.sounds.get(event)
        if not sound_file:
            return None

        return self.sounds_dir / sound_file
