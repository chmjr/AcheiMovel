from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import AsyncIterator, Any

from sqlalchemy.orm import Session


@dataclass
class RawListing:
    source: str
    source_id: str
    source_url: str
    title: str
    description: str | None
    price: Decimal | None
    condo_fee: Decimal | None
    iptu_yearly: Decimal | None
    city: str
    neighborhood: str | None
    address: str | None
    property_type: str
    area_privative: Decimal | None
    bedrooms: int | None
    bathrooms: int | None
    parking_spots: int | None
    photos: list[str] = field(default_factory=list)
    listed_at: str | None = None
    raw_payload: dict = field(default_factory=dict)
    auction_data: dict | None = None
    bank_data: dict | None = None


class BaseScraper(ABC):
    source: str
    category: str

    @abstractmethod
    async def discover(self) -> AsyncIterator[str]:
        """Yield listing URLs for this source."""
        raise NotImplementedError

    @abstractmethod
    async def parse(self, url: str) -> RawListing | None:
        """Parse one listing URL into normalized raw data."""
        raise NotImplementedError

    async def run(self, db: Session) -> dict[str, Any]:
        from radar.services.ingestion import persist_raw_listing

        stats: dict[str, Any] = {
            "collected": 0,
            "parsed": 0,
            "new": 0,
            "updated": 0,
            "errors": 0,
            "error_messages": [],
        }
        async for url in self.discover():
            stats["collected"] += 1
            try:
                listing = await self.parse(url)
                if listing:
                    stats["parsed"] += 1
                    status = persist_raw_listing(db, listing)
                    if status in {"new", "updated"}:
                        stats[status] += 1
            except Exception as exc:
                db.rollback()
                stats["errors"] += 1
                stats["error_messages"].append(str(exc))
        return stats
