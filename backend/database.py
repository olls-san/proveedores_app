"""
Database configuration and models for the supplier sales MVP.

This module defines the SQLAlchemy engine, session, base class and ORM models
used by the FastAPI backend. All tables are created automatically when this
module is imported by main.py.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    JSON,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# SQLite database URL. When deploying in production you can switch to a
# full‑featured database like PostgreSQL by modifying this URI. The
# ``check_same_thread`` argument is required for SQLite to allow multiple
# threads (FastAPI uses threads for each request).
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# A session factory bound to the engine. Each request should create its own
# session via ``SessionLocal`` and close it when finished.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models. All models should inherit from this.
Base = declarative_base()


class Supplier(Base):
    """A registered supplier who can log in to the system.

    ``supplier_id_tecopos`` refers to the identifier used by the external
    Tecopos API. ``email`` is used for login. Passwords are stored as
    bcrypt hashes in ``password_hash``. Relationships are defined to link
    suppliers to their sales, conciliations and inventory snapshots.
    """

    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id_tecopos = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sales = relationship("Sale", back_populates="supplier", cascade="all, delete-orphan")
    conciliations = relationship(
        "Conciliation", back_populates="supplier", cascade="all, delete-orphan"
    )
    inventory_snapshots = relationship(
        "InventorySnapshot", back_populates="supplier", cascade="all, delete-orphan"
    )


class Sale(Base):
    """Raw sales data downloaded from the external Tecopos API.

    The ``data`` column stores the entire JSON payload returned by the API for
    later analysis. ``total_sales`` and ``total_units`` store aggregate
    metrics computed when the sale is downloaded. The ``date_from`` and
    ``date_to`` fields record the range used when querying the API.
    """

    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    date_from = Column(DateTime, nullable=False)
    date_to = Column(DateTime, nullable=False)
    data = Column(JSON, nullable=False)
    total_sales = Column(Numeric(18, 2), nullable=False)
    total_units = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="sales")


class Conciliation(Base):
    """Summary information derived from one or more sales.

    Conciliations allow providers to reconcile their sales over a period of
    time. They can be generated from a single ``Sale`` or from multiple
    historical sales. The business rules for these calculations can be
    extended later.
    """

    __tablename__ = "conciliations"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    range_label = Column(String, nullable=False)
    orders = Column(Integer, nullable=False)
    sales_qty = Column(Integer, nullable=False)
    revenue = Column(Numeric(18, 2), nullable=False)
    discounts = Column(Numeric(18, 2), nullable=False)
    total = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="conciliations")


class InventorySnapshot(Base):
    """Snapshot of the supplier's inventory at a particular moment.

    Only the product identifier, name and total quantity are recorded. More
    fields can be added later (e.g., cost, price, category). Multiple
    snapshots per supplier allow tracking the inventory over time.
    """

    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    total_quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="inventory_snapshots")


# Create all tables if they do not exist. Importing this module in main.py
# triggers the table creation. In production you might handle migrations
# differently (e.g. using Alembic).
Base.metadata.create_all(bind=engine)