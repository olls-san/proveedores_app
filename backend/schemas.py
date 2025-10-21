"""
Pydantic models for request and response bodies.

These schemas define the shape of data exchanged via the API. They are
separated from the ORM models to avoid accidental leakage of internal
database state and to provide input validation.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """Model returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data stored inside the JWT payload."""

    id: Optional[int] = None
    email: Optional[str] = None


class SupplierBase(BaseModel):
    """Base attributes shared by supplier models."""

    email: str
    name: str
    supplier_id_tecopos: int = Field(..., alias="supplierIdTecopos")


class SupplierCreate(SupplierBase):
    """Attributes required to register a new supplier."""

    password: str


class SupplierResponse(SupplierBase):
    """Public representation of a supplier."""

    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class SaleProduct(BaseModel):
    """Representation of a single product's sales for the UI."""

    productId: int
    name: str
    quantitySales: int
    totalQuantity: int
    totalSales: float
    totalSalesMainCurrency: Optional[float] = None


class SaleResponse(BaseModel):
    """Returned when a sale query is performed.

    ``saleId`` is returned so that the client can reference this sale when
    creating a conciliation. Without it, the client would have to query
    the list of sales to obtain the most recent record.
    """

    saleId: int
    products: List[SaleProduct]
    totalSales: float
    totalUnits: int


class ConciliationCreate(BaseModel):
    """Body for creating a conciliation from an existing sale."""

    sale_id: int


class ConciliationResponse(BaseModel):
    """Representation of a conciliation record for the UI."""

    id: int
    range_label: str
    orders: int
    sales_qty: int
    revenue: float
    discounts: float
    total: float
    created_at: datetime

    class Config:
        orm_mode = True


class InventoryItem(BaseModel):
    """Simplified representation of an inventory snapshot."""

    product_id: int
    name: str
    total_quantity: int

    class Config:
        orm_mode = True