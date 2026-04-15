from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from radar.db import Base


class NeighborhoodStat(Base):
    __tablename__ = "neighborhood_stats"
    __table_args__ = (
        UniqueConstraint("city", "neighborhood", "property_type", name="uq_neighborhood_stats_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str] = mapped_column(String, nullable=False)
    neighborhood: Mapped[str] = mapped_column(String, nullable=False)
    property_type: Mapped[str] = mapped_column(String, nullable=False)
    sample_size: Mapped[int] = mapped_column(nullable=False)
    price_per_sqm_p25: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_per_sqm_p50: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_per_sqm_p65: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_per_sqm_p75: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    avg_days_listed: Mapped[int | None]
    liquidity_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
