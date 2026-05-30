"""
Servicio de Gestión de Gastos Ocultos.

Este módulo implementa las reglas de negocio y jerarquías de resolución para los
gastos indirectos (gastos ocultos) en Kitchy, aplicando un flujo de fallback
(específico de receta -> defaults de usuario -> defaults de base de datos) para empaque y energía.
"""
from uuid import UUID
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gasto_oculto import GastoOculto
from app.models.user import User


class HiddenCostService:
    """
    Servicio para resolver, crear y actualizar los gastos ocultos de las recetas de los usuarios.
    """

    @staticmethod
    async def get_gastos_para_receta(db: AsyncSession, receta_id: UUID, usuario_id: UUID) -> Dict[
        str, Optional[GastoOculto]]:
        """
        Resuelve los gastos ocultos aplicables a una receta aplicando la regla de jerarquía (Fallback).

        La regla jerárquica de resolución sigue los siguientes pasos:
        1. Busca si existe una configuración de GastoOculto activa y específica para la receta (`receta_id`).
        2. Si no existe, recupera los valores de configuración por defecto globales del usuario (`User`).
        3. Si no existen registros específicos, busca y retorna los gastos globales del usuario (`receta_id IS NULL`).
        4. Si no hay registros de ningún tipo, instancia y retorna objetos GastoOculto temporales inicializados
           con los valores por defecto del perfil del usuario (empaque en MXN y desgaste en %).

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            receta_id (UUID): ID de la receta para la que se consultan los gastos.
            usuario_id (UUID): ID del usuario dueño de la receta.

        Returns:
            Dict[str, Optional[GastoOculto]]: Diccionario que contiene las instancias
                del modelo GastoOculto para 'empaque' y 'gas_luz'.
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
        Realiza un Upsert (Update o Insert) de la configuración de un gasto oculto.

        Busca la configuración del gasto específico del tipo dado para la receta.
        Si existe, actualiza sus campos; si no existe, crea un nuevo registro.
        Este método hace commit de la transacción de forma inmediata.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            receta_id (UUID): ID de la receta afectada.
            tipo (str): Tipo de gasto ('empaque' o 'gas_luz').
            activo (bool): Estado de activación del gasto oculto.
            usuario_id (UUID): ID del usuario que solicita la operación.
            valor (Decimal): El valor del gasto. Por defecto 0.00.
            es_porcentaje (bool): Si el valor representa un porcentaje del costo neto. Por defecto False.

        Returns:
            GastoOculto: La instancia creada o actualizada de GastoOculto.
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
        Inicializa los gastos ocultos por defecto al crear una receta nueva.

        Crea registros de empaque (en $0 inactivo) y energía (en 0% inactivo).
        Esta función agrega los objetos a la sesión pero **no realiza commit**,
        delegando la transacción ACID al servicio que la invoca (generalmente RecetaService).

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            receta_id (UUID): ID de la receta recién creada.
            usuario_id (UUID): ID del usuario creador.
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