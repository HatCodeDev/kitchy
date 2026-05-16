import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


@pytest.fixture
def usuario_id():
    """Proporciona un usuario_id consistente para los tests."""
    return uuid4()


@pytest.fixture
def db():
    """Proporciona una base de datos mock usando AsyncMock."""
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db
