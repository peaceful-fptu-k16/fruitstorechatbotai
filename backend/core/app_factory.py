from __future__ import annotations

from collections.abc import Iterable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    """Create a FastAPI app with shared database bootstrap and optional agents."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize schema, seed catalog data, then build stateful services once."""
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
        """Expose a tiny service descriptor for browser and uptime checks."""
        return {
            "service": service_name,
            "status": "ok",
            "docs": "/docs",
        }

    @app.get("/health")
    def health():
        """Report service health and required AI readiness when agents are enabled."""
        services = getattr(app.state, "services", None)
        if services is None:
            return {"status": "healthy"}

        ai_status = services.ai_runtime_status(probe_lm_studio=True)
        if not ai_status["ready"]:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "ai": ai_status},
            )

        return {"status": "healthy", "ai": ai_status}

    return app
