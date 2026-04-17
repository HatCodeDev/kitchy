from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from uuid import UUID

from app.models.receta import Receta
from app.models.gasto_oculto import GastoOculto


class CostCalculationService:
    @staticmethod
    def _redondear(valor: Decimal) -> Decimal:
        """Aplica redondeo financiero exacto a 2 decimales (MXN)."""
        return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def calcular_costo(
            receta: Receta,
            insumos_precios: Dict[UUID, Decimal],
            gastos_ocultos: Dict[str, GastoOculto]
    ) -> Dict[str, Any]:
        """
        Motor de cálculo de costos y precio sugerido de Kitchy.
        """
        # Costo Base: Insumos
        costo_insumos = Decimal('0.00')
        for ingrediente in receta.ingredientes:
            # Obtenemos el precio unitario del diccionario inyectado
            precio_unitario = insumos_precios.get(ingrediente.insumo_id, Decimal('0.00'))
            costo_insumos += precio_unitario * ingrediente.cantidad_usada

        # Gastos Ocultos (Empaque y Energía)
        costo_empaque = Decimal('0.00')
        gasto_empaque = gastos_ocultos.get('empaque')
        if gasto_empaque and gasto_empaque.activo:
            if gasto_empaque.es_porcentaje:
                costo_empaque = costo_insumos * (gasto_empaque.valor / Decimal('100'))
            else:
                costo_empaque = gasto_empaque.valor

        costo_energia = Decimal('0.00')
        gasto_energia = gastos_ocultos.get('gas_luz')
        if gasto_energia and gasto_energia.activo:
            if gasto_energia.es_porcentaje:
                costo_energia = costo_insumos * (gasto_energia.valor / Decimal('100'))
            else:
                costo_energia = gasto_energia.valor

        # Sumatorias y Divisiones
        costo_total = costo_insumos + costo_empaque + costo_energia

        # Prevenir división por cero (aunque Pydantic ya lo valida, el backend debe ser inquebrantable)
        porciones = receta.porciones if receta.porciones > 0 else 1
        costo_por_porcion = costo_total / Decimal(porciones)

        # Precio Sugerido (Costo por porción + Margen de ganancia)
        margen = receta.margen_pct / Decimal('100')
        precio_sugerido = costo_por_porcion * (Decimal('1') + margen)

        # Cálculo del Desglose Porcentual (Para gráficas en el Frontend)
        pct_insumos = Decimal('0.00')
        pct_empaque = Decimal('0.00')
        pct_energia = Decimal('0.00')

        if costo_total > 0:
            # Calculamos insumos y empaque
            pct_insumos = CostCalculationService._redondear((costo_insumos / costo_total) * Decimal('100'))
            pct_empaque = CostCalculationService._redondear((costo_empaque / costo_total) * Decimal('100'))
            # La energía se calcula por diferencia para garantizar que siempre sume exactamente 100%
            pct_energia = Decimal('100.00') - pct_insumos - pct_empaque

        # Retorno de resultados con formato monetario exacto
        return {
            "costo_insumos": CostCalculationService._redondear(costo_insumos),
            "costo_empaque": CostCalculationService._redondear(costo_empaque),
            "costo_energia": CostCalculationService._redondear(costo_energia),
            "costo_total": CostCalculationService._redondear(costo_total),
            "costo_por_porcion": CostCalculationService._redondear(costo_por_porcion),
            "precio_sugerido": CostCalculationService._redondear(precio_sugerido),
            "desglose_pct": {
                "insumos": pct_insumos,
                "empaque": pct_empaque,
                "gas_luz": pct_energia
            }
        }