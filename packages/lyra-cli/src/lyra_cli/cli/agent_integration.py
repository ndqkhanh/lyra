"""Agent Loop Integration for Lyra TUI — All Context Optimization Phases (A–H).

Phase A — Multi-turn conversation history
Phase B — Output verbosity control (Caveman 60.6k★ inspired)
Phase C — Tool output filtering via ToolOutputFilter (RTK 48.4k★ inspired)
Phase D — Sliding window + rolling summary via ContextManager (MemGPT inspired)
Phase E — Core memory injection via MemoryManager
Phase F — Heuristic prompt compression via HeuristicCompressor (LLMLingua inspired)
Phase G — Semantic retrieval indexing via SemanticRetriever
Phase H — Anthropic prompt caching + context budget alerts
"""

from __future__ import annotations

from typing import AsyncIterator, Any

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Internal optimisation helpers — imported at top level (same package, always present)
from .context_manager import ContextBudget, ContextManager
from .prompt_compressor import HeuristicCompressor
from .semantic_retriever import SemanticRetriever
from .tool_output_filter import ToolOutputFilter
from .tool_registry import ToolRegistry
from .default_tools import register_default_tools

# Eager tools integration
from lyra_cli.eager_tools import SealDetector, EagerExecutorPool, MetricsCollector


# ── Phase H: Provider context limits (tokens) ──────────────────────────────
_CONTEXT_LIMITS: dict[str, int] = {
    "claude-opus-4-7": 200_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
    "deepseek-chat": 64_000,
    "deepseek-reasoner": 64_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
}

# ── Phase H: Pricing per MTok (input_usd, output_usd) ─────────────────────
_PRICING: dict[str, tuple[float, float]] = {
    "anthropic": (3.0, 15.0),    # Claude Sonnet 4.6
    "deepseek": (0.27, 1.10),    # DeepSeek V3
    "openai": (2.5, 10.0),       # GPT-4o
}

# ── Phase B: Verbosity system-prompt injections ────────────────────────────
_VERBOSITY_PROMPTS: dict[str, str] = {
    "lite": (
        "Be concise. Use short sentences. Omit filler phrases and pleasantries."
    ),
    "full": (
        "Respond with maximum brevity. Use fragments where unambiguous. "
        "No preamble, no trailing summaries, no filler. Code over prose. "
        "Bullet points over paragraphs when explaining."
    ),
    "ultra": (
        "Respond in the fewest possible words. Fragments and labels only. "
        "No complete sentences unless code requires them. Maximum information density."
    ),
    "off": "",
}

_BASE_SYSTEM = (
    "You are Lyra, a precise technical AI research and coding assistant. "
    "Be direct and accurate."
)


class TUIAgentIntegration:
    """Integrates LLM providers with TUI — all context optimization phases (A–H)."""

    def __init__(
        self,
        model: str,
        repo_root: Any,
        budget_cap_usd: float | None = None,
    ) -> None:
        self.model = model
        self.repo_root = repo_root
        self.budget_cap_usd = budget_cap_usd

        # Provider state
        self._client: Any = None
        self._provider: str = ""          # "anthropic" | "openai"
        self._original_provider: str = "" # "anthropic" | "openai" | "deepseek"
        self._model_name: str = ""
        self._context_limit: int = 100_000
        self._pricing: tuple[float, float] = (1.0, 5.0)

        # Phase B: Verbosity
        self._verbosity: str = "full"

        # Phase C: Tool output filter (set in initialize)
        self._tool_filter: ToolOutputFilter | None = None

        # Phase D: Context manager (lazy — needs summarizer bound after initialize)
        self._context_manager: ContextManager | None = None

        # Phase E: Memory manager (set in initialize, optional)
        self._memory_manager: Any = None

        # Phase F: Heuristic compressor (set in initialize)
        self._compressor: HeuristicCompressor | None = None

        # Phase G: Semantic retriever (set in initialize)
        self._retriever: SemanticRetriever | None = None

        # Tool registry
        self._tool_registry: ToolRegistry | None = None

        # Eager tools
        self._seal_detector: SealDetector | None = None
        self._executor_pool: EagerExecutorPool | None = None
        self._metrics_collector: MetricsCollector | None = None

        # Phase H: Cache tracking
        self._cache_saved_tokens: int = 0

        # Usage stats
        self._total_tokens: int = 0
        self._total_cost: float = 0.0
        self._context_tokens: int = 0

    # ── Initialization ─────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize LLM client and all optimization helpers."""
        from .credentials import CredentialManager, parse_model_string

        cred_mgr = CredentialManager()
        provider, model_name = parse_model_string(self.model)

        creds = cred_mgr.get_provider(provider)
        if not creds:
            raise ValueError(f"No credentials found for provider: {provider}")

        api_key = creds.get("api_key")
        base_url = creds.get("base_url")

        if provider == "anthropic":
            if not HAS_ANTHROPIC:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            client_kwargs: dict = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            self._client = anthropic.AsyncAnthropic(**client_kwargs)
            self._provider = "anthropic"
            self._pricing = _PRICING["anthropic"]

        elif provider in ("openai", "deepseek"):
            if not HAS_OPENAI:
                raise ImportError("openai package not installed. Run: pip install openai")
            client_kwargs = {"api_key": api_key}
            if provider == "deepseek":
                client_kwargs["base_url"] = base_url or "https://api.deepseek.com"
            elif base_url:
                client_kwargs["base_url"] = base_url
            self._client = openai.AsyncOpenAI(**client_kwargs)
            self._provider = "openai"
            self._pricing = _PRICING[provider]  # "deepseek" or "openai"

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        self._original_provider = provider
        self._model_name = model_name
        self._context_limit = _CONTEXT_LIMITS.get(model_name, 100_000)

        # Phase C, F, G: eager-init zero-dep helpers
        self._tool_filter = ToolOutputFilter()
        self._compressor = HeuristicCompressor()
        self._retriever = SemanticRetriever()

        # Phase E: memory manager (optional — graceful if DB unavailable)
        try:
            from .memory_manager import MemoryManager
            self._memory_manager = MemoryManager()
        except Exception:
            self._memory_manager = None

        # Initialize tool registry
        self._tool_registry = ToolRegistry()
        register_default_tools(self._tool_registry)

        # Initialize eager tools
        self._metrics_collector = MetricsCollector()
        self._seal_detector = SealDetector(metrics=self._metrics_collector)
        self._executor_pool = EagerExecutorPool(
            tool_registry={name: self._tool_registry.execute for name in ["read_file", "search_code", "list_files"]},
            metrics=self._metrics_collector,
        )

    def _ensure_context_manager(self) -> ContextManager:
        """Phase D: Lazy-init ContextManager (needs self._summarize_turns bound after initialize)."""
        if self._context_manager is None:
            self._context_manager = ContextManager(
                budget=ContextBudget(),
                summarizer=self._summarize_turns,
            )
        return self._context_manager

    # ── Public control API ─────────────────────────────────────────────────

    def set_verbosity(self, level: str) -> None:
        """Phase B: Set output verbosity (lite | full | ultra | off)."""
        if level not in _VERBOSITY_PROMPTS:
            raise ValueError(f"Unknown verbosity '{level}'. Choose: lite, full, ultra, off")
        self._verbosity = level

    def get_verbosity(self) -> str:
        return self._verbosity

    def filter_tool_output(self, tool_name: str, output: str) -> str:
        """Phase C: Filter a tool result before injecting into context."""
        if self._tool_filter is None:
            return output
        return self._tool_filter.filter(tool_name, output)

    def retrieve_relevant(self, query: str, top_k: int = 5) -> list[dict]:
        """Phase G: Retrieve semantically relevant past turns for a query."""
        if self._retriever is None:
            return []
        return self._retriever.retrieve(query, top_k=top_k)

    def clear_history(self) -> None:
        """Phase A+D+G: Reset conversation memory."""
        if self._context_manager is not None:
            self._context_manager.clear()
        if self._retriever is not None:
            self._retriever.clear()

    def history_stats(self) -> dict:
        """Full context statistics across all phases."""
        cm = self._context_manager.stats() if self._context_manager else {}
        tool = self._tool_filter.session_stats() if self._tool_filter else {}
        return {
            **cm,
            "tool_filter": tool,
            "retriever_size": self._retriever.size if self._retriever else 0,
            "verbosity": self._verbosity,
            "cache_saved_tokens": self._cache_saved_tokens,
            "context_limit": self._context_limit,
            "context_pct": round(
                self._context_tokens / max(self._context_limit, 1) * 100, 1
            ),
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost,
        }

    # ── Main agent loop ────────────────────────────────────────────────────

    async def run_agent(self, user_input: str) -> AsyncIterator[dict]:
        """Stream a response — all optimization phases active.

        Yields dicts: {type: "text"|"tool"|"usage"|"warning", content: str, metadata?: dict}
        """
        if not self._client:
            await self.initialize()

        # Phase D: get sliding-window history
        cm = self._ensure_context_manager()

        # Phase B+E: build system prompt
        system = self._build_system_prompt()

        # Phase D: history = summary block + verbatim recent turns
        messages = cm.build_messages(system)

        # Append current user turn
        messages.append({"role": "user", "content": user_input})

        # Phase F: compress older messages, leave last 2 untouched
        if self._compressor is not None:
            messages = self._compressor.compress_messages(messages, skip_last=2)

        # Stream from provider, collect assistant output
        assistant_content = ""
        try:
            if self._provider == "anthropic":
                async for event in self._run_anthropic(messages):
                    if event["type"] == "text":
                        assistant_content += event["content"]
                    yield event
            elif self._provider == "openai":
                async for event in self._run_openai(messages):
                    if event["type"] == "text":
                        assistant_content += event["content"]
                    yield event
        except Exception as e:
            yield {"type": "text", "content": f"\n\nError: {str(e)}\n"}
            return

        # Phase A+D: record completed turn in context manager
        if assistant_content:
            cm.add_messages(user_input, assistant_content)

        # Phase G: index both sides in retriever
        if self._retriever is not None and assistant_content:
            self._retriever.index({"role": "user", "content": user_input})
            self._retriever.index({"role": "assistant", "content": assistant_content})

        # Phase D: compress history if over budget (may call LLM)
        compressions_before = cm.stats().get("compressions", 0)
        await cm.maybe_compress()
        compressions_after = cm.stats().get("compressions", 0)

        # Wave 3: emit compaction notice when a summary was just written
        if compressions_after > compressions_before:
            turns_summarized = cm.stats().get("summarized_turns", 0)
            yield {
                "type": "compaction",
                "content": "",
                "metadata": {"turns": turns_summarized},
            }

        # Phase H: emit budget warning if context is high
        budget_event = self._check_context_budget()
        if budget_event:
            yield budget_event

    # ── System prompt ──────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Phase B+E: Combine base prompt, verbosity instruction, and core memory."""
        parts = [_BASE_SYSTEM]

        verbosity = _VERBOSITY_PROMPTS.get(self._verbosity, "")
        if verbosity:
            parts.append(verbosity)

        # Phase E: inject core memory facts (always-in-context, ≤500 tokens)
        if self._memory_manager is not None:
            try:
                core_block = self._memory_manager.get_core_prompt_block()
                if core_block:
                    parts.append(core_block)
            except Exception:
                pass

        return "\n\n".join(filter(None, parts))

    # ── Provider implementations ───────────────────────────────────────────

    async def _run_anthropic(self, messages: list[dict]) -> AsyncIterator[dict]:
        """Phase H: Anthropic streaming with cache_control on system prefix."""
        try:
            # Extract system messages — Anthropic takes them separately
            system_texts: list[str] = []
            chat_msgs: list[dict] = []
            for msg in messages:
                if msg.get("role") == "system":
                    system_texts.append(msg["content"])
                else:
                    chat_msgs.append(msg)

            stream_kwargs: dict = {
                "model": self._model_name,
                "max_tokens": 4096,
                "messages": chat_msgs,
            }
            # Add tools if registry available
            if self._tool_registry:
                tools = self._tool_registry.get_tool_definitions()
                if tools:
                    stream_kwargs["tools"] = tools
            # Phase H: cache_control on stable system prefix (90% cost on re-use)
            if system_texts:
                stream_kwargs["system"] = [
                    {
                        "type": "text",
                        "text": "\n\n".join(system_texts),
                        "cache_control": {"type": "ephemeral"},
                    }
                ]

            async with self._client.messages.stream(**stream_kwargs) as stream:
                # Start metrics collection
                if self._metrics_collector:
                    self._metrics_collector.start_stream()

                # Process stream events for text and tool_use blocks
                async for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            yield {"type": "text", "content": delta.text}
                        elif hasattr(delta, "partial_json") and self._seal_detector:
                            # Process chunk for seal detection
                            chunk = {"tool_call_id": getattr(event, "index", ""), "arguments": delta.partial_json}
                            sealed_blocks = self._seal_detector.process_chunk(chunk)

                            # Dispatch sealed tools eagerly
                            for block in sealed_blocks:
                                if self._executor_pool and self._tool_registry:
                                    idempotent = self._tool_registry.is_idempotent(block.name)
                                    await self._executor_pool.dispatch(block, idempotent=idempotent)

                message = await stream.get_final_message()

                # Flush any remaining sealed blocks
                if self._seal_detector:
                    sealed_blocks = self._seal_detector.flush()
                    for block in sealed_blocks:
                        if self._executor_pool and self._tool_registry:
                            idempotent = self._tool_registry.is_idempotent(block.name)
                            await self._executor_pool.dispatch(block, idempotent=idempotent)

                # Collect eager tool results
                if self._executor_pool:
                    results = await self._executor_pool.collect_results()
                    for result in results:
                        if result.error:
                            yield {"type": "tool", "content": f"Tool error: {result.error}"}
                        else:
                            yield {"type": "tool", "content": f"Tool result: {result.result}"}

                # Execute non-idempotent tools (deferred until message_stop)
                if hasattr(message, "content"):
                    for block in message.content:
                        if block.type == "tool_use":
                            if self._tool_registry and not self._tool_registry.is_idempotent(block.name):
                                tool_result = await self._execute_tool(block)
                                yield {"type": "tool", "content": tool_result}
                if hasattr(message, "usage"):
                    input_tokens: int = message.usage.input_tokens
                    output_tokens: int = message.usage.output_tokens
                    cache_read: int = getattr(message.usage, "cache_read_input_tokens", 0) or 0
                    cache_write: int = getattr(message.usage, "cache_creation_input_tokens", 0) or 0

                    self._cache_saved_tokens += cache_read
                    self._total_tokens += input_tokens + output_tokens
                    self._context_tokens = input_tokens

                    in_p, out_p = self._pricing
                    billable_input = max(input_tokens - cache_read, 0)
                    self._total_cost += (
                        (billable_input / 1_000_000) * in_p
                        + (cache_read / 1_000_000) * (in_p * 0.1)
                        + (output_tokens / 1_000_000) * out_p
                    )

                    yield {
                        "type": "usage",
                        "content": "",
                        "metadata": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_cost": self._total_cost,
                            "cache_read_tokens": cache_read,
                            "cache_write_tokens": cache_write,
                        },
                    }

        except Exception as e:
            yield {"type": "text", "content": f"\n\nAnthropicError: {str(e)}\n"}

    async def _run_openai(self, messages: list[dict]) -> AsyncIterator[dict]:
        """OpenAI / DeepSeek streaming — include_usage for accurate token counts."""
        try:
            stream = await self._client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )

            input_tokens = 0
            output_tokens = 0

            async for chunk in stream:
                if chunk.usage is not None:
                    input_tokens = chunk.usage.prompt_tokens or 0
                    output_tokens = chunk.usage.completion_tokens or 0
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {"type": "text", "content": chunk.choices[0].delta.content}

            self._total_tokens += input_tokens + output_tokens
            self._context_tokens = input_tokens
            in_p, out_p = self._pricing
            self._total_cost += (
                (input_tokens / 1_000_000) * in_p
                + (output_tokens / 1_000_000) * out_p
            )

            yield {
                "type": "usage",
                "content": "",
                "metadata": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_cost": self._total_cost,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                },
            }

        except Exception as e:
            yield {"type": "text", "content": f"\n\nOpenAIError: {str(e)}\n"}

    # ── Phase D: Summarizer (called by ContextManager._compress) ──────────

    async def _execute_tool(self, tool_block: Any) -> str:
        """Execute a tool and return formatted result."""
        if not self._tool_registry:
            return f"Error: Tool registry not initialized"

        try:
            result = await self._tool_registry.execute(
                tool_block.name,
                tool_block.input,
            )
            return f"Tool {tool_block.name}: {result}"
        except Exception as e:
            return f"Tool {tool_block.name} error: {str(e)}"

    async def _summarize_turns(self, turns: list[dict], existing_summary: str) -> str:
        """One-shot LLM call to compress old conversation turns into a summary."""
        msgs: list[dict] = []
        if existing_summary:
            msgs.append({
                "role": "system",
                "content": f"Previous summary:\n{existing_summary}",
            })
        msgs.extend(t for t in turns if t.get("role") in ("user", "assistant"))
        msgs.append({
            "role": "user",
            "content": (
                "Summarize the above conversation in ≤200 words. Dense prose, no headers. "
                "Capture: decisions, facts established, tasks done, open questions."
            ),
        })

        try:
            if self._provider == "anthropic":
                system_text = next(
                    (m["content"] for m in msgs if m.get("role") == "system"), ""
                )
                chat = [m for m in msgs if m.get("role") != "system"]
                create_kwargs: dict = {"model": self._model_name, "max_tokens": 512, "messages": chat}
                if system_text:
                    create_kwargs["system"] = system_text
                resp = await self._client.messages.create(**create_kwargs)
                return resp.content[0].text if resp.content else existing_summary

            elif self._provider == "openai":
                resp = await self._client.chat.completions.create(
                    model=self._model_name, max_tokens=512, messages=msgs
                )
                return resp.choices[0].message.content or existing_summary

        except Exception:
            pass

        return existing_summary

    # ── Phase H: Budget monitoring ─────────────────────────────────────────

    def _check_context_budget(self) -> dict | None:
        """Return a warning event if context usage is high."""
        ratio = self._context_tokens / max(self._context_limit, 1)
        if ratio >= 0.85:
            return {
                "type": "warning",
                "content": (
                    f"\n\033[33m⚠ Context at {ratio:.0%} of limit "
                    f"({self._context_tokens:,}/{self._context_limit:,} tokens). "
                    "Run /history clear to reset.\033[0m\n"
                ),
            }
        if ratio >= 0.70:
            return {
                "type": "warning",
                "content": (
                    f"\n\033[2m[Context: {ratio:.0%} of {self._context_limit:,} token limit]\033[0m\n"
                ),
            }
        return None

    # ── Real research engine (Phase I) ────────────────────────────────────

    async def research(self, topic: str) -> AsyncIterator[dict]:
        """Run the real multi-hop research pipeline.

        Yields the same event dict format as run_agent():
          {type: "phase"|"finding"|"progress"|"done"|"error", ...}
        """
        if not self._client:
            await self.initialize()
        try:
            from .research_pipeline import RealResearchPipeline
            from .credentials import CredentialManager
            cred_mgr = CredentialManager()
            pipeline = RealResearchPipeline(
                client=self._client,
                provider=self._provider,
                model_name=self._model_name,
                cred_mgr=cred_mgr,
            )
            async for event in pipeline.run(topic):
                yield event
        except Exception as e:
            yield {"type": "error", "content": str(e)}

    # ── Stats ──────────────────────────────────────────────────────────────

    def get_usage_stats(self) -> dict:
        """Usage stats for TUI status bar."""
        return {
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost,
            "context_tokens": self._context_tokens,
            "cache_saved_tokens": self._cache_saved_tokens,
        }
