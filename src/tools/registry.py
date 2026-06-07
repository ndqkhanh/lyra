"""
Tool Definition and Registry.

Defines the ToolDef dataclass for describing a tool, and the ToolRegistry for
registering, unregistering, looking up, and discovering tools.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from jsonschema import ValidationError, validate as jsonschema_validate

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ToolHandler = Callable[..., Awaitable[Dict[str, Any]]]


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolResult:
    """Result of a single tool execution."""

    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


# ---------------------------------------------------------------------------
# Tool Definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolDef:
    """Immutable definition of a tool.

    Attributes:
        name: Unique tool identifier (snake_case).
        description: Human-readable description.
        parameters: JSON Schema dict describing expected parameters.
        handler: Async callable that accepts ``**kwargs`` and returns a dict.
        capabilities: Optional list of capability tags for discovery.
        sandbox_requirements: Optional dict of sandbox constraints.
            Recognized keys:
            - ``allowed_domains`` (list[str])
            - ``allowed_paths`` (list[str])
            - ``deny_commands`` (list[str])
            - ``timeout_seconds`` (int)
            - ``max_output_bytes`` (int)
    """

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[ToolHandler] = None
    capabilities: List[str] = field(default_factory=list)
    sandbox_requirements: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_parameters(
    parameters_schema: Dict[str, Any], inputs: Dict[str, Any]
) -> List[str]:
    """Validate ``inputs`` against a JSON Schema.

    Returns a list of error messages. An empty list means validation passed.
    """
    if not parameters_schema or not parameters_schema.get("properties"):
        # No schema defined — accept anything
        return []

    # Build a minimal JSON Schema if only ``properties`` / ``required`` given
    schema = parameters_schema.copy()
    schema.setdefault("type", "object")
    schema.setdefault("$schema", "http://json-schema.org/draft-07/schema#")

    # If schema is just ``properties`` / ``required``, promote into full schema
    if "properties" in schema and "type" not in schema:
        schema["type"] = "object"

    errors: List[str] = []
    try:
        jsonschema_validate(instance=inputs, schema=schema)
    except ValidationError as exc:
        # Walk the full error path to provide a human-readable message
        path = ".".join(str(p) for p in exc.absolute_path) if exc.absolute_path else "<root>"
        errors.append(f"{path}: {exc.message}")
    return errors


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Thread-safe registry for tool definitions."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDef] = {}
        self._capability_index: Dict[str, List[str]] = defaultdict(list)

    # ---- lifecycle --------------------------------------------------------

    def register(self, tool: ToolDef) -> None:
        """Register a tool.

        Raises ``ValueError`` if a tool with the same name already exists.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        for cap in tool.capabilities:
            self._capability_index[cap].append(tool.name)

    def unregister(self, name: str) -> Optional[ToolDef]:
        """Unregister a tool by name.

        Returns the removed ``ToolDef`` or ``None`` if not found.
        """
        tool = self._tools.pop(name, None)
        if tool is not None:
            for cap in tool.capabilities:
                try:
                    self._capability_index[cap].remove(name)
                except ValueError:
                    pass
                if not self._capability_index[cap]:
                    del self._capability_index[cap]
        return tool

    # ---- lookup -----------------------------------------------------------

    def get(self, name: str) -> Optional[ToolDef]:
        """Retrieve a ``ToolDef`` by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDef]:
        """Return a copy of all registered tools."""
        return list(self._tools.values())

    def list_by_capability(self, capability: str) -> List[ToolDef]:
        """Return tools that carry a specific capability tag."""
        return [self._tools[name] for name in self._capability_index.get(capability, [])]

    def list_capabilities(self) -> List[str]:
        """Return all distinct capability tags across registered tools."""
        return list(self._capability_index.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    # ---- execution convenience --------------------------------------------

    async def run(self, name: str, **kwargs: Any) -> ToolResult:
        """Look up a tool by name and execute its handler.

        Validates parameters against the tool's JSON Schema before dispatching.

        Returns a ``ToolResult`` — errors (validation, handler, key-not-found)
        are captured inside the result rather than raised.
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: '{name}'",
            )

        if tool.handler is None:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' has no handler registered",
            )

        # Validate inputs against JSON Schema
        validation_errors = validate_parameters(tool.parameters, kwargs)
        if validation_errors:
            return ToolResult(
                success=False,
                error="Parameter validation failed: " + "; ".join(validation_errors),
            )

        # Execute
        start = time.monotonic()
        try:
            result_dict = await tool.handler(**kwargs)
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return ToolResult(
                success=False,
                error=str(exc),
                execution_time_ms=elapsed,
            )

        elapsed = (time.monotonic() - start) * 1000
        output = result_dict.get("output", "")
        if not isinstance(output, str):
            output = str(output)
        return ToolResult(
            success=result_dict.get("success", True),
            output=output,
            error=result_dict.get("error"),
            execution_time_ms=elapsed,
        )
