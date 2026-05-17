import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.core.database import Base
from app.core.config import settings

# --- MOCK FIXTURES EXISTENTES (Retrocompatibilidad) ---

@pytest.fixture
def usuario_id():
    """Proporciona un usuario_id consistente para los tests."""
    return uuid4()


@pytest.fixture
def db():
    """Proporciona una base de datos mock usando AsyncMock."""
    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.delete = AsyncMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()
    db_mock.execute = AsyncMock()
    return db_mock


# --- NUEVAS FIXTURES REALES E INTEGRACIÓN ---

# Si DATABASE_URL_TEST no está definido, construimos uno dinámico reemplazando la BD por 'kitchy_test'
DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST")
if not DATABASE_URL_TEST:
    base_url = settings.DATABASE_URL
    if "/kitchy_db" in base_url:
        DATABASE_URL_TEST = base_url.replace("/kitchy_db", "/kitchy_test")
    else:
        # Reemplazamos la última parte de la URL con 'kitchy_test'
        parts = base_url.rsplit("/", 1)
        DATABASE_URL_TEST = f"{parts[0]}/kitchy_test"

# Opciones adicionales para compatibilidad con SQLite (para CI/fallback)
engine_options = {}
if "sqlite" in DATABASE_URL_TEST:
    from sqlalchemy.pool import StaticPool
    engine_options["poolclass"] = StaticPool
    engine_options["connect_args"] = {"check_same_thread": False}

test_engine = create_async_engine(DATABASE_URL_TEST, echo=False, **engine_options)


async def create_database_if_not_exists():
    """Verifica si la base de datos de pruebas existe, y si no, la crea."""
    if "sqlite" in DATABASE_URL_TEST:
        return
        
    # Conectamos con autocommit a la base de datos de desarrollo para crear la de tests
    admin_engine = create_async_engine(settings.DATABASE_URL, isolation_level="AUTOCOMMIT")
    
    from sqlalchemy import text
    async with admin_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname='kitchy_test'"))
        exists = result.scalar()
        if not exists:
            await conn.execute(text("CREATE DATABASE kitchy_test"))
            
    await admin_engine.dispose()


async def init_db():
    """Crea todas las tablas en la base de datos de pruebas."""
    import app.models
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def bootstrap_db():
    """Asegura la existencia de la base de datos y recrea el esquema."""
    await create_database_if_not_exists()
    await init_db()
    await test_engine.dispose()


def pytest_sessionstart(session):
    """Gancho de pytest que se ejecuta una sola vez al inicio de toda la suite."""
    asyncio.run(bootstrap_db())


@pytest.fixture
async def db_test():
    """Proporciona una sesión de BD real aislada por transacción para cada test."""
    async with test_engine.connect() as connection:
        # Iniciamos la transacción de la conexión
        transaction = await connection.begin()
        
        # Creamos la sesión asíncrona asociada a esta conexión transaccional
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint"
        )
        
        # Sobreescribimos la dependencia de la app de FastAPI
        from main import app
        from app.core.database import get_db
        
        app.dependency_overrides[get_db] = lambda: session
        
        yield session
        
        # Rollback y limpieza al finalizar el test
        await session.close()
        await transaction.rollback()
        await test_engine.dispose()
        
        # Limpiamos los overrides
        app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_test):
    """Proporciona un cliente HTTP asíncrono para consumir la API de FastAPI."""
    from httpx import AsyncClient, ASGITransport
    from main import app
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_user(db_test):
    """Crea un usuario de prueba en la base de datos de test y retorna sus credenciales/objeto."""
    from app.models.user import User
    from app.core.security import get_password_hash
    
    email = "test_user_fixtures@kitchy.com"
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    user = User(
        email=email,
        hashed_password=hashed,
        plan="free"
    )
    
    db_test.add(user)
    await db_test.flush()
    
    return {
        "email": email,
        "password": password,
        "user_object": user
    }
