from uuid import UUID
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.receta import Receta
from app.models.ingrediente_receta import IngredienteReceta
from app.models.paso_receta import PasoReceta
from app.models.insumo import Insumo
from app.schemas.receta import RecetaCreate, RecetaUpdate
from app.services.hidden_cost_service import HiddenCostService
from app.services.cost_calculation_service import CostCalculationService


class RecetaService:

    @staticmethod
    async def get_all(db: AsyncSession, usuario_id: UUID) -> List[Receta]:
        """Obtiene todas las recetas activas del usuario con sus relaciones."""
        query = (
            select(Receta)
            .where(Receta.usuario_id == usuario_id, Receta.activa == True)
            .options(
                selectinload(Receta.ingredientes).selectinload(IngredienteReceta.insumo),
                selectinload(Receta.pasos),
                selectinload(Receta.gastos_ocultos)
            )
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, receta_id: UUID, usuario_id: UUID) -> Receta:
        """Obtiene una receta con todas sus relaciones cargadas."""
        query = (
            select(Receta)
            .where(Receta.id == receta_id, Receta.usuario_id == usuario_id, Receta.activa == True)
            .options(
                selectinload(Receta.ingredientes).selectinload(IngredienteReceta.insumo),
                selectinload(Receta.pasos),
                selectinload(Receta.gastos_ocultos)
            )
        )
        result = await db.execute(query)
        receta = result.scalar_one_or_none()
        if not receta:
            raise HTTPException(status_code=404, detail="Receta no encontrada o inactiva")
        return receta

    @staticmethod
    async def update_receta(db: AsyncSession, receta_id: UUID, data: RecetaUpdate, usuario_id: UUID) -> Receta:
        """Actualización completa de la receta, incluyendo ingredientes y pasos."""
        receta = await RecetaService.get_by_id(db, receta_id, usuario_id)

        update_data = data.model_dump(exclude_unset=True)

        for key in ["nombre", "porciones", "margen_pct"]:
            if key in update_data:
                setattr(receta, key, update_data[key])

        if "ingredientes" in update_data:
            # 1. Vaciamos la lista actual
            receta.ingredientes.clear()

            # 2. Obligamos a la BD a ejecutar los DELETE (Evita el Error de UniqueConstraint)
            await db.flush()

            # 3. Insertamos los nuevos
            for ing_dict in update_data["ingredientes"]:
                # Asignación EXPLÍCITA para evitar el 500 por inyección de llaves
                nuevo_ing = IngredienteReceta(
                    receta_id=receta.id,
                    insumo_id=ing_dict["insumo_id"],
                    cantidad_usada=ing_dict["cantidad_usada"],
                    unidad=ing_dict["unidad"]
                )
                receta.ingredientes.append(nuevo_ing)

        if "pasos" in update_data:
            receta.pasos.clear()
            for paso in update_data["pasos"]:
                nuevo_paso = PasoReceta(receta_id=receta.id, **paso)
                receta.pasos.append(nuevo_paso)

        await db.commit()
        await db.refresh(receta)
        return receta

    @staticmethod
    async def create_receta(db: AsyncSession, data: RecetaCreate, usuario_id: UUID) -> Receta:
        """Crea la receta, sus relaciones y gastos default en UNA SOLA transacción."""
        # Crear Receta base
        nueva_receta = Receta(
            usuario_id=usuario_id,
            nombre=data.nombre,
            porciones=data.porciones,
            margen_pct=data.margen_pct,
            activa=True
        )
        db.add(nueva_receta)
        await db.flush()  # Obtiene el ID generado sin hacer commit final

        # Agregar Ingredientes
        for ingrediente in data.ingredientes:
            nuevo_ing = IngredienteReceta(
                receta_id=nueva_receta.id,
                **ingrediente.model_dump()
            )
            db.add(nuevo_ing)

        # Agregar Pasos
        for paso in data.pasos:
            nuevo_paso = PasoReceta(
                receta_id=nueva_receta.id,
                **paso.model_dump()
            )
            db.add(nuevo_paso)

        # Inicializar Gastos Ocultos (Llamada síncrona, sin commit interno)
        HiddenCostService.crear_gastos_default(db, nueva_receta.id, usuario_id)

        # Commit de toda la transacción (ACID)
        await db.commit()

        # Retornar la receta con sus relaciones cargadas
        return await RecetaService.get_by_id(db, nueva_receta.id, usuario_id)

    @staticmethod
    async def delete_receta(db: AsyncSession, receta_id: UUID, usuario_id: UUID) -> bool:
        """Soft delete de la receta."""
        receta = await RecetaService.get_by_id(db, receta_id, usuario_id)
        receta.activa = False
        await db.commit()
        return True

    @staticmethod
    async def calcular_costeo(db: AsyncSession, receta_id: UUID, usuario_id: UUID) -> Dict[str, Any]:
        """Prepara los datos y llama a la calculadora de costos."""
        receta = await RecetaService.get_by_id(db, receta_id, usuario_id)

        # Obtener precios de insumos en una sola query
        ids_insumos = [ing.insumo_id for ing in receta.ingredientes]
        precios_query = select(Insumo.id, Insumo.precio_compra, Insumo.cantidad_comprada).where(
            Insumo.id.in_(ids_insumos))
        precios_result = await db.execute(precios_query)

        mapa_precios = {}
        for row in precios_result:
            unitario = row.precio_compra / row.cantidad_comprada if row.cantidad_comprada > 0 else 0
            mapa_precios[row.id] = unitario

        # Obtener gastos con lógica de Fallback (Específico vs Global)
        gastos = await HiddenCostService.get_gastos_para_receta(db, receta_id, usuario_id)

        # Calcular y retornar
        return CostCalculationService.calcular_costo(receta, mapa_precios, gastos)