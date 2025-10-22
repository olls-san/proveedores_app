# backend/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import relationship
from .database import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    supplier_id_tecopos = Column(Integer, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones opcionales si las necesitas más tarde:
    # conciliations = relationship("Conciliation", back_populates="supplier")

# Modelos mínimos opcionales si los usas en endpoints:
class Conciliation(Base):
    __tablename__ = "conciliations"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, index=True, nullable=False)
    range_label = Column(String(100), nullable=False)
    orders = Column(Integer, default=0, nullable=False)
    sales_qty = Column(Integer, default=0, nullable=False)
    revenue = Column(Float, default=0.0, nullable=False)
    discounts = Column(Float, default=0.0, nullable=False)
    total = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # supplier = relationship("Supplier", back_populates="conciliations")
