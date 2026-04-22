from uuid import UUID
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gasto_oculto import GastoOculto


class HiddenCostService:

    @staticmethod
    async def get_gastos_para_receta(db: AsyncSession, receta_id: UUID, usuario_id: UUID) -> Dict[
        str, Optional[GastoOculto]]:
        """
        Resuelve los gastos ocultos aplicando la regla de Fallback:
        1. Busca configuración específica de la receta.
        2. Si un gasto no está configurado, usa la configuración global del usuario (receta_id IS NULL).
        """
        # Obtener gastos específicos de esta receta
        query_especificos = select(GastoOculto).where(
            GastoOculto.receta_id == receta_id,
            GastoOculto.usuario_id == usuario_id
        )
        result_especificos = await db.execute(query_especificos)
        gastos_especificos = result_especificos.scalars().all()

        # Obtener gastos globales del usuario
        query_globales = select(GastoOculto).where(
            GastoOculto.receta_id.is_(None),
            GastoOculto.usuario_id == usuario_id
        )
        result_globales = await db.execute(query_globales)
        gastos_globales = result_globales.scalars().all()

        # Mapeamos a diccionarios rápidos por 'tipo' ('empaque' o 'gas_luz')
        mapa_especificos = {g.tipo: g for g in gastos_especificos}
        mapa_globales = {g.tipo: g for g in gastos_globales}

        # Resolución de jerarquía (Fallback)
        # Prefiere el específico. Si es None, toma el global. Si ambos son None, retorna None.
        resultado = {
            'empaque': mapa_especificos.get('empaque') or mapa_globales.get('empaque'),
            'gas_luz': mapa_especificos.get('gas_luz') or mapa_globales.get('gas_luz')
        }

        return resultado

    @staticmethod
    async def toggle_gasto(
            db: AsyncSession,
            receta_id: UUID,
            tipo: str,
            activo: bool,
            usuario_id: UUID,
            valor: Decimal = Decimal('0.00'),  # Default seguro por si no existe
            es_porcentaje: bool = False  # Default seguro por si no existe
    ) -> GastoOculto:
        """
        Upsert (Update or Insert) de un gasto oculto para una receta específica.
        """
        query = select(GastoOculto).where(
            GastoOculto.receta_id == receta_id,
            GastoOculto.tipo == tipo,
            GastoOculto.usuario_id == usuario_id
        )
        result = await db.execute(query)
        gasto = result.scalar_one_or_none()

        if gasto:
            # Si ya existe, solo cambiamos su estado activo
            gasto.activo = activo
        else:
            # Si no existe (porque lo borró o es una receta vieja), lo creamos
            gasto = GastoOculto(
                usuario_id=usuario_id,
                receta_id=receta_id,
                tipo=tipo,
                valor=valor,
                es_porcentaje=es_porcentaje,
                activo=activo
            )
            db.add(gasto)

        # Aquí sí hacemos commit porque este método responde a un endpoint HTTP individual
        await db.commit()
        await db.refresh(gasto)
        return gasto

    @staticmethod
    def crear_gastos_default(db: AsyncSession, receta_id: UUID, usuario_id: UUID):
        """
        Inicializa los gastos en $0 y desactivados al crear una receta nueva.
        NOTA: No hace commit. Se delega al RecetaService para mantener la transacción ACID.
        """
        gasto_empaque = GastoOculto(
            usuario_id=usuario_id,
            receta_id=receta_id,
            tipo='empaque',
            valor=Decimal('0.00'),
            es_porcentaje=False,  # El empaque suele ser monto fijo ($)
            activo=False
        )

        gasto_gas_luz = GastoOculto(
            usuario_id=usuario_id,
            receta_id=receta_id,
            tipo='gas_luz',
            valor=Decimal('0.00'),
            es_porcentaje=True,  # La energía suele ser porcentaje (%)
            activo=False
        )

        db.add_all([gasto_empaque, gasto_gas_luz])