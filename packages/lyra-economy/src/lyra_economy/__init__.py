"""Agent Economy Marketplace — agents trade services, buy/sell data, bid for resources.

The first-ever agent marketplace. Enables agents to:
- List services for sale (code review, testing, research, etc.)
- Buy services from other agents
- Bid for compute, data, and other resources
- Form economic specializations
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "ServiceListing",
    "ServiceOffer",
    "TradeResult",
    "AgentEconomy",
    "TokenWallet",
]


class ListingStatus(Enum):
    ACTIVE = auto()
    PENDING = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass
class ServiceListing:
    id: str
    agent_id: str
    service: str
    description: str
    price: float
    status: ListingStatus = ListingStatus.ACTIVE
    created_at: float = 0.0


@dataclass
class ServiceOffer:
    listing_id: str
    buyer_id: str
    amount: float
    accepted: bool = False


@dataclass
class TradeResult:
    listing_id: str
    buyer_id: str
    seller_id: str
    service: str
    price: float
    success: bool
    timestamp: float = 0.0


class TokenWallet:
    """Agent token wallet for economic participation."""

    def __init__(self, agent_id: str, initial_balance: float = 100.0):
        self.agent_id = agent_id
        self.balance = initial_balance
        self.transaction_log: list[dict[str, Any]] = []

    def spend(self, amount: float, reason: str) -> bool:
        if self.balance < amount:
            return False
        self.balance -= amount
        self.transaction_log.append({"type": "spend", "amount": amount, "reason": reason, "time": time.time()})
        return True

    def earn(self, amount: float, reason: str) -> None:
        self.balance += amount
        self.transaction_log.append({"type": "earn", "amount": amount, "reason": reason, "time": time.time()})

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "balance": self.balance,
            "transactions": len(self.transaction_log),
        }


class AgentEconomy:
    """Decentralized marketplace for agent services."""

    def __init__(self):
        self.listings: dict[str, ServiceListing] = {}
        self.wallets: dict[str, TokenWallet] = {}
        self.trades: list[TradeResult] = []
        self._listing_counter = 0

    def register_agent(self, agent_id: str, initial_balance: float = 100.0) -> TokenWallet:
        wallet = TokenWallet(agent_id, initial_balance)
        self.wallets[agent_id] = wallet
        return wallet

    def list_service(self, agent_id: str, service: str, description: str, price: float) -> Optional[ServiceListing]:
        if agent_id not in self.wallets:
            logger.warning(f"Agent {agent_id} not registered in economy")
            return None
        self._listing_counter += 1
        listing = ServiceListing(
            id=f"svc_{self._listing_counter}",
            agent_id=agent_id,
            service=service,
            description=description,
            price=price,
            created_at=time.time(),
        )
        self.listings[listing.id] = listing
        logger.info(f"Listed: {service} by {agent_id} for {price} tokens")
        return listing

    def search_services(self, query: str, max_price: Optional[float] = None) -> list[ServiceListing]:
        results = []
        query_lower = query.lower()
        for listing in self.listings.values():
            if listing.status != ListingStatus.ACTIVE:
                continue
            if query_lower in listing.service.lower() or query_lower in listing.description.lower():
                if max_price is None or listing.price <= max_price:
                    results.append(listing)
        return results

    def buy_service(self, listing_id: str, buyer_id: str) -> TradeResult:
        listing = self.listings.get(listing_id)
        if not listing or listing.status != ListingStatus.ACTIVE:
            return TradeResult(listing_id, buyer_id, "", "", 0, False)

        buyer_wallet = self.wallets.get(buyer_id)
        seller_wallet = self.wallets.get(listing.agent_id)

        if not buyer_wallet or not seller_wallet:
            return TradeResult(listing_id, buyer_id, listing.agent_id, listing.service, listing.price, False)

        if not buyer_wallet.spend(listing.price, f"Bought: {listing.service}"):
            return TradeResult(listing_id, buyer_id, listing.agent_id, listing.service, listing.price, False)

        seller_wallet.earn(listing.price, f"Sold: {listing.service}")
        listing.status = ListingStatus.COMPLETED

        result = TradeResult(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=listing.agent_id,
            service=listing.service,
            price=listing.price,
            success=True,
            timestamp=time.time(),
        )
        self.trades.append(result)
        return result

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "active_listings": sum(1 for l in self.listings.values() if l.status == ListingStatus.ACTIVE),
            "completed_trades": len(self.trades),
            "registered_agents": len(self.wallets),
            "total_listings": len(self.listings),
        }
