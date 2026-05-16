import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi import HTTPException

from app.services.pedido_service import PedidoService
from app.schemas.pedido import PedidoCreate, LineaPedidoCreate, PedidoUpdate
from app.models.pedido import Pedido
from app.utils.whatsapp import build_whatsapp_url


# Fixture de Base de Datos simulada
@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Explicitly set add as a MagicMock since SQLAlchemy's add is synchronous
    # and AsyncMock would make it awaitable by default.
    db.add = MagicMock()
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

    # Simulamos el comportamiento del refresh y del execute
    async def mock_refresh(instance):
        instance.id = uuid4()
        instance.cliente_whatsapp = "5512345678"

    mock_db.refresh.side_effect = mock_refresh
    
    # Mock para el select(Pedido) final
    mock_pedido = MagicMock(spec=Pedido)
    mock_pedido.id = uuid4()
    mock_pedido.estado = "pendiente"
    mock_pedido.cliente_nombre = "Rocio Ponce"
    mock_pedido.cliente_whatsapp = "5512345678"
    mock_pedido.lineas = []

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = mock_pedido
    mock_db.execute.return_value = mock_result

    pedido = await PedidoService.create_pedido(mock_db, data, usuario_id)

    assert pedido.estado == "pendiente"
    assert pedido.cliente_nombre == "Rocio Ponce"
    assert pedido.whatsapp_url == "https://wa.me/525512345678"
    assert mock_db.add.call_count == 3  # 1 del pedido + 1 de la línea + 1 notificacion
    mock_db.commit.assert_awaited()


# ==========================================
# TESTS MÁQUINA DE ESTADOS
# ==========================================

@pytest.mark.asyncio
async def test_transicion_valida_pendiente_a_en_preparacion(mock_db):
    """C. Verifica una transición de estado legal."""
    usuario_id = uuid4()
    pedido_id = uuid4()

    # Simulamos un pedido en la base de datos
    mock_pedido = Pedido(id=pedido_id, usuario_id=usuario_id, estado="pendiente", cliente_whatsapp="5511223344")
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_result.scalar_one.return_value = mock_pedido
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
    mock_pedido = Pedido(id=pedido_id, usuario_id=usuario_id, estado="pendiente", cliente_whatsapp="5511223344")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_result.scalar_one.return_value = mock_pedido
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

    mock_pedido = Pedido(id=uuid4(), usuario_id=usuario_id, estado="en_preparacion", cliente_whatsapp="5511223344")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_result.scalar_one.return_value = mock_pedido
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
# TESTS NOTIFICACIONES PROGRAMADAS (E9-02)
# ==========================================

@pytest.mark.asyncio
async def test_notificacion_programada_creada_al_crear_pedido(mock_db):
    """J. Verifica que al crear un pedido se intente programar la notificación."""
    usuario_id = uuid4()
    
    linea = LineaPedidoCreate(
        nombre_producto="Test",
        cantidad_porciones=1,
        precio_acordado_mxn=Decimal("10.00")
    )
    
    # Entrega en 10 horas para asegurar que entre en el umbral de notificación
    data = PedidoCreate(
        cliente_nombre="Test Notif",
        cliente_whatsapp="5511223344",
        fecha_entrega=datetime.now(timezone.utc) + timedelta(hours=10),
        lineas=[linea]
    )

    async def mock_refresh(instance):
        instance.id = uuid4()
        instance.cliente_whatsapp = "5511223344"

    mock_db.refresh.side_effect = mock_refresh

    # Mock para el select(Pedido) final
    mock_pedido = MagicMock(spec=Pedido)
    mock_pedido.id = uuid4()
    mock_pedido.cliente_whatsapp = "5511223344"
    mock_pedido.lineas = []

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = mock_pedido
    mock_db.execute.return_value = mock_result

    await PedidoService.create_pedido(mock_db, data, usuario_id)

    # Verificamos que se llamó a db.add varias veces:
    # 1. Pedido
    # 2. Línea de pedido
    # 3. NotificacionProgramada (Vía NotificacionService)
    assert mock_db.add.call_count == 3
    mock_db.commit.assert_awaited()

@pytest.mark.asyncio
async def test_reprogramar_notificacion_al_cambiar_fecha(mock_db):
    """K. Verifica que al actualizar la fecha se llame a cancelar y programar."""
    usuario_id = uuid4()
    pedido_id = uuid4()
    
    # Mock de pedido existente
    mock_pedido = Pedido(
        id=pedido_id, 
        usuario_id=usuario_id, 
        estado="pendiente", 
        fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
        cliente_whatsapp="5511223344",
        lineas=[]
    )
    
    # Mock del resultado de la query de búsqueda
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_pedido
    mock_result.scalar_one.return_value = mock_pedido
    mock_db.execute.return_value = mock_result
    
    # Nueva fecha
    nueva_fecha = datetime.now(timezone.utc) + timedelta(days=2)
    update_data = PedidoUpdate(fecha_entrega=nueva_fecha)
    
    await PedidoService.update_pedido(mock_db, pedido_id, update_data, usuario_id)
    
    # Verificamos el commit de la actualización
    assert mock_db.commit.call_count >= 1
    # La lógica de NotificacionService.cancelar_recordatorio usa db.execute(update(...))
    # La lógica de NotificacionService.programar_recordatorio usa db.add(...)
    assert mock_db.execute.call_count >= 1
    assert mock_db.add.call_count >= 1