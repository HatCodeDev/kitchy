from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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

    # SMTP / email provider (required — fail loud at startup if missing)
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    MAIL_FROM: str

    # Password reset
    RESET_LINK_BASE_URL: str = "https://kitchy.vonlunant.site/reset-password"
    RESET_TOKEN_TTL_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        # AÑADIDO: Ahora usamos self.POSTGRES_HOST.
        # En Windows será 'localhost', en Docker será 'db'. ¡Magia pura!
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:5432/{self.POSTGRES_DB}"

    # AÑADIDO: extra="ignore" previene que Pydantic crashee si agregamos cosas al .env después
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# Instanciamos las configuraciones para usarlas en toda la app
settings = Settings()