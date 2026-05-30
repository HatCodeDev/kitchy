"""
Controlador de Recetas y Costeos culinarios.

Este router expone los endpoints para administrar las recetas, sus ingredientes,
pasos del proceso de elaboración, costeo detallado y la gestión de gastos ocultos (empaque/servicios).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Literal
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.receta import Receta  # <-- Importante para el tipado del helper
from app.schemas.receta import (
    RecetaCreate,
    RecetaResponse,
    GastoOcultoCreate,
    GastoOcultoResponse,
    ToggleGastoRequest,
    RecetaUpdate
)
from app.services.receta_service import RecetaService
from app.services.hidden_cost_service import HiddenCostService

router = APIRouter()


async def inyectar_costos_a_receta(receta: Receta, db: AsyncSession, usuario_id: UUID) -> Receta:
    """
    Enriquece la instancia de una Receta inyectándole de forma dinámica campos calculados de costo.

    Este helper inyecta los atributos dinámicos `costo_por_porcion` y `precio_sugerido` en tiempo
    de ejecución, los cuales son necesarios para satisfacer el esquema de respuesta `RecetaResponse`.

    Args:
        receta (Receta): Instancia de receta recuperada de la base de datos.
        db (AsyncSession): Conexión activa de base de datos asíncrona.
        usuario_id (UUID): ID del usuario propietario.

    Returns:
        Receta: La misma instancia enriquecida con los atributos financieros.
    """
    costos = await RecetaService.calcular_costeo(db, receta.id, usuario_id)
    setattr(receta, 'costo_por_porcion', costos['costo_por_porcion'])
    setattr(receta, 'precio_sugerido', costos['precio_sugerido'])
    return receta


# ENDPOINTS

@router.get("/", response_model=List[RecetaResponse])
async def get_recetas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene todas las recetas activas del usuario autenticado.

    Cada receta devuelta incluye la precarga de ingredientes, insumos, pasos,
    y es enriquecida automáticamente con los cálculos vigentes de costo unitario y precio sugerido.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    recetas = await RecetaService.get_all(db, current_user.id)
    # Enriquecemos toda la lista usando el helper
    return [await inyectar_costos_a_receta(r, db, current_user.id) for r in recetas]


@router.post("/", response_model=RecetaResponse, status_code=status.HTTP_201_CREATED)
async def create_receta(
    data: RecetaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva receta detallada junto con sus ingredientes y pasos.

    Inicializa de forma atómica la receta, los ingredientes y sus pasos, y configura
    automáticamente los registros desactivados por defecto de GastoOculto para empaques ($0.00)
    y servicios (0.00%) garantizando la consistencia transaccional.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    receta = await RecetaService.create_receta(db, data, current_user.id)
    # Enriquecemos la receta recién creada
    return await inyectar_costos_a_receta(receta, db, current_user.id)


@router.get("/{id}", response_model=RecetaResponse)
async def get_receta(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de una receta y sus métricas financieras calculadas al vuelo.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).

    ### Respuestas:
    * **404 Not Found**: Si la receta no existe o está desactivada.
    """
    receta = await RecetaService.get_by_id(db, id, current_user.id)
    # Enriquecemos la receta consultada
    return await inyectar_costos_a_receta(receta, db, current_user.id)


@router.put("/{id}", response_model=RecetaResponse)
async def update_receta(
    id: UUID,
    data: RecetaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza completamente las propiedades, ingredientes y pasos de una receta.

    Limpia y reconstruye las listas de ingredientes y secuencias de pasos de forma segura
    para garantizar la consistencia referencial y evitar violaciones de índices únicos.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    receta = await RecetaService.update_receta(db, id, data, current_user.id)
    # Enriquecemos la receta después de actualizarla
    return await inyectar_costos_a_receta(receta, db, current_user.id)


@router.delete("/{id}")
async def delete_receta(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Desactiva lógicamente una receta (Soft Delete) del catálogo del usuario.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    await RecetaService.delete_receta(db, id, current_user.id)
    return {"mensaje": "Receta desactivada correctamente"}


@router.get("/{id}/costeo", response_model=Dict[str, Any])
async def calcular_costo_receta(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ejecuta el análisis financiero integral y detallado para una receta.

    Retorna un desglose monetario exacto del costo neto de ingredientes, empaques,
    energía/depreciaciones, prorrateos por porción de rendimiento y porcentajes de participación.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await RecetaService.calcular_costeo(db, id, current_user.id)


@router.post("/{id}/gastos-ocultos", response_model=GastoOcultoResponse)
async def upsert_gasto_oculto(
    id: UUID,
    data: GastoOcultoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Configura, crea o actualiza las propiedades de un gasto oculto para una receta.

    Permite definir montos fijos en MXN o tasas porcentuales aplicables sobre el costo neto.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await HiddenCostService.toggle_gasto(
        db=db,
        receta_id=id,
        tipo=data.tipo,
        activo=data.activo,
        usuario_id=current_user.id,
        valor=data.valor,
        es_porcentaje=data.es_porcentaje
    )


@router.patch("/{id}/gastos-ocultos/{tipo}/toggle", response_model=GastoOcultoResponse)
async def toggle_gasto_oculto(
    id: UUID,
    tipo: Literal['empaque', 'gas_luz'],
    data: ToggleGastoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activa o desactiva lógicamente un gasto oculto (Fallback Toggle).

    Al desactivarlo, el sistema automáticamente reevaluará los cálculos utilizando los defaults
    globales del usuario, manteniendo coherencia sin requerir re-configurar montos.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await HiddenCostService.toggle_gasto(db, id, tipo, data.activo, current_user.id)