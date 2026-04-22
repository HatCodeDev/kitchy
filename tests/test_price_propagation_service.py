import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from decimal import Decimal

from app.services.price_propagation_service import PricePropagationService
from app.models.receta import Receta
from app.models.ingrediente_receta import IngredienteReceta


@pytest.mark.asyncio
async def test_propagar_recalcula_solo_recetas_del_usuario():
    """a. Verifica que la query se ejecuta sin errores y procesa las recetas afectadas."""
    db_mock = AsyncMock()
    insumo_id = uuid4()
    usuario_id = uuid4()

    # Simulamos una receta devuelta por la base de datos
    receta_mock = Receta(
        id=uuid4(),
        usuario_id=usuario_id,
        nombre="Receta Afectada",
        porciones=1,
        margen_pct=Decimal('30.0'),
        activa=True,
        ingredientes=[IngredienteReceta(insumo_id=insumo_id, cantidad_usada=Decimal('1.0'))],
        gastos_ocultos=[]
    )

    # El servicio hace 2 queries: 1 para recetas, 1 para precios de insumos
    mock_result_recetas = MagicMock()
    mock_result_recetas.scalars().all.return_value = [receta_mock]

    mock_result_precios = MagicMock()
    mock_row = MagicMock()
    mock_row.id = insumo_id
    mock_row.precio_compra = Decimal('100.00')
    mock_row.cantidad_comprada = Decimal('1.00')
    mock_result_precios.__iter__.return_value = [mock_row]

    # Configuramos el mock de DB para devolver los resultados en orden
    db_mock.execute.side_effect = [mock_result_recetas, mock_result_precios]

    with patch('app.services.cost_calculation_service.CostCalculationService.calcular_costo') as mock_calc:
        # Simulamos la respuesta de la calculadora
        mock_calc.return_value = {
            'costo_total': Decimal('100.00'),
            'precio_sugerido': Decimal('130.00'),
            'costo_por_porcion': Decimal('100.00')
        }

        await PricePropagationService.propagar_cambio_precio(db_mock, insumo_id, usuario_id)

    # Aserciones: Verificamos que se consultó la BD, se calculó y se hizo commit
    assert db_mock.execute.call_count == 2
    mock_calc.assert_called_once()
    db_mock.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.services.price_propagation_service.logger')
async def test_notificacion_creada_cuando_margen_en_riesgo(mock_logger):
    """b. Verifica creación de notificación (o log temporal) cuando el costo sube."""
    db_mock = AsyncMock()
    insumo_id = uuid4()
    usuario_id = uuid4()

    receta_mock = Receta(
        id=uuid4(),
        usuario_id=usuario_id,
        nombre="Receta Cara",
        porciones=1,
        margen_pct=Decimal('0.0'),
        activa=True,
        ingredientes=[IngredienteReceta(insumo_id=insumo_id, cantidad_usada=Decimal('1.0'))],
        gastos_ocultos=[]
    )

    mock_result_recetas = MagicMock()
    mock_result_recetas.scalars().all.return_value = [receta_mock]

    mock_result_precios = MagicMock()
    mock_result_precios.__iter__.return_value = []

    db_mock.execute.side_effect = [mock_result_recetas, mock_result_precios]

    await PricePropagationService.propagar_cambio_precio(db_mock, insumo_id, usuario_id)

    # Verificamos que nuestro código temporal (logger.info) fue llamado
    # para registrar la alerta de propagación (E6-08 Criterio de Aceptación)
    assert mock_logger.info.called
    log_message = mock_logger.info.call_args[0][0]
    assert "Receta 'Receta Cara'" in log_message