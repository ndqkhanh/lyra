"""Model registry and definitions for Lyra"""

from dataclasses import dataclass


@dataclass
class ModelInfo:
    """Information about a model"""
    id: str
    name: str
    provider: str
    description: str
    input_price: float  # per Mtok
    output_price: float  # per Mtok
    context_window: int
    capabilities: list[str]
    api_key_env: str  # Environment variable for API key


# Model registry
MODELS = [
    # Anthropic models
    ModelInfo(
        id="claude-opus-4-20250514",
        name="Claude Opus 4.7",
        provider="Anthropic",
        description="Most capable",
        input_price=5.0,
        output_price=25.0,
        context_window=1_000_000,
        capabilities=["thinking", "vision", "tools"],
        api_key_env="ANTHROPIC_API_KEY"
    ),
    ModelInfo(
        id="claude-sonnet-4-20250514",
        name="Claude Sonnet 4.6",
        provider="Anthropic",
        description="Best for everyday",
        input_price=3.0,
        output_price=15.0,
        context_window=200_000,
        capabilities=["vision", "tools"],
        api_key_env="ANTHROPIC_API_KEY"
    ),
    ModelInfo(
        id="claude-haiku-4-20250514",
        name="Claude Haiku 4.5",
        provider="Anthropic",
        description="Fastest",
        input_price=1.0,
        output_price=5.0,
        context_window=200_000,
        capabilities=["tools"],
        api_key_env="ANTHROPIC_API_KEY"
    ),

    # OpenAI models
    ModelInfo(
        id="gpt-4-turbo",
        name="GPT-4 Turbo",
        provider="OpenAI",
        description="OpenAI flagship",
        input_price=10.0,
        output_price=30.0,
        context_window=128_000,
        capabilities=["vision", "tools"],
        api_key_env="OPENAI_API_KEY"
    ),
    ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        description="Multimodal",
        input_price=5.0,
        output_price=15.0,
        context_window=128_000,
        capabilities=["vision", "audio", "tools"],
        api_key_env="OPENAI_API_KEY"
    ),

    # Google models
    ModelInfo(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        provider="Google",
        description="Long context",
        input_price=3.5,
        output_price=10.5,
        context_window=2_000_000,
        capabilities=["vision", "tools"],
        api_key_env="GOOGLE_API_KEY"
    ),
]


# Effort levels
EFFORT_LEVELS = ["low", "medium", "high", "xhigh"]


class ModelRegistry:
    """Registry for managing models"""

    def __init__(self):
        self.models = MODELS

    def get_model(self, model_id: str) -> ModelInfo | None:
        """Get model by ID"""
        for model in self.models:
            if model.id == model_id:
                return model
        return None

    def get_all_models(self) -> list[ModelInfo]:
        """Get all models"""
        return self.models

    def format_context_window(self, size: int) -> str:
        """Format context window size"""
        if size >= 1_000_000:
            return f"{size // 1_000_000}M context"
        elif size >= 1_000:
            return f"{size // 1_000}K context"
        else:
            return f"{size} tokens"


# Global registry instance
_registry = ModelRegistry()


def get_registry() -> ModelRegistry:
    """Get the global model registry"""
    return _registry
