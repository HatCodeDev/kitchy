"""
Tests de integración: Pedido + PuntoEntrega.

Valida: FK validation, display resolution, soft-delete handling.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.models.pedido import Pedido
from app.models.punto_entrega import PuntoEntrega
from app.schemas.pedido import PedidoCreate, LineaPedidoCreate, PedidoUpdate
from app.schemas.punto_entrega import PuntoEntregaCreate
from app.services.pedido_service import PedidoService
from fastapi import HTTPException, status


@pytest.fixture
def usuario_id():
    return uuid4()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


# ==========================================
# TESTS: FK Validation
# ==========================================

@pytest.mark.asyncio
async def test_validate_punto_entrega_fk_accepts_valid(mock_db, usuario_id):
    """_validate_punto_entrega_fk no levanta si FK es válido."""
    punto_id = uuid4()

    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=PuntoEntrega(id=punto_id, usuario_id=usuario_id))
    mock_db.execute = AsyncMock(return_value=result)

    # No debería levantar
    await PedidoService._validate_punto_entrega_fk(mock_db, punto_id, usuario_id)


@pytest.mark.asyncio
async def test_validate_punto_entrega_fk_rejects_cross_tenant(mock_db, usuario_id):
    """_validate_punto_entrega_fk levanta 422 para FK de otro usuario."""
    punto_id = uuid4()
    other_user = uuid4()

    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)  # No encontrado
    mock_db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await PedidoService._validate_punto_entrega_fk(mock_db, punto_id, other_user)

    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validate_punto_entrega_fk_accepts_none(mock_db, usuario_id):
    """_validate_punto_entrega_fk acepta None sin validar."""
    # Simplemente retorna sin hacer nada
    await PedidoService._validate_punto_entrega_fk(mock_db, None, usuario_id)
    # No debería llamar a execute


# ==========================================
# TESTS: Display Resolution
# ==========================================

@pytest.mark.asyncio
async def test_set_display_resolution_fk_precedence(mock_db, usuario_id):
    """_set_display_resolution prioriza FK.nombre sobre texto."""
    pedido = MagicMock(spec=Pedido)
    punto_rel = MagicMock(spec=PuntoEntrega)
    punto_rel.nombre = "Punto A"

    pedido.punto_entrega_rel = punto_rel
    pedido.punto_entrega = "Texto alternativo"

    PedidoService._set_display_resolution(pedido)

    assert pedido.punto_entrega_display == "Punto A"


@pytest.mark.asyncio
async def test_set_display_resolution_fallback_to_text(mock_db, usuario_id):
    """_set_display_resolution cae al texto si no hay FK."""
    pedido = MagicMock(spec=Pedido)
    pedido.punto_entrega_rel = None
    pedido.punto_entrega = "Casa cliente"

    PedidoService._set_display_resolution(pedido)

    assert pedido.punto_entrega_display == "Casa cliente"


@pytest.mark.asyncio
async def test_set_display_resolution_null_both(mock_db, usuario_id):
    """_set_display_resolution es None si no hay FK ni texto."""
    pedido = MagicMock(spec=Pedido)
    pedido.punto_entrega_rel = None
    pedido.punto_entrega = None

    PedidoService._set_display_resolution(pedido)

    assert pedido.punto_entrega_display is None


@pytest.mark.asyncio
async def test_set_display_resolution_soft_deleted_fk(mock_db, usuario_id):
    """_set_display_resolution resuelve soft-deleted FK (activo=False)."""
    pedido = MagicMock(spec=Pedido)
    punto_rel = MagicMock(spec=PuntoEntrega)
    punto_rel.nombre = "Punto Eliminado"
    punto_rel.activo = False

    pedido.punto_entrega_rel = punto_rel
    pedido.punto_entrega = "Alternativa"

    PedidoService._set_display_resolution(pedido)

    # FK aún resuelve aunque esté soft-deleted
    assert pedido.punto_entrega_display == "Punto Eliminado"


# ==========================================
# TESTS: Create with FK Validation
# ==========================================

@pytest.mark.asyncio
async def test_create_pedido_validates_fk_if_provided(mock_db, usuario_id):
    """create_pedido valida FK antes de crear."""
    punto_id = uuid4()

    # Mock: validación falla
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=result)

    linea = LineaPedidoCreate(
        nombre_producto="Pan",
        cantidad_porciones=1,
        precio_acordado_mxn=Decimal("100.00")
    )
    data = PedidoCreate(
        cliente_nombre="Cliente",
        fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
        punto_entrega_id=punto_id,
        lineas=[linea]
    )

    with pytest.raises(HTTPException) as exc:
        await PedidoService.create_pedido(mock_db, data, usuario_id)

    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
