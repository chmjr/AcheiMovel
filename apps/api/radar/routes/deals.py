from decimal import Decimal
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, joinedload

from radar.auth import require_token
from radar.db import get_db
from radar.models.analysis import DealAnalysis as DealAnalysisModel
from radar.models.listing import SourceListing
from radar.models.property import Property
from radar.schemas import DealListItem, DealListResponse, InvestorProfile, MarketStatsInput, PropertyInput
from radar.services.analyzer import analyze_property

router = APIRouter(prefix="/deals", tags=["deals"], dependencies=[Depends(require_token)])


# ---------------------------------------------------------------------------
# Demo fallback — shown when the database contains no real analyses yet
# ---------------------------------------------------------------------------

_DEMO_PROPERTIES = [
    PropertyInput(
        property_id="demo-kobrasol-001",
        title="Apartamento antigo com vaga no Kobrasol",
        property_type="apartamento",
        category="bank_owned",
        city="Sao Jose",
        neighborhood="Kobrasol",
        purchase_price=Decimal("220000"),
        area_privative=Decimal("72"),
        condo_fee=Decimal("520"),
        iptu_yearly=Decimal("1200"),
        bedrooms=2,
        bathrooms=1,
        parking_spots=1,
        has_elevator=True,
        floor=3,
        source_name="Demonstração interna",
        source_url=None,
        is_demo=True,
    ),
    PropertyInput(
        property_id="demo-centro-002",
        title="Kitnet no Centro com reforma leve",
        property_type="apartamento",
        category="common",
        city="Florianopolis",
        neighborhood="Centro",
        purchase_price=Decimal("260000"),
        area_privative=Decimal("38"),
        condo_fee=Decimal("430"),
        iptu_yearly=Decimal("900"),
        bedrooms=1,
        bathrooms=1,
        parking_spots=0,
        has_elevator=True,
        floor=6,
        source_name="Demonstração interna",
        source_url=None,
        is_demo=True,
    ),
]

_DEMO_MARKET: dict[tuple[str, str, str], MarketStatsInput] = {
    ("Sao Jose", "Kobrasol", "apartamento"): MarketStatsInput(
        price_per_sqm_p50=Decimal("7600"),
        price_per_sqm_p65=Decimal("8300"),
        liquidity_score=Decimal("8"),
    ),
    ("Florianopolis", "Centro", "apartamento"): MarketStatsInput(
        price_per_sqm_p50=Decimal("9300"),
        price_per_sqm_p65=Decimal("10200"),
        liquidity_score=Decimal("7"),
    ),
}


def _demo_items(min_score: Decimal, max_capital: Decimal, city: str | None, category: str | None) -> list[DealListItem]:
    investor = InvestorProfile(max_capital=max_capital)
    items: list[DealListItem] = []
    for prop in _DEMO_PROPERTIES:
        if city and prop.city != city:
            continue
        if category and prop.category != category:
            continue
        market = _DEMO_MARKET[(prop.city, prop.neighborhood, prop.property_type)]
        deal = analyze_property(prop, market, investor, renovation_level="medium")
        if deal.score < min_score or deal.decision == "discard":
            continue
        items.append(
            DealListItem(
                property_id=prop.property_id,
                title=prop.title,
                score=deal.score,
                decision=deal.decision,
                category=prop.category,
                city=prop.city,
                neighborhood=prop.neighborhood,
                property_type=prop.property_type,
                purchase_price=deal.purchase_price,
                estimated_market_value=deal.estimated_market_value,
                estimated_resale_value=deal.estimated_resale_value,
                renovation_cost=deal.renovation_cost,
                total_cost=deal.total_cost,
                capital_required=deal.capital_required,
                estimated_profit=deal.estimated_profit,
                margin_pct=deal.margin_pct,
                roi_pct=deal.roi_pct,
                annualized_roi_pct=deal.annualized_roi_pct,
                estimated_months=deal.estimated_months,
                risk_level=deal.risk_level,
                source_name=prop.source_name,
                primary_source_url=prop.source_url,
                is_demo=True,
                source_count=1,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Helpers for DB-backed responses
# ---------------------------------------------------------------------------

def _best_listing(prop: Property) -> SourceListing | None:
    """Return the active listing with the lowest price for a property."""
    active = [l for l in prop.source_listings if l.is_active and l.price]
    if not active:
        return None
    return min(active, key=lambda l: l.price)  # type: ignore[arg-type]


def _to_deal_list_item(analysis: DealAnalysisModel, prop: Property, listing: SourceListing | None) -> DealListItem:
    source_count = sum(1 for l in prop.source_listings if l.is_active)
    return DealListItem(
        property_id=str(prop.id),
        title=(listing.title if listing else None) or f"{prop.property_type.title()} em {prop.neighborhood}",
        score=analysis.score or Decimal("0"),
        decision=analysis.decision or "discard",
        category=prop.category,
        city=prop.city,
        neighborhood=prop.neighborhood,
        property_type=prop.property_type,
        purchase_price=analysis.purchase_price or Decimal("0"),
        estimated_market_value=analysis.estimated_market_value or Decimal("0"),
        estimated_resale_value=analysis.estimated_resale_value or Decimal("0"),
        renovation_cost=analysis.renovation_cost or Decimal("0"),
        total_cost=analysis.total_cost or Decimal("0"),
        capital_required=analysis.capital_required or Decimal("0"),
        estimated_profit=analysis.estimated_profit or Decimal("0"),
        margin_pct=analysis.margin_pct or Decimal("0"),
        roi_pct=analysis.roi_pct or Decimal("0"),
        annualized_roi_pct=analysis.annualized_roi_pct or Decimal("0"),
        estimated_months=analysis.estimated_months or 10,
        risk_level=analysis.risk_level or "medium",
        source_name=listing.source if listing else "coleta",
        primary_source_url=listing.source_url if listing else None,
        is_demo=False,
        source_count=source_count,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=DealListResponse)
async def list_deals(
    db: Session = Depends(get_db),
    min_score: Decimal = Query(default=Decimal("50")),
    max_capital: Decimal = Query(default=Decimal("300000")),
    city: str | None = None,
    category: str | None = None,
    order_by: str = Query(default="score"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> DealListResponse:
    # Query the canonical view: base scenario, financed, medium renovation
    q = (
        db.query(DealAnalysisModel)
        .options(
            joinedload(DealAnalysisModel.property).joinedload(Property.source_listings)
        )
        .join(Property, Property.id == DealAnalysisModel.property_id)
        .filter(
            DealAnalysisModel.scenario == "base",
            DealAnalysisModel.financing_mode == "financed",
            DealAnalysisModel.renovation_level == "medium",
            DealAnalysisModel.score >= min_score,
            DealAnalysisModel.decision != "discard",
            DealAnalysisModel.capital_required <= max_capital,
        )
    )
    if city:
        q = q.filter(Property.city == city)
    if category:
        q = q.filter(Property.category == category)

    analyses = q.all()

    # Fall back to demo data when the database has no real analyses yet
    if not analyses:
        items = _demo_items(min_score, max_capital, city, category)
        _sort(items, order_by)
        page = items[offset: offset + limit]
        return DealListResponse(
            items=page,
            total=len(items),
            facets={"by_category": _facet(items, "category"), "by_city": _facet(items, "city")},
        )

    items = [_to_deal_list_item(a, a.property, _best_listing(a.property)) for a in analyses]
    _sort(items, order_by)
    page = items[offset: offset + limit]
    return DealListResponse(
        items=page,
        total=len(items),
        facets={"by_category": _facet(items, "category"), "by_city": _facet(items, "city")},
    )


@router.get("/{property_id}")
async def get_deal(property_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    # Handle demo IDs without hitting the DB
    if property_id.startswith("demo-"):
        return _demo_detail(property_id)

    try:
        pid = uuid.UUID(property_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    prop = (
        db.query(Property)
        .options(joinedload(Property.source_listings))
        .filter(Property.id == pid)
        .one_or_none()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    analyses = (
        db.query(DealAnalysisModel)
        .filter(DealAnalysisModel.property_id == pid)
        .order_by(DealAnalysisModel.score.desc())
        .all()
    )

    listing = _best_listing(prop)
    return {
        "property": {
            "property_id": str(prop.id),
            "title": (listing.title if listing else None) or f"{prop.property_type.title()} em {prop.neighborhood}",
            "city": prop.city,
            "neighborhood": prop.neighborhood,
            "property_type": prop.property_type,
            "category": prop.category,
            "area_privative": str(prop.area_privative) if prop.area_privative else None,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "parking_spots": prop.parking_spots,
            "floor": prop.floor,
            "has_elevator": prop.has_elevator,
            "source_name": listing.source if listing else "coleta",
            "source_url": listing.source_url if listing else None,
            "source_count": sum(1 for l in prop.source_listings if l.is_active),
            "is_demo": False,
        },
        "analyses": [
            {
                "scenario": a.scenario,
                "financing_mode": a.financing_mode,
                "renovation_level": a.renovation_level,
                "purchase_price": str(a.purchase_price),
                "estimated_market_value": str(a.estimated_market_value),
                "estimated_resale_value": str(a.estimated_resale_value),
                "renovation_cost": str(a.renovation_cost),
                "transaction_costs": str(a.transaction_costs),
                "holding_costs": str(a.holding_costs),
                "selling_costs": str(a.selling_costs),
                "contingency": str(a.contingency),
                "total_cost": str(a.total_cost),
                "capital_required": str(a.capital_required),
                "estimated_profit": str(a.estimated_profit),
                "margin_pct": str(a.margin_pct),
                "roi_pct": str(a.roi_pct),
                "annualized_roi_pct": str(a.annualized_roi_pct),
                "estimated_months": a.estimated_months,
                "risk_level": a.risk_level,
                "risk_flags": a.risk_flags or [],
                "score": str(a.score),
                "decision": a.decision,
                "score_breakdown": a.score_breakdown or {},
            }
            for a in analyses
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _demo_detail(property_id: str) -> dict[str, Any]:
    investor = InvestorProfile()
    prop = next((p for p in _DEMO_PROPERTIES if p.property_id == property_id), None)
    if not prop:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    market = _DEMO_MARKET[(prop.city, prop.neighborhood, prop.property_type)]
    analyses = [
        analyze_property(prop, market, investor, renovation_level=r, scenario=s, financing_mode=m)
        for r in ("light", "medium")
        for s in ("conservative", "base", "optimistic")
        for m in ("cash", "financed")
    ]
    return {
        "property": {
            "property_id": prop.property_id,
            "title": prop.title,
            "city": prop.city,
            "neighborhood": prop.neighborhood,
            "property_type": prop.property_type,
            "category": prop.category,
            "area_privative": str(prop.area_privative),
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "parking_spots": prop.parking_spots,
            "floor": prop.floor,
            "has_elevator": prop.has_elevator,
            "source_name": prop.source_name,
            "source_url": prop.source_url,
            "source_count": 1,
            "is_demo": True,
        },
        "analyses": [
            {
                "scenario": a.scenario,
                "financing_mode": a.financing_mode,
                "renovation_level": a.renovation_level,
                "purchase_price": str(a.purchase_price),
                "estimated_market_value": str(a.estimated_market_value),
                "estimated_resale_value": str(a.estimated_resale_value),
                "renovation_cost": str(a.renovation_cost),
                "transaction_costs": str(a.transaction_costs),
                "holding_costs": str(a.holding_costs),
                "selling_costs": str(a.selling_costs),
                "contingency": str(a.contingency),
                "total_cost": str(a.total_cost),
                "capital_required": str(a.capital_required),
                "estimated_profit": str(a.estimated_profit),
                "margin_pct": str(a.margin_pct),
                "roi_pct": str(a.roi_pct),
                "annualized_roi_pct": str(a.annualized_roi_pct),
                "estimated_months": a.estimated_months,
                "risk_level": a.risk_level,
                "risk_flags": a.risk_flags,
                "score": str(a.score),
                "decision": a.decision,
                "score_breakdown": {k: float(v) for k, v in a.score_breakdown.items()},
            }
            for a in analyses
        ],
    }


_SORTERS: dict[str, Any] = {
    "score": lambda item: item.score,
    "profit": lambda item: item.estimated_profit,
    "annualized_roi": lambda item: item.annualized_roi_pct,
    "capital_required": lambda item: -item.capital_required,
}


def _sort(items: list[DealListItem], order_by: str) -> None:
    items.sort(key=_SORTERS.get(order_by, _SORTERS["score"]), reverse=True)


def _facet(items: list[DealListItem], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(getattr(item, attr))
        counts[key] = counts.get(key, 0) + 1
    return counts
