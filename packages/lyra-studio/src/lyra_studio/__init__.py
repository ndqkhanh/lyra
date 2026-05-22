"""Visual Agent Builder — GUI for designing, connecting, and deploying agent pipelines.

Inspired by Langflow (148K⭐) and Dify (142K⭐) — visual agent builders
that dominate the market. Lyra's drag-and-drop agent pipeline designer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "NodeDefinition",
    "PipelineEdge",
    "AgentPipeline",
    "AgentStudio",
]


@dataclass
class NodeDefinition:
    id: str
    node_type: str
    label: str
    config: dict[str, Any] = field(default_factory=dict)
    x: float = 0.0
    y: float = 0.0


@dataclass
class PipelineEdge:
    source_id: str
    target_id: str
    label: str = ""


@dataclass
class AgentPipeline:
    id: str
    name: str
    nodes: list[NodeDefinition] = field(default_factory=list)
    edges: list[PipelineEdge] = field(default_factory=list)


class AgentStudio:
    """Visual agent pipeline builder — drag, connect, deploy."""

    NODE_TYPES = ["input", "llm", "tool", "skill", "memory", "router", "output", "condition", "loop", "sub_agent"]

    def __init__(self):
        self.pipelines: dict[str, AgentPipeline] = {}
        self._counter = 0

    def create_pipeline(self, name: str) -> AgentPipeline:
        self._counter += 1
        pipe = AgentPipeline(id=f"pipe_{self._counter}", name=name)
        self.pipelines[pipe.id] = pipe
        return pipe

    def add_node(self, pipeline_id: str, node_type: str, label: str, config: Optional[dict] = None) -> Optional[NodeDefinition]:
        pipe = self.pipelines.get(pipeline_id)
        if not pipe or node_type not in self.NODE_TYPES:
            return None
        node = NodeDefinition(id=f"node_{len(pipe.nodes)+1}", node_type=node_type, label=label, config=config or {})
        pipe.nodes.append(node)
        return node

    def connect(self, pipeline_id: str, source_id: str, target_id: str, label: str = "") -> bool:
        pipe = self.pipelines.get(pipeline_id)
        if not pipe:
            return False
        pipe.edges.append(PipelineEdge(source_id=source_id, target_id=target_id, label=label))
        return True

    def validate(self, pipeline_id: str) -> dict[str, Any]:
        pipe = self.pipelines.get(pipeline_id)
        if not pipe:
            return {"valid": False, "errors": ["Pipeline not found"]}
        errors = []
        if not pipe.nodes:
            errors.append("Pipeline has no nodes")
        has_input = any(n.node_type == "input" for n in pipe.nodes)
        has_output = any(n.node_type == "output" for n in pipe.nodes)
        if not has_input:
            errors.append("Pipeline has no input node")
        if not has_output:
            errors.append("Pipeline has no output node")
        return {"valid": len(errors) == 0, "errors": errors, "node_count": len(pipe.nodes), "edge_count": len(pipe.edges)}

    def export(self, pipeline_id: str) -> Optional[dict[str, Any]]:
        pipe = self.pipelines.get(pipeline_id)
        if not pipe:
            return None
        return {"id": pipe.id, "name": pipe.name, "nodes": [(n.node_type, n.label) for n in pipe.nodes], "edges": [(e.source_id, e.target_id) for e in pipe.edges]}

    @property
    def stats(self) -> dict[str, Any]:
        return {"pipelines": len(self.pipelines), "node_types": self.NODE_TYPES}
