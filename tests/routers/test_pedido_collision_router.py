import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from main import app
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.pedido_service import PedidoService
from app.schemas.pedido import ColisionHoraResponse

@pytest.fixture
def mock_user():
    return User(id=uuid4(), email="test@kitchy.com")

@pytest.fixture
def override_auth(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    del app.dependency_overrides[get_current_user]

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_check_colision_endpoint_unauthenticated(client):
    """GET /check-colision sin auth retorna 401."""
    # Importante: No aplicamos el override_auth aquí
    response = await client.get("/api/v1/pedidos/check-colision", params={"fecha_entrega": "2026-05-20T14:00:00Z"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_check_colision_endpoint_success(client, override_auth):
    """GET /check-colision con auth retorna 200 y el esquema correcto."""
    
    mock_resp = ColisionHoraResponse(
        hay_colision=True,
        cantidad=2,
        hora_inicio="14:00",
        hora_fin="15:00"
    )
    
    with patch.object(PedidoService, "check_colision_hora", new_callable=AsyncMock) as mock_method:
        mock_method.return_value = mock_resp
        
        response = await client.get(
            "/api/v1/pedidos/check-colision", 
            params={"fecha_entrega": "2026-05-20T14:00:00Z"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert data["hay_colision"] is True
    assert data["cantidad"] == 2
    assert data["hora_inicio"] == "14:00"
    assert data["hora_fin"] == "15:00"

@pytest.mark.asyncio
async def test_check_colision_endpoint_fail_silently(client, override_auth):
    """GET /check-colision falla silenciosamente ante errores del service."""
    
    with patch.object(PedidoService, "check_colision_hora", side_effect=Exception("DB Down")):
        response = await client.get(
            "/api/v1/pedidos/check-colision", 
            params={"fecha_entrega": "2026-05-20T14:00:00Z"}
        )
        
    assert response.status_code == 200
    data = response.json()
    assert data["hay_colision"] is False
    assert data["cantidad"] == 0
