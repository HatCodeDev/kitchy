"""
Servicio de Gestión de Insumos y Stock.

Este módulo provee la lógica de negocio para la gestión del inventario de materias primas (insumos),
incluyendo la creación, filtrado inteligente por stock crítico, actualización parcial,
propagación automática de costos en recetas, borrado lógico con verificación de dependencias,
y la bitácora inmutable de transacciones de stock (movimientos de inventario).
"""
from uuid import UUID
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from sqlalchemy import select, update, case
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from datetime import datetime, timezone
from sqlalchemy import desc
from app.models.movimiento_insumo import MovimientoInsumo
from app.schemas.movimiento_insumo import MovimientoCreate
from app.models.insumo import Insumo
from app.schemas.insumo import InsumoCreate, InsumoUpdate


class InsumoService:
    """
    Servicio que implementa la administración de insumos y bitácora de stock de Kitchy.
    """
    @staticmethod
    async def create_insumo(db: AsyncSession, data: InsumoCreate, usuario_id: UUID) -> Insumo:
        """
        Registra un nuevo insumo en el inventario y establece su stock inicial.

        El stock inicial (`cantidad_actual`) se establece de forma automática igual
        a la cantidad declarada en la compra inicial (`cantidad_comprada`).

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            data (InsumoCreate): Payload del insumo a crear con datos de compra.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            Insumo: La instancia del insumo recién creado y persistido.
        """
        
        nuevo_insumo = Insumo(
            **data.model_dump(),
            usuario_id=usuario_id,
            cantidad_actual=data.cantidad_comprada, 
            fecha_ultimo_precio=date.today(),
            activo=True
        )

        db.add(nuevo_insumo)
        await db.commit()
        await db.refresh(nuevo_insumo)
        return nuevo_insumo

    @staticmethod
    async def get_insumos(db: AsyncSession, usuario_id: UUID, activo: bool = True) -> List[Insumo]:
        """
        Recupera el listado de insumos con aislamiento de usuario y ordenamiento de criticidad.

        Aplica ordenamiento compuesto: primero sitúa los insumos con stock por debajo o
        igual a su nivel de alerta mínimo configurado, y posteriormente ordena alfabéticamente
        por nombre del insumo.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            usuario_id (UUID): ID del usuario propietario.
            activo (bool): Flag para filtrar por registros activos o borrados lógicamente. Por defecto True.

        Returns:
            List[Insumo]: Lista de insumos ordenados de forma inteligente.
        """
        query = (
            select(Insumo)
            .where(Insumo.usuario_id == usuario_id, Insumo.activo == activo)
            .order_by(
                # El 'case' permite priorizar insumos con stock bajo (0 es mayor prioridad que 1)
                case(
                    (Insumo.cantidad_actual <= Insumo.alerta_minimo, 0),
                    else_=1
                ),
                Insumo.nombre
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, insumo_id: UUID, usuario_id: UUID) -> Insumo:
        """
        Busca un insumo específico validando la pertenencia del usuario (Multi-tenancy).

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            insumo_id (UUID): ID del insumo buscado.
            usuario_id (UUID): ID del usuario que solicita la consulta.

        Returns:
            Insumo: La instancia de Insumo encontrada.

        Raises:
            HTTPException: 404 si no existe, o 403 si pertenece a otro usuario (Seguridad).
        """
        query = select(Insumo).where(Insumo.id == insumo_id)
        result = await db.execute(query)
        insumo = result.scalar_one_or_none()

        if not insumo:
            raise HTTPException(status_code=404, detail="Insumo no encontrado")

        if insumo.usuario_id != usuario_id:
            # Seguridad: Si el insumo existe pero no es del usuario, lanzamos 403.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este insumo"
            )

        return insumo

    @staticmethod
    async def update_insumo(db: AsyncSession, insumo_id: UUID, data: InsumoUpdate, usuario_id: UUID) -> Insumo:
        """
        Actualiza parcialmente (PATCH) las propiedades de un insumo.

        Si se modifica el `precio_compra` o la `cantidad_comprada`, recalcula el precio
        unitario e invoca a `PricePropagationService` de forma asíncrona para actualizar
        al vuelo los costos de todas las recetas en las que participe este insumo.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            insumo_id (UUID): ID del insumo a actualizar.
            data (InsumoUpdate): DTO con los cambios a aplicar.
            usuario_id (UUID): ID del usuario solicitante.

        Returns:
            Insumo: El objeto Insumo actualizado.
        """
        # Validar que el insumo exista y pertenezca al usuario
        insumo = await InsumoService.get_by_id(db, insumo_id, usuario_id)

        # Extraer solo los campos que el cliente envió
        update_data = data.model_dump(exclude_unset=True)

        # Detectar si hubo cambios que afecten el costo (RN-03)
        # Si cambia el precio_compra O la cantidad_comprada, el precio_unitario cambia.
        cambio_en_costo = "precio_compra" in update_data or "cantidad_comprada" in update_data

        if "precio_compra" in update_data:
            insumo.fecha_ultimo_precio = date.today()

        # Aplicar cambios al objeto
        for key, value in update_data.items():
            setattr(insumo, key, value)

        # Guardar cambios en el Insumo
        await db.commit()
        await db.refresh(insumo)

        # Si el costo cambió, notificamos al PricePropagationService
        if cambio_en_costo:
            # Importación local (Lazy Import) para evitar errores de importación circular
            from app.services.price_propagation_service import PricePropagationService

            # Lanzamos la propagación para que recalcule las recetas afectadas
            await PricePropagationService.propagar_cambio_precio(
                db=db,
                insumo_id=insumo_id,
                usuario_id=usuario_id
            )

        return insumo

    @staticmethod
    async def soft_delete(db: AsyncSession, insumo_id: UUID, usuario_id: UUID) -> bool:
        """
        Realiza la desactivación lógica (soft delete) de un insumo de inventario.

        Antes de desactivar, valida que el insumo no esté referenciado por ingredientes activos
        en recetas existentes para proteger la integridad referencial lógica del sistema.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            insumo_id (UUID): ID del insumo a desactivar.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            bool: True si la desactivación fue exitosa.

        Raises:
            HTTPException: 400 si el insumo está siendo utilizado en alguna receta activa.
        """
        insumo = await InsumoService.get_by_id(db, insumo_id, usuario_id)

        # Verificar uso en recetas antes de desactivar (RN-05)
        from app.models.ingrediente_receta import IngredienteReceta
        query_uso = select(IngredienteReceta).where(IngredienteReceta.insumo_id == insumo_id).limit(1)
        result_uso = await db.execute(query_uso)
        
        if result_uso.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el insumo porque está siendo utilizado en una o más recetas."
            )

        insumo.activo = False
        await db.commit()
        return True

    @staticmethod
    async def registrar_movimiento(
            db: AsyncSession,
            insumo_id: UUID,
            data: MovimientoCreate,
            usuario_id: UUID
    ) -> Insumo:
        """
        Registra una transacción de stock, actualiza stock físico y dispara alertas.

        Calcula el nuevo balance de stock (suma si es 'entrada', resta si es 'salida').
        Si es salida y no hay suficiente stock físico, lanza error 400.
        Inserta un registro inmutable en `MovimientoInsumo`.
        Si el stock actual es igual o menor al mínimo de alerta, programa de forma inmediata
        una `NotificacionProgramada` de tipo 'alerta_desabasto'.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            insumo_id (UUID): ID del insumo afectado.
            data (MovimientoCreate): DTO con el tipo de movimiento, cantidad y motivo.
            usuario_id (UUID): ID del usuario que registra la transacción.

        Returns:
            Insumo: La instancia de Insumo con stock y estado actualizados.

        Raises:
            HTTPException: 400 si hay desabasto de stock para realizar la salida.
        """
        # a. Validar pertenencia (reutilizamos la seguridad ya creada)
        insumo = await InsumoService.get_by_id(db, insumo_id, usuario_id)

        # b & c. Lógica de modificación de stock con validación de integridad
        if data.tipo == 'entrada':
            insumo.cantidad_actual += data.cantidad
        elif data.tipo == 'salida':
            # NUESTRA REGLA DE ORO: Validar que el stock no quede en negativo
            if insumo.cantidad_actual < data.cantidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente. Tienes {insumo.cantidad_actual} {insumo.unidad} pero intentas sacar {data.cantidad}."
                )
            insumo.cantidad_actual -= data.cantidad

        # d & e. Registrar el movimiento histórico (Inmutable)
        nuevo_movimiento = MovimientoInsumo(
            insumo_id=insumo_id,
            usuario_id=usuario_id,
            tipo=data.tipo,
            cantidad=data.cantidad,
            motivo=data.motivo,
            fecha=datetime.now(timezone.utc)
        )
        db.add(nuevo_movimiento)

        # f. Evaluar alerta de desabasto
        # Si el stock actual cruzó la línea del mínimo, disparamos la alerta.
        if insumo.cantidad_actual <= insumo.alerta_minimo:
            # Crear NotificacionProgramada (Épica E9-01)
            from app.models.notificacion_programada import NotificacionProgramada
            alerta = NotificacionProgramada(
                usuario_id=usuario_id,
                insumo_id=insumo_id,
                tipo='alerta_desabasto',
                fecha_programada=datetime.now(timezone.utc)
            )
            db.add(alerta)

        # g. Guardar la transacción
        # Al hacer commit aquí, SQLAlchemy guarda la actualización del Insumo y la
        # inserción del Movimiento en un solo bloque. Si algo falla, nada se guarda.
        await db.commit()
        await db.refresh(insumo)

        # h. Retornar insumo actualizado
        return insumo

    @staticmethod
    async def get_movimientos(db: AsyncSession, insumo_id: UUID, usuario_id: UUID, limit: int = 5) -> List[
        MovimientoInsumo]:
        """
        Recupera el historial cronológico de movimientos de stock para un insumo.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            insumo_id (UUID): ID del insumo a auditar.
            usuario_id (UUID): ID del usuario que solicita la auditoría.
            limit (int): Número máximo de movimientos a retornar. Por defecto 5.

        Returns:
            List[MovimientoInsumo]: Listado de movimientos ordenados por fecha descendente.
        """
        # Validamos que el insumo exista y sea del usuario
        await InsumoService.get_by_id(db, insumo_id, usuario_id)

        query = (
            select(MovimientoInsumo)
            .where(MovimientoInsumo.insumo_id == insumo_id)
            .order_by(desc(MovimientoInsumo.fecha))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
