from uuid import UUID
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gasto_oculto import GastoOculto
from app.models.user import User


class HiddenCostService:

    @staticmethod
    async def get_gastos_para_receta(db: AsyncSession, receta_id: UUID, usuario_id: UUID) -> Dict[
        str, Optional[GastoOculto]]:
        """
        Resuelve los gastos ocultos aplicando la regla de Fallback:
        1. Busca configuración específica de la receta.
        2. Si no hay configuración específica activa de receta, usa los defaults globales del usuario (de la tabla users).
        3. Si no hay defaults del usuario, usa la configuración global del usuario de la tabla gastos_ocultos (receta_id IS NULL).
        """
        # Obtener gastos específicos de esta receta
        query_especificos = select(GastoOculto).where(
            GastoOculto.receta_id == receta_id,
            GastoOculto.usuario_id == usuario_id
        )
        result_especificos = await db.execute(query_especificos)
        gastos_especificos = result_especificos.scalars().all()

        # Obtener gastos globales del usuario (receta_id IS NULL)
        query_globales = select(GastoOculto).where(
            GastoOculto.receta_id.is_(None),
            GastoOculto.usuario_id == usuario_id
        )
        result_globales = await db.execute(query_globales)
        gastos_globales = result_globales.scalars().all()

        # Obtener el usuario para sus defaults globales
        query_user = select(User).where(User.id == usuario_id)
        result_user = await db.execute(query_user)
        usuario = result_user.scalar_one_or_none()

        empaque_val = usuario.empaque_mxn_default if (usuario and usuario.empaque_mxn_default is not None) else Decimal('0.00')
        desgaste_val = usuario.desgaste_pct_default if (usuario and usuario.desgaste_pct_default is not None) else Decimal('0.00')

        # Mapeamos a diccionarios rápidos por 'tipo' ('empaque' o 'gas_luz')
        mapa_especificos = {g.tipo: g for g in gastos_especificos}
        mapa_globales = {g.tipo: g for g in gastos_globales}

        # Resolución de jerarquía (Fallback)
        # Prefiere el específico si está activo. Si no, toma el default global del usuario o el global de gastos_ocultos.
        gasto_empaque = mapa_especificos.get('empaque')
        if not gasto_empaque or not gasto_empaque.activo:
            global_empaque = mapa_globales.get('empaque')
            if global_empaque:
                global_empaque.valor = empaque_val
                global_empaque.activo = True
                gasto_empaque = global_empaque
            else:
                gasto_empaque = GastoOculto(
                    usuario_id=usuario_id,
                    receta_id=None,
                    tipo='empaque',
                    valor=empaque_val,
                    es_porcentaje=False,
                    activo=True
                )

        gasto_gas_luz = mapa_especificos.get('gas_luz')
        if not gasto_gas_luz or not gasto_gas_luz.activo:
            global_gas_luz = mapa_globales.get('gas_luz')
            if global_gas_luz:
                global_gas_luz.valor = desgaste_val
                global_gas_luz.activo = True
                gasto_gas_luz = global_gas_luz
            else:
                gasto_gas_luz = GastoOculto(
                    usuario_id=usuario_id,
                    receta_id=None,
                    tipo='gas_luz',
                    valor=desgaste_val,
                    es_porcentaje=True,
                    activo=True
                )

        resultado = {
            'empaque': gasto_empaque,
            'gas_luz': gasto_gas_luz
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
            # Si ya existe, actualizamos todos los campos enviados
            gasto.activo = activo
            gasto.valor = valor
            gasto.es_porcentaje = es_porcentaje
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