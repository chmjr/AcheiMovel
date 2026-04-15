from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


Category = Literal["common", "bank_owned", "auction"]
FinancingMode = Literal["cash", "financed"]
RenovationLevel = Literal["light", "medium"]
RiskLevel = Literal["low", "medium", "high"]
Decision = Literal["discard", "monitor", "analyze", "priority", "immediate"]


class InvestorProfile(BaseModel):
    max_capital: Decimal = Decimal("300000")
    min_profit: Decimal = Decimal("80000")
    min_margin_pct: Decimal = Decimal("30")
    min_score: int = 50
    max_months: int = 12
    allow_financing: bool = True
    default_entry_pct: Decimal = Decimal("25")
    interest_rate_yearly: Decimal = Decimal("11")
    target_cities: list[str] = Field(
        default_factory=lambda: ["Florianopolis", "Sao Jose", "Palhoca", "Biguacu"]
    )


class PropertyInput(BaseModel):
    property_id: str
    title: str
    property_type: str
    category: Category
    city: str
    neighborhood: str
    purchase_price: Decimal
    area_privative: Decimal
    condo_fee: Decimal = Decimal("0")
    iptu_yearly: Decimal = Decimal("0")
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking_spots: int | None = None
    has_elevator: bool | None = None
    floor: int | None = None
    source_name: str = "Demonstração interna"
    source_url: str | None = None
    is_demo: bool = False
    risk_flags: list[str] = Field(default_factory=list)


class ManualPropertyCreate(BaseModel):
    title: str
    description: str | None = None
    property_type: str
    category: Category = "common"
    city: str
    neighborhood: str
    address: str | None = None
    purchase_price: Decimal
    area_privative: Decimal
    area_total: Decimal | None = None
    condo_fee: Decimal = Decimal("0")
    iptu_yearly: Decimal = Decimal("0")
    bedrooms: int | None = None
    bathrooms: int | None = None
    parking_spots: int | None = None
    floor: int | None = None
    has_elevator: bool | None = None
    age_years: int | None = None
    condition: str | None = None
    source_name: str = "Cadastro manual"
    source_url: str | None = None


class ManualPropertyResponse(BaseModel):
    property_id: str
    source_listing_id: str
    fingerprint: str
    title: str
    city: str
    neighborhood: str
    purchase_price: Decimal
    source_name: str


class MarketStatsInput(BaseModel):
    price_per_sqm_p50: Decimal
    price_per_sqm_p65: Decimal
    liquidity_score: Decimal = Decimal("5")


class DealAnalysis(BaseModel):
    property_id: str
    scenario: Literal["conservative", "base", "optimistic"]
    financing_mode: FinancingMode
    purchase_price: Decimal
    estimated_market_value: Decimal
    estimated_resale_value: Decimal
    renovation_level: RenovationLevel
    renovation_cost: Decimal
    transaction_costs: Decimal
    holding_costs: Decimal
    selling_costs: Decimal
    contingency: Decimal
    total_cost: Decimal
    capital_required: Decimal
    estimated_profit: Decimal
    margin_pct: Decimal
    roi_pct: Decimal
    annualized_roi_pct: Decimal
    estimated_months: int
    risk_level: RiskLevel
    risk_flags: list[str]
    score: Decimal
    decision: Decision
    score_breakdown: dict[str, Decimal]


class DealListItem(BaseModel):
    property_id: str
    title: str
    score: Decimal
    decision: Decision
    category: Category
    city: str
    neighborhood: str
    property_type: str
    purchase_price: Decimal
    estimated_market_value: Decimal
    estimated_resale_value: Decimal
    renovation_cost: Decimal
    total_cost: Decimal
    capital_required: Decimal
    estimated_profit: Decimal
    margin_pct: Decimal
    roi_pct: Decimal
    annualized_roi_pct: Decimal
    estimated_months: int
    risk_level: RiskLevel
    source_name: str
    primary_source_url: str | None = None
    is_demo: bool = False
    source_count: int = 1


class DealListResponse(BaseModel):
    items: list[DealListItem]
    total: int
    facets: dict[str, dict[str, int]]
