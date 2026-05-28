"""Hook registry - Built-in hook definitions"""


from .hook_manager import HookType


class HookRegistry:
    """Registry of built-in hooks"""

    def __init__(self):
        self.hooks: dict[str, dict] = {}

    def register_hook(self, name: str, hook_type: HookType, description: str,
                     handler: callable, enabled: bool = True):
        """Register a built-in hook"""
        self.hooks[name] = {
            "type": hook_type,
            "description": description,
            "handler": handler,
            "enabled": enabled,
        }

    def get_hook(self, name: str) -> dict:
        """Get hook definition"""
        return self.hooks.get(name)

    def list_hooks(self, hook_type: HookType = None) -> list[dict]:
        """List all hooks, optionally filtered by type"""
        if hook_type:
            return [
                {"name": name, **hook}
                for name, hook in self.hooks.items()
                if hook["type"] == hook_type
            ]
        return [{"name": name, **hook} for name, hook in self.hooks.items()]


# Global registry instance
_registry = HookRegistry()


def get_registry() -> HookRegistry:
    """Get global hook registry"""
    return _registry
