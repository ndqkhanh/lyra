"""The AgentLoop: think → act → observe, with hooks, permissions, budgets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .hooks import HookEvent, HookRegistry
from .messages import Message, StopReason, ToolCall, ToolResult
from .models import LLMProvider
from .observability import Tracer
from .permissions import (
    Decision,
    PermissionMode,
    PermissionPolicy,
    resolve_decision,
)
from .tools import ToolRegistry


@dataclass
class LoopResult:
    final_text: str
    transcript: list[Message]
    steps: int
    stop_reason: str
    tool_calls_count: int = 0
    blocked_calls_count: int = 0


# A function that decides whether an `ask`-permission call should be approved.
# Default test-friendly impl: auto-approve. Real deployments pass a human-gated version.
ApprovalFn = Callable[[ToolCall], bool]


def auto_approve(_call: ToolCall) -> bool:
    return True


class AgentLoop:
    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolRegistry,
        *,
        hooks: Optional[HookRegistry] = None,
        permission_mode: PermissionMode = PermissionMode.DEFAULT,
        policy: Optional[PermissionPolicy] = None,
        tracer: Optional[Tracer] = None,
        approval: ApprovalFn = auto_approve,
        max_steps: int = 20,
        system_prompt: str = "You are a helpful agent. Use tools precisely.",
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.hooks = hooks or HookRegistry()
        self.permission_mode = permission_mode
        self.policy = policy or PermissionPolicy()
        self.tracer = tracer or Tracer()
        self.approval = approval
        self.max_steps = max_steps
        self.system_prompt = system_prompt

    def run(self, task: str, initial_messages: Optional[list[Message]] = None) -> LoopResult:
        transcript: list[Message] = list(initial_messages or [])
        if not any(m.role == "system" for m in transcript):
            transcript.insert(0, Message.system(self.system_prompt))
        transcript.append(Message.user(task))

        tool_count = 0
        blocked = 0

        with self.tracer.span("agent.run", task_preview=task[:80]):
            for step in range(self.max_steps):
                with self.tracer.span("agent.step", step=step) as sp:
                    resp = self.llm.generate(transcript, tools=self.tools.schemas())
                    transcript.append(resp)
                    sp.attributes["tool_calls"] = len(resp.tool_calls)

                    if not resp.has_tool_calls() or resp.stop_reason == StopReason.END_TURN:
                        return LoopResult(
                            final_text=resp.content,
                            transcript=transcript,
                            steps=step + 1,
                            stop_reason=str(resp.stop_reason or "end_turn"),
                            tool_calls_count=tool_count,
                            blocked_calls_count=blocked,
                        )

                    results: list[ToolResult] = []
                    for call in resp.tool_calls:
                        tool_count += 1
                        result = self._execute_call(call)
                        if result.is_error and "blocked by" in result.content:
                            blocked += 1
                        results.append(result)

                    transcript.append(Message.tool(results))

            # max steps exhausted
            last_text = ""
            for m in reversed(transcript):
                if m.role == "assistant" and m.content:
                    last_text = m.content
                    break
            return LoopResult(
                final_text=last_text or "step budget exhausted",
                transcript=transcript,
                steps=self.max_steps,
                stop_reason="max_steps",
                tool_calls_count=tool_count,
                blocked_calls_count=blocked,
            )

    # -- internal -----------------------------------------------------------------

    def _execute_call(self, call: ToolCall) -> ToolResult:
        self.tracer.incr("tool.calls")
        tool = self.tools.get(call.name)
        tool_writes = tool.writes if tool else False
        tool_risk = tool.risk if tool else "low"

        decision = resolve_decision(
            call,
            mode=self.permission_mode,
            policy=self.policy,
            tool_writes=tool_writes,
            tool_risk=tool_risk,
        )

        if decision.decision == Decision.DENY:
            self.tracer.incr("tool.denied")
            return ToolResult(
                call_id=call.id,
                content=f"blocked by policy: {decision.reason}",
                is_error=True,
            )

        if decision.decision == Decision.ASK:
            if not self.approval(call):
                self.tracer.incr("tool.rejected_by_approval")
                return ToolResult(
                    call_id=call.id,
                    content=f"blocked by approver: {decision.reason}",
                    is_error=True,
                )

        pre = self.hooks.run(HookEvent.PRE_TOOL_USE, call)
        if pre.block:
            self.tracer.incr("tool.pre_hook_blocked")
            return ToolResult(
                call_id=call.id,
                content=f"blocked by hook: {pre.reason}",
                is_error=True,
            )

        with self.tracer.span(f"tool.{call.name}") as sp:
            result = self.tools.execute(call)
            sp.attributes["is_error"] = result.is_error

        post = self.hooks.run(HookEvent.POST_TOOL_USE, call, result)
        if post.annotation:
            result = ToolResult(
                call_id=result.call_id,
                content=f"{result.content}\n[hook] {post.annotation}",
                is_error=result.is_error,
            )
        return result
