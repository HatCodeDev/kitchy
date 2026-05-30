# Kitchy API - Motor de Gestión y Costeo Gastronómico

Un backend de alto rendimiento diseñado para empoderar a microemprendedores y creadores gastronómicos, optimizando la cadena de valor, controlando stocks en tiempo real y automatizando la planificación financiera de recetas y pedidos.

---

## Ruta Rápida de Inicio (Docker)
Si querés ver el backend corriendo en 2 minutos:

1. **Configurar Entorno**: Duplicar el archivo `.env.example` como `.env` (o usar el que ya está configurado para desarrollo local).
2. **Levantar Contenedores**:
   ```bash
   docker compose up --build -d
   ```
3. **Ejecutar Migraciones y Semilla**:
   ```bash
   # Correr migraciones de Alembic
   docker compose exec api alembic upgrade head
   
   # Opcional: Cargar base de datos con datos de prueba
   docker compose exec api python scripts/seed_db.py
   ```
4. **¡Listo!** Entrá a [http://localhost:3000/docs](http://localhost:3000/docs) para explorar la documentación interactiva y autogenerada de Swagger.

---

## Stack Tecnológico
| Componente | Tecnología | Razón / Detalle |
| :--- | :--- | :--- |
| **Framework Principal** | FastAPI (v0.110.0+) | Alto rendimiento asíncrono, tipado estricto con Python y generación automática de OpenAPI. |
| **Servidor ASGI** | Uvicorn (v0.29.0+) | Ejecución ultrarrápida del motor de FastAPI con soporte de recarga en caliente. |
| **Base de Datos** | PostgreSQL 15 (Alpine) | Motor relacional robusto, ACID-compliant y de excelente desempeño con contenedores livianos. |
| **ORM / Driver** | SQLAlchemy (v2.0.0+) + `asyncpg` | Acceso asíncrono completo al motor de base de datos para evitar bloqueos de I/O en peticiones concurrentes. |
| **Control de Migraciones** | Alembic (v1.13.0+) | Versionamiento declarativo e incremental del esquema de base de datos. |
| **Validación y Configuración**| Pydantic + `pydantic-settings` | Validación robusta de payloads en endpoints y parsing seguro del archivo de entorno `.env`. |
| **Seguridad y Criptografía** | PyJWT + Bcrypt (v3.2.2) | Hash asimétrico seguro para contraseñas de usuarios y tokens JWT firmados (Bearer) con expiración de 7 días. |
| **Rate Limiting** | SlowAPI (v0.1.9+) | Defensa activa contra ataques de fuerza bruta y abuso de cuota basada en tokens por IP/Ruta. |
| **Suite de Pruebas** | Pytest + `pytest-asyncio` + HTTPX | Pruebas de integración rápidas y aisladas a nivel transaccional (rollback automático en cada test). |

---

## Arquitectura y Funcionamiento Core

Kitchy está diseñado bajo patrones de **Clean Architecture** estructurados de forma modular y desacoplada.

### Organización del Repositorio
```
backend-kitchy/
├── alembic/                  # Scripts e historial de migraciones de la base de datos
├── app/                      # Código fuente del backend
│   ├── core/                 # Configuraciones base (BD, seguridad, CORS, rate limiting)
│   ├── jobs/                 # Tareas asíncronas en segundo plano (lifespan)
│   ├── models/               # Modelos declarativos de SQLAlchemy (ORM)
│   ├── routers/              # Controladores y endpoints REST modularizados
│   ├── schemas/              # Esquemas Pydantic para validación y serialización de datos
│   ├── services/             # Lógica de negocio pura (costeos, conversión, pedidos)
│   └── utils/                # Utilidades generales
├── scripts/                  # Scripts administrativos (seeding de datos, auto-generación de specs)
├── tests/                    # Suite completa de tests unitarios y de integración
├── Dockerfile                # Receta de construcción del contenedor de la API (Python Slim)
├── docker-compose.yml        # Orquestación local para desarrollo rápido (API + Postgres)
└── main.py                   # Inicialización y ciclo de vida (Lifespan) de FastAPI
```

### Mecanismos Clave del Negocio

1. **Multi-Tenancy por Aislamiento Lógico**:
   Para garantizar la privacidad y seguridad de la información, cada petición requiere un token JWT en las cabeceras. Las consultas a la base de datos se filtran rigurosamente mediante el `user_id` decodificado en el payload, asegurando que un usuario jamás acceda a los insumos, recetas o pedidos de otro.

2. **Motor de Costeo en Tiempo Real (`CostCalculationService`)**:
   Implementa las fórmulas culinarias exactas de la gastronomía profesional:
   * **Costo Neto de Insumos**: Traduce unidades usadas en recetas (ej. gramos) a la unidad de compra (ej. kilogramos) usando un robusto `UnitConversionService`.
   * **Gastos Ocultos Adicionales**: Aplica recargos configurables por empaque o energía (gas/electricidad) tanto por monto fijo como porcentual.
   * **Márgenes y Precio Sugerido**: Calcula el margen de contribución y sugiere precios finales con redondeo estándar ROUND_HALF_UP exacto para divisas.
   * **Suma 100% Asegurada**: El desglose porcentual calcula el último costo indirecto por diferencia para evitar errores por redondeo de mermas y asegurar que el gráfico sume exactamente 100%.

3. **Background Jobs asíncronos en el Lifespan**:
   En lugar de recurrir a dependencias pesadas como Celery o Redis, Kitchy aprovecha el ciclo de vida asíncrono de FastAPI. Al iniciar, levanta un bucle asíncrono asilado en background (`procesar_notificaciones_loop`) que consulta periódicamente notificaciones pendientes de despacho (alertas de stock bajo, confirmación de pedidos) y las procesa de manera no bloqueante.

4. **Testing Transaccional Autocontenido (`db_test`)**:
   La suite de pruebas utiliza fixtures en `tests/conftest.py` que inician una transacción real en la base de datos de test (`kitchy_test`) y ejecutan un **rollback automático** al terminar cada test. Esto permite que las pruebas corran con la velocidad de una DB en memoria, pero con la veracidad estructural de Postgres.

---

## Requisitos Previos
* **Docker** y **Docker Compose** instalados en tu máquina.
* **Git** para clonar el repositorio.
* *(Opcional)* Python 3.12 y PostgreSQL locales si decidís correrlo sin contenedores.

---

## Instrucciones Detalladas con Docker (Desarrollo)

### 1. Variables de Entorno (`.env`)
El archivo `.env` ya viene configurado con credenciales predeterminadas para desarrollo rápido. Si deseás personalizarlo, creá o editá el `.env` con las siguientes llaves:
```env
POSTGRES_USER=kitchy_admin
POSTGRES_PASSWORD=super_secret_password_123
POSTGRES_DB=kitchy_db
POSTGRES_HOST=db  # Importante: Dentro de la red de Docker debe ser 'db'
SECRET_KEY=kitchy_super_llave_maestra_secreta_2026_no_compartir
```

### 2. Levantando los Servicios
El orquestador de Docker levantará dos servicios:
* **`db`** (`postgres:15-alpine`): Con volumen persistente asignado y un mecanismo de `healthcheck` que avisa cuando está listo para aceptar conexiones.
* **`api`** (FastAPI): Construido a partir de la imagen ligera `python:3.12-slim` con recarga en caliente habilitada (`--reload`). Expone el puerto `8000` de forma interna y lo mapea al puerto **`3000`** en tu máquina local.

Ejecutá:
```bash
docker compose up -d
```

### 3. Migraciones del Esquema
Para aplicar la estructura de tablas inicial:
```bash
docker compose exec api alembic upgrade head
```

### 4. Alimentar Base de Datos (Seeding)
Kitchy incluye un script inteligente que puebla la base de datos con insumos, recetas y pedidos de prueba para que puedas explorar la API inmediatamente con un usuario demo:
```bash
docker compose exec api python scripts/seed_db.py
```

### 5. Ejecutar la Suite de Pruebas
Para correr toda la batería de tests dentro del entorno Dockerizado (usa una base de datos real aislada `kitchy_test`):
```bash
docker compose exec api pytest -v
```

---

## Guía de Instalación y Ejecución Local (Sin Docker)
Si preferís trabajar directamente sobre tu sistema operativo:

1. **Crear y activar entorno virtual**:
   ```bash
   python -m venv .venv
   # En Windows:
   .venv\Scripts\activate
   # En Unix/macOS:
   source .venv/bin/activate
   ```
2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Instancia local de Postgres**:
   Asegurate de tener corriendo Postgres localmente y de crear las bases de datos `kitchy_db` y `kitchy_test`. Ajustá tu `.env` para usar `localhost`:
   ```env
   POSTGRES_HOST=localhost
   ```
4. **Ejecutar migraciones locales**:
   ```bash
   alembic upgrade head
   ```
5. **Correr el servidor**:
   ```bash
   uvicorn main:app --reload
   ```
   *La API estará accesible localmente en [http://127.0.0.1:8000](http://127.0.0.1:8000).*

---

## Endpoints Clave
* **Swagger UI / Documentación interactiva**: `/docs`
* **Health Check**: `GET /`
* **Autenticación (`/api/v1/auth`)**: `/login` (emisión de JWT), `/register`.
* **Insumos (`/api/v1/insumos`)**: Catálogo culinario, stock mínimo, movimientos de inventario.
* **Recetas (`/api/v1/recetas`)**: Creación de recetas, mermas, cálculo automático de costo y sugerencia de precios.
* **Pedidos (`/api/v1/pedidos`)**: Gestión de órdenes, enlace de WhatsApp autogenerado para contacto directo, hoja de ruta de producción diaria y colisión de horarios.
* **Temporizadores (`/api/v1/temporizadores`)**: Control de tiempos de cocción críticos en tiempo real.
* **Puntos de Entrega (`/api/v1/puntos-entrega`)**: Puntos físicos/virtuales para entrega de pedidos.

---

¡Disfrutá desarrollando en Kitchy! 🍳 Si tenés dudas o necesitás asistencia, contactá al soporte tecnológico en `soporte@kitchy.com`.
