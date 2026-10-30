from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app.logging_setup import configure_logging
from app.middleware import CorrelationIdMiddleware
from app.routers import auth, billing, catalog, usage


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(catalog.router)
    app.include_router(usage.router)
    app.include_router(billing.router)

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "environment": settings.environment,
            "payment_provider": settings.payment_provider,
            "money": "Decimal",
            "outbox_sync": settings.outbox_sync,
            "database": "postgres" if settings.is_postgres else "other",
        }

    return app


app = create_app()
