from lyra_music import MusicAgent
class TestMusic:
    def test_compose(self):
        m = MusicAgent(); notes = m.compose("C", 120, 4); assert len(notes) == 16
