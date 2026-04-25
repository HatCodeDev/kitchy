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
        # 2. LLENAR LA ALACENA (Compras Mayoristas Reales)
        # ---------------------------------------------------------
        print("🛒 Ingresando facturas de compra a la Alacena...")

        insumo_harina = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Harina de Fuerza (Bulto 44kg)", unidad="kg", precio_compra=Decimal('450.00'), cantidad_comprada=Decimal('44.0'), alerta_minimo=Decimal('5.0')), usuario.id)

        insumo_huevo = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Huevo San Juan (Caja 360pz)", unidad="pz", precio_compra=Decimal('1100.00'), cantidad_comprada=Decimal('360.0'), alerta_minimo=Decimal('30.0')), usuario.id)

        insumo_azafran = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Azafrán Español Extra (Estuche 50g)", unidad="kg", precio_compra=Decimal('3500.00'), cantidad_comprada=Decimal('0.0500'), alerta_minimo=Decimal('0.0050')), usuario.id)

        insumo_arroz = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Arroz Bomba D.O.", unidad="kg", precio_compra=Decimal('120.00'), cantidad_comprada=Decimal('1.0'), alerta_minimo=Decimal('0.5')), usuario.id)

        insumo_almendra = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Polvo de Almendra Fina", unidad="kg", precio_compra=Decimal('380.00'), cantidad_comprada=Decimal('1.0'), alerta_minimo=Decimal('0.2')), usuario.id)

        insumo_azucar_glass = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Azúcar Glass", unidad="kg", precio_compra=Decimal('60.00'), cantidad_comprada=Decimal('1.0'), alerta_minimo=Decimal('0.2')), usuario.id)

        # CORRECCIÓN: "L" mayúscula cambiada a "l" minúscula
        insumo_aceite = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Aceite Vegetal (Bidón 20l)", unidad="l", precio_compra=Decimal('800.00'), cantidad_comprada=Decimal('20.0'), alerta_minimo=Decimal('2.0')), usuario.id)

        insumo_chile = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Chile de Árbol Seco", unidad="kg", precio_compra=Decimal('180.00'), cantidad_comprada=Decimal('1.0'), alerta_minimo=Decimal('0.2')), usuario.id)

        insumo_cafe = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Café Grano Especialidad Veracruz", unidad="kg", precio_compra=Decimal('420.00'), cantidad_comprada=Decimal('1.0'), alerta_minimo=Decimal('0.2')), usuario.id)

        # CORRECCIÓN: "L" mayúscula cambiada a "l" minúscula
        insumo_agua = await InsumoService.create_insumo(db, InsumoCreate(
            nombre="Agua Purificada (Garrafón)", unidad="l", precio_compra=Decimal('45.00'), cantidad_comprada=Decimal('20.0'), alerta_minimo=Decimal('2.0')), usuario.id)

        # ---------------------------------------------------------
        # 3. CREAR EL MENÚ (Fichas Técnicas Profesionales)
        # ---------------------------------------------------------
        print("\n📋 Redactando Fichas Técnicas de Recetas...")

        # --- CASO 1: PAELLA PREMIUM ---
        receta_paella = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Paella Valenciana Premium", porciones=4, margen_pct=Decimal('60.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_arroz.id, cantidad_usada=Decimal('0.4'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_agua.id, cantidad_usada=Decimal('1.2'), unidad="l"), # CORRECCIÓN
                IngredienteCreate(insumo_id=insumo_azafran.id, cantidad_usada=Decimal('0.001'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_aceite.id, cantidad_usada=Decimal('0.05'), unidad="l") # CORRECCIÓN
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Sofreír base en aceite", duracion_segundos=600, es_critico=False),
                PasoCreate(orden=2, descripcion="Añadir arroz, agua e infusión de azafrán", duracion_segundos=300, es_critico=False),
                PasoCreate(orden=3, descripcion="Cocción a fuego medio sin mover", duracion_segundos=1200, es_critico=True),
                PasoCreate(orden=4, descripcion="Reposo (Socarrat)", duracion_segundos=300, es_critico=False)
            ]
        ), usuario.id)

        # --- CASO 2: PAN DE MASA MADRE ---
        receta_pan = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Hogaza de Masa Madre (Sourdough)", porciones=1, margen_pct=Decimal('45.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_harina.id, cantidad_usada=Decimal('0.8'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_agua.id, cantidad_usada=Decimal('0.6'), unidad="l") # CORRECCIÓN
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Autólisis (Mezcla inicial)", duracion_segundos=3600),
                PasoCreate(orden=2, descripcion="Amasado francés (Slap & Fold)", duracion_segundos=900),
                PasoCreate(orden=3, descripcion="Fermentación en bloque con pliegues", duracion_segundos=14400),
                PasoCreate(orden=4, descripcion="Horneado en olla de hierro a 250°C", duracion_segundos=2700, es_critico=True)
            ]
        ), usuario.id)
        await HiddenCostService.toggle_gasto(db, receta_pan.id, tipo='gas_luz', activo=True, usuario_id=usuario.id, valor=Decimal('12.00'), es_porcentaje=True)

        # --- CASO 3: MACARONS FRANCESES ---
        receta_macarons = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Caja de 6 Macarons (Regalo)", porciones=1, margen_pct=Decimal('70.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_almendra.id, cantidad_usada=Decimal('0.15'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_azucar_glass.id, cantidad_usada=Decimal('0.15'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_huevo.id, cantidad_usada=Decimal('3.0'), unidad="pz")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Tamizar secos (Tant pour tant)", duracion_segundos=600),
                PasoCreate(orden=2, descripcion="Montar merengue francés", duracion_segundos=480),
                PasoCreate(orden=3, descripcion="Macaronage", duracion_segundos=600, es_critico=True),
                PasoCreate(orden=4, descripcion="Secado a temperatura ambiente", duracion_segundos=2400),
                PasoCreate(orden=5, descripcion="Horneado a 140°C", duracion_segundos=840, es_critico=True)
            ]
        ), usuario.id)
        await HiddenCostService.toggle_gasto(db, receta_macarons.id, tipo='empaque', activo=True, usuario_id=usuario.id, valor=Decimal('35.00'), es_porcentaje=False)

        # --- CASO 4: CAFÉ AMERICANO ---
        receta_cafe = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Café Americano (Dine-in)", porciones=1, margen_pct=Decimal('80.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_cafe.id, cantidad_usada=Decimal('0.018'), unidad="kg"),
                IngredienteCreate(insumo_id=insumo_agua.id, cantidad_usada=Decimal('0.250'), unidad="l") # CORRECCIÓN
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Moler granos finos", duracion_segundos=15),
                PasoCreate(orden=2, descripcion="Extracción de espresso", duracion_segundos=30, es_critico=True),
                PasoCreate(orden=3, descripcion="Diluir con agua caliente", duracion_segundos=15)
            ]
        ), usuario.id)

        # --- CASO 5: SALSA MACHA ---
        receta_salsa = await RecetaService.create_receta(db, RecetaCreate(
            nombre="Lote Producción: Salsa Macha Artesanal", porciones=50, margen_pct=Decimal('150.0'),
            ingredientes=[
                IngredienteCreate(insumo_id=insumo_aceite.id, cantidad_usada=Decimal('5.0'), unidad="l"), # CORRECCIÓN
                IngredienteCreate(insumo_id=insumo_chile.id, cantidad_usada=Decimal('0.8'), unidad="kg")
            ],
            pasos=[
                PasoCreate(orden=1, descripcion="Desvenar chiles", duracion_segundos=1800),
                PasoCreate(orden=2, descripcion="Freír chiles sin quemar", duracion_segundos=300, es_critico=True),
                PasoCreate(orden=3, descripcion="Licuar con aceite temperado", duracion_segundos=600),
                PasoCreate(orden=4, descripcion="Envasado al vacío", duracion_segundos=3600)
            ]
        ), usuario.id)

        # ---------------------------------------------------------
        # 4. AGENDA DE PEDIDOS (Operatividad Real) 🟢 NUEVO
        # ---------------------------------------------------------
        print("\n📅 Agendando Pedidos para la semana...")
        ahora = datetime.now(timezone.utc)

        # CASO A: Pedido Pendiente (Urgente para mañana)
        pedido_mañana = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Ethan",
            cliente_whatsapp="2215805068",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
            punto_entrega="Pick-up en Cocina",
            notas="Empaque de regalo, por favor.",
            lineas=[
                LineaPedidoCreate(nombre_producto="Caja de Macarons", cantidad_porciones=2,
                                  precio_acordado_mxn=Decimal('450.00'), receta_id=receta_macarons.id),
                LineaPedidoCreate(nombre_producto="Hogaza Especial", cantidad_porciones=1,
                                  precio_acordado_mxn=Decimal('120.00'), receta_id=receta_pan.id)
            ]
        ), usuario.id)
        print(f"✅ Pedido PENDIENTE creado para mañana (Cliente: {pedido_mañana.cliente_nombre})")

        # CASO B: Pedido En Preparación (Para hoy más tarde)
        pedido_hoy = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Hotel Plaza Eventos",
            cliente_whatsapp="5587654321",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
            punto_entrega="Recepción Hotel Plaza",
            lineas=[
                LineaPedidoCreate(nombre_producto="Paella Gigante (12pax)", cantidad_porciones=3,
                                  precio_acordado_mxn=Decimal('1800.00'), receta_id=receta_paella.id)
            ]
        ), usuario.id)
        # Avanzamos el estado usando el Service
        await PedidoService.cambiar_estado(db, pedido_hoy.id, "en_preparacion", usuario.id)
        print(f"✅ Pedido EN PREPARACIÓN creado para hoy (Cliente: {pedido_hoy.cliente_nombre})")

        # CASO C: Pedido Entregado (Historial y prueba de descuento de stock)
        # Nota: Ponemos fecha futura cercana para que pase RN-01, pero lo marcamos como entregado para simular cierre
        pedido_cerrado = await PedidoService.create_pedido(db, PedidoCreate(
            cliente_nombre="Cami",
            cliente_whatsapp="2491827883",
            fecha_entrega=datetime.now(timezone.utc) + timedelta(days=1),
            lineas=[
                LineaPedidoCreate(nombre_producto="Hogaza de Masa Madre", cantidad_porciones=5,
                                  precio_acordado_mxn=Decimal('500.00'), receta_id=receta_pan.id)
            ]
        ), usuario.id)
        # Ciclo completo de la máquina de estados
        await PedidoService.cambiar_estado(db, pedido_cerrado.id, "en_preparacion", usuario.id)
        await PedidoService.cambiar_estado(db, pedido_cerrado.id, "listo", usuario.id)
        await PedidoService.cambiar_estado(db, pedido_cerrado.id, "entregado", usuario.id)
        print(f"✅ Pedido ENTREGADO creado (Simulando historial y descuento de stock)")

        print("\n🚀 ¡Base de Datos de Kitchy lista para pruebas en la App!")

if __name__ == "__main__":
    asyncio.run(seed_database())