from __future__ import annotations

from hashlib import sha256
from typing import Iterable, Optional

from sqlalchemy import Select, select, text
from sqlalchemy.orm import Session

from backend.core.text import normalize_text
from backend.database.models import (
    Conversation,
    ConversationMessage,
    FaqDocument,
    IdempotencyKey,
    InventoryEvent,
    Product,
)


_PRODUCT_SCHEMA_PATCH_COLUMNS: tuple[tuple[str, str], ...] = (
    ("juiciness_level", "INTEGER NOT NULL DEFAULT 5"),
    ("aroma_level", "INTEGER NOT NULL DEFAULT 5"),
    ("crunchiness_level", "INTEGER NOT NULL DEFAULT 5"),
    ("fiber_level", "INTEGER NOT NULL DEFAULT 5"),
    ("vitamin_c_level", "INTEGER NOT NULL DEFAULT 5"),
    ("sugar_content_level", "INTEGER NOT NULL DEFAULT 5"),
    ("calories_per_100g", "INTEGER NOT NULL DEFAULT 55"),
    ("shelf_life_days", "INTEGER NOT NULL DEFAULT 5"),
    ("color", "TEXT NOT NULL DEFAULT 'mixed'"),
    ("best_use", "TEXT NOT NULL DEFAULT 'Ăn tươi'"),
)


def _ensure_product_schema_columns(db: Session) -> None:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "sqlite":
        return

    columns = db.execute(text("PRAGMA table_info(products)")).mappings().all()
    existing_columns = {str(row.get("name", "")) for row in columns}

    changed = False
    for column_name, ddl in _PRODUCT_SCHEMA_PATCH_COLUMNS:
        if column_name in existing_columns:
            continue
        db.execute(text(f"ALTER TABLE products ADD COLUMN {column_name} {ddl}"))
        changed = True

    if changed:
        db.commit()


def seed_products(db: Session) -> None:
    _ensure_product_schema_columns(db)

    canonical_products = [
        {
            "name": "Xoài Cát Hòa Lộc",
            "category": "fruit",
            "price": 85000,
            "stock": 40,
            "sweetness_level": 9,
            "sourness_level": 1,
            "seed_level": 4,
            "juiciness_level": 7,
            "aroma_level": 8,
            "crunchiness_level": 4,
            "fiber_level": 5,
            "vitamin_c_level": 6,
            "sugar_content_level": 8,
            "calories_per_100g": 60,
            "shelf_life_days": 5,
            "texture": "mềm",
            "color": "vàng",
            "best_use": "Ăn tươi, sinh tố",
            "origin": "Tiền Giang",
            "season": "hè",
            "description": "Xoài Cát Hòa Lộc ngọt đậm, thơm, ít xơ.",
        },
        {
            "name": "Cam Úc",
            "category": "fruit",
            "price": 65000,
            "stock": 25,
            "sweetness_level": 6,
            "sourness_level": 4,
            "seed_level": 2,
            "juiciness_level": 9,
            "aroma_level": 6,
            "crunchiness_level": 7,
            "fiber_level": 6,
            "vitamin_c_level": 9,
            "sugar_content_level": 6,
            "calories_per_100g": 47,
            "shelf_life_days": 12,
            "texture": "mọng nước",
            "color": "cam",
            "best_use": "Ép nước, ăn sáng",
            "origin": "Úc",
            "season": "quanh năm",
            "description": "Cam Úc vị ngọt nhẹ, chua thanh, giàu vitamin C.",
        },
        {
            "name": "Nho Mẫu Đơn",
            "category": "fruit",
            "price": 180000,
            "stock": 12,
            "sweetness_level": 8,
            "sourness_level": 2,
            "seed_level": 1,
            "juiciness_level": 7,
            "aroma_level": 7,
            "crunchiness_level": 8,
            "fiber_level": 5,
            "vitamin_c_level": 4,
            "sugar_content_level": 8,
            "calories_per_100g": 69,
            "shelf_life_days": 7,
            "texture": "giòn",
            "color": "xanh ngọc",
            "best_use": "Ăn tươi, tráng miệng",
            "origin": "Hàn Quốc",
            "season": "thu",
            "description": "Nho Mẫu Đơn vỏ mỏng, giòn, ngọt nhẹ và ít hạt.",
        },
        {
            "name": "Bưởi Da Xanh",
            "category": "fruit",
            "price": 55000,
            "stock": 18,
            "sweetness_level": 7,
            "sourness_level": 3,
            "seed_level": 5,
            "juiciness_level": 8,
            "aroma_level": 7,
            "crunchiness_level": 6,
            "fiber_level": 8,
            "vitamin_c_level": 8,
            "sugar_content_level": 5,
            "calories_per_100g": 38,
            "shelf_life_days": 14,
            "texture": "chắc múi",
            "color": "xanh",
            "best_use": "Ăn kiêng, salad",
            "origin": "Bến Tre",
            "season": "quanh năm",
            "description": "Bưởi Da Xanh mùi thơm, múi dày, vị thanh ngọt.",
        },
        {
            "name": "Táo Envy",
            "category": "fruit",
            "price": 95000,
            "stock": 30,
            "sweetness_level": 7,
            "sourness_level": 3,
            "seed_level": 1,
            "juiciness_level": 7,
            "aroma_level": 6,
            "crunchiness_level": 9,
            "fiber_level": 6,
            "vitamin_c_level": 5,
            "sugar_content_level": 6,
            "calories_per_100g": 52,
            "shelf_life_days": 20,
            "texture": "giòn",
            "color": "đỏ",
            "best_use": "Ăn vặt, salad",
            "origin": "New Zealand",
            "season": "quanh năm",
            "description": "Táo Envy giòn rụm, ngọt dịu, phù hợp ăn trực tiếp hoặc làm salad.",
        },
        {
            "name": "Dâu Tây Đà Lạt",
            "category": "fruit",
            "price": 110000,
            "stock": 22,
            "sweetness_level": 7,
            "sourness_level": 4,
            "seed_level": 1,
            "juiciness_level": 8,
            "aroma_level": 9,
            "crunchiness_level": 4,
            "fiber_level": 5,
            "vitamin_c_level": 7,
            "sugar_content_level": 6,
            "calories_per_100g": 33,
            "shelf_life_days": 4,
            "texture": "mềm mọng",
            "color": "đỏ",
            "best_use": "Sinh tố, tráng miệng",
            "origin": "Đà Lạt",
            "season": "đông xuân",
            "description": "Dâu tây Đà Lạt thơm rõ, vị cân bằng, hợp làm món tráng miệng.",
        },
        {
            "name": "Kiwi Xanh",
            "category": "fruit",
            "price": 90000,
            "stock": 20,
            "sweetness_level": 6,
            "sourness_level": 5,
            "seed_level": 1,
            "juiciness_level": 8,
            "aroma_level": 6,
            "crunchiness_level": 5,
            "fiber_level": 8,
            "vitamin_c_level": 8,
            "sugar_content_level": 5,
            "calories_per_100g": 61,
            "shelf_life_days": 10,
            "texture": "mềm",
            "color": "xanh",
            "best_use": "Ăn kiêng, detox",
            "origin": "New Zealand",
            "season": "quanh năm",
            "description": "Kiwi xanh chua nhẹ, nhiều chất xơ, phù hợp thực đơn cân bằng.",
        },
        {
            "name": "Lê Hàn Quốc",
            "category": "fruit",
            "price": 105000,
            "stock": 16,
            "sweetness_level": 6,
            "sourness_level": 2,
            "seed_level": 2,
            "juiciness_level": 9,
            "aroma_level": 5,
            "crunchiness_level": 8,
            "fiber_level": 6,
            "vitamin_c_level": 5,
            "sugar_content_level": 5,
            "calories_per_100g": 42,
            "shelf_life_days": 15,
            "texture": "giòn mọng",
            "color": "vàng nhạt",
            "best_use": "Ép nước, ăn tươi",
            "origin": "Hàn Quốc",
            "season": "thu",
            "description": "Lê Hàn giòn, mọng nước, vị ngọt thanh và dễ ăn.",
        },
        {
            "name": "Thanh Long Ruột Đỏ",
            "category": "fruit",
            "price": 45000,
            "stock": 28,
            "sweetness_level": 6,
            "sourness_level": 2,
            "seed_level": 2,
            "juiciness_level": 8,
            "aroma_level": 5,
            "crunchiness_level": 5,
            "fiber_level": 7,
            "vitamin_c_level": 6,
            "sugar_content_level": 5,
            "calories_per_100g": 50,
            "shelf_life_days": 7,
            "texture": "mềm mọng",
            "color": "hồng đỏ",
            "best_use": "Giải nhiệt, smoothie bowl",
            "origin": "Bình Thuận",
            "season": "hè",
            "description": "Thanh long ruột đỏ mát, ngọt vừa, giàu chất chống oxy hóa tự nhiên.",
        },
        {
            "name": "Dứa Mật",
            "category": "fruit",
            "price": 50000,
            "stock": 24,
            "sweetness_level": 7,
            "sourness_level": 4,
            "seed_level": 1,
            "juiciness_level": 9,
            "aroma_level": 8,
            "crunchiness_level": 4,
            "fiber_level": 6,
            "vitamin_c_level": 8,
            "sugar_content_level": 7,
            "calories_per_100g": 50,
            "shelf_life_days": 6,
            "texture": "mọng nước",
            "color": "vàng",
            "best_use": "Ép nước, tráng miệng",
            "origin": "Tiền Giang",
            "season": "hè",
            "description": "Dứa mật thơm rõ, vị chua ngọt cân bằng, rất hợp ép nước.",
        },
        {
            "name": "Chuối Già Nam Mỹ",
            "category": "fruit",
            "price": 42000,
            "stock": 35,
            "sweetness_level": 8,
            "sourness_level": 1,
            "seed_level": 1,
            "juiciness_level": 6,
            "aroma_level": 7,
            "crunchiness_level": 3,
            "fiber_level": 7,
            "vitamin_c_level": 4,
            "sugar_content_level": 7,
            "calories_per_100g": 89,
            "shelf_life_days": 5,
            "texture": "mềm dẻo",
            "color": "vàng",
            "best_use": "Ăn sáng, làm bánh",
            "origin": "Ecuador",
            "season": "quanh năm",
            "description": "Chuối già vị ngọt đậm, dễ no, hợp bữa sáng và bữa phụ.",
        },
        {
            "name": "Việt Quất",
            "category": "fruit",
            "price": 195000,
            "stock": 14,
            "sweetness_level": 7,
            "sourness_level": 3,
            "seed_level": 1,
            "juiciness_level": 7,
            "aroma_level": 7,
            "crunchiness_level": 5,
            "fiber_level": 7,
            "vitamin_c_level": 7,
            "sugar_content_level": 5,
            "calories_per_100g": 57,
            "shelf_life_days": 5,
            "texture": "mọng",
            "color": "tím xanh",
            "best_use": "Ăn kiêng, ăn với sữa chua",
            "origin": "Mỹ",
            "season": "hè",
            "description": "Việt quất chua ngọt nhẹ, giàu vi chất, hợp món yogurt và granola.",
        },
        {
            "name": "Ổi Lê",
            "category": "fruit",
            "price": 38000,
            "stock": 26,
            "sweetness_level": 5,
            "sourness_level": 3,
            "seed_level": 6,
            "juiciness_level": 7,
            "aroma_level": 6,
            "crunchiness_level": 8,
            "fiber_level": 9,
            "vitamin_c_level": 9,
            "sugar_content_level": 4,
            "calories_per_100g": 41,
            "shelf_life_days": 8,
            "texture": "giòn",
            "color": "xanh lá",
            "best_use": "Ăn kiêng, ép nước",
            "origin": "Đồng Nai",
            "season": "quanh năm",
            "description": "Ổi lê giòn, thơm nhẹ, nhiều chất xơ và khá ít đường tự nhiên.",
        },
        {
            "name": "Mận Hậu Sơn La",
            "category": "fruit",
            "price": 70000,
            "stock": 19,
            "sweetness_level": 6,
            "sourness_level": 5,
            "seed_level": 3,
            "juiciness_level": 7,
            "aroma_level": 7,
            "crunchiness_level": 6,
            "fiber_level": 6,
            "vitamin_c_level": 6,
            "sugar_content_level": 6,
            "calories_per_100g": 46,
            "shelf_life_days": 6,
            "texture": "giòn nhẹ",
            "color": "tím đỏ",
            "best_use": "Ăn vặt, tráng miệng",
            "origin": "Sơn La",
            "season": "hè",
            "description": "Mận hậu vị chua ngọt rõ, giòn nhẹ, thích hợp ăn lạnh.",
        },
    ]

    existing_products = list(db.scalars(select(Product).order_by(Product.id.asc())))
    existing_by_key: dict[str, Product] = {}
    for product in existing_products:
        key = normalize_text(product.name)
        keeper = existing_by_key.get(key)
        if keeper is None:
            existing_by_key[key] = product
            continue

        # Merge duplicates by keeping the first record and best stock level.
        if product.stock > keeper.stock:
            keeper.stock = product.stock
        db.delete(product)

    for item in canonical_products:
        key = normalize_text(item["name"])
        existing = existing_by_key.get(key)

        if existing:
            for field_name, value in item.items():
                if field_name == "stock":
                    continue
                setattr(existing, field_name, value)
        else:
            db.add(Product(**item))

    canonical_faqs = {
        "shipping": {
            "question": "Shop giao hàng trong bao lâu?",
            "answer": "Nội thành giao trong 2-4 giờ, ngoại thành 1-2 ngày.",
        },
        "return": {
            "question": "Chính sách đổi trả như thế nào?",
            "answer": "Đổi trả trong 24 giờ nếu sản phẩm hư hỏng hoặc sai đơn.",
        },
        "storage": {
            "question": "Bảo quản trái cây ra sao?",
            "answer": "Bảo quản lạnh 4-8°C và tránh ánh nắng trực tiếp.",
        },
    }

    existing_faq_records = list(db.scalars(select(FaqDocument).order_by(FaqDocument.id.asc())))
    existing_faqs: dict[str, FaqDocument] = {}
    for doc in existing_faq_records:
        keeper = existing_faqs.get(doc.topic)
        if keeper is None:
            existing_faqs[doc.topic] = doc
            continue
        db.delete(doc)

    for topic, item in canonical_faqs.items():
        existing = existing_faqs.get(topic)
        if existing:
            existing.question = item["question"]
            existing.answer = item["answer"]
        else:
            db.add(FaqDocument(topic=topic, question=item["question"], answer=item["answer"]))

    db.commit()


def _filter_products_by_query(products: list[Product], query: Optional[str]) -> list[Product]:
    if not query:
        return products

    normalized_query = normalize_text(query)
    if not normalized_query:
        return products

    return [
        product
        for product in products
        if normalized_query in normalize_text(product.name)
    ]


def list_products(
    db: Session,
    *,
    only_available: bool = False,
    query: Optional[str] = None,
    limit: int = 20,
) -> list[Product]:
    statement: Select[tuple[Product]] = select(Product)

    if only_available:
        statement = statement.where(Product.stock > 0)

    statement = statement.order_by(Product.price.asc())
    products = list(db.scalars(statement))
    products = _filter_products_by_query(products, query)
    return products[:limit]


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    return db.get(Product, product_id)


def find_products_by_name(db: Session, name: str, limit: int = 5) -> list[Product]:
    statement = (
        select(Product)
        .order_by(Product.stock.desc(), Product.price.asc())
    )
    products = list(db.scalars(statement))
    products = _filter_products_by_query(products, name)
    return products[:limit]


def list_faq_documents(db: Session) -> list[FaqDocument]:
    return list(db.scalars(select(FaqDocument)))


def get_or_create_conversation(db: Session, session_id: str, user_id: str) -> Conversation:
    existing = db.scalar(select(Conversation).where(Conversation.session_id == session_id))
    if existing:
        return existing

    conversation = Conversation(session_id=session_id, user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def save_message(
    db: Session,
    *,
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    metadata_json: Optional[dict] = None,
) -> ConversationMessage:
    conversation = get_or_create_conversation(db, session_id=session_id, user_id=user_id)
    message = ConversationMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        metadata_json=metadata_json or {},
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(db: Session, session_id: str, limit: int = 6) -> list[ConversationMessage]:
    conversation = db.scalar(select(Conversation).where(Conversation.session_id == session_id))
    if not conversation:
        return []

    statement = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation.id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    return list(reversed(list(db.scalars(statement))))


def hash_updates(updates: Iterable[dict]) -> str:
    joined = "|".join(
        f"{item['product_id']}:{item['operation']}:{item['quantity']}" for item in updates
    )
    return sha256(joined.encode("utf-8")).hexdigest()


def check_existing_idempotent_response(
    db: Session, *, endpoint: str, idempotency_key: str, request_hash: str
) -> Optional[dict]:
    record = db.scalar(
        select(IdempotencyKey)
        .where(IdempotencyKey.endpoint == endpoint)
        .where(IdempotencyKey.key == idempotency_key)
    )
    if not record:
        return None

    if record.request_hash != request_hash:
        raise ValueError("Idempotency key was already used with a different payload")

    return record.response_json


def store_idempotent_response(
    db: Session,
    *,
    endpoint: str,
    idempotency_key: str,
    request_hash: str,
    response_json: dict,
) -> None:
    record = IdempotencyKey(
        endpoint=endpoint,
        key=idempotency_key,
        request_hash=request_hash,
        response_json=response_json,
    )
    db.add(record)
    db.commit()


def update_stock(
    db: Session,
    *,
    actor: str,
    product_id: int,
    quantity: int,
    operation: str,
) -> Product:
    product = get_product_by_id(db, product_id)
    if product is None:
        raise ValueError(f"Product id={product_id} not found")

    if operation == "set":
        new_stock = max(0, quantity)
        delta = new_stock - product.stock
    elif operation == "inc":
        delta = quantity
        new_stock = max(0, product.stock + quantity)
    elif operation == "dec":
        delta = -quantity
        new_stock = max(0, product.stock - quantity)
    else:
        raise ValueError("operation must be one of: set, inc, dec")

    product.stock = new_stock
    event = InventoryEvent(
        product_id=product.id,
        actor=actor,
        operation=operation,
        quantity_delta=delta,
        new_stock=new_stock,
    )
    db.add(event)
    db.commit()
    db.refresh(product)
    return product
