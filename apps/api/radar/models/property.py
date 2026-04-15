import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from radar.db import Base


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        Index("idx_properties_city_neigh", "city", "neighborhood"),
        Index("idx_properties_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    property_type: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    neighborhood: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str | None] = mapped_column(String)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    area_privative: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    area_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    bedrooms: Mapped[int | None]
    bathrooms: Mapped[int | None]
    parking_spots: Mapped[int | None]
    floor: Mapped[int | None]
    has_elevator: Mapped[bool | None]
    age_years: Mapped[int | None]
    condition: Mapped[str | None] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    source_listings = relationship("SourceListing", back_populates="property", cascade="all, delete-orphan")
    deal_analyses = relationship("DealAnalysis", back_populates="property", cascade="all, delete-orphan")
