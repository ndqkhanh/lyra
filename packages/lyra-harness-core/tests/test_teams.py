"""Tests for harness_core.teams — TaskList + Mailbox + AgentTeam."""
from __future__ import annotations

import pytest

from harness_core.teams import (
    AgentRole,
    AgentTeam,
    Mailbox,
    MailboxRouter,
    Message,
    Task,
    TaskList,
    TaskStatus,
)


# --- Task / TaskList ----------------------------------------------------


class TestTask:
    def test_valid(self):
        t = Task(task_id="t1", description="x")
        assert t.is_claimable is True
        assert t.is_terminal is False

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError):
            Task(task_id="", description="x")

    def test_empty_description_rejected(self):
        with pytest.raises(ValueError):
            Task(task_id="t1", description="")

    def test_in_progress_requires_assignee(self):
        with pytest.raises(ValueError):
            Task(task_id="t1", description="x", status=TaskStatus.IN_PROGRESS)

    def test_terminal_states(self):
        for s in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED):
            t = Task(task_id="t1", description="x", status=s)
            assert t.is_terminal is True
            assert t.is_claimable is False


class TestTaskList:
    def test_add_and_get(self):
        tl = TaskList()
        t = tl.add(description="research X")
        assert tl.get(t.task_id).description == "research X"

    def test_add_duplicate_id_rejected(self):
        tl = TaskList()
        tl.add(description="x", task_id="t1")
        with pytest.raises(ValueError):
            tl.add(description="y", task_id="t1")

    def test_claim_next_returns_oldest(self):
        tl = TaskList()
        tl.add(description="first", task_id="t1")
        tl.add(description="second", task_id="t2")
        claimed = tl.claim_next(agent_id="spoke")
        assert claimed.task_id == "t1"
        assert claimed.status == TaskStatus.IN_PROGRESS
        assert claimed.assigned_to == "spoke"

    def test_claim_next_respects_priority(self):
        tl = TaskList()
        tl.add(description="low", task_id="lo", priority=0)
        tl.add(description="high", task_id="hi", priority=10)
        claimed = tl.claim_next(agent_id="spoke")
        assert claimed.task_id == "hi"

    def test_claim_next_empty_returns_none(self):
        assert TaskList().claim_next(agent_id="spoke") is None

    def test_claim_skips_in_progress(self):
        tl = TaskList()
        tl.add(description="a", task_id="t1")
        tl.add(description="b", task_id="t2")
        first = tl.claim_next(agent_id="s1")
        second = tl.claim_next(agent_id="s2")
        assert {first.task_id, second.task_id} == {"t1", "t2"}
        # No more claimable tasks.
        assert tl.claim_next(agent_id="s3") is None

    def test_complete(self):
        tl = TaskList()
        tl.add(description="x", task_id="t1")
        tl.claim_next(agent_id="s1")
        done = tl.complete(task_id="t1", agent_id="s1", output={"result": "ok"})
        assert done.status == TaskStatus.DONE
        assert done.output == {"result": "ok"}

    def test_complete_wrong_agent_raises(self):
        tl = TaskList()
        tl.add(description="x", task_id="t1")
        tl.claim_next(agent_id="s1")
        with pytest.raises(PermissionError):
            tl.complete(task_id="t1", agent_id="other-agent")

    def test_complete_terminal_raises(self):
        tl = TaskList()
        tl.add(description="x", task_id="t1")
        tl.claim_next(agent_id="s1")
        tl.complete(task_id="t1", agent_id="s1")
        with pytest.raises(ValueError):
            tl.complete(task_id="t1", agent_id="s1")

    def test_fail(self):
        tl = TaskList()
        tl.add(description="x", task_id="t1")
        tl.claim_next(agent_id="s1")
        failed = tl.fail(task_id="t1", agent_id="s1", error="kaboom")
        assert failed.status == TaskStatus.FAILED
        assert failed.error == "kaboom"

    def test_cancel(self):
        tl = TaskList()
        tl.add(description="x", task_id="t1")
        cancelled = tl.cancel(task_id="t1")
        assert cancelled.status == TaskStatus.CANCELLED

    def test_cancel_terminal_raises(self):
        tl = TaskList()
        tl.add(description="x", task_id="t1")
        tl.cancel(task_id="t1")
        with pytest.raises(ValueError):
            tl.cancel(task_id="t1")

    def test_list_filtered(self):
        tl = TaskList()
        tl.add(description="a", task_id="t1")
        tl.add(description="b", task_id="t2")
        tl.claim_next(agent_id="s1")
        pending = tl.list_all(status=TaskStatus.PENDING)
        in_progress = tl.list_all(status=TaskStatus.IN_PROGRESS)
        assert len(pending) == 1
        assert len(in_progress) == 1

    def test_stats(self):
        tl = TaskList()
        tl.add(description="a", task_id="t1")
        tl.add(description="b", task_id="t2")
        tl.claim_next(agent_id="s1")
        tl.complete(task_id="t1", agent_id="s1")
        s = tl.stats()
        assert s["total"] == 2
        assert s["pending"] == 1
        assert s["done"] == 1


# --- Mailbox / MailboxRouter --------------------------------------------


class TestMessage:
    def test_valid(self):
        m = Message(msg_id="m1", sender="a", recipient="b", body="hi")
        assert m.is_broadcast is False

    def test_broadcast(self):
        m = Message(msg_id="m1", sender="a", recipient="*", body="hi")
        assert m.is_broadcast is True

    def test_empty_fields_rejected(self):
        with pytest.raises(ValueError):
            Message(msg_id="", sender="a", recipient="b", body="x")
        with pytest.raises(ValueError):
            Message(msg_id="m", sender="", recipient="b", body="x")
        with pytest.raises(ValueError):
            Message(msg_id="m", sender="a", recipient="", body="x")


class TestMailbox:
    def test_deliver_and_receive(self):
        mb = Mailbox(agent_id="alice")
        mb.deliver(Message(msg_id="m1", sender="bob", recipient="alice", body="hi"))
        msg = mb.receive()
        assert msg.body == "hi"
        assert mb.receive() is None  # FIFO drained

    def test_recipient_mismatch_rejected(self):
        mb = Mailbox(agent_id="alice")
        with pytest.raises(ValueError):
            mb.deliver(Message(msg_id="m", sender="x", recipient="bob", body="z"))

    def test_broadcast_accepted(self):
        mb = Mailbox(agent_id="alice")
        # Broadcast messages are accepted regardless of agent_id.
        mb.deliver(Message(msg_id="m", sender="x", recipient="*", body="z"))
        assert len(mb) == 1

    def test_peek_doesnt_remove(self):
        mb = Mailbox(agent_id="alice")
        mb.deliver(Message(msg_id="m1", sender="b", recipient="alice", body="x"))
        peeked = mb.peek()
        assert peeked.body == "x"
        assert len(mb) == 1

    def test_drain_empties_inbox(self):
        mb = Mailbox(agent_id="alice")
        for i in range(3):
            mb.deliver(Message(msg_id=f"m{i}", sender="b", recipient="alice", body=str(i)))
        drained = mb.drain()
        assert len(drained) == 3
        assert len(mb) == 0


class TestMailboxRouter:
    def test_register_and_send(self):
        router = MailboxRouter()
        router.register(Mailbox(agent_id="alice"))
        router.register(Mailbox(agent_id="bob"))
        msg = router.send(sender="alice", recipient="bob", body="hello")
        bob = router.get("bob")
        received = bob.receive()
        assert received.body == "hello"
        assert received.msg_id == msg.msg_id

    def test_duplicate_register_rejected(self):
        router = MailboxRouter()
        router.register(Mailbox(agent_id="alice"))
        with pytest.raises(ValueError):
            router.register(Mailbox(agent_id="alice"))

    def test_unregister(self):
        router = MailboxRouter()
        router.register(Mailbox(agent_id="alice"))
        assert router.unregister("alice") is True
        assert router.unregister("alice") is False  # already gone

    def test_send_to_unknown_recipient_undelivered(self):
        router = MailboxRouter()
        router.register(Mailbox(agent_id="alice"))
        router.send(sender="alice", recipient="bob", body="missing")
        assert len(router.undelivered) == 1

    def test_broadcast_fans_out(self):
        router = MailboxRouter()
        router.register(Mailbox(agent_id="alice"))
        router.register(Mailbox(agent_id="bob"))
        router.register(Mailbox(agent_id="carol"))
        router.send(sender="alice", recipient="*", body="all hands")
        # Sender doesn't get their own broadcast.
        assert len(router.get("alice")) == 0
        assert len(router.get("bob")) == 1
        assert len(router.get("carol")) == 1

    def test_stats(self):
        router = MailboxRouter()
        router.register(Mailbox(agent_id="a"))
        router.register(Mailbox(agent_id="b"))
        router.send(sender="a", recipient="b", body="x")
        router.send(sender="a", recipient="missing", body="y")
        s = router.stats()
        assert s["mailboxes"] == 2
        assert s["undelivered"] == 1
        assert s["queued_total"] == 1


# --- AgentTeam ----------------------------------------------------------


class TestAgentTeam:
    def _basic_team(self):
        team = AgentTeam(team_id="research-team")
        team.add_agent(agent_id="lead", role=AgentRole.LEAD)
        team.add_agent(agent_id="spoke-1", role=AgentRole.SPOKE)
        team.add_agent(agent_id="spoke-2", role=AgentRole.SPOKE)
        return team

    def test_team_id_required(self):
        with pytest.raises(ValueError):
            AgentTeam(team_id="")

    def test_lead_id(self):
        team = self._basic_team()
        assert team.lead_id == "lead"
        assert set(team.spoke_ids) == {"spoke-1", "spoke-2"}

    def test_two_leads_rejected(self):
        team = self._basic_team()
        with pytest.raises(ValueError):
            team.add_agent(agent_id="lead-2", role=AgentRole.LEAD)

    def test_duplicate_agent_rejected(self):
        team = self._basic_team()
        with pytest.raises(ValueError):
            team.add_agent(agent_id="spoke-1", role=AgentRole.SPOKE)

    def test_remove_agent(self):
        team = self._basic_team()
        assert team.remove_agent("spoke-1") is True
        assert team.role_of("spoke-1") is None

    def test_only_lead_can_add_tasks(self):
        team = self._basic_team()
        team.add_task(description="x", added_by="lead")
        with pytest.raises(PermissionError):
            team.add_task(description="y", added_by="spoke-1")

    def test_only_spoke_can_claim(self):
        team = self._basic_team()
        team.add_task(description="x", added_by="lead")
        with pytest.raises(PermissionError):
            team.claim_next(agent_id="lead")
        claimed = team.claim_next(agent_id="spoke-1")
        assert claimed is not None

    def test_complete_flows_through(self):
        team = self._basic_team()
        t = team.add_task(description="x", added_by="lead")
        team.claim_next(agent_id="spoke-1")
        done = team.complete_task(task_id=t.task_id, agent_id="spoke-1", output="ok")
        assert done.status == TaskStatus.DONE

    def test_send_within_team(self):
        team = self._basic_team()
        team.send(sender="lead", recipient="spoke-1", body="here's a hint")
        msg = team.receive(agent_id="spoke-1")
        assert msg.body == "here's a hint"

    def test_send_outside_team_rejected(self):
        team = self._basic_team()
        with pytest.raises(ValueError):
            team.send(sender="lead", recipient="external", body="x")

    def test_send_from_non_member_rejected(self):
        team = self._basic_team()
        with pytest.raises(PermissionError):
            team.send(sender="external", recipient="lead", body="x")

    def test_broadcast_skips_sender(self):
        team = self._basic_team()
        team.send(sender="lead", recipient="*", body="all hands")
        # Lead doesn't receive their own broadcast.
        assert team.receive(agent_id="lead") is None
        # Both spokes do.
        assert team.receive(agent_id="spoke-1") is not None
        assert team.receive(agent_id="spoke-2") is not None

    def test_only_lead_cancels(self):
        team = self._basic_team()
        t = team.add_task(description="x", added_by="lead")
        with pytest.raises(PermissionError):
            team.cancel_task(task_id=t.task_id, agent_id="spoke-1")
        team.cancel_task(task_id=t.task_id, agent_id="lead")

    def test_stats(self):
        team = self._basic_team()
        team.add_task(description="a", added_by="lead")
        team.add_task(description="b", added_by="lead")
        team.claim_next(agent_id="spoke-1")
        s = team.stats()
        assert s["agents"] == 3
        assert s["lead_id"] == "lead"
        assert s["spokes"] == 2
        assert s["tasks"]["total"] == 2

    def test_end_to_end_workflow(self):
        """Full workflow: lead adds task → spoke claims → spoke completes →
        spoke notifies lead → lead acks via broadcast."""
        team = self._basic_team()
        t1 = team.add_task(description="search papers", added_by="lead")
        t2 = team.add_task(description="summarise", added_by="lead")
        # Spokes claim concurrently.
        c1 = team.claim_next(agent_id="spoke-1")
        c2 = team.claim_next(agent_id="spoke-2")
        assert c1.task_id != c2.task_id
        # Both complete.
        team.complete_task(task_id=c1.task_id, agent_id="spoke-1", output="paper list")
        team.complete_task(task_id=c2.task_id, agent_id="spoke-2", output="summary")
        # Spokes notify lead.
        team.send(sender="spoke-1", recipient="lead", body="done with search")
        team.send(sender="spoke-2", recipient="lead", body="done with summary")
        msg1 = team.receive(agent_id="lead")
        msg2 = team.receive(agent_id="lead")
        assert {msg1.sender, msg2.sender} == {"spoke-1", "spoke-2"}
        # Lead broadcasts thanks.
        team.send(sender="lead", recipient="*", body="thanks all")
        assert team.receive(agent_id="spoke-1").body == "thanks all"
        assert team.receive(agent_id="spoke-2").body == "thanks all"
