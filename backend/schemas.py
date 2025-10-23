"""
Pydantic models for request and response bodies.

These schemas define the shape of data exchanged via the API. They are
separated from the ORM models to avoid accidental leakage of internal
database state and to provide input validation.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

# -------- Auth ---------
class Token(BaseModel):
    """Model returned after successful authentication."""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Data stored inside the JWT payload (deprecated, kept for compatibility)."""
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

# -------- Sales --------
class SaleProduct(BaseModel):
    """Representation of a single product's sales. Optional placeholder for future use."""
    productId: Optional[int] = None
    name: Optional[str] = None
    quantitySales: Optional[int] = None
    totalQuantity: Optional[int] = None
    totalSales: Optional[float] = None
    totalSalesMainCurrency: Optional[float] = None

class SaleResponse(BaseModel):
    """Summary of sales for a date range.

    Fields mirror the expected response shape used by the frontend dashboard. At minimum,
    include aggregated totals and optionally a list of products and sale identifier.
    """
    saleId: Optional[int] = None
    products: Optional[List[SaleProduct]] = None
    totalSales: float = 0.0
    totalUnits: float = 0.0
    dateFrom: Optional[datetime] = None
    dateTo: Optional[datetime] = None
    data: Optional[dict] = None

# -------- Conciliations --------
class ConciliationCreate(BaseModel):
    """Request body for creating a conciliation from a sale.

    Only the sale identifier is required; the backend will compute summary fields.
    """
    sale_id: int

class ConciliationResponse(BaseModel):
    id: int
    supplier_id: int
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
