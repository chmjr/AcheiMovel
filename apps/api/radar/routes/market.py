from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from radar.auth import require_token
from radar.db import SessionLocal, get_db
from radar.models.market import NeighborhoodStat
from radar.services.deal_persistence import analyze_and_persist_all
from radar.services.market_stats import compute_neighborhood_stats

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(require_token)])


def _run_compute_stats() -> None:
    with SessionLocal() as db:
        compute_neighborhood_stats(db)


def _run_analyze_all() -> None:
    with SessionLocal() as db:
        analyze_and_persist_all(db)


def _run_full_pipeline() -> None:
    """Compute market stats first so analyses use fresh percentiles."""
    with SessionLocal() as db:
        compute_neighborhood_stats(db)
    with SessionLocal() as db:
        analyze_and_persist_all(db)


@router.get("/stats")
async def get_market_stats(
    city: str | None = None,
    property_type: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    q = db.query(NeighborhoodStat)
    if city:
        q = q.filter(NeighborhoodStat.city == city)
    if property_type:
        q = q.filter(NeighborhoodStat.property_type == property_type)
    stats = q.order_by(NeighborhoodStat.city, NeighborhoodStat.neighborhood).all()

    return {
        "items": [
            {
                "city": s.city,
                "neighborhood": s.neighborhood,
                "property_type": s.property_type,
                "sample_size": s.sample_size,
                "price_per_sqm_p25": str(s.price_per_sqm_p25) if s.price_per_sqm_p25 else None,
                "price_per_sqm_p50": str(s.price_per_sqm_p50) if s.price_per_sqm_p50 else None,
                "price_per_sqm_p65": str(s.price_per_sqm_p65) if s.price_per_sqm_p65 else None,
                "price_per_sqm_p75": str(s.price_per_sqm_p75) if s.price_per_sqm_p75 else None,
                "liquidity_score": str(s.liquidity_score) if s.liquidity_score else None,
                "computed_at": s.computed_at.isoformat() if s.computed_at else None,
            }
            for s in stats
        ],
        "total": len(stats),
    }


@router.post("/compute")
async def compute_stats(background_tasks: BackgroundTasks) -> dict:
    """Recompute price-per-sqm percentiles from active listings."""
    background_tasks.add_task(_run_compute_stats)
    return {"status": "computing"}


@router.post("/analyze")
async def analyze_all(background_tasks: BackgroundTasks) -> dict:
    """Run the full pipeline: market stats → deal analysis for all properties."""
    background_tasks.add_task(_run_full_pipeline)
    return {"status": "queued"}
