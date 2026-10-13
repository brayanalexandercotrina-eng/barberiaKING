from typing import List

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="API de Citas de Barbería",
    description="API REST para crear, consultar, actualizar y eliminar turnos de barbería.",
    version="1.0.0",
)


class CitaBarberia(BaseModel):
    id: int
    nombre_cliente: str
    servicio_solicitado: str
    precio_servicio: float = Field(gt=0, description="El precio debe ser mayor que 0.")
    atendido: bool = False


class CitaBarberiaUpdate(BaseModel):
    nombre_cliente: str
    servicio_solicitado: str
    precio_servicio: float = Field(gt=0, description="El precio debe ser mayor que 0.")
    atendido: bool


db_citas: List[CitaBarberia] = [
    CitaBarberia(
        id=1,
        nombre_cliente="Juan Pérez",
        servicio_solicitado="Corte",
        precio_servicio=20000,
        atendido=False,
    ),
    CitaBarberia(
        id=2,
        nombre_cliente="María Gómez",
        servicio_solicitado="Barba",
        precio_servicio=15000,
        atendido=True,
    ),
]


@app.get("/api/v1/citas", response_model=List[CitaBarberia])
def obtener_todas_las_citas():
    return db_citas


@app.get("/api/v1/citas/{cita_id}", response_model=CitaBarberia)
def obtener_cita_por_id(cita_id: int):
    for cita in db_citas:
        if cita.id == cita_id:
            return cita
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"La cita con ID {cita_id} no existe.",
    )


@app.post(
    "/api/v1/citas/",
    response_model=CitaBarberia,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@app.post(
    "/api/v1/citas",
    response_model=CitaBarberia,
    status_code=status.HTTP_201_CREATED,
)
def crear_cita(cita: CitaBarberia):
    if any(cita_existente.id == cita.id for cita_existente in db_citas):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una cita con el ID {cita.id}.",
        )
    db_citas.append(cita)
    return cita


@app.put("/api/v1/citas/{cita_id}", response_model=CitaBarberia)
def actualizar_cita(cita_id: int, datos_actualizados: CitaBarberiaUpdate):
    for index, cita in enumerate(db_citas):
        if cita.id == cita_id:
            cita_actualizada = CitaBarberia(
                id=cita_id,
                **datos_actualizados.dict(),
            )
            db_citas[index] = cita_actualizada
            return cita_actualizada
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No se puede actualizar: la cita con ID {cita_id} no existe.",
    )


@app.delete("/api/v1/citas/{cita_id}")
def eliminar_cita(cita_id: int):
    for index, cita in enumerate(db_citas):
        if cita.id == cita_id:
            db_citas.pop(index)
            return {"mensaje": f"La cita con ID {cita_id} fue eliminada exitosamente."}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No se puede eliminar: la cita con ID {cita_id} no existe.",
    )
