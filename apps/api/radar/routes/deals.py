from decimal import Decimal
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
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
    min_roi: Decimal | None = Query(default=None),
    min_margin: Decimal | None = Query(default=None),
    min_profit: Decimal | None = Query(default=None),
    city: str | None = None,
    category: str | None = None,
    source: str | None = None,
    property_type: str | None = None,
    decision: str | None = None,
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
    if property_type:
        q = q.filter(Property.property_type == property_type)

    analyses = q.all()

    # When analyses have not been persisted yet, rank the real collected listings
    # so the dashboard never hides live scraper results behind demo data.
    if not analyses:
        real_items = _real_listing_items(db, min_score, max_capital, city, category, property_type)
        real_items = _filter_items(real_items, min_roi, min_margin, min_profit, source, decision)
        if real_items:
            _sort(real_items, order_by)
            page = real_items[offset: offset + limit]
            return DealListResponse(
                items=page,
                total=len(real_items),
                facets={
                    "by_category": _facet(real_items, "category"),
                    "by_city": _facet(real_items, "city"),
                },
            )

        items = _demo_items(min_score, max_capital, city, category)
        _sort(items, order_by)
        page = items[offset: offset + limit]
        return DealListResponse(
            items=page,
            total=len(items),
            facets={"by_category": _facet(items, "category"), "by_city": _facet(items, "city")},
        )

    items = [_to_deal_list_item(a, a.property, _best_listing(a.property)) for a in analyses]
    items = _filter_items(items, min_roi, min_margin, min_profit, source, decision)
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
    if not analyses and listing:
        preliminary = _preliminary_analysis_dict(prop, listing, db)
        analyses_payload = [preliminary] if preliminary else []
    else:
        analyses_payload = [
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
        ]

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
        "analyses": analyses_payload,
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


def _real_listing_items(
    db: Session,
    min_score: Decimal,
    max_capital: Decimal,
    city: str | None,
    category: str | None,
    property_type: str | None,
) -> list[DealListItem]:
    market_rates = _market_rates(db)
    properties = (
        db.query(Property)
        .options(joinedload(Property.source_listings))
        .join(SourceListing, SourceListing.property_id == Property.id)
        .filter(SourceListing.is_active.is_(True), SourceListing.price.isnot(None))
    )
    if city:
        properties = properties.filter(Property.city == city)
    if category:
        properties = properties.filter(Property.category == category)
    if property_type:
        properties = properties.filter(Property.property_type == property_type)

    items: list[DealListItem] = []
    for prop in properties.distinct().all():
        listing = _best_listing(prop)
        if not listing or not listing.price:
            continue
        item = _preliminary_item(prop, listing, market_rates)
        if not item:
            continue
        if item.capital_required > max_capital or item.score < min_score:
            continue
        items.append(item)
    return items


def _preliminary_item(
    prop: Property,
    listing: SourceListing,
    market_rates: dict[tuple[str, str, str], Decimal],
) -> DealListItem | None:
    if not listing.price:
        return None

    purchase_price = listing.price
    area = prop.area_privative or Decimal("0")
    renovation_cost = _renovation_estimate(area, prop.property_type)
    transaction_costs = (purchase_price * Decimal("0.045")).quantize(Decimal("0.01"))
    financing_costs = (purchase_price * Decimal("0.04")).quantize(Decimal("0.01"))
    entry = (purchase_price * Decimal("0.25")).quantize(Decimal("0.01"))
    contingency = ((renovation_cost + transaction_costs) * Decimal("0.12")).quantize(Decimal("0.01"))
    capital_required = (entry + financing_costs + transaction_costs + renovation_cost + contingency).quantize(
        Decimal("0.01")
    )
    estimated_market_value, estimated_resale = _estimated_values(prop, purchase_price, area, market_rates)
    selling_costs = (estimated_resale * Decimal("0.06")).quantize(Decimal("0.01"))
    total_cost = (
        purchase_price + transaction_costs + renovation_cost + selling_costs + contingency
    ).quantize(Decimal("0.01"))
    profit = (estimated_resale - total_cost).quantize(Decimal("0.01"))
    margin_pct = _pct(profit, estimated_resale)
    roi_pct = _pct(profit, capital_required)
    annualized_roi_pct = _annualize_simple(roi_pct, 10)
    score = _preliminary_score(
        prop,
        listing,
        capital_required,
        profit,
        margin_pct,
        annualized_roi_pct,
    )
    decision = _preliminary_decision(score, profit, margin_pct, annualized_roi_pct)

    return DealListItem(
        property_id=str(prop.id),
        title=listing.title or f"{prop.property_type.title()} em {prop.neighborhood}",
        score=score,
        decision=decision,
        category=prop.category,
        city=prop.city,
        neighborhood=prop.neighborhood,
        property_type=prop.property_type,
        purchase_price=purchase_price,
        estimated_market_value=estimated_market_value,
        estimated_resale_value=estimated_resale,
        renovation_cost=renovation_cost,
        total_cost=total_cost,
        capital_required=capital_required,
        estimated_profit=profit,
        margin_pct=margin_pct,
        roi_pct=roi_pct,
        annualized_roi_pct=annualized_roi_pct,
        estimated_months=10,
        risk_level="medium" if prop.category in {"auction", "bank_owned"} else "low",
        source_name=listing.source,
        primary_source_url=listing.source_url,
        is_demo=False,
        source_count=sum(1 for l in prop.source_listings if l.is_active),
    )


def _preliminary_analysis_dict(prop: Property, listing: SourceListing, db: Session) -> dict[str, Any] | None:
    item = _preliminary_item(prop, listing, _market_rates(db))
    if not item:
        return None
    transaction_costs = (item.purchase_price * Decimal("0.045")).quantize(Decimal("0.01"))
    selling_costs = (item.estimated_resale_value * Decimal("0.06")).quantize(Decimal("0.01"))
    contingency = ((item.renovation_cost + transaction_costs) * Decimal("0.12")).quantize(Decimal("0.01"))
    return {
        "scenario": "base",
        "financing_mode": "financed",
        "renovation_level": "medium",
        "purchase_price": str(item.purchase_price),
        "estimated_market_value": str(item.estimated_market_value),
        "estimated_resale_value": str(item.estimated_resale_value),
        "renovation_cost": str(item.renovation_cost),
        "transaction_costs": str(transaction_costs),
        "holding_costs": "0.00",
        "selling_costs": str(selling_costs),
        "contingency": str(contingency),
        "total_cost": str(item.total_cost),
        "capital_required": str(item.capital_required),
        "estimated_profit": str(item.estimated_profit),
        "margin_pct": str(item.margin_pct),
        "roi_pct": str(item.roi_pct),
        "annualized_roi_pct": str(item.annualized_roi_pct),
        "estimated_months": item.estimated_months,
        "risk_level": item.risk_level,
        "risk_flags": ["triagem_preliminar"],
        "score": str(item.score),
        "decision": item.decision,
        "score_breakdown": {
            "retorno": 35,
            "margem": 25,
            "lucro": 20,
            "capital": 10,
            "dados": 10,
        },
    }


def _market_rates(db: Session) -> dict[tuple[str, str, str], Decimal]:
    grouped: dict[tuple[str, str, str], list[Decimal]] = {}
    rows = (
        db.query(Property, SourceListing)
        .join(SourceListing, SourceListing.property_id == Property.id)
        .filter(
            SourceListing.is_active.is_(True),
            SourceListing.price.isnot(None),
            Property.area_privative.isnot(None),
            Property.area_privative > 0,
        )
        .all()
    )

    for prop, listing in rows:
        if not listing.price or not prop.area_privative:
            continue
        sqm = (listing.price / prop.area_privative).quantize(Decimal("0.01"))
        keys = [
            (_norm(prop.city), _norm(prop.neighborhood), prop.property_type),
            (_norm(prop.city), "*", prop.property_type),
            ("*", "*", prop.property_type),
        ]
        for key in keys:
            grouped.setdefault(key, []).append(sqm)

    return {key: _percentile(values, Decimal("0.65")) for key, values in grouped.items() if len(values) >= 3}


def _estimated_values(
    prop: Property,
    purchase_price: Decimal,
    area: Decimal,
    market_rates: dict[tuple[str, str, str], Decimal],
) -> tuple[Decimal, Decimal]:
    rate = _lookup_rate(prop, market_rates)
    if rate and area > 0:
        market_value = (area * rate).quantize(Decimal("0.01"))
        uplift = {
            "apartamento": Decimal("1.08"),
            "casa": Decimal("1.06"),
            "terreno": Decimal("1.00"),
        }.get(prop.property_type, Decimal("1.04"))
        resale = (market_value * uplift).quantize(Decimal("0.01"))
        return market_value, resale

    fallback = {
        "auction": Decimal("1.18"),
        "bank_owned": Decimal("1.16"),
        "common": Decimal("1.10"),
    }.get(prop.category, Decimal("1.10"))
    resale = (purchase_price * fallback).quantize(Decimal("0.01"))
    return purchase_price, resale


def _lookup_rate(prop: Property, rates: dict[tuple[str, str, str], Decimal]) -> Decimal | None:
    keys = [
        (_norm(prop.city), _norm(prop.neighborhood), prop.property_type),
        (_norm(prop.city), "*", prop.property_type),
        ("*", "*", prop.property_type),
    ]
    for key in keys:
        if key in rates:
            return rates[key]
    return None


def _percentile(values: list[Decimal], pct: Decimal) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        return Decimal("0")
    index = int((len(ordered) - 1) * float(pct))
    return ordered[index].quantize(Decimal("0.01"))


def _norm(value: str | None) -> str:
    return " ".join((value or "Nao informado").lower().split())


def _renovation_estimate(area: Decimal, property_type: str) -> Decimal:
    if property_type == "terreno" or area <= 0:
        return Decimal("0")
    return (area * Decimal("850")).quantize(Decimal("0.01"))


def _preliminary_score(
    prop: Property,
    listing: SourceListing,
    capital_required: Decimal,
    profit: Decimal,
    margin_pct: Decimal,
    annualized_roi_pct: Decimal,
) -> Decimal:
    if profit <= 0 or margin_pct <= 0 or annualized_roi_pct <= 0:
        return max(Decimal("0"), min(Decimal("45"), Decimal("30") + annualized_roi_pct / Decimal("3"))).quantize(
            Decimal("0.01")
        )

    score = Decimal("0")
    if annualized_roi_pct >= Decimal("80"):
        score += Decimal("35")
    elif annualized_roi_pct >= Decimal("50"):
        score += Decimal("30")
    elif annualized_roi_pct >= Decimal("30"):
        score += Decimal("24")
    elif annualized_roi_pct >= Decimal("15"):
        score += Decimal("16")
    else:
        score += Decimal("8")

    if margin_pct >= Decimal("30"):
        score += Decimal("25")
    elif margin_pct >= Decimal("20"):
        score += Decimal("18")
    elif margin_pct >= Decimal("10"):
        score += Decimal("10")
    else:
        score += Decimal("4")

    if profit >= Decimal("80000"):
        score += Decimal("20")
    elif profit >= Decimal("40000"):
        score += Decimal("13")
    elif profit >= Decimal("15000"):
        score += Decimal("7")
    else:
        score += Decimal("3")

    if capital_required <= Decimal("150000"):
        score += Decimal("10")
    elif capital_required <= Decimal("300000"):
        score += Decimal("6")
    if prop.area_privative:
        score += Decimal("4")
    if prop.bedrooms is not None:
        score += Decimal("2")
    if prop.neighborhood and prop.neighborhood != "Nao informado":
        score += Decimal("2")
    return min(score, Decimal("100")).quantize(Decimal("0.01"))


def _preliminary_decision(
    score: Decimal,
    profit: Decimal,
    margin_pct: Decimal,
    annualized_roi_pct: Decimal,
) -> str:
    if profit <= 0 or margin_pct <= 0 or annualized_roi_pct <= 0:
        return "discard"
    if score >= Decimal("85") and annualized_roi_pct >= Decimal("30"):
        return "priority"
    if score >= Decimal("70") and annualized_roi_pct >= Decimal("15"):
        return "analyze"
    if score >= Decimal("50"):
        return "monitor"
    return "discard"


def _filter_items(
    items: list[DealListItem],
    min_roi: Decimal | None,
    min_margin: Decimal | None,
    min_profit: Decimal | None,
    source: str | None,
    decision: str | None,
) -> list[DealListItem]:
    filtered = items
    if min_roi is not None:
        filtered = [item for item in filtered if item.annualized_roi_pct >= min_roi]
    if min_margin is not None:
        filtered = [item for item in filtered if item.margin_pct >= min_margin]
    if min_profit is not None:
        filtered = [item for item in filtered if item.estimated_profit >= min_profit]
    if source:
        filtered = [item for item in filtered if item.source_name == source]
    if decision:
        filtered = [item for item in filtered if item.decision == decision]
    return filtered


def _pct(value: Decimal, base: Decimal) -> Decimal:
    if base == 0:
        return Decimal("0")
    return (value / base * Decimal("100")).quantize(Decimal("0.01"))


def _annualize_simple(roi_pct: Decimal, months: int) -> Decimal:
    if months <= 0:
        return Decimal("0")
    roi = float(roi_pct / Decimal("100"))
    annualized = ((1 + roi) ** (12 / months) - 1) * 100 if roi > -1 else -100
    return Decimal(str(annualized)).quantize(Decimal("0.01"))


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
