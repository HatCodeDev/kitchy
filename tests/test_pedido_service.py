import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException

from app.services.pedido_service import PedidoService
from app.schemas.pedido import PedidoCreate, LineaPedidoCreate
from app.models.pedido import Pedido
from app.utils.whatsapp import build_whatsapp_url


# Fixture de Base de Datos simulada
@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()  # add() de SQLAlchemy es síncrono
    return db


# ==========================================
# TESTS RN-01: VALIDACIÓN DE FECHAS
# ==========================================

@pytest.mark.asyncio
async def test_crear_pedido_con_fecha_pasada_rechazada(mock_db):
    """A. Valida RN-01: El servicio rechaza fechas pasadas."""
    usuario_id = uuid4()

    # Usamos un mock para el payload para saltar la validación de Pydantic
    # y probar exclusivamente la lógica del PedidoService.
    data_mock = MagicMock(spec=PedidoCreate)
    data_mock.fecha_entrega = datetime.now(timezone.utc) - timedelta(hours=1)

    with pytest.raises(HTTPException) as exc_info:
        await PedidoService.create_pedido(mock_db, data_mock, usuario_id)

    assert exc_info.value.status_code == 400
    assert "futuro" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_crear_pedido_valido(mock_db):
    """B. Verifica creación correcta con fecha futura y estado por defecto."""
    usuario_id = uuid4()

    linea = LineaPedidoCreate(
        nombre_producto="Hogaza de Masa Madre",
        cantidad_porciones=2,
        precio_acordado_mxn=Decimal("150.00")
    )

    data = PedidoCreate(
        cliente_nombre="Rocio Ponce",
        cliente_whatsapp="5512345678",
        fecha_entrega=datetime.now(timezone.utc) + timedelta(days=2),
        lineas=[linea]
    )

    # Simulamos el comportamiento del refresh
    async def mock_refresh(instance):
        instance.id = uuid4()

    mock_db.refresh.side_effect = mock_refresh

    pedido = await PedidoService.create_pedido(mock_db, data, usuario_id)

    assert pedido.estado == "pendiente"
    assert pedido.cliente_nombre == "Rocio Ponce"
    assert pedido.whatsapp_url == "https://wa.me/525512345678"
    assert mock_db.add.call_count == 2  # 1 del pedido + 1 de la línea
    mock_db.commit.assert_awaited_once()


# ==========================================
# TESTS MÁQUINA DE ESTADOS
# ==========================================

@pytest.mark.asyncio
async def test_transicion_valida_pendiente_a_en_preparacion(mock_db):
    """C. Verifica una transición de estado legal."""
    usuario_id = uuid4()
    pedido_id = uuid4()

    # Simulamos un pedido en la base de datos
    mock_pedido = Pedido(id=pedido_id, usuario_id=usuario_id, estado="pendiente")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_db.execute.return_value = mock_result

    pedido_actualizado = await PedidoService.cambiar_estado(mock_db, pedido_id, "en_preparacion", usuario_id)

    assert pedido_actualizado.estado == "en_preparacion"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_transicion_valida_ciclo_completo(mock_db):
    """D. Simula el ciclo normal de vida de un pedido paso a paso."""
    usuario_id = uuid4()
    pedido_id = uuid4()

    # Creamos el objeto de forma mutante
    mock_pedido = Pedido(id=pedido_id, usuario_id=usuario_id, estado="pendiente")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_db.execute.return_value = mock_result

    # 1. Pendiente -> En Preparación
    await PedidoService.cambiar_estado(mock_db, pedido_id, "en_preparacion", usuario_id)
    assert mock_pedido.estado == "en_preparacion"

    # 2. En Preparación -> Listo
    await PedidoService.cambiar_estado(mock_db, pedido_id, "listo", usuario_id)
    assert mock_pedido.estado == "listo"

    # 3. Listo -> Entregado (Terminal)
    await PedidoService.cambiar_estado(mock_db, pedido_id, "entregado", usuario_id)
    assert mock_pedido.estado == "entregado"


@pytest.mark.asyncio
async def test_transicion_invalida_rechazada(mock_db):
    """E. Verifica que reboten saltos de estado ilegales."""
    usuario_id = uuid4()

    mock_pedido = Pedido(id=uuid4(), usuario_id=usuario_id, estado="pendiente")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        # Intento ilegal: de pendiente directo a entregado
        await PedidoService.cambiar_estado(mock_db, mock_pedido.id, "entregado", usuario_id)

    assert exc_info.value.status_code == 400
    assert "Transición inválida" in exc_info.value.detail


@pytest.mark.asyncio
async def test_no_cambiar_estado_desde_entregado(mock_db):
    """F. Verifica que 'entregado' es un estado bloqueado/terminal."""
    usuario_id = uuid4()

    mock_pedido = Pedido(id=uuid4(), usuario_id=usuario_id, estado="entregado")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await PedidoService.cambiar_estado(mock_db, mock_pedido.id, "cancelado", usuario_id)

    assert exc_info.value.status_code == 400
    assert "Transición inválida" in exc_info.value.detail


@pytest.mark.asyncio
async def test_cancelar_desde_cualquier_estado(mock_db):
    """G. Verifica que la cancelación funciona desde estados productivos."""
    usuario_id = uuid4()

    mock_pedido = Pedido(id=uuid4(), usuario_id=usuario_id, estado="en_preparacion")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_db.execute.return_value = mock_result

    pedido = await PedidoService.cambiar_estado(mock_db, mock_pedido.id, "cancelado", usuario_id)
    assert pedido.estado == "cancelado"


# ==========================================
# TESTS UTILITARIO WHATSAPP
# ==========================================

def test_build_whatsapp_url_con_10_digitos():
    """H. Verifica la normalización de números puros de 10 dígitos."""
    assert build_whatsapp_url("5512345678") == "https://wa.me/525512345678"


def test_build_whatsapp_url_con_codigo_pais():
    """I. Verifica que respeta el código de país si ya viene incluido."""
    assert build_whatsapp_url("+525512345678") == "https://wa.me/525512345678"


# ==========================================
# TESTS NOTIFICACIONES PROGRAMADAS
# ==========================================

@pytest.mark.skip(reason="TODO E9-02: Se implementará la creación de NotificacionProgramada")
def test_notificacion_programada_creada_al_crear_pedido():
    """J. Reservado para cuando exista el módulo de alertas de la Epica 9."""
    pass