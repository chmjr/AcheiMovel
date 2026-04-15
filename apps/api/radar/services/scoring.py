from decimal import Decimal

from radar.schemas import DealAnalysis, InvestorProfile


def compute_score(
    deal: DealAnalysis,
    investor: InvestorProfile,
    liquidity_score: Decimal,
) -> tuple[Decimal, dict[str, Decimal]]:
    breakdown: dict[str, Decimal] = {}

    discount = Decimal("0")
    if deal.estimated_market_value > 0:
        discount = (deal.estimated_market_value - deal.purchase_price) / deal.estimated_market_value

    if discount >= Decimal("0.30"):
        breakdown["discount"] = Decimal("30")
    elif discount >= Decimal("0.20"):
        breakdown["discount"] = Decimal("20")
    elif discount >= Decimal("0.10"):
        breakdown["discount"] = Decimal("10")
    else:
        breakdown["discount"] = Decimal("0")

    if deal.margin_pct >= Decimal("35"):
        breakdown["margin"] = Decimal("25")
    elif deal.margin_pct >= Decimal("30"):
        breakdown["margin"] = Decimal("20")
    elif deal.margin_pct >= Decimal("25"):
        breakdown["margin"] = Decimal("12")
    elif deal.margin_pct >= Decimal("15"):
        breakdown["margin"] = Decimal("6")
    else:
        breakdown["margin"] = Decimal("0")

    breakdown["liquidity"] = min(Decimal("15"), liquidity_score * Decimal("1.5"))
    breakdown["risk"] = {"low": Decimal("10"), "medium": Decimal("5"), "high": Decimal("0")}[deal.risk_level]
    breakdown["renovation"] = {"light": Decimal("10"), "medium": Decimal("6")}[deal.renovation_level]
    breakdown["data_quality"] = _score_data_quality(deal)

    capital_ratio = deal.capital_required / investor.max_capital if investor.max_capital else Decimal("99")
    if capital_ratio <= Decimal("0.6"):
        breakdown["capital_fit"] = Decimal("5")
    elif capital_ratio <= Decimal("0.8"):
        breakdown["capital_fit"] = Decimal("4")
    elif capital_ratio <= Decimal("1"):
        breakdown["capital_fit"] = Decimal("2")
    else:
        breakdown["capital_fit"] = Decimal("0")

    return sum(breakdown.values(), Decimal("0")).quantize(Decimal("0.01")), breakdown


def decide(score: Decimal, margin_pct: Decimal) -> str:
    if score < Decimal("50") or margin_pct < Decimal("30"):
        return "discard"
    if score <= Decimal("65"):
        return "monitor"
    if score <= Decimal("80"):
        return "analyze"
    if score <= Decimal("90"):
        return "priority"
    return "immediate"


def _score_data_quality(deal: DealAnalysis) -> Decimal:
    points = Decimal("0")
    if deal.estimated_market_value > 0:
        points += Decimal("1")
    if deal.estimated_resale_value > 0:
        points += Decimal("1")
    if deal.purchase_price > 0:
        points += Decimal("1")
    if deal.renovation_cost > 0:
        points += Decimal("1")
    if deal.risk_flags is not None:
        points += Decimal("1")
    return points
