from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pedido import Pedido
from app.models.linea_pedido import LineaPedido
from app.schemas.pedido import PedidoCreate

# STUB: E7-08 (Si aún no tienes el archivo app/utils/whatsapp.py, coméntalo o créalo vacío)
try:
    from app.utils.whatsapp import build_whatsapp_url
except ImportError:
    def build_whatsapp_url(numero: str) -> Optional[str]:
        return f"https://wa.me/52{numero}" if numero else None


class PedidoService:
    # MÁQUINA DE ESTADOS
    TRANSICIONES_VALIDAS = {
        "pendiente": ["en_preparacion", "cancelado"],
        "en_preparacion": ["listo", "cancelado"],
        "listo": ["entregado", "cancelado"],
        "entregado": [],  # Estado terminal (No se puede salir de aquí)
        "cancelado": []  # Estado terminal
    }

    @staticmethod
    async def create_pedido(db: AsyncSession, data: PedidoCreate, usuario_id: UUID) -> Pedido:
        """Crea un pedido asegurando que la fecha sea futura."""


        ahora_utc = datetime.now(timezone.utc)
        fecha_entrega_utc = data.fecha_entrega
        if fecha_entrega_utc.tzinfo is None:
            fecha_entrega_utc = fecha_entrega_utc.replace(tzinfo=timezone.utc)

        if fecha_entrega_utc <= ahora_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de entrega debe ser en el futuro"
            )

        # Crear cabecera del Pedido
        nuevo_pedido = Pedido(
            usuario_id=usuario_id,
            cliente_nombre=data.cliente_nombre,
            cliente_whatsapp=data.cliente_whatsapp,
            fecha_entrega=data.fecha_entrega,
            punto_entrega=data.punto_entrega,
            notas=data.notas,
            estado="pendiente"
        )
        db.add(nuevo_pedido)
        await db.flush()  # Obtener ID sin hacer commit final

        # Crear Líneas de Pedido (Cascade)
        for linea_data in data.lineas:
            nueva_linea = LineaPedido(
                pedido_id=nuevo_pedido.id,
                receta_id=linea_data.receta_id,
                nombre_producto=linea_data.nombre_producto,
                cantidad_porciones=linea_data.cantidad_porciones,
                precio_acordado_mxn=linea_data.precio_acordado_mxn
            )
            db.add(nueva_linea)

        #  Programar Recordatorio (E9-02)
        # fecha_recordatorio = data.fecha_entrega - timedelta(hours=2)
        # NotificacionService.programar(..., fecha_recordatorio)

        # Commit de la Transacción
        await db.commit()
        await db.refresh(nuevo_pedido)

        #  Inyectar el campo computado para que lo lea el Schema de Response
        nuevo_pedido.whatsapp_url = build_whatsapp_url(nuevo_pedido.cliente_whatsapp)

        return nuevo_pedido

    @staticmethod
    async def get_pedidos(
            db: AsyncSession,
            usuario_id: UUID,
            estado: Optional[str] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[Pedido]:
        """Obtiene la agenda ordenada cronológicamente."""

        query = select(Pedido).where(Pedido.usuario_id == usuario_id)

        if estado:
            query = query.where(Pedido.estado == estado)

        # Orden ascendente (los más urgentes salen primero) y selectinload para las líneas
        query = query.order_by(Pedido.fecha_entrega.asc()) \
            .limit(limit).offset(offset) \
            .options(selectinload(Pedido.lineas))

        result = await db.execute(query)
        pedidos = list(result.scalars().all())

        # Inyectar url computada en tiempo de ejecución
        for p in pedidos:
            p.whatsapp_url = build_whatsapp_url(p.cliente_whatsapp)

        return pedidos

    @staticmethod
    async def get_by_id(db: AsyncSession, pedido_id: UUID, usuario_id: UUID) -> Pedido:
        """Obtiene un pedido específico con sus líneas."""
        query = select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.usuario_id == usuario_id
        ).options(selectinload(Pedido.lineas))

        result = await db.execute(query)
        pedido = result.scalar_one_or_none()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")

        pedido.whatsapp_url = build_whatsapp_url(pedido.cliente_whatsapp)
        return pedido

    @staticmethod
    async def cambiar_estado(db: AsyncSession, pedido_id: UUID, nuevo_estado: str, usuario_id: UUID) -> Pedido:
        """Máquina de Estados Unidireccional y gatillo para Opción A (Inventario)."""

        pedido = await PedidoService.get_by_id(db, pedido_id, usuario_id)
        estado_actual = pedido.estado

        #  Validar que el nuevo estado existe en las reglas del negocio
        if nuevo_estado not in PedidoService.TRANSICIONES_VALIDAS:
            raise HTTPException(
                status_code=400,
                detail=f"Estado desconocido: {nuevo_estado}"
            )

        # Validar Transición (Máquina de estados)
        if nuevo_estado not in PedidoService.TRANSICIONES_VALIDAS[estado_actual]:
            raise HTTPException(
                status_code=400,
                detail=f"Transición inválida: No puedes pasar de '{estado_actual}' a '{nuevo_estado}' directamente."
            )

        # Aplicar el cambio
        pedido.estado = nuevo_estado
        pedido.fecha_modificacion = datetime.now(timezone.utc)


        # GATILLO DE INVENTARIO
        if nuevo_estado == "entregado":
            # TODO: Llamar al InventarioService para descontar insumos
            # await InventarioService.descontar_por_pedido(db, pedido.id, usuario_id)
            pass

        await db.commit()
        await db.refresh(pedido)
        return pedido