"""
Pydantic models for request and response bodies.

These schemas define the shape of data exchanged via the API. They are
separated from the ORM models to avoid accidental leakage of internal
database state and to provide input validation.
"""

# backend/schemas.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic import BaseModel, Field, ConfigDict


# ----------------------------
# Auth
# ----------------------------
class Token(BaseModel):
    """Model returned after successful authentication."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data stored inside the JWT payload."""
    id: Optional[int] = None
    email: Optional[str] = None


# -------- Supplier --------
class SupplierCreate(BaseModel):
    email: str
    name: str
    supplierIdTecopos: int = Field(..., description="ID usado en Tecopos")
    password: str


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    email: str
    name: str
    supplierIdTecopos: int = Field(..., alias="supplierIdTecopos")
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------- Sales --------
class SaleResponse(BaseModel):
    # Resumen para dashboard
    totalSales: float = 0.0
    totalUnits: float = 0.0
    dateFrom: Optional[datetime] = None
    dateTo: Optional[datetime] = None
    # Campo opcional por si devuelves el JSON crudo
    data: Optional[dict] = None


# -------- Conciliations --------
class ConciliationCreate(BaseModel):
    rangeLabel: str
    orders: int = 0
    salesQty: int = 0
    revenue: float = 0.0
    discounts: float = 0.0


class ConciliationResponse(BaseModel):
    id: int
    supplierId: int = Field(..., alias="supplier_id")
    rangeLabel: str
    orders: int
    salesQty: int
    revenue: float
    discounts: float
    total: float
    created_at: datetime


# -------- Inventory --------
class InventoryItem(BaseModel):
    productId: int
    name: str
    totalQuantity: int


class InventoryResponse(BaseModel):
    items: List[InventoryItem] = []
