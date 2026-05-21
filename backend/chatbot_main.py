from backend.api.chat import router as chat_router
from backend.api.facebook import router as facebook_router
from backend.api.inventory import router as inventory_router
from backend.api.products import router as products_router
from backend.api.recommend import router as recommend_router
from backend.core.app_factory import create_app


app = create_app(
    title="Fruit Store Chatbot Service",
    service_name="fruit-store-chatbot-service",
    routers=(facebook_router, chat_router, recommend_router, products_router, inventory_router),
    build_services=True,
)
