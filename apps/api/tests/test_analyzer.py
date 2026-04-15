from decimal import Decimal

from radar.schemas import InvestorProfile, MarketStatsInput, PropertyInput
from radar.services.analyzer import analyze_property


def test_financed_analysis_keeps_capital_separate_from_total_cost():
    prop = PropertyInput(
        property_id="test-1",
        title="Apto teste",
        property_type="apartamento",
        category="bank_owned",
        city="Sao Jose",
        neighborhood="Kobrasol",
        purchase_price=Decimal("285000"),
        area_privative=Decimal("72"),
        condo_fee=Decimal("500"),
        iptu_yearly=Decimal("1200"),
    )
    market = MarketStatsInput(
        price_per_sqm_p50=Decimal("7600"),
        price_per_sqm_p65=Decimal("8300"),
        liquidity_score=Decimal("8"),
    )

    deal = analyze_property(prop, market, InvestorProfile(), financing_mode="financed")

    assert deal.capital_required < deal.total_cost
    assert deal.score >= 0
