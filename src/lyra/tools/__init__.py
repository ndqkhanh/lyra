"""
Tools system for Lyra.

Provides tool registration (ToolDef, ToolRegistry), sandboxed execution (ToolExecutor),
sandbox configuration, built-in tools (ReadFile, WriteFile, RunBash, WebSearch),
compound chain execution, deferred dynamic loading, advanced tools
(WebSearch, CodeExec, PDFRead, DataAnalysis, APICall),
provider normalization (Anthropic/OpenAI/DeepSeek), and dynamic tool search.
"""

from lyra.tools.builtins import register_builtins
from lyra.tools.compound_executor import (
    ChainResult,
    ChainStep,
    ChainType,
    CompoundExecutor,
    ToolChain,
    parse_chain,
)
from lyra.tools.dynamic_loader import DynamicToolLoader, LazyToolProxy, ToolSpec
from lyra.tools.executor import ToolExecutor
from lyra.tools.provider_normalizer import (
    ProviderNormalizer,
    ProviderToolDef,
    ProviderType,
    ToolFormat,
    ToolFormatError,
)
from lyra.tools.registry import ToolDef, ToolHandler, ToolRegistry, ToolResult, validate_parameters
from lyra.tools.sandbox import (
    DENYLIST_PATTERNS,
    SandboxConfig,
    check_command_safety,
    check_domain_safety,
    check_path_safety,
)
from lyra.tools.tool_search import ToolIndex, ToolSearch, ToolSearchResult

__all__ = [
    # Core types
    "ToolDef",
    "ToolResult",
    "ToolHandler",
    # Registry
    "ToolRegistry",
    "validate_parameters",
    # Executor
    "ToolExecutor",
    # Sandbox
    "SandboxConfig",
    "DENYLIST_PATTERNS",
    "check_command_safety",
    "check_path_safety",
    "check_domain_safety",
    # Built-in tools
    "register_builtins",
    # Compound chain execution
    "CompoundExecutor",
    "ToolChain",
    "ChainStep",
    "ChainResult",
    "ChainType",
    "parse_chain",
    # Dynamic loader
    "DynamicToolLoader",
    "ToolSpec",
    "LazyToolProxy",
    # Provider normalizer
    "ProviderNormalizer",
    "ProviderToolDef",
    "ProviderType",
    "ToolFormat",
    "ToolFormatError",
    # Tool search
    "ToolSearch",
    "ToolSearchResult",
    "ToolIndex",
]

__version__ = "8.3.0"
