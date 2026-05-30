"""
Servicio de Gestión de Recetas de Cocina.

Este módulo implementa el control CRUD para recetas culinarias, incluyendo la orquestación
de sus ingredientes, pasos ordenados de preparación y gastos indirectos. También integra
el motor de costeo culinario (CostCalculationService) y gestiona transacciones ACID complejas.
"""
from uuid import UUID
from typing import List, Dict, Any, Union
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from decimal import Decimal

from app.models.receta import Receta
from app.models.ingrediente_receta import IngredienteReceta
from app.models.paso_receta import PasoReceta
from app.models.insumo import Insumo
from app.schemas.receta import RecetaCreate, RecetaUpdate
from app.services.hidden_cost_service import HiddenCostService
from app.services.cost_calculation_service import CostCalculationService
from app.services.unit_conversion_service import UnitConversionService


class RecetaService:
    """
    Servicio encargado de administrar las recetas, sus procesos y la liquidación financiera.
    """

    @staticmethod
    async def get_all(db: AsyncSession, usuario_id: UUID) -> List[Receta]:
        """
        Obtiene todas las recetas activas de un usuario cargando sus relaciones de forma óptima.

        Utiliza `selectinload` para precargar de manera eficiente ingredientes (con sus respectivos
        insumos), pasos de preparación y configuraciones de gastos ocultos en un mínimo de ráfagas SQL.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            usuario_id (UUID): ID del usuario dueño de las recetas.

        Returns:
            List[Receta]: Listado de recetas activas del usuario.
        """
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
        """
        Busca una receta activa por ID validando la propiedad y cargando sus relaciones.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            receta_id (UUID): ID de la receta buscada.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            Receta: La instancia de Receta cargada.

        Raises:
            HTTPException: 404 si la receta no existe, pertenece a otro usuario o está inactiva.
        """
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
        """
        Actualiza completamente los datos, ingredientes y pasos de una receta.

        Para evitar infracciones de UniqueConstraints de base de datos en ingredientes y pasos,
        aplica un patrón de borrado de relaciones huérfanas seguido de una llamada a `db.flush()`
        antes de insertar las nuevas listas de ingredientes y pasos de forma atómica.
        Realiza la conversión de tiempos de duración a segundos si es necesario.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            receta_id (UUID): ID de la receta a modificar.
            data (RecetaUpdate): DTO con los campos básicos, nuevos ingredientes y pasos.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            Receta: La instancia de Receta actualizada y re-consultada de la base de datos.
        """
        receta = await RecetaService.get_by_id(db, receta_id, usuario_id)
        update_data = data.model_dump(exclude_unset=True)

        for key in ["nombre", "porciones", "margen_pct"]:
            if key in update_data:
                setattr(receta, key, update_data[key])

        if "ingredientes" in update_data:
            receta.ingredientes.clear()
            await db.flush()  # Limpia la "mesa" para evitar colisión de IDs
            for ing_dict in update_data["ingredientes"]:
                nuevo_ing = IngredienteReceta(
                    receta_id=receta.id,
                    insumo_id=ing_dict["insumo_id"],
                    cantidad_usada=ing_dict["cantidad_usada"],
                    unidad=ing_dict["unidad"]
                )
                receta.ingredientes.append(nuevo_ing)

        if "pasos" in update_data:
            receta.pasos.clear()
            await db.flush()
            for paso_dict in update_data["pasos"]:
                duracion_final = paso_dict.get("duracion_segundos")
                
                # Si el front mandó duracion + unidad, convertimos
                if paso_dict.get("duracion") is not None:
                    duracion_final = int(UnitConversionService.convertir(
                        cantidad=paso_dict["duracion"],
                        unidad_origen=paso_dict.get("unidad", "seg"),
                        unidad_destino="seg"
                    ))

                nuevo_paso = PasoReceta(
                    receta_id=receta.id,
                    orden=paso_dict["orden"],
                    descripcion=paso_dict["descripcion"],
                    duracion_segundos=duracion_final,
                    es_critico=paso_dict.get("es_critico", False)
                )
                receta.pasos.append(nuevo_paso)

        await db.commit()
        # En lugar de refresh, re-consultamos con relaciones para evitar Lazy Loading Error
        return await RecetaService.get_by_id(db, receta.id, usuario_id)

    @staticmethod
    async def create_receta(db: AsyncSession, data: RecetaCreate, usuario_id: UUID) -> Receta:
        """
        Crea una nueva receta, sus ingredientes, pasos y gastos por defecto de forma atómica.

        Inicializa los gastos ocultos desactivados mediante `HiddenCostService.crear_gastos_default`
        y persiste todo bajo una única transacción ACID coordinada.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            data (RecetaCreate): DTO con los detalles de la receta, ingredientes y pasos.
            usuario_id (UUID): ID del usuario creador.

        Returns:
            Receta: La receta creada con todas sus relaciones resueltas.
        """
        nueva_receta = Receta(
            usuario_id=usuario_id,
            nombre=data.nombre,
            porciones=data.porciones,
            margen_pct=data.margen_pct,
            activa=True
        )
        db.add(nueva_receta)
        await db.flush()

        for ingrediente in data.ingredientes:
            nuevo_ing = IngredienteReceta(
                receta_id=nueva_receta.id,
                **ingrediente.model_dump()
            )
            db.add(nuevo_ing)

        for paso in data.pasos:
            duracion_final = paso.duracion_segundos
            
            if paso.duracion is not None:
                duracion_final = int(UnitConversionService.convertir(
                    cantidad=paso.duracion,
                    unidad_origen=paso.unidad or "seg",
                    unidad_destino="seg"
                ))

            nuevo_paso = PasoReceta(
                receta_id=nueva_receta.id,
                orden=paso.orden,
                descripcion=paso.descripcion,
                duracion_segundos=duracion_final,
                es_critico=paso.es_critico
            )
            db.add(nuevo_paso)

        HiddenCostService.crear_gastos_default(db, nueva_receta.id, usuario_id)
        await db.commit()

        # Re-consulta explícita para asegurar que el objeto devuelto es completo
        return await RecetaService.get_by_id(db, nueva_receta.id, usuario_id)

    @staticmethod
    async def delete_receta(db: AsyncSession, receta_id: UUID, usuario_id: UUID) -> bool:
        """
        Desactiva lógicamente (soft delete) una receta del sistema.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            receta_id (UUID): ID de la receta a desactivar.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            bool: True si la desactivación fue exitosa.
        """
        receta = await RecetaService.get_by_id(db, receta_id, usuario_id)
        receta.activa = False
        await db.commit()
        return True

    @staticmethod
    async def calcular_costeo(
            db: AsyncSession,
            receta_or_id: Union[UUID, Receta],
            usuario_id: UUID
    ) -> Dict[str, Any]:
        """
        Calcula el costeo culinario y financiero de una receta.

        Para optimizar recursos de red y consultas SQL, acepta tanto el ID de la receta
        como la instancia de la receta ya cargada (evitando consultas duplicadas si se invoca
        desde colecciones). Obtiene los precios unitarios actuales de todos sus ingredientes en
        una sola query, resuelve la jerarquía de gastos ocultos y corre el motor de cálculo.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            receta_or_id (Union[UUID, Receta]): ID de la receta o su instancia cargada.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            Dict[str, Any]: Resultados monetarios desglosados y precio sugerido.
        """
        # Lógica inteligente de carga:
        if isinstance(receta_or_id, UUID):
            receta = await RecetaService.get_by_id(db, receta_or_id, usuario_id)
        else:
            receta = receta_or_id

        # Obtener precios de insumos en una sola query
        ids_insumos = [ing.insumo_id for ing in receta.ingredientes]
        precios_query = select(Insumo.id, Insumo.precio_compra, Insumo.cantidad_comprada, Insumo.unidad).where(
            Insumo.id.in_(ids_insumos))
        precios_result = await db.execute(precios_query)

        mapa_precios = {}
        for row in precios_result:
            unitario = row.precio_compra / row.cantidad_comprada if row.cantidad_comprada > 0 else Decimal('0.00')
            mapa_precios[row.id] = {
                "precio_unitario": unitario,
                "unidad_compra": row.unidad
            }

        # Obtener gastos con lógica de Fallback (Específico vs Global)
        gastos = await HiddenCostService.get_gastos_para_receta(db, receta.id, usuario_id)

        # Calcular y retornar
        return CostCalculationService.calcular_costo(receta, mapa_precios, gastos)