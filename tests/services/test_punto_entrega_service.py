"""
Tests para PuntoEntregaService.

Nota: Estos son tests unitarios que validan la lógica de negocio.
Para tests de integración con BD real, usar pytest con AsyncSession fixture.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.punto_entrega import PuntoEntrega
from app.schemas.punto_entrega import (
    PuntoEntregaCreate,
    PuntoEntregaUpdate,
    PuntoEntregaPatch
)
from app.services.punto_entrega_service import PuntoEntregaService
from fastapi import HTTPException, status


@pytest.fixture
def usuario_id():
    return uuid4()


@pytest.fixture
def mock_db():
    """Mock de AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


# ==========================================
# TESTS: Create (validación de duplicados)
# ==========================================

@pytest.mark.asyncio
async def test_create_punto_entrega_raises_422_on_duplicate_nombre(mock_db, usuario_id):
    """Crear punto con nombre duplicado levanta 422."""
    # Mock: la segunda llamada a execute retorna un punto existente
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=PuntoEntrega())
    mock_db.execute = AsyncMock(return_value=result)

    data = PuntoEntregaCreate(nombre="Duplicado")

    with pytest.raises(HTTPException) as exc:
        await PuntoEntregaService.create(mock_db, usuario_id, data)

    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_punto_entrega_strips_blank_direccion(mock_db, usuario_id):
    """Direccion blank se convierte a None por el validator."""
    # Mock: primera query (duplicados) retorna None, segunda para refresh retorna el punto
    result1 = MagicMock()
    result1.scalar_one_or_none = MagicMock(return_value=None)

    result2 = MagicMock()
    punto_mock = MagicMock(spec=PuntoEntrega)
    punto_mock.nombre = "Test"
    punto_mock.direccion = None
    result2.scalar_one_or_none = MagicMock(return_value=punto_mock)

    mock_db.execute = AsyncMock(side_effect=[result1, result2])

    # El validator de Pydantic convierte "   " a None
    data = PuntoEntregaCreate(nombre="Test", direccion="   ")

    await PuntoEntregaService.create(mock_db, usuario_id, data)

    assert data.direccion is None


# ==========================================
# TESTS: Get or 404
# ==========================================

@pytest.mark.asyncio
async def test_get_or_404_returns_404_for_missing(mock_db, usuario_id):
    """get_or_404 levanta 404 para punto inexistente."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await PuntoEntregaService.get_or_404(mock_db, uuid4(), usuario_id)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_or_404_returns_404_for_cross_tenant(mock_db, usuario_id):
    """get_or_404 levanta 404 para punto de otro usuario."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=result)

    other_user = uuid4()

    with pytest.raises(HTTPException) as exc:
        await PuntoEntregaService.get_or_404(mock_db, uuid4(), other_user)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_or_404_returns_404_for_inactive(mock_db, usuario_id):
    """get_or_404 levanta 404 para punto soft-deleted (activo=False)."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)  # No encontrado porque activo=False
    mock_db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await PuntoEntregaService.get_or_404(mock_db, uuid4(), usuario_id)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ==========================================
# TESTS: Soft Delete
# ==========================================

@pytest.mark.asyncio
async def test_soft_delete_calls_get_or_404(mock_db, usuario_id):
    """soft_delete valida que el punto existe y es del usuario."""
    punto_id = uuid4()

    # Mock: get_or_404 primero, luego refresh
    punto = MagicMock(spec=PuntoEntrega)
    punto.id = punto_id
    punto.activo = True

    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=punto)
    mock_db.execute = AsyncMock(return_value=result)

    await PuntoEntregaService.soft_delete(mock_db, punto_id, usuario_id)

    # Verificar que commit fue llamado
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_soft_delete_404_for_nonexistent(mock_db, usuario_id):
    """soft_delete levanta 404 para punto inexistente."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await PuntoEntregaService.soft_delete(mock_db, uuid4(), usuario_id)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ==========================================
# TESTS: Update / Patch
# ==========================================

@pytest.mark.asyncio
async def test_update_duplicate_nombre_422(mock_db, usuario_id):
    """update levanta 422 si nuevo nombre ya existe."""
    punto_id = uuid4()

    # Mock: get_or_404 retorna el punto, luego execute (for duplicate check) retorna otro
    punto = MagicMock(spec=PuntoEntrega)
    punto.id = punto_id
    punto.nombre = "Original"
    punto.activo = True

    result_get = MagicMock()
    result_get.scalar_one_or_none = MagicMock(return_value=punto)

    result_dup = MagicMock()
    result_dup.scalar_one_or_none = MagicMock(return_value=PuntoEntrega())  # Duplicado!

    mock_db.execute = AsyncMock(side_effect=[result_get, result_dup])

    data = PuntoEntregaUpdate(nombre="Diferente")

    with pytest.raises(HTTPException) as exc:
        await PuntoEntregaService.update(mock_db, punto_id, usuario_id, data)

    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_patch_partial_update(mock_db, usuario_id):
    """patch actualiza solo los campos enviados."""
    punto_id = uuid4()

    punto = MagicMock(spec=PuntoEntrega)
    punto.id = punto_id
    punto.nombre = "Original"
    punto.descripcion = "Desc original"

    result_get = MagicMock()
    result_get.scalar_one_or_none = MagicMock(return_value=punto)
    mock_db.execute = AsyncMock(return_value=result_get)

    data = PuntoEntregaPatch(descripcion="Nueva desc")

    await PuntoEntregaService.patch(mock_db, punto_id, usuario_id, data)

    # El punto debería haber sido modificado
    assert punto.descripcion == "Nueva desc"
    mock_db.commit.assert_called()
