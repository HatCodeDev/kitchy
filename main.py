from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Inicializamos la aplicación FastAPI. 
# Esto genera automáticamente la documentación Swagger que luego usaremos para Dart.
app = FastAPI(
    title="Kitchy API",
    description="Backend",
    version="1.0.0"
)

# CORS
# Definimos quién tiene permiso de comunicarse con nuestra API.
# En desarrollo usamos ["*"] para permitir que el emulador
# de Flutter se conecte sin problemas. En producción (cuando lo subas a un servidor real)
# cambiaremos esto estrictamente por el dominio de tu app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones de cualquier origen (solo para desarrollo local)
    allow_credentials=True, # Permite el envío de cookies y credenciales de autenticación
    allow_methods=["*"],  # Permite todos los métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

# Creamos nuestro primer Endpoint (Ruta) de prueba
@app.get("/", tags=["Health Check"])
def health_check():
    """
    Ruta raíz para verificar que el servidor está levantado y funcionando.
    """
    return {
        "estado": "OK",
        "mensaje": "¡El motor de Kitchy está funcionando correctamente!"
    }