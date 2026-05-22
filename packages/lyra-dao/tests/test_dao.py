"""Tests for lyra-dao."""
from lyra_dao import DAOManager, ProposalStatus

class TestDAOManager:
    def test_propose(self):
        d = DAOManager()
        p = d.propose("Improve testing", "Add more tests", "agent_1")
        assert p.title == "Improve testing"

    def test_vote_passes(self):
        d = DAOManager(quorum=2, approval_threshold=0.5)
        d.register_voter("a1"); d.register_voter("a2")
        p = d.propose("Test", "desc", "a1")
        p.status = ProposalStatus.VOTING
        d.vote(p.id, True); d.vote(p.id, True)
        assert d.proposals[p.id].status == ProposalStatus.PASSED
