from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pedido import Pedido
from app.models.linea_pedido import LineaPedido
from app.schemas.pedido import PedidoCreate, PedidoUpdate
from app.services.produccion_service import ProduccionService

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

        #  Programar Recordatorio
        # fecha_recordatorio = data.fecha_entrega - timedelta(hours=2)
        # NotificacionService.programar(..., fecha_recordatorio)

        await db.commit()
        
        # Recargar con relaciones para la respuesta
        query = select(Pedido).where(Pedido.id == nuevo_pedido.id).options(selectinload(Pedido.lineas))
        result = await db.execute(query)
        nuevo_pedido = result.scalar_one()

        # Inyectar el campo computado
        nuevo_pedido.whatsapp_url = build_whatsapp_url(nuevo_pedido.cliente_whatsapp)

        return nuevo_pedido

    @staticmethod
    async def update_pedido(db: AsyncSession, pedido_id: UUID, data: PedidoUpdate, usuario_id: UUID) -> Pedido:
        """Actualiza un pedido existente y sus líneas."""
        pedido = await PedidoService.get_by_id(db, pedido_id, usuario_id)

        # Solo permitir editar si no está entregado ni cancelado
        if pedido.estado in ["entregado", "cancelado"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede editar un pedido con estado '{pedido.estado}'"
            )

        # Actualizar campos básicos
        if data.cliente_nombre is not None:
            pedido.cliente_nombre = data.cliente_nombre
        if data.cliente_whatsapp is not None:
            pedido.cliente_whatsapp = data.cliente_whatsapp
        if data.fecha_entrega is not None:
            pedido.fecha_entrega = data.fecha_entrega
        if data.punto_entrega is not None:
            pedido.punto_entrega = data.punto_entrega
        if data.notas is not None:
            pedido.notas = data.notas

        # Actualizar líneas si se enviaron
        if data.lineas is not None:
            # Borrar líneas viejas
            for linea in list(pedido.lineas):
                await db.delete(linea)
            
            # Forzar limpieza en la sesión antes de insertar nuevas
            await db.flush()

            # Insertar nuevas
            for linea_data in data.lineas:
                nueva_linea = LineaPedido(
                    pedido_id=pedido.id,
                    receta_id=linea_data.receta_id,
                    nombre_producto=linea_data.nombre_producto,
                    cantidad_porciones=linea_data.cantidad_porciones,
                    precio_acordado_mxn=linea_data.precio_acordado_mxn
                )
                db.add(nueva_linea)

        pedido.fecha_modificacion = datetime.now(timezone.utc)
        
        await db.commit()
        
        # Recargar con relaciones para la respuesta
        query = select(Pedido).where(Pedido.id == pedido.id).options(selectinload(Pedido.lineas))
        result = await db.execute(query)
        pedido = result.scalar_one()

        pedido.whatsapp_url = build_whatsapp_url(pedido.cliente_whatsapp)
        return pedido

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
            # Llamamos al Orquestador para que cruce las líneas con las recetas y descuente la alacena
            await ProduccionService.descontar_insumos_por_pedido(db, pedido.id, usuario_id)

        await db.commit()
        
        # Recargar con relaciones para la respuesta
        query = select(Pedido).where(Pedido.id == pedido.id).options(selectinload(Pedido.lineas))
        result = await db.execute(query)
        pedido = result.scalar_one()

        return pedido