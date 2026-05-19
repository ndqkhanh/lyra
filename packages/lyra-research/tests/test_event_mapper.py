"""
Tests for Event Mapper (Funny Sounds Phase 1)

Tests event mapping and milestone detection.
"""

import pytest
from lyra_research.sounds.event_mapper import EventMapper, SoundEvent


class TestEventMapper:
    """Test event mapper"""

    def test_map_syntax_error(self):
        """Test mapping syntax errors"""
        mapper = EventMapper()

        assert mapper.map_error("SyntaxError: invalid syntax") == SoundEvent.SYNTAX_ERROR
        assert mapper.map_error("Parse error at line 10") == SoundEvent.SYNTAX_ERROR
        assert mapper.map_error("Unexpected token") == SoundEvent.SYNTAX_ERROR

    def test_map_logic_error(self):
        """Test mapping logic errors"""
        mapper = EventMapper()

        assert mapper.map_error("AssertionError: value should be positive") == SoundEvent.LOGIC_ERROR
        assert mapper.map_error("Logic error in calculation") == SoundEvent.LOGIC_ERROR
        assert mapper.map_error("Invalid argument") == SoundEvent.LOGIC_ERROR

    def test_map_rate_limit_error(self):
        """Test mapping rate limit errors"""
        mapper = EventMapper()

        assert mapper.map_error("Rate limit exceeded") == SoundEvent.RATE_LIMIT
        assert mapper.map_error("Too many requests") == SoundEvent.RATE_LIMIT
        assert mapper.map_error("Quota exceeded") == SoundEvent.RATE_LIMIT

    def test_map_generic_error(self):
        """Test mapping generic errors"""
        mapper = EventMapper()

        assert mapper.map_error("Unknown error occurred") == SoundEvent.ERROR
        assert mapper.map_error("Something went wrong") == SoundEvent.ERROR

    def test_detect_milestone_10(self):
        """Test detecting milestone at 10 tasks"""
        mapper = EventMapper()
        assert mapper.detect_milestone(10) == SoundEvent.MILESTONE

    def test_detect_milestone_25(self):
        """Test detecting milestone at 25 tasks"""
        mapper = EventMapper()
        assert mapper.detect_milestone(25) == SoundEvent.MILESTONE

    def test_detect_milestone_50(self):
        """Test detecting milestone at 50 tasks"""
        mapper = EventMapper()
        assert mapper.detect_milestone(50) == SoundEvent.MILESTONE

    def test_detect_milestone_100(self):
        """Test detecting milestone at 100 tasks"""
        mapper = EventMapper()
        assert mapper.detect_milestone(100) == SoundEvent.MILESTONE

    def test_no_milestone_for_other_counts(self):
        """Test no milestone for non-milestone counts"""
        mapper = EventMapper()

        assert mapper.detect_milestone(5) is None
        assert mapper.detect_milestone(15) is None
        assert mapper.detect_milestone(99) is None
        assert mapper.detect_milestone(101) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
