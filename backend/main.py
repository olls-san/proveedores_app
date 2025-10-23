# backend/main.py
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import SessionLocal, engine, Base
from .models import Supplier, Conciliation, TecoposCredential
from .schemas import (
    SupplierCreate,
    SupplierResponse,
    Token,
    SaleResponse,  # Legacy placeholder used by /sales
    ConciliationCreate,
    ConciliationResponse,
    InventoryResponse,
    SaveTecoposTokenRequest,
    MaskedCredentialResponse,
    LinkTecoposSupplierRequest,
    SalesQuery,
    SaleItem,
    SalePeriodResponse,
)
from .auth import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user_id,
)

from .crypto import encrypt_str, decrypt_str
from .integrations.tecopos import (
    REGIONS,
    list_businesses_with_token,
    list_suppliers_with_token,
    get_selled_products,
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
    # Verifica que el email no esté ya registrado
    if db.query(Supplier).filter(Supplier.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    # Creamos un nuevo proveedor sin campos de Tecopos. La vinculación se hará
    # posteriormente mediante los endpoints de integración.
    sup = Supplier(
        email=user.email,
        name=user.name,
        password_hash=get_password_hash(user.password),
    )
    db.add(sup)
    db.commit()
    db.refresh(sup)

    # Construye la respuesta incluyendo los nuevos campos (nulos por defecto) y
    # mantiene supplierIdTecopos para compatibilidad del frontend existente.
    supplier_id_int: int | None = None
    if sup.tecopos_supplier_id and str(sup.tecopos_supplier_id).isdigit():
        supplier_id_int = int(sup.tecopos_supplier_id)
    return SupplierResponse(
        id=sup.id,
        email=sup.email,
        name=sup.name,
        created_at=sup.created_at,
        tecopos_region=sup.tecopos_region,
        tecopos_business_id=sup.tecopos_business_id,
        tecopos_supplier_id=sup.tecopos_supplier_id,
        tecopos_supplier_name=sup.tecopos_supplier_name,
        supplierIdTecopos=supplier_id_int,
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
    """Devuelve la información del usuario actual incluyendo datos de Tecopos."""
    user = db.query(Supplier).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    sid_int: int | None = None
    if user.tecopos_supplier_id and str(user.tecopos_supplier_id).isdigit():
        sid_int = int(user.tecopos_supplier_id)
    return SupplierResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        tecopos_region=user.tecopos_region,
        tecopos_business_id=user.tecopos_business_id,
        tecopos_supplier_id=user.tecopos_supplier_id,
        tecopos_supplier_name=user.tecopos_supplier_name,
        supplierIdTecopos=sid_int,
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


# --------- Integraciones con Tecopos ---------

@app.get("/regions")
def get_regions():
    """Devuelve la lista de regiones disponibles para Tecopos."""
    # Devuelve pares clave/etiqueta para ser consumidos por el frontend
    return [
        {"key": region, "label": f"Región {idx + 1}"}
        for idx, region in enumerate(REGIONS)
    ]


@app.post("/me/tecopos/save-token", response_model=MaskedCredentialResponse)
def save_token_and_link_business(
    payload: SaveTecoposTokenRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Guarda el token de Tecopos para un usuario y vincula el negocio por nombre.

    El token nunca se devuelve en claro. Se almacena cifrado en la base de datos.
    """
    # Validar región
    if payload.region not in REGIONS:
        raise HTTPException(status_code=400, detail="Región inválida")
    # Obtener usuario
    user = db.query(Supplier).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Validar token listando negocios
    try:
        businesses = list_businesses_with_token(payload.region, payload.access_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token inválido o error de acceso en {payload.region}: {e}")
    # Resolver el negocio por nombre (normaliza a minúsculas y quita espacios)
    q = payload.business_name.strip().lower()
    exact = [b for b in businesses if str(b.get("name", "")).strip().lower() == q]
    chosen = None
    if len(exact) == 1:
        chosen = exact[0]
    elif len(businesses) == 1:
        chosen = businesses[0]
    if not chosen:
        names = [b.get("name") for b in businesses]
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró un negocio único. Disponibles: {names[:8]}",
        )
    # Extraer businessId (varía según API de Tecopos)
    business_id = str(chosen.get("id") or chosen.get("businessId") or "")
    if not business_id:
        raise HTTPException(status_code=502, detail="La respuesta de Tecopos no contiene businessId")
    # Guardar o actualizar la credencial cifrada
    cred = (
        db.query(TecoposCredential)
        .filter(TecoposCredential.user_id == user_id, TecoposCredential.region == payload.region)
        .first()
    )
    from datetime import datetime as _dt

    token_enc = encrypt_str(payload.access_token)
    if cred:
        cred.access_token_enc = token_enc
        cred.updated_at = _dt.utcnow()
    else:
        cred = TecoposCredential(
            user_id=user_id,
            region=payload.region,
            access_token_enc=token_enc,
        )
        db.add(cred)
    # Actualizar usuario con región y business ID
    user.tecopos_region = payload.region
    user.tecopos_business_id = business_id
    db.add(user)
    db.commit()
    return MaskedCredentialResponse(
        region=payload.region,
        business_name=chosen.get("name"),
        has_token=True,
        expires_at=None,
    )


@app.post("/me/link-tecopos-supplier")
def link_tecopos_supplier_endpoint(
    payload: LinkTecoposSupplierRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Vincula el proveedor local con su identificador remoto en Tecopos."""
    user = db.query(Supplier).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if not user.tecopos_region or not user.tecopos_business_id:
        raise HTTPException(status_code=400, detail="Primero vincula región y negocio")
    # Recuperar credencial para la región
    cred = (
        db.query(TecoposCredential)
        .filter(TecoposCredential.user_id == user_id, TecoposCredential.region == user.tecopos_region)
        .first()
    )
    if not cred:
        raise HTTPException(status_code=401, detail="Falta token Tecopos para esta región")
    # Descifrar token
    access_token = decrypt_str(cred.access_token_enc)
    # Buscar proveedor por nombre
    try:
        found = list_suppliers_with_token(
            user.tecopos_region, user.tecopos_business_id, access_token, payload.supplier_name
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error buscando proveedor en Tecopos: {e}")
    q = payload.supplier_name.strip().lower()
    exact = [it for it in found if str(it.get("name", "")).strip().lower() == q]
    chosen = None
    if len(exact) == 1:
        chosen = exact[0]
    elif len(found) == 1:
        chosen = found[0]
    if not chosen:
        names = [it.get("name") for it in found]
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró un proveedor único. Coincidencias: {names[:8]}",
        )
    # Guardar identificadores en el usuario
    user.tecopos_supplier_id = str(chosen.get("id")) if chosen.get("id") is not None else None
    user.tecopos_supplier_name = chosen.get("name") or payload.supplier_name
    db.add(user)
    db.commit()
    return {"ok": True, "linked_supplier": user.tecopos_supplier_name}


@app.post("/sales/period", response_model=SalePeriodResponse)
def get_sales_period_endpoint(
    payload: SalesQuery,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Obtiene el resumen de ventas en el rango de fechas indicado."""
    user = db.query(Supplier).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if not user.tecopos_region or not user.tecopos_business_id:
        raise HTTPException(status_code=400, detail="Falta vincular región y negocio para este proveedor")
    # Recuperar credencial
    cred = (
        db.query(TecoposCredential)
        .filter(TecoposCredential.user_id == user_id, TecoposCredential.region == user.tecopos_region)
        .first()
    )
    if not cred:
        raise HTTPException(status_code=401, detail="Falta token Tecopos para esta región")
    access_token = decrypt_str(cred.access_token_enc)
    # Llamar al API de Tecopos
    try:
        raw = get_selled_products(
            user.tecopos_region,
            user.tecopos_business_id,
            access_token,
            payload.date_from.strftime("%Y-%m-%d"),
            payload.date_to.strftime("%Y-%m-%d"),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error consultando ventas en Tecopos: {e}")
    # Filtrar por proveedor (por ID si está vinculado o por nombre en caso contrario)
    id_str = user.tecopos_supplier_id.strip() if user.tecopos_supplier_id else None
    name_norm = (user.tecopos_supplier_name or user.name).strip().lower()
    items: list[SaleItem] = []
    total_units = 0.0
    total_sales = 0.0
    for it in raw:
        sid = str(it.get("supplierId") or it.get("supplier_id") or "")
        sname = str(it.get("supplierName") or it.get("supplier_name") or "").strip().lower()
        belongs = True
        if id_str:
            belongs = sid == id_str
        else:
            belongs = sname == name_norm
        if not belongs:
            continue
        # Extrae cantidades y totales usando claves comunes
        q_raw = (
            it.get("quantity")
            or it.get("quantitySales")
            or it.get("units")
            or it.get("quantity_sales")
            or 0
        )
        amt_raw = (
            it.get("total")
            or it.get("totalSales")
            or it.get("total_amount")
            or it.get("totalSalesMainCurrency")
            or 0
        )
        try:
            q = float(q_raw)
        except Exception:
            q = 0.0
        try:
            amt = float(amt_raw)
        except Exception:
            amt = 0.0
        items.append(
            SaleItem(
                product_id=str(
                    it.get("productId")
                    or it.get("product_id")
                    or it.get("id")
                    or ""
                ),
                product_name=it.get("productName") or it.get("name") or None,
                quantity=q,
                total_amount=amt,
                currency=it.get("currency") or None,
            )
        )
        total_units += q
        total_sales += amt
    return SalePeriodResponse(
        supplier_id=user.id,
        supplier_name=user.name,
        total_sales=round(total_sales, 2),
        total_units=round(total_units, 2),
        date_from=payload.date_from,
        date_to=payload.date_to,
        data=items,
    )

