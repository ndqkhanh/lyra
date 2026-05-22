"""Tests for lyra-emotion."""
from lyra_emotion import EmotionEngine
class TestEmotionEngine:
    def test_recognize_joy(self):
        e = EmotionEngine(); s = e.recognize("I'm so happy today!")
        assert s.primary == "joy"
    def test_calibrate_response(self):
        e = EmotionEngine(); s = e.recognize("I'm really angry about this"); cal = e.calibrate_response(s)
        assert cal["suggested_tone"] == "calm"
