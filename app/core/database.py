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

# 4. Dependencia de FastAPI para obtener la sesión de BD en cada petición
async def get_db():
    """
    Crea una sesión de base de datos por cada request y la cierra al terminar.
    Esto previene fugas de memoria y bloqueos en la base de datos.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    """
    Crea las tablas en PostgreSQL basándose en los modelos de SQLAlchemy.
    En producción, usaríamos Alembic para migraciones, pero para desarrollo esto es ideal.
    """
    # Importamos el módulo de modelos completo aquí para evitar dependencias circulares.
    # Al hacer esto, Python lee el archivo app/models/__init__.py, cargando todos los
    # modelos (User, Insumo, etc.) en memoria para que SQLAlchemy los detecte.
    import app.models

    async with engine.begin() as conn:
        # Crea todas las tablas que hereden de 'Base'
        await conn.run_sync(Base.metadata.create_all)