import json
import logging
import os
from typing import Generator, List, Optional
from urllib.parse import urlsplit

import firebase_admin
from fastapi import Depends, FastAPI, Header, HTTPException, status
from firebase_admin import auth, credentials
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Float, Integer, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

app = FastAPI(
    title="API de Citas de Barbería",
    description="API REST para crear, consultar, actualizar y eliminar turnos de barbería.",
    version="1.0.0",
)

logger = logging.getLogger(__name__)


def _database_url() -> str:
    # Render supplies this variable at runtime; trim accidental pasted whitespace.
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url or not raw_url.strip():
        if os.getenv("RENDER", "").lower() == "true":
            logger.error("DATABASE_URL no está configurada en Render.")
            raise RuntimeError("DATABASE_URL no está configurada en Render.")
        logger.warning("DATABASE_URL no configurada; usando SQLite local.")
        return "sqlite:///./barberia.db"

    url = raw_url.strip()
    safe_url = url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url
    parsed_url = urlsplit(safe_url)
    try:
        host = parsed_url.hostname or "sin-host"
        port = parsed_url.port or "predeterminado"
    except ValueError:
        host, port = "URL-inválida", "inválido"
    logger.info(
        "DATABASE_URL configurada: esquema=%s host=%s puerto=%s espacios_exteriores_recortados=%s",
        parsed_url.scheme or "sin-esquema",
        host,
        port,
        raw_url != url,
    )
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if (".supabase.co" in url or ".supabase.com" in url) and "sslmode=" not in url:
        url += "&sslmode=require" if "?" in url else "?sslmode=require"
    return url


DATABASE_URL = _database_url()
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class ORMBase(DeclarativeBase):
    pass


class CitaRegistro(ORMBase):
    __tablename__ = "citas_barberia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre_cliente: Mapped[str] = mapped_column(String(120), nullable=False)
    servicio_solicitado: Mapped[str] = mapped_column(String(120), nullable=False)
    precio_servicio: Mapped[float] = mapped_column(Float, nullable=False)
    atendido: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verificar_usuario(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    """Verifica tokens Firebase cuando se configura el servicio; en local permite desarrollo."""
    service_account = os.getenv("FIREBASE_CREDENTIALS_JSON")
    auth_required = os.getenv("REQUIRE_FIREBASE_AUTH", "false").lower() == "true"
    if not service_account:
        if auth_required:
            raise HTTPException(status_code=503, detail="Firebase Auth no está configurado.")
        return None

    try:
        try:
            firebase_app = firebase_admin.get_app()
        except ValueError:
            firebase_app = firebase_admin.initialize_app(
                credentials.Certificate(json.loads(service_account))
            )
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Se requiere un token Firebase Bearer.")
        token = authorization.split(" ", 1)[1]
        return auth.verify_id_token(token, app=firebase_app)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=401, detail="Token Firebase inválido.") from error


@app.get("/")
def inicio():
    return {"mensaje": "API de Barbería activa", "documentacion": "/docs"}


@app.get("/health")
def salud():
    return {"estado": "ok"}


class CitaBarberia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_cliente: str = Field(min_length=1, max_length=120)
    servicio_solicitado: str = Field(min_length=1, max_length=120)
    precio_servicio: float = Field(gt=0, description="El precio debe ser mayor que 0.")
    atendido: bool = False


class CitaBarberiaUpdate(BaseModel):
    nombre_cliente: str = Field(min_length=1, max_length=120)
    servicio_solicitado: str = Field(min_length=1, max_length=120)
    precio_servicio: float = Field(gt=0, description="El precio debe ser mayor que 0.")
    atendido: bool


@app.on_event("startup")
def preparar_base_de_datos():
    ORMBase.metadata.create_all(bind=engine)
    # Datos de demostración únicamente para una base recién creada.
    with SessionLocal() as db:
        if db.scalar(select(CitaRegistro.id).limit(1)) is None:
            db.add_all(
                [
                    CitaRegistro(
                        id=1,
                        nombre_cliente="Juan Pérez",
                        servicio_solicitado="Corte",
                        precio_servicio=20000,
                        atendido=False,
                    ),
                    CitaRegistro(
                        id=2,
                        nombre_cliente="María Gómez",
                        servicio_solicitado="Barba",
                        precio_servicio=15000,
                        atendido=True,
                    ),
                ]
            )
            db.commit()


@app.get("/api/v1/barberia", response_model=List[CitaBarberia])
def obtener_todas_las_citas(
    db: Session = Depends(get_db), _usuario: Optional[dict] = Depends(verificar_usuario)
):
    return db.scalars(select(CitaRegistro).order_by(CitaRegistro.id)).all()


@app.get("/api/v1/barberia/{cita_id}", response_model=CitaBarberia)
def obtener_cita_por_id(
    cita_id: int,
    db: Session = Depends(get_db),
    _usuario: Optional[dict] = Depends(verificar_usuario),
):
    cita = db.get(CitaRegistro, cita_id)
    if cita:
        return cita
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"La cita con ID {cita_id} no existe.",
    )


@app.post(
    "/api/v1/barberia/",
    response_model=CitaBarberia,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@app.post(
    "/api/v1/barberia",
    response_model=CitaBarberia,
    status_code=status.HTTP_201_CREATED,
)
def crear_cita(
    cita: CitaBarberia,
    db: Session = Depends(get_db),
    _usuario: Optional[dict] = Depends(verificar_usuario),
):
    registro = CitaRegistro(**cita.model_dump())
    db.add(registro)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una cita con el ID {cita.id}.",
        ) from error
    db.refresh(registro)
    return registro


@app.put("/api/v1/barberia/{cita_id}", response_model=CitaBarberia)
def actualizar_cita(
    cita_id: int,
    datos_actualizados: CitaBarberiaUpdate,
    db: Session = Depends(get_db),
    _usuario: Optional[dict] = Depends(verificar_usuario),
):
    cita = db.get(CitaRegistro, cita_id)
    if cita:
        for campo, valor in datos_actualizados.model_dump().items():
            setattr(cita, campo, valor)
        db.commit()
        db.refresh(cita)
        return cita
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No se puede actualizar: la cita con ID {cita_id} no existe.",
    )


@app.delete("/api/v1/barberia/{cita_id}")
def eliminar_cita(
    cita_id: int,
    db: Session = Depends(get_db),
    _usuario: Optional[dict] = Depends(verificar_usuario),
):
    cita = db.get(CitaRegistro, cita_id)
    if cita:
        db.delete(cita)
        db.commit()
        return {"mensaje": f"La cita con ID {cita_id} fue eliminada exitosamente."}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No se puede eliminar: la cita con ID {cita_id} no existe.",
    )
