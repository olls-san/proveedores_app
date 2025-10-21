"""
Main FastAPI application entry point.

This module defines the API routes for authentication, sales queries,
conciliations and inventory. It ties together the database models,
authentication utilities and simulated external API access.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from .database import Sale, Supplier, InventorySnapshot, Conciliation
from .schemas import (
    SupplierCreate,
    SupplierResponse,
    Token,
    SaleResponse,
    SaleProduct,
    ConciliationCreate,
    ConciliationResponse,
    InventoryItem,
)
from .auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
    get_password_hash,
)

app = FastAPI(title="Supplier Sales MVP")

# Allow all origins for demonstration. In production you should set this to
# the domain hosting your frontend to prevent other sites from accessing your
# API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/register", response_model=SupplierResponse, status_code=201)
def register_supplier(user: SupplierCreate, db: Session = Depends(get_db)):
    """Register a new supplier.

    A new supplier can sign up by providing an email, password, name and the
    external Tecopos supplier ID. Passwords are stored as bcrypt hashes.
    """

    existing = db.query(Supplier).filter(Supplier.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )
    supplier = Supplier(
        email=user.email,
        name=user.name,
        supplier_id_tecopos=user.supplier_id_tecopos,
        password_hash=get_password_hash(user.password),
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@app.post("/auth/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Authenticate a supplier and return an access token."""

    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"id": user.id})
    return Token(access_token=access_token)


def simulate_tecopos_api(date_from: str, date_to: str, supplier_id: int):
    """Simulate data returned by the external Tecopos API.

    In a real deployment this function would perform an HTTP request to the
    Tecopos API using ``requests`` or ``httpx``. Because network access is
    unavailable in this environment, we return deterministic dummy data
    representing product sales. The structure matches the sample provided by
    the user.

    Each call returns the same three products with quantities depending on
    the date range (longer ranges yield more units).
    """

    # Calculate a multiplier based on the date range length in days to
    # simulate varying sales volumes.
    try:
        start_dt = datetime.strptime(date_from, "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(date_to, "%Y-%m-%d %H:%M")
    except ValueError:
        # Fallback if time component is not provided
        start_dt = datetime.strptime(date_from.split(" ")[0], "%Y-%m-%d")
        end_dt = datetime.strptime(date_to.split(" ")[0], "%Y-%m-%d")
    days = max((end_dt - start_dt).days, 1)
    multiplier = max(days // 5, 1)
    products = []
    sample_products = [
        {
            "productId": 137187,
            "name": "Aceite Mini",
            "quantitySales": 50 * multiplier,
            "totalQuantity": 200 * multiplier,
            "totalSales": 350.0 * multiplier,
            "totalSalesMainCurrency": 87500.0 * multiplier,
        },
        {
            "productId": 137188,
            "name": "Arroz Paquete",
            "quantitySales": 80 * multiplier,
            "totalQuantity": 300 * multiplier,
            "totalSales": 640.0 * multiplier,
            "totalSalesMainCurrency": 160000.0 * multiplier,
        },
        {
            "productId": 137189,
            "name": "Frijoles Bolsa",
            "quantitySales": 30 * multiplier,
            "totalQuantity": 120 * multiplier,
            "totalSales": 240.0 * multiplier,
            "totalSalesMainCurrency": 60000.0 * multiplier,
        },
    ]
    products.extend(sample_products)
    return {"products": products}


@app.get("/sales", response_model=SaleResponse)
def fetch_sales(
    dateFrom: str,
    dateTo: str,
    supplierId: int,
    db: Session = Depends(get_db),
    current_user: Supplier = Depends(get_current_user),
):
    """Download sales for a supplier and persist them.

    The authenticated user can request sales for a specific supplier ID and
    date range. In this demo the data is simulated; in production it would
    be fetched from the Tecopos API. The result is stored in the ``sales``
    table and a summary is returned to the client.
    """

    # Only allow fetching data for the authenticated supplier's Tecopos ID
    if current_user.supplier_id_tecopos != supplierId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access other suppliers' data.",
        )

    # Simulate external API call
    api_data = simulate_tecopos_api(dateFrom, dateTo, supplierId)
    products = []
    total_sales = 0.0
    total_units = 0
    for prod in api_data["products"]:
        # Sum totals from either main currency or fallback list
        main_currency = prod.get("totalSalesMainCurrency")
        if main_currency is not None:
            total_sales += float(main_currency)
        else:
            total_sales += float(prod.get("totalSales", 0.0))
        total_units += int(prod.get("quantitySales", 0))
        products.append(
            SaleProduct(
                productId=prod["productId"],
                name=prod["name"],
                quantitySales=int(prod["quantitySales"]),
                totalQuantity=int(prod["totalQuantity"]),
                totalSales=float(prod["totalSales"]),
                totalSalesMainCurrency=float(prod["totalSalesMainCurrency"]),
            )
        )

    # Persist the sale in the database
    sale_record = Sale(
        supplier_id=current_user.id,
        date_from=datetime.strptime(dateFrom, "%Y-%m-%d %H:%M"),
        date_to=datetime.strptime(dateTo, "%Y-%m-%d %H:%M"),
        data=api_data,
        total_sales=total_sales,
        total_units=total_units,
    )
    db.add(sale_record)
    db.commit()
    db.refresh(sale_record)

    # Update inventory snapshot: insert new snapshot rows
    for prod in api_data["products"]:
        snapshot = InventorySnapshot(
            supplier_id=current_user.id,
            product_id=prod["productId"],
            name=prod["name"],
            total_quantity=int(prod["totalQuantity"]),
        )
        db.add(snapshot)
    db.commit()

    return SaleResponse(
        saleId=sale_record.id,
        products=products,
        totalSales=total_sales,
        totalUnits=total_units,
    )


@app.post("/conciliations", response_model=ConciliationResponse, status_code=201)
def create_conciliation(
    body: ConciliationCreate,
    db: Session = Depends(get_db),
    current_user: Supplier = Depends(get_current_user),
):
    """Create a conciliation from a previously stored sale.

    The client provides a sale ID. The server computes summary metrics and
    stores them as a conciliation. In this simple implementation the order
    count is derived from the number of products in the sale data and
    discounts are zero because sample data does not include discounts.
    """

    sale = db.query(Sale).filter(Sale.id == body.sale_id, Sale.supplier_id == current_user.id).first()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found.")
    # Extract data
    products = sale.data.get("products", [])
    orders = len(products)
    sales_qty = sum(int(p.get("quantitySales", 0)) for p in products)
    revenue = float(sale.total_sales)
    discounts = 0.0
    total = revenue - discounts
    range_label = f"{sale.date_from.strftime('%d %b %Y')} – {sale.date_to.strftime('%d %b %Y')}"
    conc = Conciliation(
        supplier_id=current_user.id,
        range_label=range_label,
        orders=orders,
        sales_qty=sales_qty,
        revenue=revenue,
        discounts=discounts,
        total=total,
    )
    db.add(conc)
    db.commit()
    db.refresh(conc)
    return ConciliationResponse(
        id=conc.id,
        range_label=conc.range_label,
        orders=conc.orders,
        sales_qty=conc.sales_qty,
        revenue=float(conc.revenue),
        discounts=float(conc.discounts),
        total=float(conc.total),
        created_at=conc.created_at,
    )


@app.get("/conciliations", response_model=List[ConciliationResponse])
def list_conciliations(
    db: Session = Depends(get_db), current_user: Supplier = Depends(get_current_user)
) -> List[ConciliationResponse]:
    """Return all conciliations for the current supplier."""

    concs = (
        db.query(Conciliation)
        .filter(Conciliation.supplier_id == current_user.id)
        .order_by(Conciliation.created_at.desc())
        .all()
    )
    return [
        ConciliationResponse(
            id=c.id,
            range_label=c.range_label,
            orders=c.orders,
            sales_qty=c.sales_qty,
            revenue=float(c.revenue),
            discounts=float(c.discounts),
            total=float(c.total),
            created_at=c.created_at,
        )
        for c in concs
    ]


@app.get("/inventory", response_model=List[InventoryItem])
def get_inventory(
    db: Session = Depends(get_db), current_user: Supplier = Depends(get_current_user)
) -> List[InventoryItem]:
    """Return the latest inventory snapshot for each product.

    We select the most recent snapshot per product. In a production system
    additional logic might filter by date or compute the current quantity
    based on movements.
    """

    # Get the latest snapshot ID per product
    # Subquery to find latest snapshot id per product and supplier
    subq = (
        db.query(
            InventorySnapshot.product_id,
            InventorySnapshot.name,
            InventorySnapshot.total_quantity,
            InventorySnapshot.created_at,
        )
        .filter(InventorySnapshot.supplier_id == current_user.id)
        .order_by(InventorySnapshot.product_id, InventorySnapshot.created_at.desc())
        .all()
    )
    # Use dictionary to keep the latest entry per product
    latest = {}
    for p_id, name, qty, created_at in subq:
        if p_id not in latest:
            latest[p_id] = (name, qty)
    return [InventoryItem(product_id=pid, name=name, total_quantity=qty) for pid, (name, qty) in latest.items()]


@app.get("/me", response_model=SupplierResponse)
def read_current_user(
    current_user: Supplier = Depends(get_current_user),
) -> SupplierResponse:
    """Return details about the currently authenticated user."""

    return SupplierResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        supplier_id_tecopos=current_user.supplier_id_tecopos,
        created_at=current_user.created_at,
    )