import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
load_dotenv()
# Importaciones de Arquitectura Core
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash

# Importamos TODOS los modelos para que SQLAlchemy sepa qué tablas borrar y crear
from app.models.user import User
from app.models.insumo import Insumo
from app.models.receta import Receta
from app.models.ingrediente_receta import IngredienteReceta
from app.models.paso_receta import PasoReceta
from app.models.gasto_oculto import GastoOculto
from app.models.pedido import Pedido
from app.models.linea_pedido import LineaPedido

# Schemas y Servicios
from app.schemas.insumo import InsumoCreate
from app.schemas.receta import RecetaCreate, IngredienteCreate, PasoCreate
from app.schemas.pedido import PedidoCreate, LineaPedidoCreate
from app.services.insumo_service import InsumoService
from app.services.receta_service import RecetaService
from app.services.hidden_cost_service import HiddenCostService
from app.services.pedido_service import PedidoService


async def reset_database():
    """LA BOMBA ATOMICA: Borra todas las tablas y las vuelve a crear vacias."""
    print("ATENCION: Destruyendo base de datos actual...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("OK: Tablas eliminadas.")
        await conn.run_sync(Base.metadata.create_all)
        print("OK: Tablas recreadas en blanco.")


async def seed_database():
    await reset_database()
    print("\nIniciando el sembrado de Postres Reales en Kitchy...")

    async with AsyncSessionLocal() as db:
        # ---------------------------------------------------------
        # 1. CREAR EL USUARIO REPOSTERO
        # ---------------------------------------------------------
        usuario = User(
            email="chef@kitchy.com ",
            hashed_password=get_password_hash("Flutter2026!"),
            is_active=True
        )
        db.add(usuario)
        await db.commit()
        await db.refresh(usuario)
        print(f"\nPerfil de Repostero Emprendedor creado: {usuario.email}")

        # ---------------------------------------------------------
        # 2. LLENAR LA ALACENA (Insumos de Reposteria)
        # ---------------------------------------------------------
        print("Ingresando facturas de insumos de reposteria...")

        ins_harina = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Harina de Trigo Todo Uso", unidad="kg", precio_compra=Decimal('22.50'), cantidad_comprada=Decimal('20.0'), alerta_minimo=Decimal('5.0')), usuario.id)

        ins_azucar = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Azúcar Estándar", unidad="kg", precio_compra=Decimal('28.00'), cantidad_comprada=Decimal('15.0'), alerta_minimo=Decimal('3.0')), usuario.id)

        ins_huevos = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Huevo Blanco (Cono 30 pz)", unidad="pz", precio_compra=Decimal('85.00'), cantidad_comprada=Decimal('90.0'), alerta_minimo=Decimal('15.0')), usuario.id)

        ins_leche_cond = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Leche Condensada (Lata 387g)", unidad="pz", precio_compra=Decimal('27.50'), cantidad_comprada=Decimal('24.0'), alerta_minimo=Decimal('6.0')), usuario.id)

        ins_leche_evap = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Leche Evaporada (Lata 360ml)", unidad="pz", precio_compra=Decimal('21.00'), cantidad_comprada=Decimal('24.0'), alerta_minimo=Decimal('6.0')), usuario.id)

        ins_queso_crema = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Queso Crema (Barra 190g)", unidad="pz", precio_compra=Decimal('36.00'), cantidad_comprada=Decimal('20.0'), alerta_minimo=Decimal('4.0')), usuario.id)

        ins_mantequilla = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Mantequilla Sin Sal (90g)", unidad="pz", precio_compra=Decimal('24.00'), cantidad_comprada=Decimal('30.0'), alerta_minimo=Decimal('5.0')), usuario.id)

        ins_vainilla = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Esencia de Vainilla", unidad="ml", precio_compra=Decimal('45.00'), cantidad_comprada=Decimal('500.0'), alerta_minimo=Decimal('50.0')), usuario.id)

        ins_cocoa = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Cocoa en Polvo", unidad="kg", precio_compra=Decimal('180.00'), cantidad_comprada=Decimal('2.0'), alerta_minimo=Decimal('0.5')), usuario.id)

        ins_leche_entera = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Leche Entera", unidad="l", precio_compra=Decimal('26.00'), cantidad_comprada=Decimal('12.0'), alerta_minimo=Decimal('2.0')), usuario.id)

        ins_frutos_rojos = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Mezcla de Frutos Rojos (Congelados)", unidad="kg", precio_compra=Decimal('145.00'), cantidad_comprada=Decimal('5.0'), alerta_minimo=Decimal('1.0')), usuario.id)

        ins_galleta_maria = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Galletas María (Paquete 170g)", unidad="pz", precio_compra=Decimal('16.00'), cantidad_comprada=Decimal('20.0'), alerta_minimo=Decimal('4.0')), usuario.id)

        # ---------------------------------------------------------
        # 3. CREAR EL RECETARIO (Postres Reales)
        # ---------------------------------------------------------
        print("\nCreando Recetas de Postres...")

        # --- RECETA 1: FLAN NAPOLITANO ---
        receta_flan = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Flan Napolitano Tradicional", porciones=8, margen_pct=Decimal('150.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=ins_leche_cond.id, cantidad_usada=Decimal('1.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_leche_evap.id, cantidad_usada=Decimal('1.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_queso_crema.id, cantidad_usada=Decimal('1.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_huevos.id, cantidad_usada=Decimal('5.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_azucar.id, cantidad_usada=Decimal('0.150'), unidad="kg"),
                IngredienteCreate(insumo_id=ins_vainilla.id, cantidad_usada=Decimal('15.0'), unidad="ml")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Hacer el caramelo con el azúcar y verter en el molde", duracion_segundos=600),
                PasoCreate(orden=2, descripcion="Licuar la leche condensada, evaporada, queso crema, huevos y vainilla", duracion_segundos=180),
                PasoCreate(orden=3, descripcion="Verter la mezcla en el molde y tapar con aluminio", duracion_segundos=120),
                PasoCreate(orden=4, descripcion="Cocer a baño María en horno a 180°C", duracion_segundos=3600, es_critico=True),
                PasoCreate(orden=5, descripcion="Dejar enfriar y refrigerar antes de desmoldar", duracion_segundos=7200)
            ]
        ), usuario.id)
        # Activar gasto de gas/luz para el horno
        await HiddenCostService.toggle_gasto(db, receta_flan.id, tipo='gas_luz', activo=True, usuario_id=usuario.id, valor=Decimal('10.0'), es_porcentaje=True)

        # --- RECETA 2: PASTEL DE CHOCOLATE ---
        receta_pastel_choc = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Pastel de Chocolate Húmedo", porciones=12, margen_pct=Decimal('180.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=ins_harina.id, cantidad_usada=Decimal('0.350'), unidad="kg"),
                IngredienteCreate(insumo_id=ins_azucar.id, cantidad_usada=Decimal('0.400'), unidad="kg"),
                IngredienteCreate(insumo_id=ins_cocoa.id, cantidad_usada=Decimal('0.080'), unidad="kg"),
                IngredienteCreate(insumo_id=ins_huevos.id, cantidad_usada=Decimal('3.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_leche_entera.id, cantidad_usada=Decimal('0.250'), unidad="l"),
                IngredienteCreate(insumo_id=ins_mantequilla.id, cantidad_usada=Decimal('1.0'), unidad="pz") # 90g
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Mezclar ingredientes secos tamizados", duracion_segundos=300),
                PasoCreate(orden=2, descripcion="Incorporar huevos, leche y mantequilla derretida", duracion_segundos=600),
                PasoCreate(orden=3, descripcion="Hornear a 175°C hasta que el palillo salga limpio", duracion_segundos=2700, es_critico=True)
            ]
        ), usuario.id)

        # --- RECETA 3: CHEESECAKE DE FRUTOS ROJOS ---
        receta_cheesecake = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Cheesecake Frutos Rojos (Sin Horno)", porciones=10, margen_pct=Decimal('120.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=ins_galleta_maria.id, cantidad_usada=Decimal('1.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_mantequilla.id, cantidad_usada=Decimal('1.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_queso_crema.id, cantidad_usada=Decimal('3.0'), unidad="pz"),
                IngredienteCreate(insumo_id=ins_azucar.id, cantidad_usada=Decimal('0.150'), unidad="kg"),
                IngredienteCreate(insumo_id=ins_frutos_rojos.id, cantidad_usada=Decimal('0.300'), unidad="kg")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Triturar galletas y mezclar con mantequilla para la base", duracion_segundos=600),
                PasoCreate(orden=2, descripcion="Batir el queso crema con el azúcar", duracion_segundos=600),
                PasoCreate(orden=3, descripcion="Montar sobre la base y refrigerar", duracion_segundos=3600, es_critico=True),
                PasoCreate(orden=4, descripcion="Decorar con los frutos rojos antes de servir", duracion_segundos=300)
            ]
        ), usuario.id)
        # Gasto fijo de empaque (caja premium)
        await HiddenCostService.toggle_gasto(db, receta_cheesecake.id, tipo='empaque', activo=True, usuario_id=usuario.id, valor=Decimal('25.00'), es_porcentaje=False)

        # ---------------------------------------------------------
        # 4. AGENDA DE PEDIDOS (Operatividad Real)
        # ---------------------------------------------------------
        print("\nAgendando Pedidos de Reposteria...")

        # CASO A: Pedido Pendiente (Para un evento el fin de semana)
        pedido_pendiente = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Ana Martínez",
            cliente_whatsapp="5512348899",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(days=3),
            punto_entrega="Salón de Eventos 'La Fiesta'",
            notas="Entregar a las 4 PM. Etiquetar como postre sin nueces.",
            lineas=[
                LineaPedidoCreate(nombre_producto="Flan Napolitano", cantidad_porciones=16, # 2 flanes
                                  precio_acordado_mxn=Decimal('600.00'), receta_id=receta_flan.id),
                LineaPedidoCreate(nombre_producto="Cheesecake Especial", cantidad_porciones=10,
                                  precio_acordado_mxn=Decimal('550.00'), receta_id=receta_cheesecake.id)
            ]
        ), usuario.id)
        print(f"OK: Pedido PENDIENTE creado (Cliente: {pedido_pendiente.cliente_nombre})")

        # CASO B: Pedido En Preparación (Para hoy en la tarde)
        pedido_hoy = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Cafetería El Grano",
            cliente_whatsapp="5587650011",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(hours=5),
            punto_entrega="Local de la Cafetería",
            lineas=[
                LineaPedidoCreate(nombre_producto="Pastel de Chocolate Húmedo", cantidad_porciones=24, # 2 pasteles
                                  precio_acordado_mxn=Decimal('1100.00'), receta_id=receta_pastel_choc.id)
            ]
        ), usuario.id)
        await PedidoService.cambiar_estado(db, pedido_hoy.id, "en_preparacion", usuario.id)
        print(f"OK: Pedido EN PREPARACION creado (Cliente: {pedido_hoy.cliente_nombre})")

        # CASO C: Pedido Entregado (Venta de ayer)
        pedido_entregado_db = Pedido(
            usuario_id=usuario.id,
            cliente_nombre="Carlos Ruiz",
            cliente_whatsapp="5599881122",
            fecha_entrega=datetime.now(timezone.utc) - timedelta(days=1),
            estado="entregado",  # Lo forzamos directo a entregado
            punto_entrega="Recoger en Local"
        )
        db.add(pedido_entregado_db)
        await db.flush()

        linea_historica = LineaPedido(
            pedido_id=pedido_entregado_db.id,
            receta_id=receta_flan.id,
            nombre_producto="Flan Napolitano",
            cantidad_porciones=8,
            precio_acordado_mxn=Decimal('320.00')
        )
        db.add(linea_historica)
        await db.commit()

        print(f"OK: Pedido ENTREGADO creado (Historico insertado por DB directo)")

        print("\nLa reposteria esta lista! Base de datos de Kitchy sembrada con exito.")

if __name__ == "__main__":
    asyncio.run(seed_database())