from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Importamos la función para crear tablas y nuestro router
from app.core.database import create_tables
from app.routers import auth, users

# Código que se ejecuta al arrancar y apagar el servidor
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas en la BD si no existen
    await create_tables()
    yield
    # Al apagar: aquí podríamos cerrar conexiones, etc. (vacío por ahora)

# Inicializamos la aplicación FastAPI con el lifespan
app = FastAPI(
    title="Kitchy API",
    description="Backend para la App Gastronómica",
    version="1.0.0",
    lifespan=lifespan
)

# CORS (Configuración de Seguridad para Flutter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CONECTAMOS NUESTRO ROUTER AQUÍ
# Prefix añade automáticamente /api/v1/auth antes de /register o /login
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuarios"])

@app.get("/", tags=["Health Check"])
def health_check():
    return {
        "estado": "OK",
        "mensaje": "¡El motor de Kitchy está funcionando correctamente!"
    }