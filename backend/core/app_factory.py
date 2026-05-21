from __future__ import annotations

from collections.abc import Iterable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.services import ServiceFactory
from backend.database.queries import seed_products
from backend.database.session import Base, SessionLocal, engine


def create_app(
    *,
    title: str,
    service_name: str,
    routers: Iterable[APIRouter],
    build_services: bool,
) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_products(db)
            app.state.services = ServiceFactory.build(db) if build_services else None
        yield

    app = FastAPI(title=title, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in routers:
        app.include_router(router)

    @app.get("/")
    def root() -> dict:
        return {
            "service": service_name,
            "status": "ok",
            "docs": "/docs",
        }

    @app.get("/health")
    def health() -> dict:
        return {"status": "healthy"}

    return app
