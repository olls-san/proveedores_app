# backend/auth.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from . import models

# ==== CONFIG JWT ====
# SUGERENCIA: en Render define SECRET_KEY como variable de entorno y léela con os.getenv.
SECRET_KEY = "change-me-in-env"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# ==== HASHING ====
# bcrypt_sha256 evita el límite de 72 bytes en contraseñas largas.
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)

def get_password_hash(password: str) -> str:
    if len(password) > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña es demasiado larga (máx. 256 caracteres).",
        )
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ==== LOOKUP USUARIO ====
def get_user_by_email(db: Session, email: str) -> Optional[models.Supplier]:
    return db.query(models.Supplier).filter(models.Supplier.email == email).first()

# ==== AUTENTICACIÓN ====
def authenticate_user(db: Session, email: str, password: str) -> Optional[models.Supplier]:
    """
    Devuelve el Supplier si las credenciales son válidas; de lo contrario, None.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

# ==== TOKENS ====
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    payload = decode_token(token)
    uid = payload.get("sub")
    if uid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return int(uid)

