import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal
from fastapi import HTTPException

from app.services.insumo_service import InsumoService
from app.schemas.insumo import InsumoCreate
from app.schemas.movimiento_insumo import MovimientoCreate
from app.models.insumo import Insumo


# Fixture que nos entrega una BD falsa (Mock) limpia antes de cada test
@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock() # AÑADIDO: Le decimos que "add" es síncrono, no asíncrono
    return db


@pytest.mark.asyncio
async def test_create_insumo_calcula_cantidad_actual_correctamente(mock_db):
    usuario_id = uuid4()
    data = InsumoCreate(
        nombre="Harina",
        unidad="kg",
        precio_compra=Decimal("100.00"),
        cantidad_comprada=Decimal("10.00"),
        alerta_minimo=Decimal("2.00")
    )

    insumo = await InsumoService.create_insumo(mock_db, data, usuario_id)

    # Verificamos que la cantidad actual herede de la cantidad comprada
    assert insumo.cantidad_actual == Decimal("10.00")
    assert insumo.usuario_id == usuario_id
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_insumos_retorna_lista(mock_db):
    usuario_id = uuid4()
    mock_result = MagicMock()
    # Simulamos que la BD devuelve una lista con un insumo
    mock_result.scalars().all.return_value = [Insumo(id=uuid4(), usuario_id=usuario_id)]
    mock_db.execute.return_value = mock_result

    resultados = await InsumoService.get_insumos(mock_db, usuario_id)

    assert len(resultados) == 1
    assert resultados[0].usuario_id == usuario_id


@pytest.mark.asyncio
async def test_get_by_id_lanza_403_para_otro_usuario(mock_db):
    usuario_dueno = uuid4()
    usuario_intruso = uuid4()
    insumo_id = uuid4()

    # Simulamos que la BD encuentra el insumo, pero es de otro dueño
    mock_insumo = Insumo(id=insumo_id, usuario_id=usuario_dueno)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_insumo
    mock_db.execute.return_value = mock_result

    # Verificamos que al intentar acceder, FastAPI lance el Error 403
    with pytest.raises(HTTPException) as exc_info:
        await InsumoService.get_by_id(mock_db, insumo_id, usuario_intruso)

    assert exc_info.value.status_code == 403
    assert "No tienes permiso" in exc_info.value.detail


@pytest.mark.skip(reason="TODO E6-05: Se implementará cuando exista el modelo Receta")
@pytest.mark.asyncio
async def test_soft_delete_rechaza_si_insumo_en_receta_activa(mock_db):
    # Test reservado para la Épica 6
    pass


@pytest.mark.asyncio
async def test_registrar_movimiento_entrada_incrementa_stock(mock_db):
    usuario_id = uuid4()
    insumo_id = uuid4()

    # Creamos un insumo falso con 10 unidades
    insumo_mock = Insumo(id=insumo_id, usuario_id=usuario_id, cantidad_actual=Decimal("10.00"),alerta_minimo=Decimal("0.00"))

    # Parcheamos get_by_id para que devuelva nuestro insumo falso sin consultar la BD
    # Nota: Usamos monkeypatch si fuera necesario, pero aquí simularemos la BD
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = insumo_mock
    mock_db.execute.return_value = mock_result

    data = MovimientoCreate(tipo="entrada", cantidad=Decimal("5.00"), motivo="compra")

    insumo_actualizado = await InsumoService.registrar_movimiento(mock_db, insumo_id, data, usuario_id)

    # 10 + 5 = 15
    assert insumo_actualizado.cantidad_actual == Decimal("15.00")
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_registrar_movimiento_salida_decrementa_stock(mock_db):
    usuario_id = uuid4()
    insumo_id = uuid4()

    insumo_mock = Insumo(id=insumo_id, usuario_id=usuario_id, cantidad_actual=Decimal("10.00"),alerta_minimo=Decimal("0.00"))
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = insumo_mock
    mock_db.execute.return_value = mock_result

    data = MovimientoCreate(tipo="salida", cantidad=Decimal("3.00"), motivo="uso_produccion")

    insumo_actualizado = await InsumoService.registrar_movimiento(mock_db, insumo_id, data, usuario_id)

    # 10 - 3 = 7
    assert insumo_actualizado.cantidad_actual == Decimal("7.00")


@pytest.mark.asyncio
async def test_registrar_movimiento_salida_rechaza_stock_negativo(mock_db):
    """Test Extra de Calidad: Valida la decisión arquitectónica que tomamos en E5-10"""
    usuario_id = uuid4()
    insumo_id = uuid4()

    # Insumo con solo 2 unidades
    insumo_mock = Insumo(id=insumo_id, usuario_id=usuario_id, cantidad_actual=Decimal("2.00"),alerta_minimo=Decimal("0.00"))
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = insumo_mock
    mock_db.execute.return_value = mock_result

    # Intentamos sacar 5 unidades
    data = MovimientoCreate(tipo="salida", cantidad=Decimal("5.00"), motivo="merma")

    with pytest.raises(HTTPException) as exc_info:
        await InsumoService.registrar_movimiento(mock_db, insumo_id, data, usuario_id)

    assert exc_info.value.status_code == 400
    assert "Stock insuficiente" in exc_info.value.detail


@pytest.mark.skip(reason="TODO E9-01: Se implementará cuando exista NotificacionProgramada")
@pytest.mark.asyncio
async def test_alerta_se_genera_cuando_stock_lte_alerta_minimo(mock_db):
    # Test reservado para la Épica 9
    pass