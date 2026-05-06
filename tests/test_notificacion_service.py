import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.services.notificacion_service import NotificacionService
from app.models.notificacion_programada import NotificacionProgramada

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db

@pytest.mark.asyncio
async def test_programar_recordatorio_exitoso(mock_db):
    """Verifica que se programe correctamente a -2 horas."""
    usuario_id = uuid4()
    pedido_id = uuid4()
    # Entrega en 5 horas
    fecha_entrega = datetime.now(timezone.utc) + timedelta(hours=5)
    
    notif = await NotificacionService.programar_recordatorio(
        mock_db, pedido_id, fecha_entrega, usuario_id
    )
    
    assert notif is not None
    assert notif.tipo == 'recordatorio_entrega'
    # La notificación debe ser 2 horas antes de la entrega (3 horas desde ahora)
    expected_time = fecha_entrega - timedelta(hours=2)
    assert notif.fecha_programada == expected_time
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_programar_recordatorio_omite_si_es_tarde(mock_db):
    """Verifica que no se cree notificación si la entrega es en menos de 2h."""
    usuario_id = uuid4()
    pedido_id = uuid4()
    # Entrega en solo 1 hora (ya pasó el umbral de las -2h)
    fecha_entrega = datetime.now(timezone.utc) + timedelta(hours=1)
    
    notif = await NotificacionService.programar_recordatorio(
        mock_db, pedido_id, fecha_entrega, usuario_id
    )
    
    assert notif is None
    mock_db.add.assert_not_called()

@pytest.mark.asyncio
async def test_cancelar_recordatorio_ejecuta_update(mock_db):
    """Verifica que se llame al update de SQLAlchemy para cancelar."""
    usuario_id = uuid4()
    pedido_id = uuid4()
    
    await NotificacionService.cancelar_recordatorio(mock_db, pedido_id, usuario_id)
    
    # Verificamos que se ejecute una sentencia en la DB
    mock_db.execute.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
