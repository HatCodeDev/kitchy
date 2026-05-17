import pytest
import jwt
from uuid import UUID
from app.core.config import settings
from app.core.limiter import limiter

# Desactivar slowapi de forma global en este módulo de test
limiter.enabled = False

@pytest.mark.asyncio
async def test_register_success(async_client):
    """
    a. test_register_success: POST /api/v1/auth/register con email y password válidos
    -> HTTP 201, body contiene id y email.
    """
    email = "new_user_register_success@kitchy.com"
    password = "securepassword123"
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == email
    # Verificar que el id es un UUID válido
    try:
        UUID(data["id"])
    except ValueError:
        pytest.fail("El id devuelto no es un UUID válido")


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client):
    """
    b. test_register_duplicate_email: registrar el mismo email dos veces
    -> segunda vez HTTP 400.
    """
    email = "duplicate_email_test@kitchy.com"
    password = "securepassword123"
    
    # Primer registro
    response1 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    assert response1.status_code == 201
    
    # Segundo registro con el mismo email
    response2 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password}
    )
    assert response2.status_code == 400
    assert response2.json()["detail"] == "El correo electrónico ya está registrado."


@pytest.mark.asyncio
async def test_login_success(async_client, test_user):
    """
    c. test_login_success: POST /api/v1/auth/login con credenciales correctas
    -> HTTP 200, body contiene access_token y token_type='bearer'.
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Verificar que el access_token se puede decodificar con PyJWT usando settings
    token = data["access_token"]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload.get("sub") == str(test_user["user_object"].id)


@pytest.mark.asyncio
async def test_login_wrong_password(async_client, test_user):
    """
    d. test_login_wrong_password: POST /api/v1/auth/login con contraseña incorrecta
    -> HTTP 401.
    """
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["email"],
            "password": "wrongpassword123"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Correo o contraseña incorrectos"


@pytest.mark.asyncio
async def test_me_with_valid_token(async_client, test_user):
    """
    e. test_me_with_valid_token: GET /api/v1/users/me con Bearer token válido
    -> HTTP 200, body contiene email del usuario.
    """
    # Primero hacemos login para obtener el token
    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Luego consumimos la ruta protegida /users/me
    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]


@pytest.mark.asyncio
async def test_me_without_token(async_client):
    """
    f. test_me_without_token: GET /api/v1/users/me sin Authorization header
    -> HTTP 401.
    """
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(async_client):
    """
    g. test_me_with_invalid_token: GET /api/v1/users/me con token='invalid.jwt.token'
    -> HTTP 401.
    """
    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid.jwt.token"}
    )
    assert response.status_code == 401
