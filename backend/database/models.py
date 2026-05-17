from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="fruit")
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sweetness_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    sourness_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    seed_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    juiciness_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    aroma_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    crunchiness_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    fiber_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    vitamin_c_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    sugar_content_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    calories_per_100g: Mapped[int] = mapped_column(Integer, nullable=False, default=55)
    shelf_life_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    texture: Mapped[str] = mapped_column(String(64), nullable=False, default="medium")
    color: Mapped[str] = mapped_column(String(64), nullable=False, default="mixed")
    best_use: Mapped[str] = mapped_column(String(128), nullable=False, default="Ăn tươi")
    origin: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    season: Mapped[str] = mapped_column(String(64), nullable=False, default="all")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    inventory_events: Mapped[list["InventoryEvent"]] = relationship(back_populates="product")


class InventoryEvent(Base):
    __tablename__ = "inventory_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    new_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    product: Mapped[Product] = relationship(back_populates="inventory_events")


class FaqDocument(Base):
    __tablename__ = "faq_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    messages: Mapped[list["ConversationMessage"]] = relationship(back_populates="conversation")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("key", name="uq_idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
