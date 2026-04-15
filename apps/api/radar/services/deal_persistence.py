"""
Analyze all scraped properties and persist DealAnalysis rows to the database.

Runs all 12 scenario combinations (2 renovation × 3 scenario × 2 financing mode)
per property and writes them to deal_analyses, replacing any stale results.
"""
from decimal import Decimal
from unicodedata import normalize as _unorm

from sqlalchemy.orm import Session

from radar.models.analysis import DealAnalysis as DealAnalysisModel
from radar.models.listing import SourceListing
from radar.models.market import NeighborhoodStat
from radar.models.property import Property
from radar.schemas import InvestorProfile, MarketStatsInput, PropertyInput
from radar.services.analyzer import analyze_property


# City-level market fallbacks for when neighborhood_stats table is empty.
# These are conservative estimates for the Floripa metro region.
_CITY_FALLBACKS: dict[str, MarketStatsInput] = {
    "florianopolis": MarketStatsInput(
        price_per_sqm_p50=Decimal("8800"),
        price_per_sqm_p65=Decimal("9700"),
        liquidity_score=Decimal("7"),
    ),
    "sao jose": MarketStatsInput(
        price_per_sqm_p50=Decimal("7200"),
        price_per_sqm_p65=Decimal("8000"),
        liquidity_score=Decimal("7"),
    ),
    "palhoca": MarketStatsInput(
        price_per_sqm_p50=Decimal("5800"),
        price_per_sqm_p65=Decimal("6500"),
        liquidity_score=Decimal("6"),
    ),
    "biguacu": MarketStatsInput(
        price_per_sqm_p50=Decimal("5200"),
        price_per_sqm_p65=Decimal("5900"),
        liquidity_score=Decimal("5"),
    ),
}

_GLOBAL_FALLBACK = MarketStatsInput(
    price_per_sqm_p50=Decimal("7000"),
    price_per_sqm_p65=Decimal("7800"),
    liquidity_score=Decimal("5"),
)


def _ascii(value: str) -> str:
    return _unorm("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")


def _get_market(db: Session, city: str, neighborhood: str, property_type: str) -> MarketStatsInput:
    stat = (
        db.query(NeighborhoodStat)
        .filter(
            NeighborhoodStat.city == city,
            NeighborhoodStat.neighborhood == neighborhood,
            NeighborhoodStat.property_type == property_type,
        )
        .one_or_none()
    )
    if stat and stat.price_per_sqm_p50 and stat.price_per_sqm_p65:
        return MarketStatsInput(
            price_per_sqm_p50=stat.price_per_sqm_p50,
            price_per_sqm_p65=stat.price_per_sqm_p65,
            liquidity_score=stat.liquidity_score or Decimal("5"),
        )
    return _CITY_FALLBACKS.get(_ascii(city), _GLOBAL_FALLBACK)


def _risk_flags(prop: Property, listing: SourceListing) -> list[str]:
    flags: list[str] = []
    if getattr(listing, "auction_detail", None) and listing.auction_detail.is_occupied:
        flags.append("occupied")
    if getattr(listing, "auction_detail", None) and not listing.auction_detail.edital_url:
        flags.append("missing_edital")
    if not prop.area_privative:
        flags.append("missing_area")
    return flags


def _build_property_input(prop: Property, listing: SourceListing) -> PropertyInput:
    return PropertyInput(
        property_id=str(prop.id),
        title=listing.title or f"{prop.property_type.title()} em {prop.neighborhood}",
        property_type=prop.property_type,
        category=prop.category,
        city=prop.city,
        neighborhood=prop.neighborhood,
        purchase_price=listing.price or Decimal("1"),
        area_privative=prop.area_privative or Decimal("50"),
        condo_fee=listing.condo_fee or Decimal("0"),
        iptu_yearly=listing.iptu_yearly or Decimal("0"),
        bedrooms=prop.bedrooms,
        bathrooms=prop.bathrooms,
        parking_spots=prop.parking_spots,
        has_elevator=prop.has_elevator,
        floor=prop.floor,
        source_name=listing.source,
        source_url=listing.source_url,
        is_demo=False,
        risk_flags=_risk_flags(prop, listing),
    )


def analyze_and_persist_all(db: Session, investor: InvestorProfile | None = None) -> dict:
    """
    Iterate every property that has at least one active listing with a price,
    compute all 12 analysis combinations and persist to deal_analyses.

    Returns a stats dict: {"processed": N, "skipped": N}.
    """
    if investor is None:
        investor = InvestorProfile()

    properties = (
        db.query(Property)
        .join(SourceListing, SourceListing.property_id == Property.id)
        .filter(
            SourceListing.is_active.is_(True),
            SourceListing.price.isnot(None),
            SourceListing.price > 0,
        )
        .distinct()
        .all()
    )

    processed = skipped = 0

    for prop in properties:
        # Pick the active listing with the lowest price as the canonical input
        listing = (
            db.query(SourceListing)
            .filter(
                SourceListing.property_id == prop.id,
                SourceListing.is_active.is_(True),
                SourceListing.price.isnot(None),
            )
            .order_by(SourceListing.price.asc())
            .first()
        )
        if not listing or not prop.area_privative or prop.area_privative <= 0:
            skipped += 1
            continue

        prop_input = _build_property_input(prop, listing)
        market = _get_market(db, prop.city, prop.neighborhood, prop.property_type)

        # Remove stale analyses before recomputing
        db.query(DealAnalysisModel).filter(DealAnalysisModel.property_id == prop.id).delete()

        for renovation in ("light", "medium"):
            for scenario in ("conservative", "base", "optimistic"):
                for mode in ("cash", "financed"):
                    deal = analyze_property(
                        prop_input,
                        market,
                        investor,
                        renovation_level=renovation,  # type: ignore[arg-type]
                        scenario=scenario,
                        financing_mode=mode,
                    )
                    db.add(
                        DealAnalysisModel(
                            property_id=prop.id,
                            scenario=scenario,
                            financing_mode=mode,
                            purchase_price=deal.purchase_price,
                            estimated_market_value=deal.estimated_market_value,
                            estimated_resale_value=deal.estimated_resale_value,
                            renovation_level=renovation,
                            renovation_cost=deal.renovation_cost,
                            transaction_costs=deal.transaction_costs,
                            holding_costs=deal.holding_costs,
                            selling_costs=deal.selling_costs,
                            contingency=deal.contingency,
                            total_cost=deal.total_cost,
                            capital_required=deal.capital_required,
                            estimated_profit=deal.estimated_profit,
                            margin_pct=deal.margin_pct,
                            roi_pct=deal.roi_pct,
                            annualized_roi_pct=deal.annualized_roi_pct,
                            estimated_months=deal.estimated_months,
                            risk_level=deal.risk_level,
                            risk_flags=deal.risk_flags,
                            score=deal.score,
                            decision=deal.decision,
                            score_breakdown={k: float(v) for k, v in deal.score_breakdown.items()},
                        )
                    )

        db.commit()
        processed += 1

    return {"processed": processed, "skipped": skipped}
