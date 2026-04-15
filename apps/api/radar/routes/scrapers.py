from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from radar.auth import require_token
from radar.db import get_db
from radar.models.scrape import ScrapeRun
from radar.workers.scrape_jobs import (
    scrape_brognoli_async,
    scrape_caixa_async,
    scrape_chaves_na_mao_async,
    scrape_imovelweb_async,
    scrape_casamare_async,
    scrape_kzue_async,
    scrape_lanceja_async,
    scrape_loft_async,
    scrape_leiloeiro_publico_async,
    scrape_mega_leiloes_async,
    scrape_olx_async,
    scrape_quintoandar_async,
    scrape_superbid_async,
    scrape_vivareal_async,
    scrape_zap_async,
)

router = APIRouter(prefix="/scrapers", tags=["scrapers"], dependencies=[Depends(require_token)])


# All triggers now use BackgroundTasks so the HTTP response returns immediately
# and the scraper (which can take minutes) runs in the background.

@router.post("/caixa/trigger")
async def trigger_caixa(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_caixa_async)
    return {"status": "queued", "source": "caixa"}


@router.post("/brognoli/trigger")
async def trigger_brognoli(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_brognoli_async)
    return {"status": "queued", "source": "brognoli"}


@router.post("/chaves-na-mao/trigger")
async def trigger_chaves_na_mao(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_chaves_na_mao_async)
    return {"status": "queued", "source": "chaves_na_mao"}


@router.post("/imovelweb/trigger")
async def trigger_imovelweb(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_imovelweb_async)
    return {"status": "queued", "source": "imovelweb"}


@router.post("/lanceja/trigger")
async def trigger_lanceja(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_lanceja_async)
    return {"status": "queued", "source": "lanceja"}


@router.post("/loft/trigger")
async def trigger_loft(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_loft_async)
    return {"status": "queued", "source": "loft"}


@router.post("/kzue/trigger")
async def trigger_kzue(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_kzue_async)
    return {"status": "queued", "source": "kzue"}


@router.post("/casamare/trigger")
async def trigger_casamare(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_casamare_async)
    return {"status": "queued", "source": "casamare"}


@router.post("/superbid/trigger")
async def trigger_superbid(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_superbid_async)
    return {"status": "queued", "source": "superbid"}


@router.post("/leiloeiro-publico/trigger")
async def trigger_leiloeiro_publico(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_leiloeiro_publico_async)
    return {"status": "queued", "source": "leiloeiro_publico"}


@router.post("/mega-leiloes/trigger")
async def trigger_mega_leiloes(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_mega_leiloes_async)
    return {"status": "queued", "source": "mega_leiloes"}


@router.post("/quintoandar/trigger")
async def trigger_quintoandar(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_quintoandar_async)
    return {"status": "queued", "source": "quintoandar"}


@router.post("/olx/trigger")
async def trigger_olx(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_olx_async)
    return {"status": "queued", "source": "olx"}


@router.post("/vivareal/trigger")
async def trigger_vivareal(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_vivareal_async)
    return {"status": "queued", "source": "vivareal"}


@router.post("/zap/trigger")
async def trigger_zap(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(scrape_zap_async)
    return {"status": "queued", "source": "zap"}


@router.get("/runs")
async def list_scrape_runs(
    db: Session = Depends(get_db),
    limit: int = 25,
) -> dict:
    runs = db.query(ScrapeRun).order_by(desc(ScrapeRun.started_at)).limit(limit).all()
    return {
        "items": [
            {
                "id": run.id,
                "source": run.source,
                "status": run.status,
                "items_collected": run.items_collected,
                "items_new": run.items_new,
                "items_updated": run.items_updated,
                "error": run.error,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
            }
            for run in runs
        ]
    }
