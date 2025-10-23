# backend/models.py
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from .database import Base  # ← usa la ÚNICA Base

class Supplier(Base):
    """
    Proveedor registrado que puede iniciar sesión.

    Este modelo almacena las credenciales básicas del proveedor junto con los
    identificadores necesarios para operar contra el API de Tecopos. El campo
    `email` es único y sirve como nombre de usuario. Los campos prefijados
    con `tecopos_` sirven para vincular al proveedor local con su respectiva
    entidad remota en Tecopos. Todas ellas son opcionales hasta que se
    complete la vinculación usando los nuevos endpoints.
    """

    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    # Nombre y credenciales de inicio de sesión
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Configuración de Tecopos (puede ser nula si el proveedor no está vinculado)
    tecopos_region = Column(String, index=True, nullable=True)
    tecopos_business_id = Column(String, index=True, nullable=True)
    tecopos_supplier_id = Column(String, index=True, nullable=True)
    tecopos_supplier_name = Column(String, nullable=True)

    # Relaciones
    sales = relationship("Sale", back_populates="supplier", cascade="all, delete-orphan")
    conciliations = relationship("Conciliation", back_populates="supplier", cascade="all, delete-orphan")
    inventory_snapshots = relationship("InventorySnapshot", back_populates="supplier", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"Supplier(id={self.id}, email={self.email!r}, name={self.name!r}, "
            f"region={self.tecopos_region!r}, business_id={self.tecopos_business_id!r}, "
            f"supplier_id={self.tecopos_supplier_id!r})"
        )


class Sale(Base):
    """Datos crudos de ventas traídos del API externo (Tecopos)."""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    date_from = Column(DateTime, nullable=False)
    date_to = Column(DateTime, nullable=False)
    data = Column(JSON, nullable=False)
    total_sales = Column(Numeric(18, 2), nullable=False)
    total_units = Column(Integer, nullable=False)  # entero es lo más natural
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    supplier = relationship("Supplier", back_populates="sales")


class Conciliation(Base):
    """Resumen derivado de una o varias ventas."""
    __tablename__ = "conciliations"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    range_label = Column(String, nullable=False)
    orders = Column(Integer, nullable=False)
    sales_qty = Column(Integer, nullable=False)
    revenue = Column(Numeric(18, 2), nullable=False)
    discounts = Column(Numeric(18, 2), nullable=False)
    total = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    supplier = relationship("Supplier", back_populates="conciliations")


class InventorySnapshot(Base):
    """Snapshot de inventario en un momento dado."""
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    total_quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    supplier = relationship("Supplier", back_populates="inventory_snapshots")

# --- Credenciales de Tecopos ---
class TecoposCredential(Base):
    """
    Almacena el token de acceso a Tecopos para un usuario y región específicos.

    El token se guarda cifrado usando una clave de aplicación (ver backend/crypto.py). Se
    permite guardar también un refresh_token y una fecha de expiración, por si en un
    futuro se desea automatizar la renovación del token.

    El par (user_id, region) es único para evitar duplicados.
    """

    __tablename__ = "tecopos_credentials"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    region = Column(String, nullable=False, index=True)
    access_token_enc = Column(String, nullable=False)
    refresh_token_enc = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("Supplier", backref="tecopos_credentials")

    __table_args__ = (UniqueConstraint("user_id", "region", name="uq_user_region"),)
