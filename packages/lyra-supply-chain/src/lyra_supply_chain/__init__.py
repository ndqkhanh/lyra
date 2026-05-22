"""Supply Chain & Logistics — inventory optimization, routing, demand forecasting."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any
logger = logging.getLogger(__name__)
__all__ = ["InventoryItem", "SupplyChainAgent"]

@dataclass
class InventoryItem: sku: str; quantity: int; reorder_point: int; lead_time_days: int

class SupplyChainAgent:
    def __init__(self): self.inventory: dict[str, InventoryItem] = {}; self.orders: list[dict] = []
    def add_item(self, sku: str, qty: int, reorder: int, lead: int) -> InventoryItem:
        i = InventoryItem(sku=sku, quantity=qty, reorder_point=reorder, lead_time_days=lead)
        self.inventory[sku] = i; return i
    def check_reorder(self) -> list[str]:
        return [sku for sku, i in self.inventory.items() if i.quantity <= i.reorder_point]
    def place_order(self, sku: str, qty: int) -> bool:
        if sku not in self.inventory: return False
        self.orders.append({"sku": sku, "qty": qty}); self.inventory[sku].quantity += qty; return True
    @property
    def stats(self) -> dict: return {"items": len(self.inventory), "orders": len(self.orders)}
