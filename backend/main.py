# backend/main.py
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from .models import Supplier, Conciliation
from .schemas import (
    SupplierCreate,
    SupplierResponse,
    Token,
    SaleResponse,
    ConciliationCreate,
    ConciliationResponse,
    InventoryResponse,
)
from .auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user_id,
)

# Crear tablas una sola vez al iniciar la app
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Proveedores MVP API")

# Ajusta allow_origins a tu dominio de frontend en producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------- AUTH ---------
@app.post("/auth/register", response_model=SupplierResponse, status_code=201)
def register_supplier(user: SupplierCreate, db: Session = Depends(get_db)):
    if db.query(Supplier).filter(Supplier.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if db.query(Supplier).filter(Supplier.supplier_id_tecopos == user.supplierIdTecopos).first():
        raise HTTPException(status_code=400, detail="supplier_id_tecopos ya registrado")

    sup = Supplier(
        email=user.email,
        name=user.name,
        supplier_id_tecopos=user.supplierIdTecopos,
        password_hash=get_password_hash(user.password),
    )
    db.add(sup)
    db.commit()
    db.refresh(sup)

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
    Espera: { "email": "...", "password": "..." }
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


# --------- ENDPOINTS PARA EL DASHBOARD (mínimos y seguros) ---------

# GET /sales → Resumen simple para que el frontend pinte el dashboard.
@app.get("/sales", response_model=SaleResponse)
def get_sales_summary(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    # Aquí podrías calcular con tus tablas reales; devolvemos un placeholder coherente
    # para evitar caídas del frontend mientras integras la fuente real.
    return SaleResponse(
        totalSales=0.0,
        totalUnits=0.0,
        dateFrom=None,
        dateTo=None,
        data=None,
    )


# GET /conciliations → lista
@app.get("/conciliations", response_model=list[ConciliationResponse])
def list_conciliations(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    cons = (
        db.query(Conciliation)
        .filter(Conciliation.supplier_id == user_id)
        .order_by(Conciliation.created_at.desc())
        .all()
    )
    return [
        ConciliationResponse(
            id=c.id,
            supplier_id=c.supplier_id,
            rangeLabel=c.range_label,
            orders=c.orders,
            salesQty=c.sales_qty,
            revenue=float(c.revenue),
            discounts=float(c.discounts),
            total=float(c.total),
            created_at=c.created_at,
        )
        for c in cons
    ]


# POST /conciliations → crea una conciliación básica (campos mínimos)
@app.post("/conciliations", response_model=ConciliationResponse, status_code=201)
def create_conciliation(
    body: ConciliationCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    total = float(body.revenue) - float(body.discounts)
    c = Conciliation(
        supplier_id=user_id,
        range_label=body.rangeLabel,
        orders=body.orders,
        sales_qty=body.salesQty,
        revenue=body.revenue,
        discounts=body.discounts,
        total=total,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return ConciliationResponse(
        id=c.id,
        supplier_id=c.supplier_id,
        rangeLabel=c.range_label,
        orders=c.orders,
        salesQty=c.sales_qty,
        revenue=float(c.revenue),
        discounts=float(c.discounts),
        total=float(c.total),
        created_at=c.created_at,
    )


# GET /inventory → estructura simple para que el frontend pinte una tabla
@app.get("/inventory", response_model=InventoryResponse)
def get_inventory(user_id: int = Depends(get_current_user_id)):
    # Devuelve vacío por ahora; el frontend no crashea.
    return InventoryResponse(items=[])

