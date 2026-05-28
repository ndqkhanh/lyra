"""Simple agent loop for CLI integration"""

import os

import anthropic

from lyra_cli.agent.callbacks import AgentOutputCallback


class SimpleAgentLoop:
    """Simple agent loop using Anthropic SDK directly"""

    def __init__(
        self,
        callback: AgentOutputCallback,
        model: str = "claude-opus-4-20250514",
        api_key: str | None = None
    ):
        self.callback = callback
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.conversation_history = []

    def process_message(self, user_message: str) -> None:
        """Process a user message through the agent loop"""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Generate turn ID
        turn_id = f"turn-{len(self.conversation_history)}"

        try:
            # Notify turn start
            self.callback.on_turn_start(turn_id)

            # Call Claude API with streaming
            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                messages=self.conversation_history,
            ) as stream:
                assistant_message = ""

                for text in stream.text_stream:
                    assistant_message += text
                    self.callback.on_stream_chunk(text)

                # Get final message
                message = stream.get_final_message()

                # Add assistant response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                # Notify turn end with usage stats
                result = {
                    "usage": {
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                        "total_tokens": message.usage.input_tokens + message.usage.output_tokens
                    }
                }
                self.callback.on_turn_end(turn_id, result)

        except Exception as e:
            self.callback.on_error(e)
            raise

    def reset_conversation(self) -> None:
        """Reset conversation history"""
        self.conversation_history = []


class AgentLoopFactory:
    """Factory for creating agent loops"""

    @staticmethod
    def create_simple_loop(
        callback: AgentOutputCallback,
        model: str = "claude-opus-4-20250514"
    ) -> SimpleAgentLoop:
        """Create a simple agent loop"""
        return SimpleAgentLoop(callback=callback, model=model)
