import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from radar.db import Base


class DealAnalysis(Base):
    __tablename__ = "deal_analyses"
    __table_args__ = (
        Index("idx_deal_analyses_score", "score"),
        Index("idx_deal_analyses_decision", "decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
    )
    scenario: Mapped[str] = mapped_column(String, nullable=False)
    financing_mode: Mapped[str] = mapped_column(String, nullable=False)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    estimated_market_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    estimated_resale_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    renovation_level: Mapped[str | None] = mapped_column(String)
    renovation_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    transaction_costs: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    holding_costs: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    selling_costs: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    contingency: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    capital_required: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    estimated_profit: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    roi_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    annualized_roi_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    estimated_months: Mapped[int | None]
    risk_level: Mapped[str | None] = mapped_column(String)
    risk_flags: Mapped[list | None] = mapped_column(JSONB)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    decision: Mapped[str | None] = mapped_column(String)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    property = relationship("Property", back_populates="deal_analyses")
