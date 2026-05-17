import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from main import app
from app.core.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User


@pytest.fixture
def mock_user_instance():
    return User(
        id=uuid4(),
        email="emprendedor@kitchy.com",
        plan="free",
        empaque_mxn_default=Decimal("0.00"),
        desgaste_pct_default=Decimal("0.00"),
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )


@pytest.mark.asyncio
async def test_update_user_config_unauthorized():
    """Valida que PUT /api/v1/users/config sin autenticación retorne 401."""
    # Limpiamos overrides para asegurar que se ejecute la validación del token real
    app.dependency_overrides.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/api/v1/users/config", json={
            "empaque_mxn_default": "15.00",
            "desgaste_pct_default": "5.0"
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_config_success(mock_user_instance):
    """Valida que PUT /api/v1/users/config con JWT válido actualice los defaults y devuelva UserResponse."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Sobrescribimos dependencias en FastAPI
    app.dependency_overrides[get_current_user] = lambda: mock_user_instance
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/api/v1/users/config", json={
            "empaque_mxn_default": "25.50",
            "desgaste_pct_default": "12.00"
        })

    # Restauramos dependencias
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["empaque_mxn_default"] == "25.50"
    assert data["desgaste_pct_default"] == "12.00"
    assert data["plan"] == "free"

    # Verificamos que se haya hecho commit y refresh
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_called_once_with(mock_user_instance)
