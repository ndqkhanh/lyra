from lyra_legal import LegalAgent
class TestLegal:
    def test_compliance(self):
        l = LegalAgent(); l.add_regulation("GDPR", "EU", "obtain consent before processing")
        v = l.check_compliance("process data"); assert len(v) > 0
