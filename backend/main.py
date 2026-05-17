from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.admin import router as admin_router
from backend.api.chat import router as chat_router
from backend.api.inventory import router as inventory_router
from backend.api.products import router as products_router
from backend.api.recommend import router as recommend_router
from backend.core.config import get_settings
from backend.core.services import ServiceFactory
from backend.database.queries import seed_products
from backend.database.session import Base, SessionLocal, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_products(db)
        app.state.services = ServiceFactory.build(db)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(recommend_router)
app.include_router(admin_router)


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}
