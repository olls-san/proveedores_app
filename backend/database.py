# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Para Render / SQLite local. Si usas Postgres, cambia la URL.
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # requerido por sqlite con threads
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ÚNICA Base global para todos los modelos
Base = declarative_base()
