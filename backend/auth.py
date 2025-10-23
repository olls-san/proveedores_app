# backend/auth.py
"""Authentication utilities and JWT helpers for the supplier sales MVP."""

from datetime import datetime, timedelta
from typing import Optional
import os

from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .models import Supplier
from .database import SessionLocal

# ==== CONFIG JWT ====
# In production, set SECRET_KEY in environment variables. Fallback to a placeholder.
SECRET_KEY = os.getenv("SECRET_KEY", "change_me_to_a_secure_random_string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h

# ==== HASHING ====
# bcrypt_sha256 avoids the 72-byte limit of classic bcrypt.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

# OAuth2 scheme to extract Bearer token from requests
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, password_hash)


def get_password_hash(password: str) -> str:
    """Hash a password for storing in the database."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token embedding the provided data.

    The `data` dict must contain serialisable values. A default expiration is added
    if none is provided.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, email: str, password: str) -> Optional[Supplier]:
    """Authenticate a user by email and password.

    Returns the user instance if authentication succeeds, otherwise None.
    """
    user = db.query(Supplier).filter(Supplier.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """Extract the user ID from a bearer token.

    The JWT is expected to contain a `sub` claim storing the user ID.
    Raises HTTP 401 if the token is invalid or missing the claim.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        return int(sub)
    except JWTError:
        raise credentials_exception
