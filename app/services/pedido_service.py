"""
Servicio de Gestión de Pedidos y Ventas.

Este módulo implementa el control de pedidos, la lógica de la máquina de estados unidireccional
(pendiente -> en_preparacion -> listo -> entregado / cancelado), la validación de colisiones horarias
de entrega, el cálculo de URLs dinámicas para notificaciones vía WhatsApp y la integración con el
módulo de producción para el descuento automático de stock de insumos al concretar entregas.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pedido import Pedido
from app.models.linea_pedido import LineaPedido
from app.models.punto_entrega import PuntoEntrega
from app.schemas.pedido import PedidoCreate, PedidoUpdate, ColisionHoraResponse
from app.services.produccion_service import ProduccionService

try:
    from app.utils.whatsapp import build_whatsapp_url
except ImportError:
    def build_whatsapp_url(numero: str) -> Optional[str]:
        return f"https://wa.me/52{numero}" if numero else None


class PedidoService:
    """
    Servicio que implementa la lógica de negocio para la gestión de pedidos y ventas de Kitchy.

    Atributos:
        TRANSICIONES_VALIDAS (dict): Define el flujo legal y permitido de la máquina de estados
            para los pedidos (pendiente -> en_preparacion -> listo -> entregado/cancelado).
    """
    # MÁQUINA DE ESTADOS
    TRANSICIONES_VALIDAS = {
        "pendiente": ["en_preparacion", "cancelado"],
        "en_preparacion": ["listo", "cancelado"],
        "listo": ["entregado", "cancelado"],
        "entregado": [],  # Estado terminal (No se puede salir de aquí)
        "cancelado": []  # Estado terminal
    }

    @staticmethod
    def _set_display_resolution(pedido: Pedido) -> None:
        """
        Resuelve y asigna dinámicamente los campos virtuales de visualización de entrega del pedido.

        Si el pedido tiene un `PuntoEntrega` formal asociado (FK), asigna su nombre y dirección.
        De lo contrario, recurre al valor de texto plano (fallback) provisto en la creación.

        Args:
            pedido (Pedido): Instancia de pedido para la cual resolver la visualización.
        """
        if pedido.punto_entrega_rel:
            pedido.punto_entrega_display = pedido.punto_entrega_rel.nombre
            pedido.punto_entrega_direccion = pedido.punto_entrega_rel.direccion
        else:
            pedido.punto_entrega_display = pedido.punto_entrega
            pedido.punto_entrega_direccion = pedido.punto_entrega

    @staticmethod
    async def _validate_punto_entrega_fk(
        db: AsyncSession,
        punto_entrega_id: Optional[UUID],
        usuario_id: UUID
    ) -> None:
        """
        Valida que un ID de punto de entrega exista en el sistema y pertenezca al usuario solicitante.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            punto_entrega_id (Optional[UUID]): ID del punto de entrega a validar.
            usuario_id (UUID): ID del usuario creador de la orden.

        Raises:
            HTTPException: 422 si el punto de entrega no existe o pertenece a otro usuario.
        """
        if not punto_entrega_id:
            return

        query = select(PuntoEntrega).where(
            and_(
                PuntoEntrega.id == punto_entrega_id,
                PuntoEntrega.usuario_id == usuario_id
            )
        )
        result = await db.execute(query)
        punto = result.scalar_one_or_none()

        if not punto:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El punto de entrega especificado no existe o no te pertenece"
            )

    @staticmethod
    async def create_pedido(db: AsyncSession, data: PedidoCreate, usuario_id: UUID) -> Pedido:
        """
        Crea, valida e inicializa un nuevo pedido con sus correspondientes líneas físicas de detalle.

        Valida que la fecha de entrega sea estrictamente futura en tiempo de servidor (UTC),
        corrobora que el punto de entrega (si es una FK) pertenezca al usuario, inserta las líneas de pedido,
        programa recordatorios automáticos de entrega 2 horas antes y persiste la transacción.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            data (PedidoCreate): DTO con los detalles básicos de cliente, fecha de entrega y líneas del pedido.
            usuario_id (UUID): ID del usuario que registra el pedido.

        Returns:
            Pedido: El pedido recién creado cargado con relaciones e información computada.

        Raises:
            HTTPException: 400 si la fecha de entrega es en el pasado o presente.
        """
        ahora_utc = datetime.now(timezone.utc)
        fecha_entrega_utc = data.fecha_entrega
        if fecha_entrega_utc.tzinfo is None:
            fecha_entrega_utc = fecha_entrega_utc.replace(tzinfo=timezone.utc)

        if fecha_entrega_utc <= ahora_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La fecha de entrega debe ser en el futuro"
            )

        # Validar FK si está presente
        await PedidoService._validate_punto_entrega_fk(db, data.punto_entrega_id, usuario_id)

        # Crear cabecera del Pedido
        nuevo_pedido = Pedido(
            usuario_id=usuario_id,
            cliente_nombre=data.cliente_nombre,
            cliente_whatsapp=data.cliente_whatsapp,
            fecha_entrega=data.fecha_entrega,
            punto_entrega=data.punto_entrega,
            punto_entrega_id=data.punto_entrega_id,
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
        from app.services.notificacion_service import NotificacionService
        await NotificacionService.programar_recordatorio(
            db=db,
            pedido_id=nuevo_pedido.id,
            fecha_entrega=data.fecha_entrega,
            usuario_id=usuario_id
        )

        await db.commit()

        # Recargar con relaciones para la respuesta
        query = select(Pedido).where(Pedido.id == nuevo_pedido.id).options(
            selectinload(Pedido.lineas),
            selectinload(Pedido.punto_entrega_rel)
        )
        result = await db.execute(query)
        nuevo_pedido = result.scalar_one()

        # Inyectar campos computados
        nuevo_pedido.whatsapp_url = build_whatsapp_url(nuevo_pedido.cliente_whatsapp)
        PedidoService._set_display_resolution(nuevo_pedido)

        return nuevo_pedido

    @staticmethod
    async def update_pedido(db: AsyncSession, pedido_id: UUID, data: PedidoUpdate, usuario_id: UUID) -> Pedido:
        """
        Actualiza los datos básicos de un pedido y reconstruye sus líneas de detalle si se especifican.

        Si se modifica la fecha de entrega, cancela los recordatorios anteriores y programa la
        nueva notificación con el nuevo horario.
        No permite la edición si el pedido ya está en un estado final ('entregado', 'cancelado').

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            pedido_id (UUID): ID del pedido a modificar.
            data (PedidoUpdate): DTO con los campos que se desean actualizar (excluyendo estado).
            usuario_id (UUID): ID del usuario dueño de la orden.

        Returns:
            Pedido: La instancia de Pedido actualizada.

        Raises:
            HTTPException: 400 si el pedido se encuentra en un estado inmutable ('entregado' o 'cancelado').
        """
        pedido = await PedidoService.get_by_id(db, pedido_id, usuario_id)

        # Solo permitir editar si no está entregado ni cancelado
        if pedido.estado in ["entregado", "cancelado"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede editar un pedido con estado '{pedido.estado}'"
            )

        # Validar FK si está presente
        if data.punto_entrega_id is not None:
            await PedidoService._validate_punto_entrega_fk(db, data.punto_entrega_id, usuario_id)

        # Actualizar campos básicos
        if data.cliente_nombre is not None:
            pedido.cliente_nombre = data.cliente_nombre
        if data.cliente_whatsapp is not None:
            pedido.cliente_whatsapp = data.cliente_whatsapp
        if data.fecha_entrega is not None:
            # Si la fecha cambia, reprogramamos el recordatorio (E9-02)
            from app.services.notificacion_service import NotificacionService
            await NotificacionService.cancelar_recordatorio(db, pedido.id, usuario_id)
            await NotificacionService.programar_recordatorio(db, pedido.id, data.fecha_entrega, usuario_id)

            pedido.fecha_entrega = data.fecha_entrega
        if data.punto_entrega is not None:
            pedido.punto_entrega = data.punto_entrega
        if data.punto_entrega_id is not None:
            pedido.punto_entrega_id = data.punto_entrega_id
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
        query = select(Pedido).where(Pedido.id == pedido.id).options(
            selectinload(Pedido.lineas),
            selectinload(Pedido.punto_entrega_rel)
        )
        result = await db.execute(query)
        pedido = result.scalar_one()

        pedido.whatsapp_url = build_whatsapp_url(pedido.cliente_whatsapp)
        PedidoService._set_display_resolution(pedido)
        return pedido

    @staticmethod
    async def check_colision_hora(
        db: AsyncSession,
        fecha_entrega: datetime,
        usuario_id: UUID,
        exclude_id: Optional[UUID] = None
    ) -> ColisionHoraResponse:
        """
        Determina si existen otros pedidos programados para entrega dentro de la misma hora truncada.

        Sirve para advertir en la UI si el emprendedor tiene compromisos de entregas colisionadas.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            fecha_entrega (datetime): La fecha y hora que se desea comprobar.
            usuario_id (UUID): ID del usuario dueño de las órdenes.
            exclude_id (Optional[UUID]): ID de pedido a excluir (útil en ediciones).

        Returns:
            ColisionHoraResponse: DTO que especifica si hay colisión, la cantidad de colisiones,
                y el inicio/fin de la ventana horaria analizada.
        """
        from sqlalchemy import func

        # Asegurar UTC y truncar para el cálculo de la ventana
        if fecha_entrega.tzinfo is None:
            fecha_entrega = fecha_entrega.replace(tzinfo=timezone.utc)

        hora_inicio_dt = fecha_entrega.replace(minute=0, second=0, microsecond=0)
        hora_fin_dt = hora_inicio_dt + timedelta(hours=1)

        # Query: pedidos del usuario, no cancelados, en la misma hora truncada
        query = select(func.count(Pedido.id)).where(
            and_(
                Pedido.usuario_id == usuario_id,
                Pedido.estado != "cancelado",
                func.date_trunc('hour', Pedido.fecha_entrega) == func.date_trunc('hour', fecha_entrega)
            )
        )

        if exclude_id:
            query = query.where(Pedido.id != exclude_id)

        result = await db.execute(query)
        count = result.scalar() or 0

        return ColisionHoraResponse(
            hay_colision=count > 0,
            cantidad=count,
            hora_inicio=hora_inicio_dt.strftime("%H:00"),
            hora_fin=hora_fin_dt.strftime("%H:00")
        )

    @staticmethod
    async def get_pedidos(
            db: AsyncSession,
            usuario_id: UUID,
            estado: Optional[str] = None,
            limit: int = 20,
            offset: int = 0
    ) -> List[Pedido]:
        """
        Obtiene la agenda cronológica de pedidos paginada para un usuario.

        Ordena los pedidos de forma ascendente por fecha de entrega (más urgente primero),
        resuelve las relaciones y carga campos de visualización y URLs para interactuar por WhatsApp.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            usuario_id (UUID): ID del usuario propietario de las órdenes.
            estado (Optional[str]): Filtro de estado del pedido ('pendiente', 'en_preparacion', etc.).
            limit (int): Límite de paginación. Por defecto 20.
            offset (int): Salto de registros. Por defecto 0.

        Returns:
            List[Pedido]: Lista de pedidos cargados y listos para representarse.
        """
        query = select(Pedido).where(Pedido.usuario_id == usuario_id)

        if estado:
            query = query.where(Pedido.estado == estado)

        # Orden ascendente (los más urgentes salen primero) y selectinload para las líneas y punto_entrega
        query = query.order_by(Pedido.fecha_entrega.asc()) \
            .limit(limit).offset(offset) \
            .options(
                selectinload(Pedido.lineas),
                selectinload(Pedido.punto_entrega_rel)
            )

        result = await db.execute(query)
        pedidos = list(result.scalars().all())

        # Inyectar campos computados en tiempo de ejecución
        for p in pedidos:
            p.whatsapp_url = build_whatsapp_url(p.cliente_whatsapp)
            PedidoService._set_display_resolution(p)

        return pedidos

    @staticmethod
    async def get_by_id(db: AsyncSession, pedido_id: UUID, usuario_id: UUID) -> Pedido:
        """
        Recupera un pedido detallado mediante su ID con aislamiento de multi-tenancy.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            pedido_id (UUID): ID del pedido a buscar.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            Pedido: Instancia de Pedido con líneas de detalle y punto de entrega precargados.

        Raises:
            HTTPException: 404 si el pedido no existe o no pertenece al usuario.
        """
        query = select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.usuario_id == usuario_id
        ).options(
            selectinload(Pedido.lineas),
            selectinload(Pedido.punto_entrega_rel)
        )

        result = await db.execute(query)
        pedido = result.scalar_one_or_none()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")

        pedido.whatsapp_url = build_whatsapp_url(pedido.cliente_whatsapp)
        PedidoService._set_display_resolution(pedido)
        return pedido

    @staticmethod
    async def cambiar_estado(db: AsyncSession, pedido_id: UUID, nuevo_estado: str, usuario_id: UUID) -> Pedido:
        """
        Ejecuta la transición del estado de un pedido según las reglas de la máquina de estados.

        Valida que la transición sea legal.
        GATILLO DE INVENTARIO: Si el estado cambia a 'entregado', invoca inmediatamente
        a `ProduccionService.descontar_insumos_por_pedido` para procesar el descuento
        automático de materias primas de la alacena/inventario del usuario de forma atómica.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            pedido_id (UUID): ID del pedido a actualizar.
            nuevo_estado (str): Estado de destino al que se desea mover el pedido.
            usuario_id (UUID): ID del usuario propietario del pedido.

        Returns:
            Pedido: Instancia del Pedido con el nuevo estado aplicado.

        Raises:
            HTTPException: 400 si el estado es desconocido o si la transición de estados viola las reglas.
        """
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
        query = select(Pedido).where(Pedido.id == pedido.id).options(
            selectinload(Pedido.lineas),
            selectinload(Pedido.punto_entrega_rel)
        )
        result = await db.execute(query)
        pedido = result.scalar_one()

        pedido.whatsapp_url = build_whatsapp_url(pedido.cliente_whatsapp)
        PedidoService._set_display_resolution(pedido)
        return pedido