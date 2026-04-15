from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from radar.db import Base


class InvestorProfile(Base):
    __tablename__ = "investor_profile"
    __table_args__ = (CheckConstraint("id = 1", name="ck_investor_profile_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    max_capital: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("300000"))
    min_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("80000"))
    min_margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("30"))
    min_score: Mapped[int] = mapped_column(default=50)
    max_months: Mapped[int] = mapped_column(default=12)
    allow_financing: Mapped[bool] = mapped_column(default=True)
    default_entry_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("25"))
    interest_rate_yearly: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("11"))
    target_cities: Mapped[list] = mapped_column(
        JSONB,
        default=lambda: ["Florianópolis", "São José", "Palhoça", "Biguaçu"],
    )
