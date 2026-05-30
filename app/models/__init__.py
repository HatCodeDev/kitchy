"""
Punto de exportación centralizado de todos los modelos de datos de la aplicación.

Importa cada modelo ORM de SQLAlchemy para garantizar que la metadata los detecte
y registre de forma automática al generar migraciones con Alembic o crear las tablas.
"""
from app.core.database import Base
from app.models.user import User
from app.models.insumo import Insumo
from app.models.movimiento_insumo import MovimientoInsumo
from app.models.receta import Receta
from app.models.ingrediente_receta import IngredienteReceta
from app.models.gasto_oculto import GastoOculto
from app.models.paso_receta import PasoReceta
from app.models.pedido import Pedido
from app.models.linea_pedido import LineaPedido
from app.models.temporizador import Temporizador
from app.models.notificacion_programada import NotificacionProgramada
from app.models.punto_entrega import PuntoEntrega