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
    @staticmethod
    async def create_insumo(db: AsyncSession, data: InsumoCreate, usuario_id: UUID) -> Insumo:
        """
        Crea un insumo y establece el stock inicial basado en la compra.
        """
        nuevo_insumo = Insumo(
            **data.model_dump(),
            usuario_id=usuario_id,
            cantidad_actual=data.cantidad_comprada,  # Stock inicial = cantidad comprada
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
        Obtiene insumos con aislamiento de usuario y ordenamiento inteligente:
        Primero los que están bajo el mínimo de alerta, luego por nombre.
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
        Busca un insumo y valida la propiedad (Multi-tenancy).
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
        Actualización parcial (PATCH) con validación de propiedad y propagación de precios.
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
        Desactivación lógica del insumo.
        """
        insumo = await InsumoService.get_by_id(db, insumo_id, usuario_id)

        # Verificar uso en recetas antes de desactivar
        # query = select(IngredienteReceta).join(Receta).where(...)

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
        Registra una entrada o salida de inventario, actualiza el stock y evalúa alertas.
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
            # from app.models.notificacion import NotificacionProgramada
            # alerta = NotificacionProgramada(tipo='alerta_desabasto', insumo_id=insumo_id...)
            # db.add(alerta)
            pass

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
        """Obtiene el historial de movimientos de un insumo, ordenado por los más recientes."""
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