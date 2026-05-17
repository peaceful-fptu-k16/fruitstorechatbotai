from backend.database.models import Product
from backend.schemas import ProductOut


def to_product_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        name=product.name,
        category=product.category,
        price=product.price,
        stock=product.stock,
        sweetness_level=product.sweetness_level,
        sourness_level=product.sourness_level,
        seed_level=product.seed_level,
        juiciness_level=product.juiciness_level,
        aroma_level=product.aroma_level,
        crunchiness_level=product.crunchiness_level,
        fiber_level=product.fiber_level,
        vitamin_c_level=product.vitamin_c_level,
        sugar_content_level=product.sugar_content_level,
        calories_per_100g=product.calories_per_100g,
        shelf_life_days=product.shelf_life_days,
        texture=product.texture,
        color=product.color,
        best_use=product.best_use,
        origin=product.origin,
        season=product.season,
        description=product.description,
    )
