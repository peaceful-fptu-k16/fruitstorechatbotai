from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


IntentName = Literal[
    "available_products",
    "inventory_check",
    "recommendation",
    "faq_shipping",
    "faq_return",
    "faq_storage",
    "admin_update_stock",
    "out_of_domain",
]


class ProductOut(BaseModel):
    id: int
    name: str
    category: str
    price: int
    stock: int
    sweetness_level: int
    sourness_level: int
    seed_level: int
    juiciness_level: int
    aroma_level: int
    crunchiness_level: int
    fiber_level: int
    vitamin_c_level: int
    sugar_content_level: int
    calories_per_100g: int
    shelf_life_days: int
    texture: str
    color: str
    best_use: str
    origin: str
    season: str
    description: str


class ChatRequest(BaseModel):
    user_id: str = Field(default="guest")
    session_id: str = Field(default="default-session")
    message: str = Field(min_length=1)
    language: str = Field(default="vi")


class CitationOut(BaseModel):
    source_id: str
    source_type: str
    snippet: str
    score: float


class ChatResponse(BaseModel):
    trace_id: str
    intent: IntentName
    confidence: float
    answer: str
    products: list[ProductOut] = Field(default_factory=list)
    citations: list[CitationOut] = Field(default_factory=list)
    fallback: bool = False


class ProductsResponse(BaseModel):
    total: int
    items: list[ProductOut]


class InventoryResponse(BaseModel):
    product: Optional[ProductOut] = None
    message: str


class RecommendRequest(BaseModel):
    query: str = Field(min_length=1)
    user_id: str = Field(default="guest")
    session_id: str = Field(default="default-session")
    budget: Optional[int] = Field(default=None, ge=0)
    limit: int = Field(default=4, ge=1, le=20)


class RecommendResponse(BaseModel):
    reasoning: str
    recommendations: list[ProductOut]


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


StockOperation = Literal["set", "inc", "dec"]


class StockUpdateItem(BaseModel):
    product_id: int
    operation: StockOperation
    quantity: int = Field(ge=0)


class AdminUpdateStockRequest(BaseModel):
    updates: list[StockUpdateItem]


class UpdatedStockItem(BaseModel):
    product_id: int
    name: str
    stock: int


class AdminUpdateStockResponse(BaseModel):
    status: str
    applied: bool
    idempotency_key: str
    updates: list[UpdatedStockItem] = Field(default_factory=list)
    actor: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class IntentResult(BaseModel):
    intent: IntentName
    confidence: float
    reason: str
