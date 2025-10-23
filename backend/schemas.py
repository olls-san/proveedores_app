"""
Pydantic models for request and response bodies.

These schemas define the shape of data exchanged via the API. They are
separated from the ORM models to avoid accidental leakage of internal
database state and to provide input validation.
"""

from datetime import datetime, date
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
    """
    Esquema de entrada para registrar un proveedor.

    A diferencia de versiones anteriores, el identificador del proveedor en
    Tecopos ya no se solicita en el registro. La vinculación con Tecopos
    se realiza posteriormente mediante los endpoints de integración.
    """

    email: str
    name: str
    password: str

class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    email: str
    name: str
    created_at: datetime
    # Campos opcionales de vinculación con Tecopos. No se exponen alias para no
    # obligar al frontend a usar los nombres internos de la base de datos.
    tecopos_region: Optional[str] = None
    tecopos_business_id: Optional[str] = None
    tecopos_supplier_id: Optional[str] = None
    tecopos_supplier_name: Optional[str] = None

    # Campo de compatibilidad legado (antiguo supplierIdTecopos) — se rellena
    # con el valor de tecopos_supplier_id para mantener el comportamiento del
    # dashboard existente. Si no hay vinculación, es None.
    supplierIdTecopos: Optional[int] = Field(default=None, alias="supplierIdTecopos")

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
    """
    Request body for creating a conciliation entry.

    Se proporcionan los datos agregados de un periodo de ventas. La aplicación
    no extrae esta información automáticamente (todavía), por lo que el
    frontend debe enviar los valores calculados. Los campos siguen la
    estructura esperada por el endpoint `/conciliations`.
    """
    rangeLabel: str
    orders: int
    salesQty: int
    revenue: float
    discounts: float

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

# ----- Tecopos Integrations -----

class SaveTecoposTokenRequest(BaseModel):
    """Petición para guardar el token de Tecopos y vincular el negocio por nombre."""

    region: str = Field(..., description="Identificador de la región: api, api2, api3 o api4")
    business_name: str = Field(..., description="Nombre del negocio en Tecopos")
    access_token: str = Field(..., description="Token Bearer obtenido de Tecopos (incluye el prefijo Bearer)")


class MaskedCredentialResponse(BaseModel):
    """
    Respuesta tras guardar o consultar la credencial de Tecopos.

    Para proteger la seguridad, no se devuelve el token en claro. Se indica
    simplemente si existe (`has_token`) y la fecha de expiración si está
    disponible.
    """

    region: str
    business_name: str
    has_token: bool
    expires_at: Optional[str] = None


class LinkTecoposSupplierRequest(BaseModel):
    """Petición para vincular el proveedor con su identificador en Tecopos."""

    supplier_name: str = Field(..., description="Nombre exacto del proveedor tal como aparece en Tecopos")


class SalesQuery(BaseModel):
    """
    Rango de fechas para consultar las ventas. Las fechas deben ser
    proporcionadas en formato YYYY-MM-DD. Se validan como objetos date.
    """

    date_from: date
    date_to: date


class SaleItem(BaseModel):
    """Detalles de un producto vendido en un periodo."""

    product_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity: float
    total_amount: float
    currency: Optional[str] = None


class SalePeriodResponse(BaseModel):
    """
    Respuesta para el endpoint de ventas por periodo. Resume las ventas
    del proveedor autenticado dentro del rango solicitado.
    """

    supplier_id: int
    supplier_name: str
    total_sales: float
    total_units: float
    date_from: date
    date_to: date
    data: List[SaleItem] = []
