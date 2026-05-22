from lyra_art import ArtAgent
class TestArt:
    def test_create(self):
        a = ArtAgent(); art = a.create("Sunset", "impressionist", "Warm colors over water")
        assert art.style == "impressionist"
