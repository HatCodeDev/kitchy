"""
Configuración centralizada de la aplicación.

Este módulo define la clase Settings que hereda de BaseSettings de Pydantic,
cargando y validando las variables de entorno definidas en el archivo `.env`.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración global y validación de variables de entorno para Kitchy API.

    Atributos:
        POSTGRES_USER (str): Nombre de usuario para la base de datos PostgreSQL.
        POSTGRES_PASSWORD (str): Contraseña para la base de datos PostgreSQL.
        POSTGRES_DB (str): Nombre de la base de datos a conectar.
        POSTGRES_HOST (str): Host del servidor PostgreSQL. Por defecto 'localhost'.
        SECRET_KEY (str): Llave secreta utilizada para firmar y verificar los tokens JWT.
        ALGORITHM (str): Algoritmo de firma para JWT. Por defecto 'HS256'.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): Tiempo de expiración del token de acceso en minutos.
            Por defecto dura 7 días.
        ALLOWED_ORIGINS (list[str]): Lista de orígenes autorizados para CORS.
    """
    # Variables de Base de Datos
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # AÑADIDO: Por defecto asumimos que estamos en local
    POSTGRES_HOST: str = "localhost"

    # Variables de Seguridad JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # El token durará 7 días
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost"]

    @property
    def DATABASE_URL(self) -> str:
        """
        Construye la URL de conexión asíncrona para PostgreSQL.

        Returns:
            str: URL formateada para su uso con asyncpg y SQLAlchemy.
        """
        # AÑADIDO: Ahora usamos self.POSTGRES_HOST.
        # En Windows será 'localhost', en Docker será 'db'. ¡Magia pura!
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:5432/{self.POSTGRES_DB}"

    # AÑADIDO: extra="ignore" previene que Pydantic crashee si agregamos cosas al .env después
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Instanciamos las configuraciones para usarlas en toda la app
settings = Settings()