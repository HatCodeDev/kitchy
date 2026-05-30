"""
Configuración de la Base de Datos y Sesiones.

Este módulo inicializa el motor asíncrono de SQLAlchemy (utilizando el driver asyncpg),
define la fábrica de sesiones para realizar operaciones asíncronas de persistencia,
expone la clase base declarativa para los modelos ORM y proporciona generadores de
sesiones para la inyección de dependencias en FastAPI.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Creamos el Motor Asíncrono
# echo=True imprimirá las consultas SQL en la terminal (útil en desarrollo)
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Creamos la Fábrica de Sesiones
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base para nuestros Modelos (Clase padre de la que heredarán todas las tablas)
Base = declarative_base()


async def get_db():
    """
    Crea una sesión de base de datos por cada petición y la cierra al finalizar.

    Esto previene fugas de memoria, mantiene las conexiones en el pool optimizadas
    y garantiza que las transacciones se manejen de manera aislada por petición.

    Yields:
        AsyncSession: Sesión de base de datos asíncrona activa de SQLAlchemy.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    """
    Crea todas las tablas definidas en los modelos en PostgreSQL.

    Nota:
        En producción se recomienda delegar esto enteramente a Alembic,
        pero esta función es sumamente útil para inicializaciones rápidas
        en entornos de prueba o desarrollo local.
    """
    # Importamos el módulo de modelos completo aquí para evitar dependencias circulares.
    # Al hacer esto, Python lee el archivo app/models/__init__.py, cargando todos los
    # modelos (User, Insumo, etc.) en memoria para que SQLAlchemy los detecte.
    import app.models

    async with engine.begin() as conn:
        # Crea todas las tablas que hereden de 'Base'
        await conn.run_sync(Base.metadata.create_all)