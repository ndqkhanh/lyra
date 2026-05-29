"""Tree rendering system for hierarchical displays"""

from dataclasses import dataclass, field
from typing import Any

from .colors import ColorEngine
from .symbols import SymbolRegistry


@dataclass
class TreeNode:
    """Tree node for hierarchical display"""
    id: str
    content: str
    children: list["TreeNode"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    collapsed: bool = False

    @property
    def depth(self) -> int:
        """Calculate depth of this node"""
        return self.metadata.get("depth", 0)

    @property
    def is_last_child(self) -> bool:
        """Check if this is the last child of its parent"""
        return self.metadata.get("is_last_child", False)


@dataclass
class RenderContext:
    """Context for tree rendering"""
    depth: int = 0
    ancestor_lines: list[bool] = field(default_factory=list)
    is_last_child: bool = False
    collapse_state: dict[str, bool] = field(default_factory=dict)


class TreeRenderer:
    """Render tree structures with box-drawing characters"""

    def __init__(self, use_colors: bool = True, use_unicode: bool = True):
        self.symbols = SymbolRegistry(use_unicode=use_unicode)
        self.colors = ColorEngine(use_colors=use_colors)

    def render_tree(self, root: TreeNode, show_root: bool = True) -> list[str]:
        """Render complete tree structure"""
        lines = []
        context = RenderContext()

        if show_root:
            lines.append(self._render_node(root, context))

        # Render children
        for i, child in enumerate(root.children):
            is_last = i == len(root.children) - 1
            child_context = RenderContext(
                depth=context.depth + 1,
                ancestor_lines=context.ancestor_lines.copy(),
                is_last_child=is_last,
                collapse_state=context.collapse_state
            )
            lines.extend(self._render_subtree(child, child_context))

        return lines

    def _render_subtree(self, node: TreeNode, context: RenderContext) -> list[str]:
        """Render node and its children recursively"""
        lines = []

        # Render this node
        lines.append(self._render_node(node, context))

        # If collapsed, don't render children
        if node.collapsed:
            return lines

        # Render children
        for i, child in enumerate(node.children):
            is_last = i == len(node.children) - 1

            # Update ancestor lines for child
            new_ancestor_lines = context.ancestor_lines.copy()
            new_ancestor_lines.append(not context.is_last_child)

            child_context = RenderContext(
                depth=context.depth + 1,
                ancestor_lines=new_ancestor_lines,
                is_last_child=is_last,
                collapse_state=context.collapse_state
            )

            lines.extend(self._render_subtree(child, child_context))

        return lines

    def _render_node(self, node: TreeNode, context: RenderContext) -> str:
        """Render a single node with proper connectors"""
        if context.depth == 0:
            # Root node - no connectors
            return node.content

        # Build prefix with ancestor lines and connector
        prefix_parts = []

        # Add vertical lines for ancestors
        for _i, has_line in enumerate(context.ancestor_lines):
            if has_line:
                prefix_parts.append(self.symbols.get("│"))
            else:
                prefix_parts.append(" ")
            prefix_parts.append(" ")

        # Add connector for this node
        if context.is_last_child:
            connector = self.symbols.get("└")
        else:
            connector = self.symbols.get("├")

        prefix_parts.append(connector)
        prefix_parts.append(self.symbols.get("─"))
        prefix_parts.append(" ")

        prefix = "".join(prefix_parts)
        styled_prefix = self.colors.dim(prefix)

        return f"{styled_prefix}{node.content}"

    def render_parallel_agents(
        self,
        agents: list[dict[str, Any]],
        show_last_tool: bool = True
    ) -> list[str]:
        """Render parallel agent execution tree"""
        lines = []

        # Header
        agent_count = len(agents)
        header = f"Running {agent_count} agents… (ctrl+o to expand)"
        symbol = self.symbols.status("running")
        lines.append(f"{self.colors.yellow(symbol)} {header}")

        # Render each agent
        for i, agent in enumerate(agents):
            is_last = i == len(agents) - 1

            # Agent line
            task = agent.get("task", "")
            tool_count = agent.get("tool_uses", 0)
            tokens = agent.get("tokens", 0)

            # Format token count
            if tokens >= 1000:
                token_str = f"{tokens / 1000:.1f}k"
            else:
                token_str = str(tokens)

            agent_line = f"{task} · {tool_count} tool uses · {token_str} tokens"

            # Connector
            if is_last:
                connector = self.symbols.get("└")
            else:
                connector = self.symbols.get("├")

            prefix = f"   {connector}─ "
            lines.append(f"{self.colors.dim(prefix)}{agent_line}")

            # Last tool call (if requested)
            if show_last_tool and "last_tool" in agent:
                last_tool = agent["last_tool"]

                # Continuation line or space
                if is_last:
                    tool_prefix = "     "
                else:
                    continuation = self.symbols.get("│")
                    tool_prefix = f"   {continuation} "

                result_connector = self.symbols.get("⎿")
                tool_line = f"{tool_prefix}{result_connector}  {last_tool}"
                lines.append(self.colors.dim(tool_line))

        return lines

    def render_file_tree(self, files: list[str], base_path: str = "") -> list[str]:
        """Render file tree structure"""
        lines = []

        for i, file_path in enumerate(files):
            is_last = i == len(files) - 1

            # Remove base path if present
            display_path = file_path
            if base_path and file_path.startswith(base_path):
                display_path = file_path[len(base_path):].lstrip("/")

            # Connector
            if is_last:
                connector = self.symbols.get("└")
            else:
                connector = self.symbols.get("├")

            prefix = f"{connector}─ "
            lines.append(f"{self.colors.dim(prefix)}{self.colors.cyan(display_path)}")

        return lines
