"""Loop manager - Core loop orchestration"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class LoopConfig:
    """Loop configuration"""
    name: str
    type: str  # "sequential" or "continuous"
    steps: list[str]
    max_iterations: int = 10
    timeout: int = 3600  # seconds
    quality_gate: bool = True


class LoopManager:
    """Manages autonomous loops"""

    def __init__(self, loops_dir: Path | None = None):
        self.loops_dir = loops_dir or Path.home() / ".lyra" / "loops"
        self.loops_dir.mkdir(parents=True, exist_ok=True)
        self.active_loops = {}

    def create_loop(self, config: LoopConfig) -> str:
        """Create a new loop"""
        loop_id = f"{config.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Save config
        config_file = self.loops_dir / f"{loop_id}.json"
        config_dict = {
            "name": config.name,
            "type": config.type,
            "steps": config.steps,
            "max_iterations": config.max_iterations,
            "timeout": config.timeout,
            "quality_gate": config.quality_gate,
            "created_at": datetime.now().isoformat(),
            "status": "created"
        }

        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2)

        return loop_id

    def start_loop(self, loop_id: str):
        """Start a loop"""
        config_file = self.loops_dir / f"{loop_id}.json"
        if not config_file.exists():
            raise ValueError(f"Loop {loop_id} not found")

        with open(config_file) as f:
            config = json.load(f)

        config["status"] = "running"
        config["started_at"] = datetime.now().isoformat()

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

        self.active_loops[loop_id] = config

    def stop_loop(self, loop_id: str):
        """Stop a loop"""
        config_file = self.loops_dir / f"{loop_id}.json"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)

            config["status"] = "stopped"
            config["stopped_at"] = datetime.now().isoformat()

            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)

        if loop_id in self.active_loops:
            del self.active_loops[loop_id]

    def get_loop_status(self, loop_id: str) -> dict:
        """Get loop status"""
        config_file = self.loops_dir / f"{loop_id}.json"
        if not config_file.exists():
            return {"status": "not_found"}

        with open(config_file) as f:
            return json.load(f)

    def list_loops(self) -> list[dict]:
        """List all loops"""
        loops = []
        for config_file in self.loops_dir.glob("*.json"):
            with open(config_file) as f:
                config = json.load(f)
                config["id"] = config_file.stem
                loops.append(config)
        return loops


# Global loop manager
_loop_manager: LoopManager | None = None


def get_loop_manager() -> LoopManager:
    """Get or create global loop manager"""
    global _loop_manager
    if _loop_manager is None:
        _loop_manager = LoopManager()
    return _loop_manager
