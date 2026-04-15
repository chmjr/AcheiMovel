from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from radar.config import get_settings
from radar.routes import deals, health, market, properties, scrapers, settings


def create_app() -> FastAPI:
    config = get_settings()
    app = FastAPI(title=config.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(deals.router, prefix=config.api_prefix)
    app.include_router(market.router, prefix=config.api_prefix)
    app.include_router(properties.router, prefix=config.api_prefix)
    app.include_router(scrapers.router, prefix=config.api_prefix)
    app.include_router(settings.router, prefix=config.api_prefix)
    return app


app = create_app()
