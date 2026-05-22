"""Spatial Reasoning Agent — 3D understanding, environment mapping, navigation."""
from __future__ import annotations
import logging, math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)
__all__ = ["Point3D", "BoundingBox", "SpatialAgent"]

@dataclass
class Point3D: x: float = 0.0; y: float = 0.0; z: float = 0.0

@dataclass
class BoundingBox: min_x: float; min_y: float; min_z: float; max_x: float; max_y: float; max_z: float

class SpatialAgent:
    def __init__(self):
        self.objects: dict[str, BoundingBox] = {}
        self._pos = Point3D()

    def register_object(self, name: str, bbox: BoundingBox) -> None:
        self.objects[name] = bbox

    def distance(self, obj_a: str, obj_b: str) -> Optional[float]:
        a, b = self.objects.get(obj_a), self.objects.get(obj_b)
        if not a or not b: return None
        return math.sqrt((a.max_x - b.min_x)**2 + (a.max_y - b.min_y)**2 + (a.max_z - b.min_z)**2)

    def move_to(self, x: float, y: float, z: float) -> None:
        self._pos = Point3D(x, y, z)

    @property
    def position(self) -> Point3D: return self._pos
