import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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
    """💥 LA BOMBA ATÓMICA: Borra todas las tablas y las vuelve a crear vacías."""
    print("☢️  ATENCIÓN: Destruyendo base de datos actual...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("✅ Tablas eliminadas.")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tablas recreadas en blanco.")


async def seed_database():
    await reset_database()
    print("\n🌱 Iniciando el sembrado Realista de Kitchy...")

    async with AsyncSessionLocal() as db:
        # ---------------------------------------------------------
        # 1. CREAR EL USUARIO CHEF
        # ---------------------------------------------------------
        usuario = User(
            email="chef@kitchy.com",
            hashed_password=get_password_hash("Flutter2026!"),
            is_active=True
        )
        db.add(usuario)
        await db.commit()
        await db.refresh(usuario)
        print(f"\n👤 Perfil de Chef Emprendedor creado: {usuario.email}")

        # ---------------------------------------------------------
        # 2. LLENAR LA ALACENA (Compras de Mercado Mexicano)
        # ---------------------------------------------------------
        print("🛒 Ingresando facturas de compra del Mercado...")

        insumo_masa = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Masa de Maíz Nixtamalizado", unidad="kg", precio_compra=Decimal('22.00'), cantidad_comprada=Decimal('50.0'), alerta_minimo=Decimal('5.0')), usuario.id)

        insumo_tortilla = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Tortilla de Maíz Taquera", unidad="kg", precio_compra=Decimal('20.00'), cantidad_comprada=Decimal('10.0'), alerta_minimo=Decimal('2.0')), usuario.id)

        insumo_cerdo = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Carne de Cerdo (Cabeza de Lomo)", unidad="kg", precio_compra=Decimal('145.00'), cantidad_comprada=Decimal('15.0'), alerta_minimo=Decimal('2.0')), usuario.id)

        insumo_pollo = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Pechuga de Pollo Deshebrada", unidad="kg", precio_compra=Decimal('160.00'), cantidad_comprada=Decimal('5.0'), alerta_minimo=Decimal('1.0')), usuario.id)

        insumo_jitomate = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Jitomate Saladet", unidad="kg", precio_compra=Decimal('35.00'), cantidad_comprada=Decimal('10.0'), alerta_minimo=Decimal('1.0')), usuario.id)

        insumo_tomatillo = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Tomate Verde (Tomatillo)", unidad="kg", precio_compra=Decimal('28.00'), cantidad_comprada=Decimal('10.0'), alerta_minimo=Decimal('1.0')), usuario.id)

        insumo_chile_serrano = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Chile Serrano Fresco", unidad="kg", precio_compra=Decimal('45.00'), cantidad_comprada=Decimal('2.0'), alerta_minimo=Decimal('0.2')), usuario.id)

        insumo_chile_guajillo = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Chile Guajillo Seco", unidad="kg", precio_compra=Decimal('180.00'), cantidad_comprada=Decimal('1.0'), alerta_minimo=Decimal('0.1')), usuario.id)

        insumo_aguacate = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Aguacate Hass Extra", unidad="kg", precio_compra=Decimal('85.00'), cantidad_comprada=Decimal('5.0'), alerta_minimo=Decimal('0.5')), usuario.id)

        insumo_crema = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Crema Ácida de Rancho", unidad="l", precio_compra=Decimal('65.00'), cantidad_comprada=Decimal('4.0'), alerta_minimo=Decimal('0.5')), usuario.id)

        insumo_queso = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Queso Fresco Desmoronado", unidad="kg", precio_compra=Decimal('120.00'), cantidad_comprada=Decimal('3.0'), alerta_minimo=Decimal('0.3')), usuario.id)

        insumo_aceite = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Aceite Vegetal", unidad="l", precio_compra=Decimal('38.00'), cantidad_comprada=Decimal('20.0'), alerta_minimo=Decimal('2.0')), usuario.id)

        insumo_cebolla = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Cebolla Blanca", unidad="kg", precio_compra=Decimal('25.00'), cantidad_comprada=Decimal('10.0'), alerta_minimo=Decimal('1.0')), usuario.id)

        insumo_maiz_pozole = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Maíz Cacahuazintle Precocido", unidad="kg", precio_compra=Decimal('45.00'), cantidad_comprada=Decimal('10.0'), alerta_minimo=Decimal('1.0')), usuario.id)

        # ---------------------------------------------------------
        # 3. CREAR EL MENÚ (Recetas Tradicionales Mexicanas)
        # ---------------------------------------------------------
        print("\n📋 Redactando Fichas Técnicas de Recetas Mexicanas...")

        # --- CASO 1: TACOS AL PASTOR ---
        receta_pastor = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Orden de Tacos al Pastor (5 pz)", porciones=1, margen_pct=Decimal('200.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_tortilla.id, cantidad_usada=Decimal('0.150'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_cerdo.id, cantidad_usada=Decimal('0.200'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_cebolla.id, cantidad_usada=Decimal('0.030'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_aceite.id, cantidad_usada=Decimal('0.020'), unidad="l")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Marinar la carne con el adobo de achiote", duracion_segundos=1800),
                PasoCreate(orden=2, descripcion="Montar el trompo o picar para plancha", duracion_segundos=600),
                PasoCreate(orden=3, descripcion="Cocer la carne a fuego alto hasta dorar", duracion_segundos=900, es_critico=True),
                PasoCreate(orden=4, descripcion="Calentar tortillas y montar con cebolla y piña", duracion_segundos=120)
            ]
        ), usuario.id)

        # --- CASO 2: CHILAQUILES VERDES ---
        receta_chilaquiles = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Chilaquiles Verdes con Pollo", porciones=1, margen_pct=Decimal('150.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_tortilla.id, cantidad_usada=Decimal('0.200'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_tomatillo.id, cantidad_usada=Decimal('0.250'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_pollo.id, cantidad_usada=Decimal('0.100'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_crema.id, cantidad_usada=Decimal('0.050'), unidad="l"),
                IngredienteCreate(insumo_id=insumo_queso.id, cantidad_usada=Decimal('0.030'), unidad="kg")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Freír los totopos de tortilla hasta que estén crujientes", duracion_segundos=600),
                PasoCreate(orden=2, descripcion="Cocer tomatillos y chiles para la salsa", duracion_segundos=900),
                PasoCreate(orden=3, descripcion="Licuar salsa y sazonar en olla", duracion_segundos=600, es_critico=True),
                PasoCreate(orden=4, descripcion="Bañar totopos, agregar pollo, crema y queso", duracion_segundos=180)
            ]
        ), usuario.id)
        await HiddenCostService.toggle_gasto(db, receta_chilaquiles.id, tipo='gas_luz', activo=True, usuario_id=usuario.id, valor=Decimal('5.00'), es_porcentaje=False)

        # --- CASO 3: POZOLE ROJO ---
        receta_pozole = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Pozole Rojo de Cerdo (Gran Plato)", porciones=1, margen_pct=Decimal('180.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_maiz_pozole.id, cantidad_usada=Decimal('0.250'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_cerdo.id, cantidad_usada=Decimal('0.150'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_chile_guajillo.id, cantidad_usada=Decimal('0.020'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_jitomate.id, cantidad_usada=Decimal('0.050'), unidad="kg")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Cocer el maíz hasta que 'floree'", duracion_segundos=7200, es_critico=True),
                PasoCreate(orden=2, descripcion="Agregar la carne de cerdo troceada", duracion_segundos=3600),
                PasoCreate(orden=3, descripcion="Preparar el adobo de chiles secos e integrar", duracion_segundos=1200),
                PasoCreate(orden=4, descripcion="Hervir todo junto para integrar sabores", duracion_segundos=1800)
            ]
        ), usuario.id)

        # --- CASO 4: GUACAMOLE ESPECIAL ---
        receta_guacamole = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Guacamole Artesanal con Totopos", porciones=2, margen_pct=Decimal('250.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_aguacate.id, cantidad_usada=Decimal('0.400'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_jitomate.id, cantidad_usada=Decimal('0.080'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_cebolla.id, cantidad_usada=Decimal('0.040'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_chile_serrano.id, cantidad_usada=Decimal('0.010'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_tortilla.id, cantidad_usada=Decimal('0.100'), unidad="kg")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Picar finamente jitomate, cebolla y chile", duracion_segundos=300),
                PasoCreate(orden=2, descripcion="Machacar el aguacate en molcajete", duracion_segundos=180),
                PasoCreate(orden=3, descripcion="Mezclar ingredientes y ajustar sal", duracion_segundos=60, es_critico=True)
            ]
        ), usuario.id)

        # ---------------------------------------------------------
        # 4. AGENDA DE PEDIDOS (Operatividad Real)
        # ---------------------------------------------------------
        print("\n📅 Agendando Pedidos de Antojitos Mexicanos...")
        ahora = datetime.now(timezone.utc)

        # CASO A: Pedido Pendiente (Taquiza para mañana)
        pedido_mañana = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Juan Pérez",
            cliente_whatsapp="5512345678",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
            punto_entrega="Domicilio Particular",
            notas="Sin picante en los chilaquiles por favor.",
            lineas=[
                LineaPedidoCreate(nombre_producto="Orden de Tacos al Pastor", cantidad_porciones=10,
                                  precio_acordado_mxn=Decimal('950.00'), receta_id=receta_pastor.id),
                LineaPedidoCreate(nombre_producto="Guacamole Grande", cantidad_porciones=2,
                                  precio_acordado_mxn=Decimal('280.00'), receta_id=receta_guacamole.id)
            ]
        ), usuario.id)
        print(f"✅ Pedido PENDIENTE creado para mañana (Cliente: {pedido_mañana.cliente_nombre})")

        # CASO B: Pedido En Preparación (Desayuno de oficina)
        pedido_hoy = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Oficina Tech Solutions",
            cliente_whatsapp="5587654321",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
            punto_entrega="Recepción Corporativo",
            lineas=[
                LineaPedidoCreate(nombre_producto="Chilaquiles Verdes con Pollo", cantidad_porciones=15,
                                  precio_acordado_mxn=Decimal('2250.00'), receta_id=receta_chilaquiles.id)
            ]
        ), usuario.id)
        await PedidoService.cambiar_estado(db, pedido_hoy.id, "en_preparacion", usuario.id)
        print(f"✅ Pedido EN PREPARACIÓN creado para hoy (Cliente: {pedido_hoy.cliente_nombre})")

        # CASO C: Pedido Entregado (Noche Mexicana)
        pedido_cerrado = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Maria Garcia",
            cliente_whatsapp="5599887766",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
            lineas=[
                LineaPedidoCreate(nombre_producto="Pozole Rojo de Cerdo", cantidad_porciones=5,
                                  precio_acordado_mxn=Decimal('750.00'), receta_id=receta_pozole.id)
            ]
        ), usuario.id)
        await PedidoService.cambiar_estado(db, pedido_cerrado.id, "en_preparacion", usuario.id)
        await PedidoService.cambiar_estado(db, pedido_cerrado.id, "listo", usuario.id)
        await PedidoService.cambiar_estado(db, pedido_cerrado.id, "entregado", usuario.id)
        print(f"✅ Pedido ENTREGADO creado (Noche Mexicana)")

        print("\n🚀 ¡Viva México! Base de Datos de Kitchy lista para pruebas.")

if __name__ == "__main__":
    asyncio.run(seed_database())