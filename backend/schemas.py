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


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    category: Optional[str] = Field(default=None, min_length=1, max_length=64)
    price: Optional[int] = Field(default=None, ge=0)
    sweetness_level: Optional[int] = Field(default=None, ge=0, le=10)
    sourness_level: Optional[int] = Field(default=None, ge=0, le=10)
    seed_level: Optional[int] = Field(default=None, ge=0, le=10)
    juiciness_level: Optional[int] = Field(default=None, ge=0, le=10)
    aroma_level: Optional[int] = Field(default=None, ge=0, le=10)
    crunchiness_level: Optional[int] = Field(default=None, ge=0, le=10)
    fiber_level: Optional[int] = Field(default=None, ge=0, le=10)
    vitamin_c_level: Optional[int] = Field(default=None, ge=0, le=10)
    sugar_content_level: Optional[int] = Field(default=None, ge=0, le=10)
    calories_per_100g: Optional[int] = Field(default=None, ge=0)
    shelf_life_days: Optional[int] = Field(default=None, ge=0)
    texture: Optional[str] = Field(default=None, min_length=1, max_length=64)
    color: Optional[str] = Field(default=None, min_length=1, max_length=64)
    best_use: Optional[str] = Field(default=None, min_length=1, max_length=128)
    origin: Optional[str] = Field(default=None, min_length=1, max_length=128)
    season: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, min_length=1)


class ProductUpdateResponse(BaseModel):
    status: str
    product: ProductOut
    changed_fields: list[str] = Field(default_factory=list)
    actor: str
    timestamp: datetime


class InventoryEventOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    actor: str
    operation: str
    quantity_delta: int
    new_stock: int
    created_at: datetime


class InventoryEventsResponse(BaseModel):
    total: int
    items: list[InventoryEventOut]


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
