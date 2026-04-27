"""Tiny JSONL-as-list-of-dicts fixtures used by every Phase M test.

Keeping these as Python literals (not on-disk fixtures) makes the test
suite self-contained and ~5x faster than reading from tmp_path."""
from __future__ import annotations

from typing import Any, Mapping


CODING_HAPPY_PATH: list[Mapping[str, Any]] = [
    {"kind": "turn", "turn": 1, "ts": 1.0, "user_input": "add validation",
     "mode": "plan",  "model": "deepseek-v4-flash",
     "tokens_in": 200, "tokens_out": 80,  "cost_delta_usd": 0.0008,
     "latency_ms": 1200.0},
    {"kind": "chat", "turn": 1, "user": "add validation",
     "assistant": "Plan: 1. find input handler 2. add isinstance check...",
     "model": "deepseek-v4-flash"},
    {"kind": "turn", "turn": 2, "ts": 2.0, "user_input": "go",
     "mode": "agent", "model": "deepseek-v4-pro",
     "tokens_in": 1800, "tokens_out": 420, "cost_delta_usd": 0.0042,
     "latency_ms": 6800.0},
    {"kind": "chat", "turn": 2, "user": "go",
     "assistant": "I'll Edit(handlers/api.py) to add the isinstance guard...",
     "model": "deepseek-v4-pro"},
]


DEBUGGING_SESSION: list[Mapping[str, Any]] = [
    {"kind": "turn", "turn": 1, "ts": 1.0,
     "user_input": "fix the failing test in tests/foo.py",
     "mode": "debug", "model": "deepseek-v4-pro",
     "tokens_in": 800, "tokens_out": 300, "cost_delta_usd": 0.0021,
     "latency_ms": 4200.0},
    {"kind": "chat", "turn": 1,
     "user": "fix the failing test in tests/foo.py",
     "assistant": "Reading the traceback... AttributeError on line 42.",
     "model": "deepseek-v4-pro"},
]


RETRY_STREAK: list[Mapping[str, Any]] = [
    {"kind": "turn", "turn": 1, "ts": 1.0,
     "user_input": "implement the cache", "mode": "agent",
     "model": "deepseek-v4-pro",
     "tokens_in": 600, "tokens_out": 200, "cost_delta_usd": 0.0015,
     "latency_ms": 3000.0},
    {"kind": "turn", "turn": 2, "ts": 2.0,
     "user_input": "still broken, try again", "mode": "agent",
     "model": "deepseek-v4-pro",
     "tokens_in": 700, "tokens_out": 250, "cost_delta_usd": 0.0018,
     "latency_ms": 3200.0},
    {"kind": "turn", "turn": 3, "ts": 3.0,
     "user_input": "no, that's wrong, fix the cache key collision",
     "mode": "agent", "model": "deepseek-v4-pro",
     "tokens_in": 800, "tokens_out": 280, "cost_delta_usd": 0.0021,
     "latency_ms": 3500.0},
]


CONVERSATION: list[Mapping[str, Any]] = [
    {"kind": "turn", "turn": 1, "ts": 1.0,
     "user_input": "hi, what can you help me with today?",
     "mode": "ask", "model": "deepseek-v4-flash",
     "tokens_in": 50, "tokens_out": 120, "cost_delta_usd": 0.0003,
     "latency_ms": 900.0},
    {"kind": "chat", "turn": 1, "user": "hi, what can you help me with today?",
     "assistant": "I'm Lyra. I can help with coding, plans, debugging, "
                  "and answering questions about your repo.",
     "model": "deepseek-v4-flash"},
]
