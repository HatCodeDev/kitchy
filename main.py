from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings

# ELIMINAMOS la importación de create_tables
from app.routers import auth, users

# Código que se ejecuta al arrancar y apagar el servidor
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ELIMINADO: await create_tables()
    # Ahora Alembic es el único responsable de crear/modificar tablas.
    yield
    # Al apagar: aquí podríamos cerrar conexiones, etc. (vacío por ahora)

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

@app.get("/", tags=["Health Check"])
def health_check():
    return {
        "estado": "OK",
        "mensaje": "¡El motor de Kitchy está funcionando correctamente!"
    }