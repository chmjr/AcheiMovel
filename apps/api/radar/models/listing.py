import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from radar.db import Base


class SourceListing(Base):
    __tablename__ = "source_listings"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_source_listing_source_id"),
        Index("idx_source_listings_active", "is_active", "last_seen_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    condo_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    iptu_yearly: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    photos: Mapped[Any | None] = mapped_column(JSONB)
    raw_payload: Mapped[Any | None] = mapped_column(JSONB)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")

    property = relationship("Property", back_populates="source_listings")
    price_history = relationship("PriceHistory", back_populates="source_listing", cascade="all, delete-orphan")
    auction_detail = relationship("AuctionDetail", back_populates="source_listing", uselist=False)
    bank_owned_detail = relationship("BankOwnedDetail", back_populates="source_listing", uselist=False)


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_listings.id", ondelete="CASCADE"),
    )
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_listing = relationship("SourceListing", back_populates="price_history")


class AuctionDetail(Base):
    __tablename__ = "auction_details"

    source_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_listings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    auction_type: Mapped[str | None] = mapped_column(String)
    auctioneer: Mapped[str | None] = mapped_column(String)
    appraisal_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    minimum_bid: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    is_occupied: Mapped[bool | None]
    auction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    second_auction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    matricula: Mapped[str | None] = mapped_column(String)
    debts_disclosed: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    auctioneer_fee_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    edital_url: Mapped[str | None] = mapped_column(String)
    financeable: Mapped[bool | None]

    source_listing = relationship("SourceListing", back_populates="auction_detail")


class BankOwnedDetail(Base):
    __tablename__ = "bank_owned_details"

    source_listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_listings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bank: Mapped[str] = mapped_column(String, nullable=False)
    sale_modality: Mapped[str | None] = mapped_column(String)
    discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    financeable: Mapped[bool | None]
    fgts_allowed: Mapped[bool | None]
    minimum_entry_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    source_listing = relationship("SourceListing", back_populates="bank_owned_detail")
