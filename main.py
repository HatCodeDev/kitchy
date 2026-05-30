"""
Punto de Entrada Principal de Kitchy API.

Este archivo inicializa la aplicación FastAPI, configura las políticas de CORS,
el control de tasa de peticiones (Rate Limiting), conecta todos los controladores (routers)
y gestiona el ciclo de vida de los servicios en segundo plano (lifespan), como el despachador de notificaciones.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter

from app.routers import auth, users, insumos, recetas, pedidos, temporizadores, notificaciones, punto_entrega_router
from app.jobs.notificacion_job import procesar_notificaciones_loop
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestor del Ciclo de Vida de la Aplicación (Lifespan).

    Inicializa servicios asíncronos en segundo plano al arrancar la aplicación
    y asegura una cancelación y liberación de recursos limpia al apagar el servidor.

    * **Background Job**: Inicia el bucle de procesamiento y despacho de notificaciones programadas (SMS/WhatsApp).
    """
    # Iniciamos el Job de background para notificaciones (E9-03)
    notif_task = asyncio.create_task(procesar_notificaciones_loop())
    yield
    # Limpieza: Cancelamos el job al cerrar la app
    notif_task.cancel()
    try:
        await notif_task
    except asyncio.CancelledError:
        pass


# Metadatos descriptivos estructurados por módulo para organizar Swagger UI
tags_metadata = [
    {
        "name": "Autenticación",
        "description": "Operaciones públicas de inicio de sesión (Login) y autoregistro. Emisión de tokens de acceso JWT (Bearer).",
    },
    {
        "name": "Usuarios",
        "description": "Operaciones para consultar y modificar el perfil del usuario autenticado y configurar los valores por defecto de costos ocultos.",
    },
    {
        "name": "Insumos",
        "description": "Gestión del catálogo de insumos de cocina (materias primas), control de stock neto e historial de transacciones de inventario.",
    },
    {
        "name": "Recetas",
        "description": "Capa financiera y operativa de preparación de alimentos. Costeo automático, sugerencias de precios de venta y control de mermas.",
    },
    {
        "name": "Pedidos",
        "description": "Registro y seguimiento de órdenes de clientes, automatización del plan de producción diaria, colisión horaria y enlaces WhatsApp pregenerados.",
    },
    {
        "name": "Temporizadores",
        "description": "Monitoreo en tiempo real de los procesos de cocción críticos asociados a las recetas y confirmación de alertas.",
    },
    {
        "name": "Notificaciones",
        "description": "Listado e historial de alertas y recordatorios programados del sistema para insumos bajos o confirmación de pedidos.",
    },
    {
        "name": "Puntos de Entrega",
        "description": "Mantenimiento de puntos físicos o virtuales formales para la entrega de pedidos terminados.",
    },
    {
        "name": "Health Check",
        "description": "Servicios de diagnóstico de salud y estado operativo del motor backend.",
    }
]

# Inicializamos la aplicación FastAPI con metadatos y especificaciones de marca
app = FastAPI(
    title="Kitchy API",
    description="""
    ## Motor de Backend Kitchy - Gestión de Producción y Costeos Gastronómicos
    
    Bienvenido a la API oficial de Kitchy, diseñada específicamente para empoderar a microemprendedores
    y creadores gastronómicos. 
    
    ### Características de la Arquitectura:
    * **Multi-Tenancy por Aislamiento Lógico**: Cada recurso se filtra y restringe estrictamente según el ID del usuario en el token JWT.
    * **Costeo en Tiempo Real**: Cálculos de margen de contribución, recargo de desgaste, costos de empaque y sugerencias financieras.
    * **Eventos Programados**: Bucle lifespan para notificaciones y alertas periódicas.
    * **Defensa en Profundidad**: Validación robusta con Pydantic y tipado estricto con PostgreSQL.
    """,
    version="1.0.0",
    contact={
        "name": "Equipo de Soporte Tecnológico Kitchy",
        "email": "soporte@kitchy.com",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan
)

# Configuración del limitador de peticiones (Rate Limiting) para evitar ataques DOS o abusos de cuota
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuración de políticas de intercambio de recursos de origen cruzado (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inyección e inclusión estructurada de rutas de negocio
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuarios"])
app.include_router(insumos.router, prefix="/api/v1/insumos", tags=["Insumos"])
app.include_router(recetas.router, prefix="/api/v1/recetas", tags=["Recetas"])
app.include_router(pedidos.router, prefix="/api/v1/pedidos", tags=["Pedidos"])
app.include_router(temporizadores.router, prefix="/api/v1/temporizadores", tags=["Temporizadores"])
app.include_router(notificaciones.router, prefix="/api/v1/notificaciones", tags=["Notificaciones"])
app.include_router(punto_entrega_router.router, prefix="/api/v1/puntos-entrega", tags=["Puntos de Entrega"])


@app.get("/", tags=["Health Check"])
def health_check():
    """
    Endpoint de Diagnóstico Simple (Health Check).

    Verifica que la instancia del servidor web esté activa y respondiendo solicitudes de red.

    ### Respuestas:
    * **200 OK**: Retorna el estado operativo exitoso de la API.
    """
    return {
        "estado": "OK",
        "mensaje": "¡El motor de Kitchy está funcionando correctamente!"
    }