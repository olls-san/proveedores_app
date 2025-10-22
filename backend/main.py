# backend/main.py
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import SessionLocal, engine
from .models import Supplier
from .schemas import SupplierCreate, SupplierResponse, Token
from .auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user_id,
)

# Crear tablas una sola vez al iniciar la app
from .database import Base
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Proveedores MVP API")

# CORS (ajusta orígenes según tu frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pon tu dominio de frontend en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencia DB por request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------- RUTAS DE AUTH ---------
@app.post("/auth/register", response_model=SupplierResponse, status_code=201)
def register_supplier(user: SupplierCreate, db: Session = Depends(get_db)):
    # Validar unicidad
    if db.query(Supplier).filter(Supplier.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if db.query(Supplier).filter(Supplier.supplier_id_tecopos == user.supplier_id_tecopos).first():
        raise HTTPException(status_code=400, detail="supplier_id_tecopos ya registrado")

    sup = Supplier(
        email=user.email,
        name=user.name,
        supplier_id_tecopos=user.supplier_id_tecopos,
        password_hash=get_password_hash(user.password),
    )
    db.add(sup)
    db.commit()
    db.refresh(sup)
    # Mapeo manual a SupplierResponse (Pydantic maneja aliases/orm_mode)
    return SupplierResponse(
        id=sup.id,
        email=sup.email,
        name=sup.name,
        supplierIdTecopos=sup.supplier_id_tecopos,
        created_at=sup.created_at,
    )


@app.post("/auth/login", response_model=Token)
def login(payload: dict, db: Session = Depends(get_db)):
    """
    Espera JSON: { "email": "...", "password": "..." }
    Devuelve: { "access_token": "...", "token_type": "bearer" }
    """
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y password son requeridos")

    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    access_token = create_access_token({"sub": str(user.id), "email": user.email}, expires_delta=timedelta(days=1))
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=SupplierResponse)
def me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(Supplier).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return SupplierResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        supplierIdTecopos=user.supplier_id_tecopos,
        created_at=user.created_at,
    )

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


