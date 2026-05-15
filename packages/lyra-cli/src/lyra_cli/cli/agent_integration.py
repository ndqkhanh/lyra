"""Agent Loop Integration for Lyra TUI.

Connects the TUI to actual LLM providers with streaming output.
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


class TUIAgentIntegration:
    """Integrates AgentLoop with TUI."""

    def __init__(self, model: str, repo_root, budget_cap_usd: float | None = None):
        self.model = model
        self.repo_root = repo_root
        self.budget_cap_usd = budget_cap_usd
        self._client: Any = None
        self._provider: str = ""
        self._model_name: str = ""
        self._total_tokens = 0
        self._total_cost = 0.0
        self._context_tokens = 0

    async def initialize(self):
        """Initialize LLM client based on model."""
        from .credentials import CredentialManager, parse_model_string

        cred_mgr = CredentialManager()
        provider, model_name = parse_model_string(self.model)

        # Get credentials for provider
        creds = cred_mgr.get_provider(provider)
        if not creds:
            raise ValueError(f"No credentials found for provider: {provider}")

        api_key = creds.get("api_key")
        base_url = creds.get("base_url")

        # Initialize client based on provider
        if provider == "anthropic":
            if not HAS_ANTHROPIC:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            self._client = anthropic.AsyncAnthropic(**client_kwargs)
            self._provider = "anthropic"
            self._model_name = model_name

        elif provider == "openai":
            if not HAS_OPENAI:
                raise ImportError("openai package not installed. Run: pip install openai")

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            self._client = openai.AsyncOpenAI(**client_kwargs)
            self._provider = "openai"
            self._model_name = model_name

        elif provider == "deepseek":
            if not HAS_OPENAI:
                raise ImportError("openai package not installed. Run: pip install openai")

            # DeepSeek uses OpenAI-compatible API
            self._client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or "https://api.deepseek.com"
            )
            self._provider = "openai"  # Use OpenAI client
            self._model_name = model_name

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def run_agent(
        self, user_input: str
    ) -> AsyncIterator[dict]:
        """Run agent with streaming output.

        Yields:
            dict with keys:
                - type: "text" | "tool" | "usage"
                - content: str
                - metadata: dict (optional)
        """
        if not self._client:
            await self.initialize()

        try:
            if self._provider == "anthropic":
                async for event in self._run_anthropic(user_input):
                    yield event
            elif self._provider == "openai":
                async for event in self._run_openai(user_input):
                    yield event
        except Exception as e:
            yield {
                "type": "text",
                "content": f"\n\nError: {str(e)}\n",
            }

    async def _run_anthropic(self, user_input: str) -> AsyncIterator[dict]:
        """Run Anthropic Claude model with streaming."""
        try:
            async with self._client.messages.stream(
                model=self._model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": user_input}],
            ) as stream:
                async for text in stream.text_stream:
                    yield {
                        "type": "text",
                        "content": text,
                    }

                # Get final message for usage stats
                message = await stream.get_final_message()

                # Update usage stats
                if hasattr(message, "usage"):
                    input_tokens = message.usage.input_tokens
                    output_tokens = message.usage.output_tokens
                    self._total_tokens += input_tokens + output_tokens
                    self._context_tokens = input_tokens

                    # Rough cost estimation (Claude Sonnet 4.6 pricing)
                    # $3/MTok input, $15/MTok output
                    input_cost = (input_tokens / 1_000_000) * 3.0
                    output_cost = (output_tokens / 1_000_000) * 15.0
                    self._total_cost += input_cost + output_cost

                    yield {
                        "type": "usage",
                        "content": "",
                        "metadata": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_cost": self._total_cost,
                        }
                    }

        except Exception as e:
            yield {
                "type": "text",
                "content": f"\n\nAnthropicError: {str(e)}\n",
            }

    async def _run_openai(self, user_input: str) -> AsyncIterator[dict]:
        """Run OpenAI/DeepSeek model with streaming."""
        try:
            stream = await self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": user_input}],
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "type": "text",
                        "content": chunk.choices[0].delta.content,
                    }

            # Note: OpenAI streaming doesn't provide usage in stream
            # Would need a separate call or use non-streaming for usage
            yield {
                "type": "usage",
                "content": "",
                "metadata": {
                    "input_tokens": 0,  # Not available in streaming
                    "output_tokens": 0,
                    "total_cost": self._total_cost,
                }
            }

        except Exception as e:
            yield {
                "type": "text",
                "content": f"\n\nOpenAIError: {str(e)}\n",
            }

    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "total_tokens": self._total_tokens,
            "total_cost": self._total_cost,
            "context_tokens": self._context_tokens,
        }
