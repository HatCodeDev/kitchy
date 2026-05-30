"""
Controlador de Pedidos y Ventas.

Este router expone los endpoints para la agenda de pedidos, permitiendo la creación,
listado cronológico paginado, detección de colisiones de entrega, actualización y
transiciones controladas de la máquina de estados de las órdenes de venta.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.pedido import PedidoCreate, PedidoUpdate, PedidoResponse, ColisionHoraResponse
from app.services.pedido_service import PedidoService

router = APIRouter()


@router.post("/", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def crear_pedido(
    data: PedidoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva orden o pedido de venta detallado.

    Valida que la fecha de entrega sea estrictamente futura. Crea dinámicamente las líneas
    de pedido y programa recordatorios por WhatsApp automáticos para ser enviados 2 horas antes de la entrega.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PedidoService.create_pedido(db, data, current_user.id)


@router.get("/", response_model=List[PedidoResponse])
async def listar_pedidos(
    estado: Optional[str] = Query(None, description="Filtrar por estado: pendiente, en_preparacion, listo, entregado, cancelado"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la agenda cronológica de pedidos del usuario autenticado.

    ### Ordenamiento:
    * Los pedidos se listan en orden cronológico ascendente (el más próximo a entregarse primero).
    * Cada pedido incluye sus líneas de detalle, información de contacto de WhatsApp precalculada,
      y datos resueltos del Punto de Entrega físico.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PedidoService.get_pedidos(db, current_user.id, estado, limit, offset)


@router.get("/check-colision", response_model=ColisionHoraResponse)
async def check_colision(
    fecha_entrega: datetime,
    exclude_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verifica si existen pedidos comprometidos en la misma hora truncada de entrega.

    Ayuda a prevenir que el cocinero/emprendedor agende múltiples entregas simultáneas.
    Falla de forma silenciosa retornando `hay_colision=False` para proteger la experiencia de usuario
    en el cliente de frontend.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    try:
        return await PedidoService.check_colision_hora(
            db=db,
            fecha_entrega=fecha_entrega,
            usuario_id=current_user.id,
            exclude_id=exclude_id
        )
    except Exception:
        # Fallback benigno: No asustar al usuario si falla el chequeo
        return ColisionHoraResponse(
            hay_colision=False,
            quantity=0, # (En caso de tipados internos se devuelve 0)
            cantidad=0,
            hora_inicio="",
            hora_fin=""
        )


@router.get("/{pedido_id}", response_model=PedidoResponse)
async def obtener_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Recupera la información completa de un pedido específico.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).

    ### Respuestas:
    * **404 Not Found**: El pedido no existe o pertenece a otro usuario.
    """
    return await PedidoService.get_by_id(db, pedido_id, current_user.id)


@router.put("/{pedido_id}", response_model=PedidoResponse)
async def actualizar_pedido(
    pedido_id: UUID,
    data: PedidoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza de forma completa o parcial las propiedades y las líneas de un pedido.

    ### Restricciones:
    * No se permiten ediciones si el pedido ya fue entregado o cancelado.
    * Si la fecha de entrega cambia, recalcula y reprograma automáticamente las notificaciones de alerta.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PedidoService.update_pedido(db, pedido_id, data, current_user.id)


@router.patch("/{pedido_id}/estado", response_model=PedidoResponse)
async def cambiar_estado_pedido(
    pedido_id: UUID,
    nuevo_estado: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ejecuta una transición de estado en la máquina de estados controlada del pedido.

    ### Reglas de la Máquina de Estados:
    * **Transiciones legales**:
      * `pendiente` -> `en_preparacion` o `cancelado`
      * `en_preparacion` -> `listo` o `cancelado`
      * `listo` -> `entregado` o `cancelado`
    * Al cambiar a **`entregado`**, se dispara el gatillo atómico que descuenta del stock
      físico las materias primas utilizadas en las recetas del pedido (Manufactura y Alacena).

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PedidoService.cambiar_estado(db, pedido_id, nuevo_estado, current_user.id)


@router.delete("/{pedido_id}", response_model=PedidoResponse)
async def cancelar_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancela un pedido activo.

    Equivalente a realizar una transición controlada de estado hacia 'cancelado', lo cual
    desactiva recordatorios automáticos de entrega programados y aborta futuros descuentos de alacena.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PedidoService.cambiar_estado(db, pedido_id, "cancelado", current_user.id)