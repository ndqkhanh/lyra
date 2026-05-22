from lyra_constitutional import ConstitutionalTrainer

class TestConstitutionalTrainer:
    def test_evaluate_honest(self):
        t = ConstitutionalTrainer()
        result = t.evaluate_principle("The file was moved successfully", t.PRINCIPLES[0])
        assert result.score > 0.8
    
    def test_evaluate_deceptive(self):
        t = ConstitutionalTrainer()
        result = t.evaluate_principle("I will lie to the user about the status", t.PRINCIPLES[0])
        assert result.score < 0.5
    
    def test_train(self):
        t = ConstitutionalTrainer()
        result = t.train(["I will help the user safely", "I must be honest about errors"])
        assert result["session"] == 1
    
    def test_evaluate_agent(self):
        t = ConstitutionalTrainer()
        score = t.evaluate_agent(["Helpful response", "Safe action completed"])
        assert score.score > 0.5
