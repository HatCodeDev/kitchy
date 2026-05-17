import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from app.services.pedido_service import PedidoService
from app.schemas.pedido import ColisionHoraResponse

@pytest.fixture
def usuario_id():
    return uuid4()

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db

@pytest.mark.asyncio
async def test_check_colision_hora_no_collision(mock_db, usuario_id):
    """Retorna hay_colision=False cuando el count es 0."""
    result = MagicMock()
    result.scalar = MagicMock(return_value=0)
    mock_db.execute.return_value = result

    fecha = datetime(2026, 5, 20, 14, 30, tzinfo=timezone.utc)
    response = await PedidoService.check_colision_hora(mock_db, fecha, usuario_id)

    assert isinstance(response, ColisionHoraResponse)
    assert response.hay_colision is False
    assert response.cantidad == 0
    assert response.hora_inicio == "14:00"
    assert response.hora_fin == "15:00"

@pytest.mark.asyncio
async def test_check_colision_hora_with_collision(mock_db, usuario_id):
    """Retorna hay_colision=True cuando el count > 0."""
    result = MagicMock()
    result.scalar = MagicMock(return_value=2)
    mock_db.execute.return_value = result

    fecha = datetime(2026, 5, 20, 10, 15, tzinfo=timezone.utc)
    response = await PedidoService.check_colision_hora(mock_db, fecha, usuario_id)

    assert response.hay_colision is True
    assert response.cantidad == 2
    assert response.hora_inicio == "10:00"
    assert response.hora_fin == "11:00"

@pytest.mark.asyncio
async def test_check_colision_hora_naive_datetime(mock_db, usuario_id):
    """Maneja correctamente datetimes naive convirtiéndolos a UTC."""
    result = MagicMock()
    result.scalar = MagicMock(return_value=0)
    mock_db.execute.return_value = result

    fecha = datetime(2026, 5, 20, 14, 30) # Naive
    response = await PedidoService.check_colision_hora(mock_db, fecha, usuario_id)

    assert response.hora_inicio == "14:00"

@pytest.mark.asyncio
async def test_check_colision_hora_calls_execute(mock_db, usuario_id):
    """Verifica que se llame al execute de la DB."""
    result = MagicMock()
    result.scalar = MagicMock(return_value=1)
    mock_db.execute.return_value = result

    pedido_id = uuid4()
    fecha = datetime(2026, 5, 20, 10, 15, tzinfo=timezone.utc)
    await PedidoService.check_colision_hora(mock_db, fecha, usuario_id, exclude_id=pedido_id)

    mock_db.execute.assert_called_once()
