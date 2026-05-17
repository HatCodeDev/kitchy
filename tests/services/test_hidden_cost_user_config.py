import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal
from app.services.hidden_cost_service import HiddenCostService
from app.models.user import User
from app.models.gasto_oculto import GastoOculto


@pytest.mark.asyncio
async def test_get_gastos_para_receta_fallback_to_user_defaults():
    """
    Test que verifica que get_gastos_para_receta retorne los defaults del usuario
    cuando no hay gastos específicos activos en la base de datos para la receta.
    """
    db = AsyncMock()
    receta_id = uuid4()
    usuario_id = uuid4()

    # Mock del usuario en la base de datos
    mock_usuario = User(
        id=usuario_id,
        email="emprendedor@kitchy.com",
        plan="free",
        empaque_mxn_default=Decimal("12.50"),
        desgaste_pct_default=Decimal("5.5")
    )

    # Creamos un mock para el resultado de execute de cada query en orden:
    # 1. query_especificos: retorna gastos específicos inactivos (activo=False, valor=0.00)
    # 2. query_globales: retorna lista vacía (sin global en BD)
    # 3. query_user: retorna el usuario mock
    
    mock_result_especificos = MagicMock()
    mock_result_especificos.scalars.return_value.all.return_value = [
        GastoOculto(usuario_id=usuario_id, receta_id=receta_id, tipo='empaque', valor=Decimal('0.00'), es_porcentaje=False, activo=False),
        GastoOculto(usuario_id=usuario_id, receta_id=receta_id, tipo='gas_luz', valor=Decimal('0.00'), es_porcentaje=True, activo=False)
    ]

    mock_result_globales = MagicMock()
    mock_result_globales.scalars.return_value.all.return_value = []

    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = mock_usuario

    # db.execute se llamará 3 veces
    db.execute.side_effect = [
        mock_result_especificos,
        mock_result_globales,
        mock_result_user
    ]

    resultado = await HiddenCostService.get_gastos_para_receta(db, receta_id, usuario_id)

    # Verificamos que se haya aplicado el fallback a los defaults del usuario
    assert resultado['empaque'] is not None
    assert resultado['empaque'].valor == Decimal("12.50")
    assert resultado['empaque'].activo is True
    assert resultado['empaque'].es_porcentaje is False

    assert resultado['gas_luz'] is not None
    assert resultado['gas_luz'].valor == Decimal("5.5")
    assert resultado['gas_luz'].activo is True
    assert resultado['gas_luz'].es_porcentaje is True
