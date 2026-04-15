"""
Async scraper job wrappers.

Each `*_async` function is called directly by FastAPI BackgroundTasks.
After a successful run that yields new or updated listings, the pipeline
automatically:
  1. Recomputes neighborhood_stats percentiles.
  2. Re-runs deal analysis for all properties.
  3. Sends a Telegram alert if any high-score (≥ 80) deals were found.
"""
from datetime import UTC, datetime

from radar.db import SessionLocal
from radar.models.scrape import ScrapeRun
from radar.scrapers.blocked_public import ImovelwebScraper, OlxScraper, VivaRealScraper, ZapScraper
from radar.scrapers.brognoli import BrognoliScraper
from radar.scrapers.caixa import CaixaScraper
from radar.scrapers.chaves_na_mao import ChavesNaMaoScraper
from radar.scrapers.lanceja import LanceJaScraper
from radar.scrapers.leiloeiro_publico import LeiloeiroPublicoScraper
from radar.scrapers.loft import LoftScraper
from radar.scrapers.loft_partner import CasaMareScraper, KzueScraper
from radar.scrapers.mega_leiloes import MegaLeiloesScraper
from radar.scrapers.quintoandar import QuintoAndarScraper
from radar.scrapers.superbid import SuperbidScraper


async def run_scraper_async(source: str, scraper) -> dict[str, object]:
    with SessionLocal() as db:
        run = ScrapeRun(source=source, status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
        try:
            stats = await scraper.run(db)
            run.status = "success" if stats["errors"] == 0 else "partial"
            run.items_collected = stats["collected"]
            run.items_new = stats["new"]
            run.items_updated = stats["updated"]
            error_messages = stats.get("error_messages") or []
            if error_messages:
                run.error = " | ".join(error_messages[:5])
            run.finished_at = datetime.now(UTC)
            db.commit()
        except Exception as exc:
            db.rollback()
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = datetime.now(UTC)
            db.add(run)
            db.commit()
            return {
                "run_id": run_id,
                "collected": 0,
                "parsed": 0,
                "new": 0,
                "updated": 0,
                "errors": 1,
                "error": str(exc),
            }

    # If the run produced new or updated listings, refresh market stats and
    # deal analyses so the dashboard reflects the latest data immediately.
    new_or_updated = stats.get("new", 0) + stats.get("updated", 0)
    if new_or_updated > 0:
        from radar.services.market_stats import compute_neighborhood_stats
        from radar.services.deal_persistence import analyze_and_persist_all

        with SessionLocal() as db:
            compute_neighborhood_stats(db)
        with SessionLocal() as db:
            analysis_result = analyze_and_persist_all(db)

        await _notify_new_deals(source, stats, analysis_result)

    return {"run_id": run_id, **stats}


async def _notify_new_deals(source: str, scrape_stats: dict, analysis_result: dict) -> None:
    """Send an email when high-score deals are found after a scrape."""
    from radar.config import get_settings
    from radar.alerts.email import send_email
    from radar.models.analysis import DealAnalysis

    config = get_settings()
    if not config.smtp_user or not config.alert_email_to:
        return

    with SessionLocal() as db:
        top_deals = (
            db.query(DealAnalysis)
            .filter(
                DealAnalysis.score >= 80,
                DealAnalysis.scenario == "base",
                DealAnalysis.financing_mode == "financed",
                DealAnalysis.renovation_level == "medium",
            )
            .order_by(DealAnalysis.score.desc())
            .limit(5)
            .all()
        )

    if not top_deals:
        return

    subject = f"[Radar Floripa] {len(top_deals)} oportunidade(s) ≥ 80 — {source.upper()}"
    lines = [
        f"Coleta: {scrape_stats.get('new', 0)} novos · {scrape_stats.get('updated', 0)} atualizados",
        f"Imóveis analisados: {analysis_result.get('processed', 0)}",
        "",
        "Top oportunidades (score ≥ 80):",
        "-" * 40,
    ]
    for deal in top_deals:
        lines.append(
            f"Nota {deal.score}  |  Lucro R$ {deal.estimated_profit:,.0f}  |  {deal.decision}"
        )

    await send_email(
        host=config.smtp_host,
        port=config.smtp_port,
        user=config.smtp_user,
        password=config.smtp_password,
        to=config.alert_email_to,
        subject=subject,
        body="\n".join(lines),
    )


# ---------------------------------------------------------------------------
# Per-source entry points (called by BackgroundTasks in routes/scrapers.py)
# ---------------------------------------------------------------------------

async def scrape_caixa_async() -> dict[str, object]:
    return await run_scraper_async("caixa", CaixaScraper())


async def scrape_brognoli_async() -> dict[str, object]:
    return await run_scraper_async("brognoli", BrognoliScraper())


async def scrape_chaves_na_mao_async() -> dict[str, object]:
    return await run_scraper_async("chaves_na_mao", ChavesNaMaoScraper())


async def scrape_imovelweb_async() -> dict[str, object]:
    return await run_scraper_async("imovelweb", ImovelwebScraper())


async def scrape_lanceja_async() -> dict[str, object]:
    return await run_scraper_async("lanceja", LanceJaScraper())


async def scrape_loft_async() -> dict[str, object]:
    return await run_scraper_async("loft", LoftScraper())


async def scrape_kzue_async() -> dict[str, object]:
    return await run_scraper_async("kzue", KzueScraper())


async def scrape_casamare_async() -> dict[str, object]:
    return await run_scraper_async("casamare", CasaMareScraper())


async def scrape_superbid_async() -> dict[str, object]:
    return await run_scraper_async("superbid", SuperbidScraper())


async def scrape_leiloeiro_publico_async() -> dict[str, object]:
    return await run_scraper_async("leiloeiro_publico", LeiloeiroPublicoScraper())


async def scrape_mega_leiloes_async() -> dict[str, object]:
    return await run_scraper_async("mega_leiloes", MegaLeiloesScraper())


async def scrape_quintoandar_async() -> dict[str, object]:
    return await run_scraper_async("quintoandar", QuintoAndarScraper())


async def scrape_olx_async() -> dict[str, object]:
    return await run_scraper_async("olx", OlxScraper())


async def scrape_vivareal_async() -> dict[str, object]:
    return await run_scraper_async("vivareal", VivaRealScraper())


async def scrape_zap_async() -> dict[str, object]:
    return await run_scraper_async("zap", ZapScraper())
