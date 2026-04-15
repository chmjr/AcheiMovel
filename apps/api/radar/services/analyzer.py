from decimal import Decimal

from radar.schemas import DealAnalysis, InvestorProfile, MarketStatsInput, PropertyInput, RenovationLevel
from radar.services.renovation import estimate_renovation_cost
from radar.services.scoring import compute_score, decide


ITBI_PCT = Decimal("0.03")
CARTORIO_PCT = Decimal("0.015")
SELLING_COST_PCT = Decimal("0.06")
FINANCING_COST_PCT = Decimal("0.04")
CONTINGENCY_PCT = Decimal("0.12")


def analyze_property(
    prop: PropertyInput,
    market: MarketStatsInput,
    investor: InvestorProfile,
    renovation_level: RenovationLevel = "medium",
    scenario: str = "base",
    financing_mode: str = "financed",
) -> DealAnalysis:
    months = _scenario_months(scenario)
    resale_value = _estimate_resale_value(prop, market, renovation_level, scenario)
    market_value = (prop.area_privative * market.price_per_sqm_p50).quantize(Decimal("0.01"))
    renovation_cost = estimate_renovation_cost(prop.area_privative, renovation_level)

    transaction_costs = (prop.purchase_price * (ITBI_PCT + CARTORIO_PCT)).quantize(Decimal("0.01"))
    selling_costs = (resale_value * SELLING_COST_PCT).quantize(Decimal("0.01"))
    holding_costs = _holding_costs(prop, investor, financing_mode, months)
    contingency = ((renovation_cost + transaction_costs + holding_costs) * CONTINGENCY_PCT).quantize(
        Decimal("0.01")
    )
    total_cost = (
        prop.purchase_price
        + transaction_costs
        + renovation_cost
        + holding_costs
        + selling_costs
        + contingency
    ).quantize(Decimal("0.01"))
    capital_required = _capital_required(
        prop=prop,
        investor=investor,
        financing_mode=financing_mode,
        renovation_cost=renovation_cost,
        transaction_costs=transaction_costs,
        holding_costs=holding_costs,
        contingency=contingency,
    )
    profit = (resale_value - total_cost).quantize(Decimal("0.01"))
    margin_pct = _pct(profit, resale_value)
    roi_pct = _pct(profit, capital_required)
    annualized_roi_pct = _annualize(roi_pct, months)
    risk_level = _risk_level(prop)

    deal = DealAnalysis(
        property_id=prop.property_id,
        scenario=scenario,
        financing_mode=financing_mode,
        purchase_price=prop.purchase_price,
        estimated_market_value=market_value,
        estimated_resale_value=resale_value,
        renovation_level=renovation_level,
        renovation_cost=renovation_cost,
        transaction_costs=transaction_costs,
        holding_costs=holding_costs,
        selling_costs=selling_costs,
        contingency=contingency,
        total_cost=total_cost,
        capital_required=capital_required,
        estimated_profit=profit,
        margin_pct=margin_pct,
        roi_pct=roi_pct,
        annualized_roi_pct=annualized_roi_pct,
        estimated_months=months,
        risk_level=risk_level,
        risk_flags=prop.risk_flags,
        score=Decimal("0"),
        decision="discard",
        score_breakdown={},
    )
    score, breakdown = compute_score(deal, investor, market.liquidity_score)
    deal.score = score
    deal.score_breakdown = breakdown
    deal.decision = decide(score, margin_pct)
    return deal


def _estimate_resale_value(
    prop: PropertyInput,
    market: MarketStatsInput,
    renovation_level: RenovationLevel,
    scenario: str,
) -> Decimal:
    base_sqm = market.price_per_sqm_p65 if scenario == "optimistic" else market.price_per_sqm_p50
    multiplier = Decimal("1.10") if renovation_level == "medium" else Decimal("1.05")
    if prop.parking_spots == 0:
        multiplier *= Decimal("0.93")
    if prop.floor and prop.floor >= 4 and prop.has_elevator is False:
        multiplier *= Decimal("0.92")
    if scenario == "conservative":
        multiplier *= Decimal("0.95")
    return (prop.area_privative * base_sqm * multiplier).quantize(Decimal("0.01"))


def _holding_costs(
    prop: PropertyInput,
    investor: InvestorProfile,
    financing_mode: str,
    months: int,
) -> Decimal:
    iptu_monthly = prop.iptu_yearly / Decimal("12")
    carrying = (prop.condo_fee + iptu_monthly) * months
    if financing_mode == "cash":
        capital_cost = (
            prop.purchase_price
            * (investor.interest_rate_yearly / Decimal("100"))
            / Decimal("12")
            * months
        )
        return (carrying + capital_cost).quantize(Decimal("0.01"))

    financed_amount = prop.purchase_price * (Decimal("1") - investor.default_entry_pct / Decimal("100"))
    monthly_rate = investor.interest_rate_yearly / Decimal("100") / Decimal("12")
    holding_finance = financed_amount * monthly_rate * months
    return (carrying + holding_finance).quantize(Decimal("0.01"))


def _capital_required(
    prop: PropertyInput,
    investor: InvestorProfile,
    financing_mode: str,
    renovation_cost: Decimal,
    transaction_costs: Decimal,
    holding_costs: Decimal,
    contingency: Decimal,
) -> Decimal:
    if financing_mode == "cash":
        purchase_cash = prop.purchase_price
        financing_costs = Decimal("0")
    else:
        purchase_cash = prop.purchase_price * investor.default_entry_pct / Decimal("100")
        financing_costs = prop.purchase_price * FINANCING_COST_PCT

    return (
        purchase_cash
        + financing_costs
        + transaction_costs
        + renovation_cost
        + holding_costs
        + contingency
    ).quantize(Decimal("0.01"))


def _risk_level(prop: PropertyInput) -> str:
    if any(flag in prop.risk_flags for flag in ["occupied", "missing_edital", "missing_matricula"]):
        return "high"
    if prop.category == "auction" or prop.risk_flags:
        return "medium"
    return "low"


def _scenario_months(scenario: str) -> int:
    return {"conservative": 12, "base": 10, "optimistic": 6}.get(scenario, 10)


def _pct(value: Decimal, base: Decimal) -> Decimal:
    if base == 0:
        return Decimal("0")
    return (value / base * Decimal("100")).quantize(Decimal("0.01"))


def _annualize(roi_pct: Decimal, months: int) -> Decimal:
    roi = float(roi_pct / Decimal("100"))
    annualized = ((1 + roi) ** (12 / months) - 1) * 100
    return Decimal(str(annualized)).quantize(Decimal("0.01"))
