from backend.api.admin import router as admin_router
from backend.api.admin_ui import router as admin_ui_router
from backend.api.inventory import router as inventory_router
from backend.api.products import router as products_router
from backend.core.app_factory import create_app


app = create_app(
    title="Fruit Store Admin Service",
    service_name="fruit-store-admin-service",
    routers=(admin_ui_router, admin_router, products_router, inventory_router),
    build_services=False,
)
