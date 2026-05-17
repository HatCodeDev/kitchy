import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from main import app
from app.core.database import get_db

class MockResult:
    def scalars(self):
        class MockScalars:
            def first(self):
                return None
        return MockScalars()

@pytest.mark.asyncio
async def test_auth_endpoints_rate_limiting():
    """
    Valida que los endpoints de autenticación (/login)
    estén limitados a 10 solicitudes por minuto por IP.
    """
    mock_db = AsyncMock()
    async def mock_execute(query):
        return MockResult()
    mock_db.execute = mock_execute
    
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Hacemos 10 solicitudes seguidas al login.
        # Deben retornar 401 (ya que las credenciales no existen), no 429.
        for i in range(10):
            response = await ac.post("/api/v1/auth/login", data={
                "username": f"nonexistent_user_{i}@kitchy.com",
                "password": "wrong_password"
            })
            assert response.status_code == 401, f"Fallo en la petición {i+1} con status: {response.status_code}"
        
        # La 11ª solicitud debe ser bloqueada con 429 Too Many Requests
        response = await ac.post("/api/v1/auth/login", data={
            "username": "nonexistent_user_11@kitchy.com",
            "password": "wrong_password"
        })
        
        assert response.status_code == 429, f"Se esperaba 429 pero se recibió {response.status_code}"
        data = response.json()
        assert data == {"error": "Rate limit exceeded: 10 per 1 minute"}


@pytest.mark.asyncio
async def test_other_endpoints_not_rate_limited():
    """
    Valida que otros endpoints no estén afectados por el rate limit de auth.
    """
    app.dependency_overrides.clear()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Hacemos 11 solicitudes al health check de la app.
        # Deben retornar 200 siempre, sin ser bloqueadas por el rate limiter.
        for _ in range(11):
            response = await ac.get("/")
            assert response.status_code == 200
