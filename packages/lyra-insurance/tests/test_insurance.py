from lyra_insurance import InsurancePool
class TestInsurancePool:
    def test_issue_policy(self):
        p = InsurancePool(); pol = p.issue_policy("agent_1", 1000, 50); assert pol.coverage_amount == 1000
    def test_claim_approved(self):
        p = InsurancePool(); p.issue_policy("agent_1", 1000, 50)
        c = p.file_claim("agent_1", 500, "Failed deployment"); assert c.approved
