# backend/models.py
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Numeric, JSON
)
from sqlalchemy.orm import relationship
from .database import Base  # ← usa la ÚNICA Base

class Supplier(Base):
    """Proveedor registrado que puede iniciar sesión."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id_tecopos = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sales = relationship("Sale", back_populates="supplier", cascade="all, delete-orphan")
    conciliations = relationship("Conciliation", back_populates="supplier", cascade="all, delete-orphan")
    inventory_snapshots = relationship("InventorySnapshot", back_populates="supplier", cascade="all, delete-orphan")


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
