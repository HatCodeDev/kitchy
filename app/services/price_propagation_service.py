import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.models.receta import Receta
from app.models.insumo import Insumo
from app.models.ingrediente_receta import IngredienteReceta
from app.services.cost_calculation_service import CostCalculationService

logger = logging.getLogger(__name__)


class PricePropagationService:
    @staticmethod
    async def propagar_cambio_precio(db: AsyncSession, insumo_id: UUID, usuario_id: UUID):
        """
        RN-03: Recalcula costos de recetas activas cuando un insumo cambia de precio.
        """
        # Buscar recetas activas del usuario que usan este insumo
        # Usamos selectinload para traer ingredientes y gastos en una sola ráfaga de red
        query = (
            select(Receta)
            .join(IngredienteReceta)
            .where(
                Receta.usuario_id == usuario_id,
                Receta.activa == True,
                IngredienteReceta.insumo_id == insumo_id
            )
            .options(
                selectinload(Receta.ingredientes),
                selectinload(Receta.gastos_ocultos)
            )
        )

        result = await db.execute(query)
        recetas_afectadas = result.scalars().all()

        if not recetas_afectadas:
            return

        for receta in recetas_afectadas:
            # Preparar datos para el cálculo
            # Necesitamos los precios actuales de TODOS los insumos de esta receta
            ids_insumos = [ing.insumo_id for ing in receta.ingredientes]
            precios_query = select(Insumo.id, Insumo.precio_compra, Insumo.cantidad_comprada, Insumo.unidad).where(
                Insumo.id.in_(ids_insumos))
            precios_result = await db.execute(precios_query)

            # Mapeamos a un diccionario esperado por el CostCalculationService
            mapa_precios = {}
            for row in precios_result:
                unitario = row.precio_compra / row.cantidad_comprada if row.cantidad_comprada > 0 else Decimal('0.00')
                mapa_precios[row.id] = {
                    "precio_unitario": unitario,
                    "unidad_compra": row.unidad
                }

            # Mapear Gastos Ocultos
            mapa_gastos = {g.tipo: g for g in receta.gastos_ocultos if g.activo}

            # Ejecutar recálculo
            analisis = CostCalculationService.calcular_costo(
                receta=receta,
                insumos_precios=mapa_precios,
                gastos_ocultos=mapa_gastos
            )

            # Lógica de Alerta: Margen en Riesgo
            # Si el costo por porción subió mucho, avisamos.
            # (Aquí compararíamos contra un histórico, por ahora logueamos)
            logger.info(
                f"Recálculo Propagado: Receta '{receta.nombre}' - "
                f"Nuevo Costo Total: {analisis['costo_total']} MXN. "
                f"Precio Sugerido: {analisis['precio_sugerido']} MXN."
            )

            #    If analisis['costo_por_porcion'] > umbral_alerta:
            #    Crear NotificacionProgramada(tipo='margen_en_riesgo', ...)
            #    db.add(notificacion)

        await db.commit()