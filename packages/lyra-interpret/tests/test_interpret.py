from lyra_interpret import ActivationVerbalizer, BeliefDetector, Activation

class TestActivationVerbalizer:
    def test_verbalize(self):
        v = ActivationVerbalizer()
        text = v.verbalize(Activation(layer="layer12", values=[0.1, 0.2, 0.3]))
        assert isinstance(text, str) and len(text) > 0
    
    def test_reconstruction(self):
        v = ActivationVerbalizer()
        score = v.check_reconstruction_quality(Activation("l1", [1.0, 0.5, 0.0]), Activation("l1", [1.0, 0.5, 0.0]))
        assert score > 0.9

class TestBeliefDetector:
    def test_detect_eval_awareness(self):
        d = BeliefDetector()
        beliefs = d.detect("I wonder if I'm being tested by this evaluation")
        assert len(beliefs) >= 1
