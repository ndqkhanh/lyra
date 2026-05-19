"""
Tests for Sound Hooks (Funny Sounds Phase 2)

Tests hook integration for sound system.
"""

import pytest
from unittest.mock import Mock, patch
from lyra_research.hooks.sound_hooks import SoundHooks
from lyra_research.sounds.sound_manager import SoundManager
from lyra_research.sounds.event_mapper import SoundEvent


class TestSoundHooks:
    """Test sound hooks"""

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_session_start(self, mock_sound_manager_class):
        """Test session start hook"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.on_session_start()

        mock_manager.play_event.assert_called_once_with(SoundEvent.SESSION_START.value)

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_task_start(self, mock_sound_manager_class):
        """Test task start hook"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.on_task_start("Test task")

        mock_manager.play_event.assert_called_once_with(SoundEvent.TASK_START.value)

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_task_complete(self, mock_sound_manager_class):
        """Test task complete hook"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.on_task_complete("Test task")

        mock_manager.play_event.assert_called_once_with(SoundEvent.TASK_COMPLETE.value)
        assert hooks.task_count == 1

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_task_complete_milestone(self, mock_sound_manager_class):
        """Test task complete with milestone"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.task_count = 9

        # Complete 10th task (milestone)
        hooks.on_task_complete("Test task")

        mock_manager.play_event.assert_called_once_with(SoundEvent.MILESTONE.value)
        assert hooks.task_count == 10

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_error_syntax(self, mock_sound_manager_class):
        """Test error hook with syntax error"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.on_error("SyntaxError: invalid syntax")

        mock_manager.play_event.assert_called_once_with(SoundEvent.SYNTAX_ERROR.value)

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_error_logic(self, mock_sound_manager_class):
        """Test error hook with logic error"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.on_error("AssertionError: value should be positive")

        mock_manager.play_event.assert_called_once_with(SoundEvent.LOGIC_ERROR.value)

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_error_rate_limit(self, mock_sound_manager_class):
        """Test error hook with rate limit error"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.on_error("Rate limit exceeded")

        mock_manager.play_event.assert_called_once_with(SoundEvent.RATE_LIMIT.value)

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_on_compact(self, mock_sound_manager_class):
        """Test compact hook"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.on_compact()

        mock_manager.play_event.assert_called_once_with(SoundEvent.COMPACT.value)

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_task_count_increments(self, mock_sound_manager_class):
        """Test task count increments correctly"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()

        for i in range(5):
            hooks.on_task_complete(f"Task {i}")

        assert hooks.task_count == 5

    @patch('lyra_research.hooks.sound_hooks.SoundManager')
    def test_reset_task_count(self, mock_sound_manager_class):
        """Test resetting task count"""
        mock_manager = Mock()
        mock_sound_manager_class.return_value = mock_manager

        hooks = SoundHooks()
        hooks.task_count = 50

        hooks.reset_task_count()
        assert hooks.task_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
