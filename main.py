from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter

from app.routers import auth, users, insumos, recetas, pedidos, temporizadores, notificaciones, punto_entrega_router, pages
from app.jobs.notificacion_job import procesar_notificaciones_loop
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Iniciamos el Job de background para notificaciones (E9-03)
    notif_task = asyncio.create_task(procesar_notificaciones_loop())
    yield
    # Limpieza: Cancelamos el job al cerrar la app
    notif_task.cancel()
    try:
        await notif_task
    except asyncio.CancelledError:
        pass

tags_metadata = [
    {
        "name": "Autenticación",
        "description": "Operaciones de inicio de sesión y registro. La lógica de JWT se maneja aquí.",
    },
    {
        "name": "Usuarios",
        "description": "Operaciones para leer y gestionar la información del usuario logueado.",
    },
]

# Inicializamos la aplicación FastAPI con metadatos
app = FastAPI(
    title="Kitchy API",
    description="""
    Bienvenido a la API oficial de Kitchy. 

    Esta API alimenta la plataforma para microemprendedores gastronómicos, 
    permitiendo control de autenticación, multi-tenancy y futuros módulos de inventario.
    """,
    version="1.0.0",
    contact={
        "name": "Equipo de Desarrollo Kitchy (Los Resolvedores)",
        "email": "soporte@kitchy.com",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan
)

# Configuración del limitador de peticiones (Rate Limiting)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CONECTAMOS NUESTRO ROUTER AQUÍ
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuarios"])
app.include_router(insumos.router, prefix="/api/v1/insumos", tags=["Insumos"])
app.include_router(recetas.router, prefix="/api/v1/recetas", tags=["Recetas"])
app.include_router(pedidos.router, prefix="/api/v1/pedidos", tags=["Pedidos"])
app.include_router(temporizadores.router, prefix="/api/v1/temporizadores", tags=["Temporizadores"])
app.include_router(notificaciones.router, prefix="/api/v1/notificaciones", tags=["Notificaciones"])
app.include_router(punto_entrega_router.router, prefix="/api/v1/puntos-entrega", tags=["Puntos de Entrega"])

# Páginas servidas a nivel raíz (ej. el formulario de reset que abre el link del mail)
app.include_router(pages.router, tags=["Pages"])

@app.get("/", tags=["Health Check"])
def health_check():
    return {
        "estado": "OK",
        "mensaje": "¡El motor de Kitchy está funcionando correctamente!"
    }