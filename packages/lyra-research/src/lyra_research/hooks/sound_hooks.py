"""
Sound Hooks

Hook integration for sound system with lifecycle events.
"""

from typing import Dict, Any
from ..sounds.sound_manager import SoundManager
from ..sounds.event_mapper import SoundEvent, EventMapper


class SoundHooks:
    """
    Hook integration for sound system

    Connects Lyra lifecycle events to sound playback.
    """

    def __init__(self, sound_manager: SoundManager = None):
        self.sound_manager = sound_manager or SoundManager()
        self.event_mapper = EventMapper()
        self.task_count = 0

    def on_session_start(self):
        """Hook: Session started"""
        self.sound_manager.play_event(SoundEvent.SESSION_START.value)

    def on_task_start(self, task_description: str):
        """Hook: Task started"""
        self.sound_manager.play_event(SoundEvent.TASK_START.value)

    def on_task_complete(self, task_description: str):
        """Hook: Task completed"""
        self.task_count += 1

        # Check for milestone
        milestone = self.event_mapper.detect_milestone(self.task_count)
        if milestone:
            self.sound_manager.play_event(milestone.value)
        else:
            self.sound_manager.play_event(SoundEvent.TASK_COMPLETE.value)

    def on_error(self, error_message: str):
        """Hook: Error occurred"""
        event = self.event_mapper.map_error(error_message)
        self.sound_manager.play_event(event.value)

    def on_compact(self):
        """Hook: Context compaction"""
        self.sound_manager.play_event(SoundEvent.COMPACT.value)

    def reset_task_count(self):
        """Reset task counter (for testing)"""
        self.task_count = 0
