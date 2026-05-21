from backend.api.admin import router as admin_router
from backend.api.admin_ui import router as admin_ui_router
from backend.api.chat import router as chat_router
from backend.api.facebook import router as facebook_router
from backend.api.inventory import router as inventory_router
from backend.api.products import router as products_router
from backend.api.recommend import router as recommend_router
from backend.core.app_factory import create_app
from backend.core.config import get_settings


settings = get_settings()

app = create_app(
    title=settings.app_name,
    service_name=settings.app_name,
    routers=(
        admin_ui_router,
        admin_router,
        facebook_router,
        chat_router,
        products_router,
        inventory_router,
        recommend_router,
    ),
    build_services=True,
)
