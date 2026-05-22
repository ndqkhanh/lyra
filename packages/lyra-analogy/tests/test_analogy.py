from lyra_analogy import AnalogyEngine
class TestAnalogyEngine:
    def test_map_across_domains(self):
        e = AnalogyEngine()
        m = e.map_across_domains("solar_system", "atom", ["planet", "orbit", "gravity"])
        assert m is not None and "atom" in m.target_domain
