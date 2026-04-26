from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.pedido import Pedido
from app.models.receta import Receta
from app.schemas.movimiento_insumo import MovimientoCreate
from app.services.insumo_service import InsumoService


class ProduccionService:
    @staticmethod
    async def descontar_insumos_por_pedido(db: AsyncSession, pedido_id: UUID, usuario_id: UUID) -> None:
        """
        Orquesta el descuento de inventario al entregar un pedido.
        Cruza las líneas del pedido con las recetas para calcular las salidas exactas.
        """
        # Obtener el pedido y sus líneas (selectinload para evitar lazy loading problems)
        query_pedido = select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.usuario_id == usuario_id
        ).options(selectinload(Pedido.lineas))

        result_pedido = await db.execute(query_pedido)
        pedido = result_pedido.scalar_one_or_none()

        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado para descuento.")

        # Procesar cada línea del pedido
        for linea in pedido.lineas:
            # Si la línea no tiene receta asociada (producto libre), saltamos
            if not linea.receta_id:
                continue

            # Obtener la receta y sus ingredientes
            query_receta = select(Receta).where(
                Receta.id == linea.receta_id,
                Receta.usuario_id == usuario_id
            ).options(selectinload(Receta.ingredientes))

            result_receta = await db.execute(query_receta)
            receta = result_receta.scalar_one_or_none()

            # Si la receta fue borrada (soft delete o físico), no podemos descontar.
            # Podríamos lanzar error, pero es más seguro para el negocio ignorarla
            # y dejar que entreguen el pedido.
            if not receta:
                continue

            # Calcular el factor de proporción
            # Ejemplo: Receta original es para 4 porciones. El cliente pidió 2. Factor = 0.5
            factor_multiplicacion = Decimal(linea.cantidad_porciones) / Decimal(receta.porciones)

            # Descontar cada ingrediente usando el InsumoService (que ya tiene la validación de stock y creación de historial)
            for ingrediente in receta.ingredientes:
                cantidad_a_descontar = ingrediente.cantidad_usada * factor_multiplicacion

                movimiento_data = MovimientoCreate(
                    tipo='salida',
                    cantidad=cantidad_a_descontar,
                    motivo='uso_produccion'
                )

                try:
                    # Usamos el InsumoService
                    # Esto garantiza que se cree el MovimientoInsumo y se reste del Insumo.cantidad_actual
                    await InsumoService.registrar_movimiento(
                        db=db,
                        insumo_id=ingrediente.insumo_id,
                        data=movimiento_data,
                        usuario_id=usuario_id
                    )
                except HTTPException as e:
                    # Si el InsumoService lanza un 400 por stock negativo, lo atrapamos
                    # y le damos contexto al usuario sobre QUÉ pedido y QUÉ ingrediente falló.
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No se puede entregar el pedido. Stock insuficiente para la receta '{receta.nombre}'. Detalle: {e.detail}"
                    )