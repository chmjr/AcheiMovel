"""
Compute price-per-sqm percentiles and liquidity scores for each
(city, neighborhood, property_type) group and persist to neighborhood_stats.
"""
from decimal import Decimal
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from radar.models.listing import SourceListing
from radar.models.market import NeighborhoodStat
from radar.models.property import Property


def _percentile(sorted_data: list[float], p: int) -> float:
    """Linear interpolation percentile on a pre-sorted list."""
    n = len(sorted_data)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_data[0]
    idx = p / 100 * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    return sorted_data[lo] + (idx - lo) * (sorted_data[hi] - sorted_data[lo])


def compute_neighborhood_stats(db: Session) -> dict:
    """
    Pull all active listings with price + area, group by
    (city, neighborhood, property_type) and upsert percentile rows.

    Returns {"updated": N, "total_listings": N}.
    """
    rows = (
        db.query(SourceListing, Property)
        .join(Property, Property.id == SourceListing.property_id)
        .filter(
            SourceListing.is_active.is_(True),
            SourceListing.price.isnot(None),
            SourceListing.price > 0,
            Property.area_privative.isnot(None),
            Property.area_privative > 0,
        )
        .all()
    )

    groups: dict[tuple[str, str, str], list[float]] = {}
    for listing, prop in rows:
        key = (prop.city, prop.neighborhood, prop.property_type)
        sqm_price = float(listing.price / prop.area_privative)
        groups.setdefault(key, []).append(sqm_price)

    updated = 0
    for (city, neighborhood, prop_type), prices in groups.items():
        if len(prices) < 2:
            continue

        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        # Liquidity heuristic: more comparable listings → higher score, capped at 10
        liquidity = Decimal(str(round(min(n / 5.0, 10), 1)))

        p25 = Decimal(str(round(_percentile(prices_sorted, 25), 2)))
        p50 = Decimal(str(round(_percentile(prices_sorted, 50), 2)))
        p65 = Decimal(str(round(_percentile(prices_sorted, 65), 2)))
        p75 = Decimal(str(round(_percentile(prices_sorted, 75), 2)))

        stat = (
            db.query(NeighborhoodStat)
            .filter(
                NeighborhoodStat.city == city,
                NeighborhoodStat.neighborhood == neighborhood,
                NeighborhoodStat.property_type == prop_type,
            )
            .one_or_none()
        )

        if stat:
            stat.sample_size = n
            stat.price_per_sqm_p25 = p25
            stat.price_per_sqm_p50 = p50
            stat.price_per_sqm_p65 = p65
            stat.price_per_sqm_p75 = p75
            stat.liquidity_score = liquidity
            stat.computed_at = datetime.now(UTC)
        else:
            db.add(
                NeighborhoodStat(
                    city=city,
                    neighborhood=neighborhood,
                    property_type=prop_type,
                    sample_size=n,
                    price_per_sqm_p25=p25,
                    price_per_sqm_p50=p50,
                    price_per_sqm_p65=p65,
                    price_per_sqm_p75=p75,
                    liquidity_score=liquidity,
                )
            )
        updated += 1

    db.commit()
    return {"updated": updated, "total_listings": len(rows)}
