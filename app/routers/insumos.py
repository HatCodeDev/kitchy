"""
Controlador de Insumos e Inventario.

Este router expone los endpoints para administrar los insumos (materias primas) del almacén,
permitiendo la creación, consulta, edición, baja lógica y registro de movimientos de stock.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

from app.schemas.insumo import InsumoCreate, InsumoUpdate, InsumoResponse
from app.schemas.movimiento_insumo import MovimientoCreate, MovimientoResponse
from app.services.insumo_service import InsumoService

# Inicializamos el router. El prefijo se define en main.py, así que aquí lo dejamos vacío.
router = APIRouter()


@router.get("/", response_model=List[InsumoResponse])
async def get_insumos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la lista de insumos registrados por el usuario autenticado.

    ### Ordenamiento inteligente:
    * Los insumos con niveles de stock crítico (debajo o igual a su alerta de mínimo)
      se priorizan en el tope del listado. Posteriormente, se ordenan alfabéticamente.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await InsumoService.get_insumos(db, usuario_id=current_user.id)


@router.post("/", response_model=InsumoResponse, status_code=status.HTTP_201_CREATED)
async def create_insumo(
    data: InsumoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo insumo y registra su stock inicial de manera atómica.

    El stock físico inicial (`cantidad_actual`) del insumo es poblado automáticamente
    a partir del campo `cantidad_comprada` provisto en la petición.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await InsumoService.create_insumo(db, data=data, usuario_id=current_user.id)


@router.get("/{id}", response_model=InsumoResponse)
async def get_insumo(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de un insumo específico por su ID.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).

    ### Respuestas:
    * **404 Not Found**: El insumo especificado no existe.
    * **403 Forbidden**: Si el insumo solicitado pertenece a otro usuario (Seguridad).
    """
    return await InsumoService.get_by_id(db, insumo_id=id, usuario_id=current_user.id)


@router.put("/{id}", response_model=InsumoResponse)
async def update_insumo(
    id: UUID,
    data: InsumoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza parcialmente los datos de un insumo existente.

    Si se modifican propiedades financieras (`precio_compra`, `cantidad_comprada`),
    el backend recalcula el costo unitario y propaga automáticamente la actualización en
    cascada a todas las recetas activas del usuario que empleen este insumo.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await InsumoService.update_insumo(db, insumo_id=id, data=data, usuario_id=current_user.id)


@router.delete("/{id}")
async def delete_insumo(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Desactiva lógicamente un insumo (Soft Delete) del sistema.

    ### Regla de negocio (RN-05):
    * No se puede dar de baja lógica un insumo si se encuentra actualmente
      asociado a una receta activa. Se debe desvincular de la receta primero.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    await InsumoService.soft_delete(db, insumo_id=id, usuario_id=current_user.id)
    return {"mensaje": "Insumo desactivado correctamente"}


@router.post("/{id}/movimientos", response_model=InsumoResponse)
async def registrar_movimiento(
    id: UUID,
    data: MovimientoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra una entrada o salida manual de stock de forma transaccional.

    ### Regla de Oro:
    * Las operaciones de **`salida`** validan estrictamente que la cantidad actual sea suficiente.
      Si el stock quedase en valores negativos, se rechaza la petición.
    * Si la cantidad actual disminuye por debajo del umbral mínimo de alerta del insumo,
      se programa de forma asíncrona una alerta por desabasto.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await InsumoService.registrar_movimiento(db, insumo_id=id, data=data, usuario_id=current_user.id)


@router.get("/{id}/movimientos", response_model=List[MovimientoResponse])
async def get_historial_movimientos(
    id: UUID,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la bitácora cronológica inmutable de transacciones de stock de un insumo.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await InsumoService.get_movimientos(db, insumo_id=id, usuario_id=current_user.id, limit=limit)