import pytest
import uuid
from decimal import Decimal
from typing import Dict, Any

from app.models.receta import Receta
from app.models.ingrediente_receta import IngredienteReceta
from app.models.gasto_oculto import GastoOculto
from app.services.cost_calculation_service import CostCalculationService


# --- FIXTURES (Datos de prueba reutilizables) ---

@pytest.fixture
def insumos_precios() -> Dict[uuid.UUID, Dict[str, Any]]:
    return {
        uuid.UUID('11111111-1111-1111-1111-111111111111'): {
            "precio_unitario": Decimal('10.00'),
            "unidad_compra": "pza"
        },
        uuid.UUID('22222222-2222-2222-2222-222222222222'): {
            "precio_unitario": Decimal('25.50'),
            "unidad_compra": "pza"
        }
    }


@pytest.fixture
def receta_base() -> Receta:
    ingrediente1 = IngredienteReceta(
        insumo_id=uuid.UUID('11111111-1111-1111-1111-111111111111'),
        cantidad_usada=Decimal('2.0'),  # 2 x $10.00 = $20.00
        unidad='pza'
    )
    ingrediente2 = IngredienteReceta(
        insumo_id=uuid.UUID('22222222-2222-2222-2222-222222222222'),
        cantidad_usada=Decimal('1.0'),  # 1 x $25.50 = $25.50
        unidad='pza'
    )
    # Costo total insumos esperado: $45.50
    return Receta(
        nombre="Pastel de Prueba",
        porciones=2,
        margen_pct=Decimal('0.0'),
        ingredientes=[ingrediente1, ingrediente2]
    )


# --- TESTS ---

def test_costo_sin_gastos_ocultos(receta_base, insumos_precios):
    """a. Verifica que el costo total sea exactamente la suma de (precio * cantidad)."""
    resultado = CostCalculationService.calcular_costo(receta_base, insumos_precios, {})

    assert resultado['costo_insumos'] == Decimal('45.50')
    assert resultado['costo_empaque'] == Decimal('0.00')
    assert resultado['costo_energia'] == Decimal('0.00')
    assert resultado['costo_total'] == Decimal('45.50')
    # 45.50 / 2 porciones = 22.75
    assert resultado['costo_por_porcion'] == Decimal('22.75')


def test_costo_con_empaque_fijo(receta_base, insumos_precios):
    """b. Verifica que se sume un gasto de empaque de valor fijo."""
    gastos = {
        'empaque': GastoOculto(tipo='empaque', valor=Decimal('5.00'), es_porcentaje=False, activo=True)
    }
    resultado = CostCalculationService.calcular_costo(receta_base, insumos_precios, gastos)

    assert resultado['costo_empaque'] == Decimal('5.00')
    assert resultado['costo_total'] == Decimal('50.50')  # 45.50 + 5.00


def test_costo_con_gas_luz_porcentaje(receta_base, insumos_precios):
    """c. Verifica que el gas/luz se calcule como el 10% del costo de insumos."""
    gastos = {
        'gas_luz': GastoOculto(tipo='gas_luz', valor=Decimal('10.00'), es_porcentaje=True, activo=True)
    }
    resultado = CostCalculationService.calcular_costo(receta_base, insumos_precios, gastos)

    # 10% de 45.50 = 4.55
    assert resultado['costo_energia'] == Decimal('4.55')
    assert resultado['costo_total'] == Decimal('50.05')


def test_costo_con_ambos_gastos(receta_base, insumos_precios):
    """d. Verifica cálculo combinado (Empaque fijo $5 + Energía 10%)."""
    gastos = {
        'empaque': GastoOculto(tipo='empaque', valor=Decimal('5.00'), es_porcentaje=False, activo=True),
        'gas_luz': GastoOculto(tipo='gas_luz', valor=Decimal('10.00'), es_porcentaje=True, activo=True)
    }
    resultado = CostCalculationService.calcular_costo(receta_base, insumos_precios, gastos)

    assert resultado['costo_total'] == Decimal('55.05')  # 45.50 + 5.00 + 4.55


def test_precio_sugerido_con_margen(receta_base, insumos_precios):
    """e. Verifica cálculo de precio sugerido con margen del 50%."""
    receta_base.margen_pct = Decimal('50.00')
    resultado = CostCalculationService.calcular_costo(receta_base, insumos_precios, {})

    # Costo por porción es 22.75. El 50% extra es 11.375 (redondeado a 11.38).
    # 22.75 * 1.50 = 34.125 -> Redondeo ROUND_HALF_UP a 2 decimales -> 34.13
    assert resultado['precio_sugerido'] == Decimal('34.13')


def test_todos_los_valores_con_2_decimales(receta_base, insumos_precios):
    """f. Verifica que TODOS los valores monetarios retornados tengan 2 decimales."""
    # Le metemos números feos para forzar el redondeo
    receta_base.ingredientes[0].cantidad_usada = Decimal('1.1234')
    resultado = CostCalculationService.calcular_costo(receta_base, insumos_precios, {})

    # El exponente de .quantize(Decimal('0.01')) nos dice los decimales exactos
    assert resultado['costo_total'].as_tuple().exponent == -2
    assert resultado['costo_por_porcion'].as_tuple().exponent == -2
    assert resultado['precio_sugerido'].as_tuple().exponent == -2